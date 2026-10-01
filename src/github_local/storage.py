from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
import time
import unicodedata
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Iterable

from .models import Issue, IssueComment
from .repository import Repository


ISSUE_RE = re.compile(r"^(?P<number>[0-9]{4,})-(?P<slug>.+)\.md$")
CLOSING_RE = re.compile(
    r"\b(?:fix(?:e[sd])?|close[sd]?|resolve[sd]?)\s+#(?P<number>[0-9]+)\b",
    re.IGNORECASE,
)
QUALIFIED_CLOSING_RE = re.compile(
    r"\b(?:fix(?:e[sd])?|close[sd]?|resolve[sd]?)\s+"
    r"(?P<owner>[A-Za-z0-9_.-]+)/(?P<repo>[A-Za-z0-9_.-]+)#(?P<number>[0-9]+)\b",
    re.IGNORECASE,
)
WINDOWS_RESERVED = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}


class StorageError(RuntimeError):
    pass


class IssueNotFound(StorageError):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def normalize_labels(values: Iterable[str] | None) -> tuple[str, ...]:
    labels: list[str] = []
    seen: set[str] = set()
    source = (values,) if isinstance(values, str) else (values or ())
    for raw in source:
        for part in raw.split(","):
            label = part.strip()
            if not label:
                raise StorageError("Issue label must not be empty")
            key = label.casefold()
            if key not in seen:
                seen.add(key)
                labels.append(label)
    return tuple(labels)


def slugify(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-.")
    slug = slug[:80].rstrip("-.") or "issue"
    if slug.upper() in WINDOWS_RESERVED:
        slug = f"issue-{slug}"
    return slug


def stable_issue_id(repository_id: str, number: int) -> str:
    digest = hashlib.sha256(f"{repository_id}#{number}".encode("utf-8")).hexdigest()[:16]
    return f"I_gl_{digest}"


class FileLock(AbstractContextManager["FileLock"]):
    def __init__(self, path: Path, timeout: float = 10.0) -> None:
        self.path = path
        self.timeout = timeout
        self._file = None

    def __enter__(self) -> "FileLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._file = self.path.open("a+b")
        self._file.seek(0, os.SEEK_END)
        if self._file.tell() == 0:
            self._file.write(b"0")
            self._file.flush()
        self._file.seek(0)
        deadline = time.monotonic() + self.timeout
        while True:
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(self._file.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(self._file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                return self
            except OSError as exc:
                if time.monotonic() >= deadline:
                    self._file.close()
                    self._file = None
                    raise StorageError(f"timed out waiting for Issue lock: {self.path}") from exc
                time.sleep(0.025)

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._file is None:
            return
        try:
            self._file.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(self._file.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl
                fcntl.flock(self._file.fileno(), fcntl.LOCK_UN)
        finally:
            self._file.close()
            self._file = None


class IssueStore:
    def __init__(self, repository: Repository, *, clock: Callable[[], str] = _utc_now) -> None:
        self.repository = repository
        self.clock = clock

    @property
    def _lock_path(self) -> Path:
        return self.repository.config_dir / "locks" / "issues.lock"

    def create(
        self,
        title: str,
        body: str = "",
        *,
        labels: Iterable[str] | None = None,
    ) -> Issue:
        title = title.strip()
        if not title:
            raise StorageError("Issue title must not be empty")
        with FileLock(self._lock_path):
            number = self._next_number()
            now = self.clock()
            issue_id = stable_issue_id(self.repository.repository_id, number)
            filename = f"{number:04d}-{slugify(title)}.md"
            target = self.repository.issues_dir / filename
            metadata = {
                "github-local": {
                    "schema": 1,
                    "id": issue_id,
                    "number": number,
                    "state": "OPEN",
                    "labels": list(normalize_labels(labels)),
                    "created_at": now,
                    "updated_at": now,
                }
            }
            self._write_issue(target, metadata, title, body, new=True)
            return self._parse(target)

    def list(
        self,
        *,
        state: str | None = None,
        labels: Iterable[str] | None = None,
        search: str | None = None,
    ) -> list[Issue]:
        wanted = state.upper() if state else None
        if wanted not in (None, "OPEN", "CLOSED"):
            raise StorageError(f"unsupported Issue state filter: {state}")
        wanted_labels = tuple(label.casefold() for label in normalize_labels(labels))
        query = search.casefold().strip() if search else None
        issues: list[Issue] = []
        for path in sorted(self.repository.issues_dir.glob("*.md")):
            if ISSUE_RE.match(path.name):
                issue = self._parse(path)
                if wanted is not None and issue.state != wanted:
                    continue
                issue_labels = {label.casefold() for label in issue.labels}
                if any(label not in issue_labels for label in wanted_labels):
                    continue
                if query:
                    haystack = "\n".join((issue.title, issue.body, *issue.labels)).casefold()
                    if query not in haystack:
                        continue
                issues.append(issue)
        return sorted(issues, key=lambda i: i.number)

    def get(self, number: int) -> Issue:
        return self._parse(self._issue_path(number))

    def count(self) -> int:
        return len(self.list())

    def delete(self, number: int) -> None:
        with FileLock(self._lock_path):
            path = self._issue_path(number)
            path.unlink()
            comments = self.repository.issues_dir / "comments" / f"{number:04d}"
            if comments.exists():
                shutil.rmtree(comments)
            comments_root = self.repository.issues_dir / "comments"
            if comments_root.exists() and not any(comments_root.iterdir()):
                comments_root.rmdir()

    def delete_all(self) -> int:
        with FileLock(self._lock_path):
            count = sum(
                1
                for path in self.repository.issues_dir.glob("*.md")
                if ISSUE_RE.match(path.name)
            )
            if self.repository.issues_dir.exists():
                shutil.rmtree(self.repository.issues_dir)
            self.repository.issues_dir.mkdir(parents=True, exist_ok=True)
            return count

    def close(self, number: int) -> Issue:
        with FileLock(self._lock_path):
            path = self._issue_path(number)
            metadata, title, body = self._read_issue(path)
            self._set_state(metadata, "CLOSED", closed_by="manual")
            self._write_issue(path, metadata, title, body)
            return self._parse(path)

    def reopen(self, number: int) -> Issue:
        with FileLock(self._lock_path):
            path = self._issue_path(number)
            metadata, title, body = self._read_issue(path)
            self._set_state(metadata, "OPEN")
            self._write_issue(path, metadata, title, body)
            return self._parse(path)

    def edit(
        self,
        number: int,
        *,
        title: str | None = None,
        body: str | None = None,
        add_labels: Iterable[str] | None = None,
        remove_labels: Iterable[str] | None = None,
    ) -> Issue:
        if title is None and body is None and add_labels is None and remove_labels is None:
            raise StorageError(
                "issue edit requires --title, --body, --body-file, --add-label, or --remove-label"
            )
        with FileLock(self._lock_path):
            path = self._issue_path(number)
            metadata, old_title, old_body = self._read_issue(path)
            new_title = old_title if title is None else title.strip()
            if not new_title:
                raise StorageError("Issue title must not be empty")
            new_body = old_body if body is None else body
            issue_meta = metadata["github-local"]
            current_labels = normalize_labels(issue_meta.get("labels", []))
            removed = {label.casefold() for label in normalize_labels(remove_labels)}
            kept = [label for label in current_labels if label.casefold() not in removed]
            existing = {label.casefold() for label in kept}
            for label in normalize_labels(add_labels):
                if label.casefold() not in existing:
                    existing.add(label.casefold())
                    kept.append(label)
            issue_meta["labels"] = kept
            issue_meta["updated_at"] = self.clock()

            new_path = self.repository.issues_dir / f"{number:04d}-{slugify(new_title)}.md"
            if new_path != path and new_path.exists():
                raise StorageError(f"refusing to overwrite existing Issue file: {new_path}")
            self._write_issue(new_path, metadata, new_title, new_body, new=new_path != path)
            if new_path != path:
                path.unlink()
            return self._parse(new_path)

    def comment(self, number: int, body: str) -> IssueComment:
        clean = body.rstrip()
        if not clean:
            raise StorageError("Issue comment must not be empty")
        with FileLock(self._lock_path):
            self._issue_path(number)
            directory = self.repository.issues_dir / "comments" / f"{number:04d}"
            existing = sorted(directory.glob("*.md")) if directory.exists() else []
            next_number = 1
            if existing:
                numbers = [int(path.stem) for path in existing if path.stem.isdigit()]
                if numbers:
                    next_number = max(numbers) + 1
            created_at = self.clock()
            target = directory / f"{next_number:04d}.md"
            metadata = {
                "github-local-comment": {
                    "schema": 1,
                    "issue": number,
                    "number": next_number,
                    "created_at": created_at,
                }
            }
            text = (
                "---\n"
                + json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
                + "\n---\n"
                + clean
                + "\n"
            )
            self._atomic_write(target, text, new=True)
            return self._parse_comment(target, expected_issue=number)

    def comments(self, number: int) -> list[IssueComment]:
        self._issue_path(number)
        directory = self.repository.issues_dir / "comments" / f"{number:04d}"
        if not directory.exists():
            return []
        comments = [
            self._parse_comment(path, expected_issue=number)
            for path in sorted(directory.glob("*.md"))
        ]
        return sorted(comments, key=lambda item: item.number)

    def reconcile_closing_references(self) -> list[int]:
        with FileLock(self._lock_path):
            head = self.repository.accepted_head()
            if head is None:
                return []

            state = self._read_closing_state()
            if state is None:
                self._write_closing_state(head)
                return []

            if state["accepted_branch"] != self.repository.accepted_branch:
                self._write_closing_state(head)
                return []

            cursor = state.get("cursor")
            if cursor == head:
                return []
            if cursor is not None and not self.repository.is_ancestor(str(cursor), head):
                self._write_closing_state(head)
                return []

            closed: list[int] = []
            qualified_name = f"{self.repository.owner}/{self.repository.name}".casefold()
            for sha, message in self.repository.accepted_commits(
                str(cursor) if cursor else None, head
            ):
                numbers = {
                    int(match.group("number"))
                    for match in QUALIFIED_CLOSING_RE.finditer(message)
                    if f"{match.group('owner')}/{match.group('repo')}".casefold()
                    == qualified_name
                }
                if self.repository.is_git_root_repository:
                    numbers.update(
                        int(match.group("number"))
                        for match in CLOSING_RE.finditer(message)
                    )
                for number in sorted(numbers):
                    try:
                        path = self._issue_path(number)
                    except IssueNotFound:
                        continue
                    metadata, title, body = self._read_issue(path)
                    if metadata["github-local"]["state"] != "OPEN":
                        continue
                    self._set_state(metadata, "CLOSED", closed_by=sha)
                    self._write_issue(path, metadata, title, body)
                    closed.append(number)

            self._write_closing_state(head)
            return sorted(set(closed))

    def _set_state(
        self,
        metadata: dict[str, dict[str, object]],
        state: str,
        *,
        closed_by: str | None = None,
    ) -> None:
        issue_meta = metadata["github-local"]
        if issue_meta["state"] == state:
            return
        now = self.clock()
        issue_meta["state"] = state
        issue_meta["updated_at"] = now
        if state == "CLOSED":
            issue_meta["closed_at"] = now
            issue_meta["closed_by"] = closed_by or "manual"
        else:
            issue_meta.pop("closed_at", None)
            issue_meta.pop("closed_by", None)

    def _next_number(self) -> int:
        maximum = 0
        for path in self.repository.issues_dir.glob("*.md"):
            match = ISSUE_RE.match(path.name)
            if match:
                maximum = max(maximum, int(match.group("number")))
        return maximum + 1

    def _issue_path(self, number: int) -> Path:
        matches = [
            path
            for path in self.repository.issues_dir.glob(f"{number:04d}-*.md")
            if ISSUE_RE.match(path.name)
        ]
        if not matches:
            raise IssueNotFound(f"Issue #{number} not found")
        if len(matches) > 1:
            names = ", ".join(p.name for p in sorted(matches))
            raise StorageError(f"duplicate Issue #{number}: {names}")
        return matches[0]

    def _render(self, metadata: dict[str, object], title: str, body: str) -> str:
        meta = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
        clean_body = body.rstrip()
        suffix = f"\n\n{clean_body}" if clean_body else ""
        return f"---\n{meta}\n---\n# {title}{suffix}\n"

    def _write_issue(
        self,
        target: Path,
        metadata: dict[str, object],
        title: str,
        body: str,
        *,
        new: bool = False,
    ) -> None:
        self._atomic_write(target, self._render(metadata, title, body), new=new)

    def _atomic_write(self, target: Path, text: str, *, new: bool = False) -> None:
        if new and target.exists():
            raise StorageError(f"refusing to overwrite existing file: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=target.parent,
                prefix=".github-local-",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                handle.write(text)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, target)
            temp_path = None
            if os.name != "nt":
                try:
                    dir_fd = os.open(target.parent, os.O_RDONLY)
                    try:
                        os.fsync(dir_fd)
                    finally:
                        os.close(dir_fd)
                except OSError:
                    pass
        finally:
            if temp_path is not None:
                temp_path.unlink(missing_ok=True)

    def _read_issue(
        self, path: Path
    ) -> tuple[dict[str, dict[str, object]], str, str]:
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise StorageError(f"Issue is not valid UTF-8: {path}") from exc
        lines = text.splitlines()
        if len(lines) < 4 or lines[0] != "---":
            raise StorageError(f"invalid Issue front matter: {path}")
        try:
            end = lines.index("---", 1)
        except ValueError as exc:
            raise StorageError(f"unterminated Issue front matter: {path}") from exc
        try:
            metadata = json.loads("\n".join(lines[1:end]))
            issue_meta = metadata["github-local"]
            if issue_meta["schema"] != 1:
                raise StorageError(f"unsupported Issue schema in {path}")
            number = int(issue_meta["number"])
            str(issue_meta["id"])
            str(issue_meta["state"])
            raw_labels = issue_meta.get("labels", [])
            if not isinstance(raw_labels, list) or not all(isinstance(label, str) for label in raw_labels):
                raise TypeError("labels must be a list of strings")
            normalize_labels(raw_labels)
            str(issue_meta["created_at"])
            str(issue_meta["updated_at"])
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise StorageError(f"invalid Issue metadata: {path}") from exc
        match = ISSUE_RE.match(path.name)
        if match is None or int(match.group("number")) != number:
            raise StorageError(f"Issue number does not match filename: {path}")
        content = lines[end + 1 :]
        while content and content[0] == "":
            content.pop(0)
        if not content or not content[0].startswith("# "):
            raise StorageError(f"Issue title heading is missing: {path}")
        title = content[0][2:].strip()
        body_lines = content[1:]
        while body_lines and body_lines[0] == "":
            body_lines.pop(0)
        body = "\n".join(body_lines).rstrip()
        return metadata, title, body

    def _parse(self, path: Path) -> Issue:
        metadata, title, body = self._read_issue(path)
        issue_meta = metadata["github-local"]
        number = int(issue_meta["number"])
        url = f"github-local://{self.repository.repository_id}/issues/{number}"
        return Issue(
            number=number,
            issue_id=str(issue_meta["id"]),
            state=str(issue_meta["state"]),
            title=title,
            body=body,
            labels=normalize_labels(issue_meta.get("labels", [])),
            created_at=str(issue_meta["created_at"]),
            updated_at=str(issue_meta["updated_at"]),
            path=path.relative_to(self.repository.workflow_root),
            url=url,
        )

    def _parse_comment(self, path: Path, *, expected_issue: int) -> IssueComment:
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
            if len(lines) < 4 or lines[0] != "---":
                raise ValueError("front matter missing")
            end = lines.index("---", 1)
            metadata = json.loads("\n".join(lines[1:end]))["github-local-comment"]
            if metadata["schema"] != 1 or int(metadata["issue"]) != expected_issue:
                raise ValueError("comment metadata mismatch")
            number = int(metadata["number"])
            created_at = str(metadata["created_at"])
            body = "\n".join(lines[end + 1 :]).rstrip()
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise StorageError(f"invalid Issue comment: {path}") from exc
        if path.stem != f"{number:04d}":
            raise StorageError(f"Issue comment number does not match filename: {path}")
        return IssueComment(
            number=number,
            created_at=created_at,
            body=body,
            path=path.relative_to(self.repository.workflow_root),
        )

    def _read_closing_state(self) -> dict[str, object] | None:
        path = self.repository.closing_state_path
        if not path.exists():
            return None
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
            if payload.get("schema") != 1:
                raise ValueError("unsupported closing state schema")
            branch = payload["accepted_branch"]
            cursor = payload.get("cursor")
            if not isinstance(branch, str) or not branch:
                raise ValueError("invalid accepted branch")
            if cursor is not None and (not isinstance(cursor, str) or not cursor):
                raise ValueError("invalid closing cursor")
            return {"schema": 1, "accepted_branch": branch, "cursor": cursor}
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise StorageError(f"invalid closing-reference state: {path}") from exc

    def _write_closing_state(self, cursor: str | None) -> None:
        payload = {
            "schema": 1,
            "accepted_branch": self.repository.accepted_branch,
            "cursor": cursor,
        }
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
        self._atomic_write(self.repository.closing_state_path, text)
