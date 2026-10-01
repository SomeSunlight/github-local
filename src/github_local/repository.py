from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


LEGACY_CONFIG_DIR = ".github-local"
CONFIG_FILE = "config.json"
SHARED_STATE_DIR = "github-local"
ISSUES_EXCLUDE = "/issues/"


class RepositoryError(RuntimeError):
    pass


def _run_git(cwd: Path, *args: str) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["git", "-C", str(cwd), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RepositoryError(f"unable to inspect Git repository at {cwd}") from exc


def _git(cwd: Path, *args: str) -> str:
    completed = _run_git(cwd, *args)
    if completed.returncode != 0:
        detail = completed.stderr.strip() or completed.stdout.strip() or "Git command failed"
        raise RepositoryError(detail)
    return completed.stdout.strip()


def _git_optional(cwd: Path, *args: str) -> str | None:
    completed = _run_git(cwd, *args)
    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def _git_layout(start: Path) -> tuple[Path, Path, Path]:
    current = start.resolve()
    if current.is_file():
        current = current.parent

    top = Path(_git(current, "rev-parse", "--show-toplevel")).resolve()
    common_raw = _git(top, "rev-parse", "--git-common-dir")
    common = Path(common_raw)
    if not common.is_absolute():
        common = (top / common).resolve()
    else:
        common = common.resolve()

    listing = _git(top, "worktree", "list", "--porcelain").splitlines()
    first = next((line for line in listing if line.startswith("worktree ")), None)
    if first is None:
        raise RepositoryError(f"unable to identify primary Git worktree from {top}")
    primary = Path(first.removeprefix("worktree ")).resolve()
    return top, primary, common


def _infer_accepted_branch(worktree: Path) -> str:
    remote_head = _git_optional(
        worktree, "symbolic-ref", "--quiet", "--short", "refs/remotes/origin/HEAD"
    )
    if remote_head and "/" in remote_head:
        return remote_head.split("/", 1)[1]

    branch = _git_optional(worktree, "symbolic-ref", "--quiet", "--short", "HEAD")
    if branch:
        return branch

    raise RepositoryError(
        "cannot infer the accepted branch from detached HEAD; "
        "rerun github-local init with --accepted-branch <branch>"
    )


def _read_config(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema") != 1:
            raise RepositoryError(f"unsupported config schema: {path}")
        owner = str(payload["owner"])
        name = str(payload["repository"])
        accepted = payload.get("accepted_branch")
        if accepted is not None and (not isinstance(accepted, str) or not accepted.strip()):
            raise RepositoryError(f"invalid accepted branch in {path}")
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RepositoryError(f"invalid repository config: {path}") from exc

    result: dict[str, object] = {"schema": 1, "owner": owner, "repository": name}
    if accepted is not None:
        result["accepted_branch"] = accepted.strip()
    return result


def _write_config(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _ensure_issues_excluded(common_dir: Path) -> None:
    exclude = common_dir / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    lines = existing.splitlines()
    if ISSUES_EXCLUDE in lines:
        return
    prefix = existing
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    exclude.write_text(prefix + ISSUES_EXCLUDE + "\n", encoding="utf-8", newline="\n")


def _tracked_issue_paths(worktree: Path) -> list[str]:
    output = _git(worktree, "ls-files", "--", "issues")
    return [line for line in output.splitlines() if line.strip()]


def _ensure_untracked_issue_store(worktree: Path) -> None:
    tracked = _tracked_issue_paths(worktree)
    if not tracked:
        return
    preview = ", ".join(tracked[:3])
    if len(tracked) > 3:
        preview += f", ... ({len(tracked)} files)"
    raise RepositoryError(
        "project-wide Issue state requires issues/ to be outside ordinary Git branch tracking; "
        f"tracked Issue path(s): {preview}. "
        "Migrate explicitly with 'git rm --cached -r issues', commit that code-state change, "
        "then rerun github-local."
    )


@dataclass(frozen=True, slots=True)
class Repository:
    root: Path
    workflow_root: Path
    git_common_dir: Path
    owner: str
    name: str
    accepted_branch: str

    @property
    def issues_dir(self) -> Path:
        return self.workflow_root / "issues"

    @property
    def config_dir(self) -> Path:
        return self.git_common_dir / SHARED_STATE_DIR

    @property
    def config_path(self) -> Path:
        return self.config_dir / CONFIG_FILE

    @property
    def closing_state_path(self) -> Path:
        return self.config_dir / "closing-state.json"

    @property
    def accepted_ref(self) -> str:
        return f"refs/heads/{self.accepted_branch}"

    def accepted_head(self) -> str | None:
        return _git_optional(self.workflow_root, "rev-parse", "--verify", self.accepted_ref)

    def is_ancestor(self, older: str, newer: str) -> bool:
        completed = _run_git(
            self.workflow_root, "merge-base", "--is-ancestor", older, newer
        )
        return completed.returncode == 0

    def accepted_commits(self, after: str | None, head: str) -> list[tuple[str, str]]:
        revision = f"{after}..{head}" if after else head
        output = _git_optional(
            self.workflow_root,
            "log",
            "--reverse",
            "--format=%H%x00%B%x00",
            revision,
        )
        if not output:
            return []

        parts = output.split("\x00")
        commits: list[tuple[str, str]] = []
        for index in range(0, len(parts) - 1, 2):
            sha = parts[index].strip()
            message = parts[index + 1].strip()
            if sha:
                commits.append((sha, message))
        return commits

    @classmethod
    def initialize(
        cls,
        root: Path,
        *,
        owner: str,
        name: str,
        accepted_branch: str | None = None,
    ) -> "Repository":
        root, workflow_root, common_dir = _git_layout(root)
        _ensure_untracked_issue_store(workflow_root)

        config_path = common_dir / SHARED_STATE_DIR / CONFIG_FILE
        existing: dict[str, object] | None = None

        if config_path.exists():
            existing = _read_config(config_path)
        else:
            legacy_path = workflow_root / LEGACY_CONFIG_DIR / CONFIG_FILE
            if legacy_path.exists():
                existing = _read_config(legacy_path)

        if existing is not None:
            identity = {"schema": 1, "owner": owner, "repository": name}
            if any(existing.get(key) != value for key, value in identity.items()):
                raise RepositoryError(
                    f"already initialized with different configuration: {config_path}"
                )
            configured_branch = existing.get("accepted_branch")
            if accepted_branch and configured_branch and accepted_branch != configured_branch:
                raise RepositoryError(
                    f"already initialized with accepted branch {configured_branch!r}"
                )
            branch = str(configured_branch or accepted_branch or _infer_accepted_branch(workflow_root))
        else:
            branch = accepted_branch or _infer_accepted_branch(workflow_root)

        payload = {
            "schema": 1,
            "owner": owner,
            "repository": name,
            "accepted_branch": branch,
        }
        _write_config(config_path, payload)

        closing_state = common_dir / SHARED_STATE_DIR / "closing-state.json"
        if not closing_state.exists():
            initial_head = _git_optional(
                workflow_root, "rev-parse", "--verify", f"refs/heads/{branch}"
            )
            closing_state.parent.mkdir(parents=True, exist_ok=True)
            closing_state.write_text(
                json.dumps(
                    {
                        "schema": 1,
                        "accepted_branch": branch,
                        "cursor": initial_head,
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
                newline="\n",
            )

        _ensure_issues_excluded(common_dir)
        (common_dir / SHARED_STATE_DIR / "locks").mkdir(parents=True, exist_ok=True)
        (workflow_root / "issues").mkdir(exist_ok=True)
        return cls(
            root=root,
            workflow_root=workflow_root,
            git_common_dir=common_dir,
            owner=owner,
            name=name,
            accepted_branch=branch,
        )

    @classmethod
    def discover(cls, start: Path | None = None) -> "Repository":
        try:
            root, workflow_root, common_dir = _git_layout(start or Path.cwd())
        except RepositoryError as exc:
            raise RepositoryError(
                "github.local is not initialized here; run github-local init at the Git root"
            ) from exc

        config_path = common_dir / SHARED_STATE_DIR / CONFIG_FILE
        if config_path.exists():
            payload = _read_config(config_path)
        else:
            legacy_candidates = [
                workflow_root / LEGACY_CONFIG_DIR / CONFIG_FILE,
                root / LEGACY_CONFIG_DIR / CONFIG_FILE,
            ]
            legacy_path = next((path for path in legacy_candidates if path.exists()), None)
            if legacy_path is None:
                raise RepositoryError(
                    "github.local is not initialized here; run github-local init at the Git root"
                )
            payload = _read_config(legacy_path)

        branch = str(payload.get("accepted_branch") or _infer_accepted_branch(workflow_root))
        normalized = {
            "schema": 1,
            "owner": str(payload["owner"]),
            "repository": str(payload["repository"]),
            "accepted_branch": branch,
        }
        if payload != normalized or not config_path.exists():
            _write_config(config_path, normalized)

        _ensure_untracked_issue_store(workflow_root)
        _ensure_issues_excluded(common_dir)
        (common_dir / SHARED_STATE_DIR / "locks").mkdir(parents=True, exist_ok=True)
        (workflow_root / "issues").mkdir(exist_ok=True)
        return cls(
            root=root,
            workflow_root=workflow_root,
            git_common_dir=common_dir,
            owner=str(normalized["owner"]),
            name=str(normalized["repository"]),
            accepted_branch=branch,
        )
