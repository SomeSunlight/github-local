from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import uuid
from dataclasses import dataclass
from pathlib import Path


CONFIG_DIR = ".github-local"
CONFIG_FILE = "config.json"
ISSUES_DIR = "issues"
CONFIG_SCHEMA = 2


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


def _git_layout_optional(start: Path) -> tuple[Path, Path, Path] | None:
    try:
        return _git_layout(start)
    except RepositoryError:
        return None


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
        "rerun issue init with --accepted-branch <branch>"
    )


def _legacy_repository_id(owner: str, name: str) -> str:
    digest = hashlib.sha256(f"{owner}/{name}".encode("utf-8")).hexdigest()[:16]
    return f"R_gl_legacy_{digest}"


def _read_config(path: Path) -> dict[str, object]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        schema = payload.get("schema")
        owner = str(payload["owner"]).strip()
        name = str(payload["repository"]).strip()
        if not owner or not name:
            raise RepositoryError(f"invalid repository identity in {path}")
        accepted = payload.get("accepted_branch")
        if accepted is not None and (not isinstance(accepted, str) or not accepted.strip()):
            raise RepositoryError(f"invalid accepted branch in {path}")

        if schema == 1:
            repository_id = _legacy_repository_id(owner, name)
        elif schema == CONFIG_SCHEMA:
            repository_id = str(payload["id"]).strip()
            if not repository_id:
                raise RepositoryError(f"invalid repository id in {path}")
        else:
            raise RepositoryError(f"unsupported config schema: {path}")
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        raise RepositoryError(f"invalid repository config: {path}") from exc

    result: dict[str, object] = {
        "schema": int(schema),
        "id": repository_id,
        "owner": owner,
        "repository": name,
    }
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


def _ancestors(start: Path):
    current = start.resolve()
    if current.is_file():
        current = current.parent
    while True:
        yield current
        if current.parent == current:
            break
        current = current.parent


def _relative_if_within(path: Path, parent: Path) -> Path | None:
    try:
        return path.resolve().relative_to(parent.resolve())
    except ValueError:
        return None


def _issue_location(start: Path) -> tuple[Path, Path, tuple[Path, Path, Path] | None]:
    requested = start.resolve()
    if requested.is_file():
        requested = requested.parent
    layout = _git_layout_optional(requested)

    for candidate in _ancestors(requested):
        physical_config = candidate / CONFIG_DIR / CONFIG_FILE
        if physical_config.is_file():
            return candidate, candidate, layout

        if layout is not None:
            git_root, primary, _common = layout
            relative = _relative_if_within(candidate, git_root)
            if relative is not None:
                canonical = (primary / relative).resolve()
                if (canonical / CONFIG_DIR / CONFIG_FILE).is_file():
                    return candidate, canonical, layout

    raise RepositoryError(
        f"no local Issue repository selected at {requested}; "
        "run 'github-local issue init' in the folder that should own Issues"
    )


def _canonical_init_root(root: Path) -> tuple[Path, Path, tuple[Path, Path, Path] | None]:
    local = root.resolve()
    if local.is_file():
        raise RepositoryError(f"Issue repository root must be a directory: {local}")
    if not local.exists():
        raise RepositoryError(f"Issue repository root does not exist: {local}")

    layout = _git_layout_optional(local)
    if layout is None:
        return local, local, None

    git_root, primary, _common = layout
    relative = _relative_if_within(local, git_root)
    if relative is None:
        return local, local, layout
    canonical = (primary / relative).resolve()
    canonical.mkdir(parents=True, exist_ok=True)
    return local, canonical, layout


def _git_exclude_patterns(primary: Path, issue_root: Path) -> tuple[str, str]:
    relative = issue_root.resolve().relative_to(primary.resolve())
    prefix = "" if str(relative) == "." else relative.as_posix().rstrip("/") + "/"
    return f"/{prefix}{ISSUES_DIR}/", f"/{prefix}{CONFIG_DIR}/"


def _ensure_excluded(common_dir: Path, primary: Path, issue_root: Path) -> None:
    exclude = common_dir / "info" / "exclude"
    exclude.parent.mkdir(parents=True, exist_ok=True)
    existing = exclude.read_text(encoding="utf-8") if exclude.exists() else ""
    lines = existing.splitlines()
    additions = [
        pattern
        for pattern in _git_exclude_patterns(primary, issue_root)
        if pattern not in lines
    ]
    if not additions:
        return
    prefix = existing
    if prefix and not prefix.endswith("\n"):
        prefix += "\n"
    exclude.write_text(
        prefix + "".join(pattern + "\n" for pattern in additions),
        encoding="utf-8",
        newline="\n",
    )


def _tracked_issue_paths(primary: Path, issue_root: Path) -> list[str]:
    relative = issue_root.resolve().relative_to(primary.resolve())
    target = (relative / ISSUES_DIR).as_posix()
    output = _git(primary, "ls-files", "--", target)
    return [line for line in output.splitlines() if line.strip()]


def _ensure_untracked_issue_store(primary: Path, issue_root: Path) -> None:
    tracked = _tracked_issue_paths(primary, issue_root)
    if not tracked:
        return
    preview = ", ".join(tracked[:3])
    if len(tracked) > 3:
        preview += f", ... ({len(tracked)} files)"
    raise RepositoryError(
        "local Issue repositories require issues/ to stay outside ordinary Git branch tracking; "
        f"tracked Issue path(s): {preview}. Remove them from the Git index explicitly, "
        "then rerun github-local."
    )


@dataclass(frozen=True, slots=True)
class Repository:
    root: Path
    workflow_root: Path
    owner: str
    name: str
    repository_id: str
    accepted_branch: str | None
    git_root: Path | None = None
    git_workflow_root: Path | None = None
    git_common_dir: Path | None = None

    @property
    def issues_dir(self) -> Path:
        return self.workflow_root / ISSUES_DIR

    @property
    def config_dir(self) -> Path:
        return self.workflow_root / CONFIG_DIR

    @property
    def config_path(self) -> Path:
        return self.config_dir / CONFIG_FILE

    @property
    def closing_state_path(self) -> Path:
        return self.config_dir / "closing-state.json"

    @property
    def issue_state_path(self) -> Path:
        return self.config_dir / "issue-state.json"

    @property
    def accepted_ref(self) -> str:
        if not self.accepted_branch:
            raise RepositoryError(
                f"local Issue repository {self.owner}/{self.name} is not associated with a Git accepted branch"
            )
        return f"refs/heads/{self.accepted_branch}"

    @property
    def has_git(self) -> bool:
        return self.git_root is not None and self.git_workflow_root is not None

    @property
    def is_git_root_repository(self) -> bool:
        return bool(
            self.has_git
            and self.workflow_root.resolve() == self.git_workflow_root.resolve()
        )

    def require_git(self) -> tuple[Path, Path]:
        if self.git_root is None or self.git_workflow_root is None:
            raise RepositoryError(
                f"local Issue repository {self.owner}/{self.name} is not inside a Git repository"
            )
        return self.git_root, self.git_workflow_root

    def accepted_head(self) -> str | None:
        if not self.has_git or not self.accepted_branch:
            return None
        return _git_optional(
            self.git_workflow_root,
            "rev-parse",
            "--verify",
            self.accepted_ref,
        )

    def is_ancestor(self, older: str, newer: str) -> bool:
        if not self.has_git:
            return False
        completed = _run_git(
            self.git_workflow_root, "merge-base", "--is-ancestor", older, newer
        )
        return completed.returncode == 0

    def accepted_commits(self, after: str | None, head: str) -> list[tuple[str, str]]:
        if not self.has_git:
            return []
        revision = f"{after}..{head}" if after else head
        output = _git_optional(
            self.git_workflow_root,
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
        owner: str = "local",
        name: str | None = None,
        accepted_branch: str | None = None,
    ) -> "Repository":
        local_root, workflow_root, layout = _canonical_init_root(root)
        config_path = workflow_root / CONFIG_DIR / CONFIG_FILE

        git_root = git_primary = common_dir = None
        if layout is not None:
            git_root, git_primary, common_dir = layout
            _ensure_untracked_issue_store(git_primary, workflow_root)
            _ensure_excluded(common_dir, git_primary, workflow_root)

        repository_name = (name or workflow_root.name).strip()
        repository_owner = owner.strip()
        if not repository_name or not repository_owner:
            raise RepositoryError("Issue repository owner and name must not be empty")

        if config_path.exists():
            existing = _read_config(config_path)
            if (
                str(existing["owner"]) != repository_owner
                or str(existing["repository"]) != repository_name
            ):
                raise RepositoryError(
                    f"already initialized as {existing['owner']}/{existing['repository']}: {workflow_root}"
                )
            repository_id = str(existing["id"])
            configured_branch = existing.get("accepted_branch")
            if accepted_branch and configured_branch and accepted_branch != configured_branch:
                raise RepositoryError(
                    f"already initialized with accepted branch {configured_branch!r}"
                )
            branch = str(configured_branch) if configured_branch else accepted_branch
            schema = int(existing["schema"])
        else:
            repository_id = f"R_gl_{uuid.uuid4().hex}"
            branch = accepted_branch
            schema = CONFIG_SCHEMA

        if branch is None and git_primary is not None:
            branch = _infer_accepted_branch(git_primary)
        if branch is not None and git_primary is None:
            raise RepositoryError("--accepted-branch requires a containing Git repository")

        if not config_path.exists():
            _write_config(
                config_path,
                {
                    "schema": CONFIG_SCHEMA,
                    "id": repository_id,
                    "owner": repository_owner,
                    "repository": repository_name,
                    **({"accepted_branch": branch} if branch else {}),
                },
            )
        elif schema == CONFIG_SCHEMA:
            # Existing schema-2 repositories are already canonical; do not rewrite them.
            pass

        (workflow_root / ISSUES_DIR).mkdir(parents=True, exist_ok=True)
        (workflow_root / CONFIG_DIR / "locks").mkdir(parents=True, exist_ok=True)

        closing_state = workflow_root / CONFIG_DIR / "closing-state.json"
        if branch and git_primary is not None and not closing_state.exists():
            initial_head = _git_optional(
                git_primary, "rev-parse", "--verify", f"refs/heads/{branch}"
            )
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

        return cls(
            root=local_root,
            workflow_root=workflow_root,
            owner=repository_owner,
            name=repository_name,
            repository_id=repository_id,
            accepted_branch=branch,
            git_root=git_root,
            git_workflow_root=git_primary,
            git_common_dir=common_dir,
        )

    @classmethod
    def discover(cls, start: Path | None = None) -> "Repository":
        local_root, workflow_root, layout = _issue_location(start or Path.cwd())
        payload = _read_config(workflow_root / CONFIG_DIR / CONFIG_FILE)

        git_root = git_primary = common_dir = None
        if layout is not None:
            git_root, git_primary, common_dir = layout
            relative = _relative_if_within(workflow_root, git_primary)
            if relative is not None:
                _ensure_untracked_issue_store(git_primary, workflow_root)
                _ensure_excluded(common_dir, git_primary, workflow_root)

        (workflow_root / ISSUES_DIR).mkdir(parents=True, exist_ok=True)
        (workflow_root / CONFIG_DIR / "locks").mkdir(parents=True, exist_ok=True)

        branch = (
            str(payload["accepted_branch"])
            if payload.get("accepted_branch") is not None
            else (_infer_accepted_branch(git_primary) if git_primary is not None else None)
        )

        return cls(
            root=local_root,
            workflow_root=workflow_root,
            owner=str(payload["owner"]),
            name=str(payload["repository"]),
            repository_id=str(payload["id"]),
            accepted_branch=branch,
            git_root=git_root,
            git_workflow_root=git_primary,
            git_common_dir=common_dir,
        )

    def deinitialize(self) -> None:
        if self.issues_dir.exists() and any(self.issues_dir.iterdir()):
            raise RepositoryError(
                f"local Issue repository {self.owner}/{self.name} still contains Issues; "
                "delete them explicitly before deinitializing"
            )
        if self.issues_dir.exists():
            self.issues_dir.rmdir()
        if self.config_dir.exists():
            shutil.rmtree(self.config_dir)
