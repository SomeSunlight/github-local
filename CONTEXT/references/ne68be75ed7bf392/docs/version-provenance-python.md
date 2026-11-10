# Python runtime version provenance

Use this pattern when a Python CLI is actively tested from editable Git checkouts or installed from Git URLs using uv/pip, and the release version alone is too ambiguous.

The goal is to keep two identities separate:

- **Release version** — the stable package/release baseline, for example `0.10.0`.
- **Development provenance** — the exact checkout or installed Git revision currently executing, for example `issue-79-version-provenance@23d1c69` or `main@f2d3679, dirty`.

The commit SHA is the immutable identity. The branch/ref is only human orientation.

## Recommended output

Source/editable checkout:

```text
toolname 0.10.0 (feature/my-change@abc1234)
```

Dirty checkout:

```text
toolname 0.10.0 (feature/my-change@abc1234, dirty)
```

Detached checkout, for example in CI:

```text
toolname 0.10.0 (detached@abc1234)
```

Installed Git-URL tool from uv/pip, resolved at a specific commit (PEP 610):

```text
toolname 0.10.0 (main@abc1234)
```

Ordinary wheel/release artifact without Git metadata:

```text
toolname 0.10.0
```

Do not encode the branch into the release version and do not bump the release version merely because another development branch exists.

## Keep one release-version source

For a normal `pyproject.toml` project, keep the canonical release version there:

```toml
[project]
name = "toolname"
version = "0.10.0"
```

Do not duplicate the literal version in `version.py`. In a source/editable checkout, read `pyproject.toml` so a pulled version change is visible immediately without reinstalling. For an installed artifact, fall back to `importlib.metadata.version()`.

## Small dependency-free implementation

Adapt the distribution name and project-root detection to the project:

```python
from __future__ import annotations

import subprocess
import tomllib
from importlib.metadata import PackageNotFoundError, version as distribution_version
from pathlib import Path

_DISTRIBUTION_NAME = "toolname"


def _project_root(start: Path | None = None) -> Path | None:
    current = (start or Path(__file__)).resolve()
    if current.is_file():
        current = current.parent

    for candidate in (current, *current.parents):
        pyproject = candidate / "pyproject.toml"
        if not pyproject.is_file():
            continue
        try:
            project = tomllib.loads(pyproject.read_text(encoding="utf-8")).get("project", {})
        except (OSError, tomllib.TOMLDecodeError):
            continue
        if project.get("name") == _DISTRIBUTION_NAME:
            return candidate
    return None


def _pyproject_version(root: Path) -> str | None:
    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8")).get("project", {})
    except (OSError, tomllib.TOMLDecodeError):
        return None

    value = project.get("version")
    return value if isinstance(value, str) and value else None


def release_version(project_root: Path | None = None) -> str:
    root = project_root or _project_root()
    if root is not None:
        value = _pyproject_version(root)
        if value is not None:
            return value

    try:
        return distribution_version(_DISTRIBUTION_NAME)
    except PackageNotFoundError:
        return "unknown"


def _git(root: Path, *args: str) -> str | None:
    try:
        completed = subprocess.run(
            ["git", "-C", str(root), *args],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=2,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None

    if completed.returncode != 0:
        return None
    return completed.stdout.strip()


def git_provenance(project_root: Path | None = None) -> str | None:
    root = project_root or _project_root()
    if root is None or not (root / ".git").exists():
        return None

    commit = _git(root, "rev-parse", "--short=7", "HEAD")
    if not commit:
        return None

    branch = _git(root, "symbolic-ref", "--quiet", "--short", "HEAD") or "detached"
    status = _git(root, "status", "--porcelain", "--untracked-files=normal")

    result = f"{branch}@{commit}"
    if status:
        result += ", dirty"
    return result


def display_version(project_root: Path | None = None) -> str:
    release = release_version(project_root)
    provenance = git_provenance(project_root)
    return f"{release} ({provenance})" if provenance else release


__version__ = release_version()
```

This intentionally shells out to Git only when version/provenance is requested. Normal program operations should not pay that cost. It handles editable checkouts; for a uv Git-URL install, extend it with the PEP 610 pattern below.

## argparse integration

A custom action lets `--version` compute the checkout identity at invocation time instead of freezing it when the parser is constructed or the package is installed:

```python
class _RuntimeVersionAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None) -> None:
        parser._print_message(f"{parser.prog} {display_version()}\n", sys.stdout)
        parser.exit()


parser.add_argument("--version", action=_RuntimeVersionAction, nargs=0)
```

Keep `--version` on stdout, matching normal CLI expectations.


## Git-URL installs: exact installed provenance (PEP 610)

A uv/pip Git-URL installation normally has no accessible .git checkout. For this case the checkout-only example above must be extended. The sibling tool [github-local](https://github.com/SomeSunlight/github-local/blob/main/src/github_local/version.py) already implements the successful pattern:

1. Read importlib.metadata.distribution("toolname").read_text("direct_url.json").
2. Require valid JSON with vcs_info.vcs == "git", a nonempty repository URL, and a validated immutable vcs_info.commit_id (40/64 hexadecimal digits). The resolved commit, not the requested branch name, identifies the installed bytes.
3. Use vcs_info.requested_revision only as human-readable orientation (branch/tag). Use detached when the requested ref is itself a hexadecimal SHA, or git@sha when no usable requested ref is present.
4. Prefer Git checkout branch/HEAD/dirty state if executing an editable source checkout. Ordinary wheels without valid Git metadata continue to return the plain release version. Never inspect the caller's current working directory to guess the installed revision.
5. Keep --version offline and on stdout.

Small independent extractor (adapt the distribution name):

~~~python
import json
import re
from importlib.metadata import PackageNotFoundError, distribution

def installed_git_origin(distribution_name: str):
    try:
        raw = distribution(distribution_name).read_text("direct_url.json")
    except (PackageNotFoundError, OSError):
        return None
    if not raw:
        return None
    try:
        record = json.loads(raw)
        info = record["vcs_info"]
        url, commit = record["url"], info["commit_id"]
        if info["vcs"] != "git" or not isinstance(url, str):
            return None
        if not isinstance(commit, str) or not re.fullmatch(r"[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", commit):
            return None
        return url, commit.lower(), info.get("requested_revision")
    except (TypeError, ValueError, KeyError, AttributeError):
        return None
~~~

## Explicit, read-only remote version check

For fast-evolving executable tools, make the network operation a deliberate separate command:

~~~text
toolname --version
# toolname 0.10.0 (main@abc1234)    ← offline

toolname version check
# Installed: toolname 0.10.0 (main@abc1234)
# Remote:    main@def5678
# Status:    behind

toolname version check --branch main
# Select a branch explicitly for detached/ambiguous installations
~~~

The reusable contract:

1. --version must remain completely offline, report only installed revision metadata, and must never check GitHub automatically.
2. version check may query the original public GitHub repository only after the operator requests it; it must not install, pull, fetch, mutate a working tree, or silently update code.
3. Determine the exact executing commit from Git or PEP 610. Identify the tracking branch from the checkout or requested Git revision. When a VCS install has no requested branch, obtain the repository default branch explicitly; for ambiguous/pinned refs, allow --branch. Do not guess where an arbitrary wheel came from.
4. Query GitHub's HTTPS REST endpoints with timeouts and without transmitting credentials: GET /repos/{owner}/{repo}/branches/{branch}; if commit SHAs differ, GET /repos/{owner}/{repo}/compare/{installed}...{remote}. Compare immutable SHAs and ancestry, not release version strings. GitHub's response status ahead means the remote head is ahead (the installed revision is behind); behind means installed ahead; diverged means divergent histories. Identical SHAs are up to date.
5. On unavailable/unsupported/private remotes, no provenance, malformed metadata, missing branches, rate limits, network failure, or incomparable commits, report **unknown**. Never call an unverified installation up to date.
6. Script-friendly exit codes: 0 equal, 1 known difference (behind/ahead/diverged), 2 unknown. Make no network request when displaying --version. Do not leak credentials or tokens to a derived URL.

After publication, the implementation reference is [ContextCanon version_check.py](https://github.com/SomeSunlight/context-canon/blob/main/src/contextcanon/version_check.py), building on [github-local version.py](https://github.com/SomeSunlight/github-local/blob/main/src/github_local/version.py).

## Additional test expectations

Test Git-URL installed metadata and malformed/non-Git fallbacks; prove --version makes no network calls; exercise explicit branch selection, missing branch/default lookup, the ahead/behind comparison direction, divergent history, no provenance, timeout/HTTP errors and fail-closed unknown. Mock HTTP responses; an automated unit suite must not depend on the network.


## Focused tests

At minimum verify:

1. `release_version()` reads the value from the checkout's `pyproject.toml`.
2. A non-Git source tree returns the plain release version.
3. A temporary Git repository returns `branch@short-sha`.
4. A modified tracked file adds `, dirty`.
5. Detached HEAD reports `detached@short-sha`.
6. CLI `--version` exits successfully and writes to stdout.

Prefer creating a real temporary Git repository in the test rather than mocking Git output; the behavior being tested is small and deterministic.

## When not to create a shared library

For this pattern the code is deliberately small and project integration differs in distribution name, root detection, CLI framework, and test layout. Copying/adapting the reference is usually simpler than adding a runtime dependency.

A shared library becomes worthwhile only if several projects need materially more behavior such as tag-derived release versions, build metadata injection, non-Git VCS support, or a centrally maintained compatibility contract.
