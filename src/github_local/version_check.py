"""Explicit, read-only GitHub comparison of the executing CLI against a branch.

Only the 'version check' CLI path accesses the network. No installation,
fetch, or mutation is performed. Unknown state never implies up-to-date.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from .version import _git, _project_root, display_version, installed_git_origin


@dataclass(frozen=True)
class InstallIdentity:
    url: str
    commit: str
    branch: str | None


@dataclass(frozen=True)
class VersionCheck:
    installed: str
    remote: str
    status: str
    detail: str = ""

    @property
    def exit_code(self) -> int:
        # 0: equal; 1: known difference; 2: cannot make a reliable comparison.
        if self.status == "up to date":
            return 0
        if self.status == "unknown":
            return 2
        return 1

    def render(self) -> str:
        reason = f" ({self.detail})" if self.detail else ""
        return f"Installed: {self.installed}\nRemote:    {self.remote}\nStatus:    {self.status}{reason}\n"


def _identity(project_root: Path | None = None) -> InstallIdentity | None:
    root = project_root or _project_root()
    if root is not None and (root / ".git").exists():
        commit = _git(root, "rev-parse", "HEAD")
        if not commit or not re.fullmatch(r"[a-fA-F0-9]{40}|[a-fA-F0-9]{64}", commit):
            return None
        url = _git(root, "remote", "get-url", "origin")
        if not url:
            return None
        branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD")
        return InstallIdentity(url, commit.lower(), branch)

    if project_root is not None:
        return None
    installed = installed_git_origin()
    if installed is None:
        return None
    url, commit, revision = installed
    if revision:
        revision = revision.removeprefix("refs/heads/").removeprefix("refs/tags/")
        if revision == "git" or re.fullmatch(r"[a-fA-F0-9]{7,64}", revision):
            revision = None
    return InstallIdentity(url, commit, revision)


def _github_coordinates(source: str) -> tuple[str, str] | None:
    """Accept only public github.com repository URLs; never send credentials."""
    if source.startswith("git@github.com:"):
        path = source.removeprefix("git@github.com:")
    else:
        try:
            parsed = urlsplit(source)
            if parsed.hostname != "github.com" or parsed.password or parsed.username not in (None, "git"):
                return None
            if parsed.scheme not in ("https", "ssh"):
                return None
            if parsed.query or parsed.fragment or parsed.port not in (None, 22, 443):
                return None
            path = parsed.path.lstrip("/")
        except ValueError:
            return None
    path = path.removesuffix(".git").strip("/")
    parts = path.split("/")
    if len(parts) != 2 or not all(re.fullmatch(r"[a-zA-Z0-9_.-]+", p) for p in parts):
        return None
    return parts[0], parts[1]


def _read_json(url: str) -> dict:
    """Make one bounded HTTPS read; malformed / unavailable responses are unknown."""
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "github-local-version-check",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urlopen(request, timeout=5) as response:
        payload = response.read(2_000_001)
    if len(payload) > 2_000_000:
        raise ValueError("GitHub response too large")
    data = json.loads(payload)
    if not isinstance(data, dict):
        raise ValueError("Unexpected GitHub response")
    return data


def check_remote_version(
    *, branch: str | None = None, project_root: Path | None = None,
) -> VersionCheck:
    """Compare the executing github-local commit against its public GitHub branch."""
    installed = f"github-local {display_version(project_root)}"
    origin = _identity(project_root)
    if origin is None:
        return VersionCheck(installed, "unavailable", "unknown", "no Git origin/commit metadata")
    repository = _github_coordinates(origin.url)
    if repository is None:
        return VersionCheck(installed, "unavailable", "unknown", "not a supported public GitHub URL")
    if branch is not None and (not branch or len(branch) > 200 or any(c in branch for c in "\r\n\t")):
        return VersionCheck(installed, "unavailable", "unknown", "invalid branch")
    owner, name = repository
    # This command checks *github-local itself*. It must never silently contact
    # a private/foreign local Issue repository or an arbitrary Git remote.
    if (owner.lower(), name.lower()) != ("somesunlight", "github-local"):
        return VersionCheck(installed, "unavailable", "unknown", "origin is not the official github-local repository")
    api = "https://api.github.com/repos/SomeSunlight/github-local"
    target_branch = branch or origin.branch
    target = "unavailable"

    try:
        if not target_branch:
            metadata = _read_json(api)
            target_branch = metadata.get("default_branch")
            if not isinstance(target_branch, str) or not target_branch:
                raise ValueError("Missing default branch")
        target = f"{target_branch}@unknown"
        info = _read_json(f"{api}/branches/{quote(target_branch, safe='')}")
        commit = info["commit"]["sha"]
        if not isinstance(commit, str) or not re.fullmatch(r"[a-fA-F0-9]{40}|[a-fA-F0-9]{64}", commit):
            raise ValueError("Invalid remote commit")
        commit = commit.lower()
        target = f"{target_branch}@{commit[:7]}"
        if commit == origin.commit:
            return VersionCheck(installed, target, "up to date")

        comparison = _read_json(f"{api}/compare/{origin.commit}...{commit}?per_page=1")
        relation = comparison.get("status")
        # GitHub's compare is 'base...head': head=remote, base=installed.
        statuses = {
            "identical": "up to date",
            "ahead": "behind",
            "behind": "ahead",
            "diverged": "diverged",
        }
        if relation not in statuses:
            raise ValueError("Unknown Git history relationship")
        return VersionCheck(installed, target, statuses[relation])
    except (OSError, ValueError, KeyError, TypeError) as exc:
        return VersionCheck(installed, target, "unknown", f"remote comparison unavailable ({type(exc).__name__})")
