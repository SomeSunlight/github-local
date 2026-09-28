from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import time
import unicodedata
from contextlib import AbstractContextManager
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from .models import Issue
from .repository import Repository


ISSUE_RE = re.compile(r"^(?P<number>[0-9]{4,})-(?P<slug>.+)\.md$")
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


def slugify(title: str) -> str:
    normalized = unicodedata.normalize("NFKD", title)
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-.")
    slug = slug[:80].rstrip("-.") or "issue"
    if slug.upper() in WINDOWS_RESERVED:
        slug = f"issue-{slug}"
    return slug


def stable_issue_id(owner: str, repo: str, number: int) -> str:
    digest = hashlib.sha256(f"{owner}/{repo}#{number}".encode("utf-8")).hexdigest()[:16]
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

    def create(self, title: str, body: str = "") -> Issue:
        title = title.strip()
        if not title:
            raise StorageError("Issue title must not be empty")
        lock_path = self.repository.config_dir / "locks" / "issues.lock"
        with FileLock(lock_path):
            number = self._next_number()
            now = self.clock()
            issue_id = stable_issue_id(self.repository.owner, self.repository.name, number)
            filename = f"{number:04d}-{slugify(title)}.md"
            target = self.repository.issues_dir / filename
            metadata = {
                "github-local": {
                    "schema": 1,
                    "id": issue_id,
                    "number": number,
                    "state": "OPEN",
                    "created_at": now,
                    "updated_at": now,
                }
            }
            text = self._render(metadata, title, body)
            self._atomic_write_new(target, text)
            return self._parse(target)

    def list(self) -> list[Issue]:
        issues: list[Issue] = []
        for path in sorted(self.repository.issues_dir.glob("*.md")):
            if ISSUE_RE.match(path.name):
                issues.append(self._parse(path))
        return sorted(issues, key=lambda i: i.number)

    def get(self, number: int) -> Issue:
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
        return self._parse(matches[0])

    def _next_number(self) -> int:
        maximum = 0
        for path in self.repository.issues_dir.glob("*.md"):
            match = ISSUE_RE.match(path.name)
            if match:
                maximum = max(maximum, int(match.group("number")))
        return maximum + 1

    def _render(self, metadata: dict[str, object], title: str, body: str) -> str:
        meta = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
        clean_body = body.rstrip()
        suffix = f"\n\n{clean_body}" if clean_body else ""
        return f"---\n{meta}\n---\n# {title}{suffix}\n"

    def _atomic_write_new(self, target: Path, text: str) -> None:
        if target.exists():
            raise StorageError(f"refusing to overwrite existing Issue file: {target}")
        target.parent.mkdir(parents=True, exist_ok=True)
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                dir=target.parent,
                prefix=".issue-",
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

    def _parse(self, path: Path) -> Issue:
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
            metadata = json.loads("\n".join(lines[1:end]))["github-local"]
            if metadata["schema"] != 1:
                raise StorageError(f"unsupported Issue schema in {path}")
            number = int(metadata["number"])
            issue_id = str(metadata["id"])
            state = str(metadata["state"])
            created_at = str(metadata["created_at"])
            updated_at = str(metadata["updated_at"])
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
        url = f"github-local://{self.repository.owner}/{self.repository.name}/issues/{number}"
        return Issue(
            number=number,
            issue_id=issue_id,
            state=state,
            title=title,
            body=body,
            created_at=created_at,
            updated_at=updated_at,
            path=path.relative_to(self.repository.root),
            url=url,
        )
