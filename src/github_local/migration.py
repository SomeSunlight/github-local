"""Explicit migration of legacy local-only Markdown into ordinary Git files."""
from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .repository import Repository, _ensure_gitignore, _git_identity
from .storage import FileLock, IssueStore, ISSUE_RE, StorageError, _utc_now


ISSUE_UUID = re.compile(r"^I_gl_[0-9a-f]{32}$")
COMMENT_UUID = re.compile(r"^C_gl_[0-9a-f]{32}$")
NUMBERED_COMMENT_RE = re.compile(r"^[0-9]{4,}\.md$")


def _frontmatter(
    path: Path, *, comment: bool = False, allow_plain: bool = False
) -> tuple[dict, list[str]]:
    """Read structured metadata or recognize plain legacy Markdown for migration.

    Other commands retain strict parsers. Corrupt existing front matter is
    never replaced under the pretext of importing a plain Markdown record.
    """
    kind = "comment" if comment else "Issue"
    key = "github-local-comment" if comment else "github-local"
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise StorageError(f"cannot read legacy {kind} {path}: {exc}") from exc

    if not lines or lines[0] != "---":
        if allow_plain:
            if comment and NUMBERED_COMMENT_RE.fullmatch(path.name):
                return {}, lines
            if (not comment and ISSUE_RE.match(path.name) and lines
                    and lines[0].startswith("# ") and lines[0][2:].strip()):
                return {}, lines
            raise StorageError(
                f"cannot adopt plain Markdown {kind} {path}: "
                "expected a numbered Issue filename and '# Title' on the "
                "first line (or a numeric legacy comment filename)"
            )
        raise StorageError(
            f"cannot migrate legacy {kind} {path}: missing JSON front matter; "
            "use migration to adopt well-formed plain Markdown"
        )

    try:
        end = lines.index("---", 1)
    except ValueError as exc:
        raise StorageError(
            f"cannot migrate legacy {kind} {path}: missing closing '---' "
            "for JSON front matter"
        ) from exc
    try:
        data = json.loads("\n".join(lines[1:end]))
    except json.JSONDecodeError as exc:
        raise StorageError(
            f"cannot migrate legacy {kind} {path}: invalid JSON in front matter "
            f"at line {exc.lineno + 1}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(data, dict) or not isinstance(data.get(key), dict):
        raise StorageError(
            f"cannot migrate legacy {kind} {path}: front matter must contain "
            f"the '{key}' metadata object"
        )
    return data, lines[end + 1:]


def _file_modified_time(path: Path) -> str:
    """Last file modification is only an approximation of legacy creation."""
    try:
        return (datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
                .replace(microsecond=0).isoformat().replace("+00:00", "Z"))
    except (OSError, OverflowError, ValueError) as exc:
        raise StorageError(f"cannot read legacy file timestamp: {path}") from exc


def _issue_record(path: Path) -> tuple[dict, list[str], bool]:
    data, content = _frontmatter(path, allow_plain=True)
    match = ISSUE_RE.match(path.name)
    if match is None:
        raise StorageError(f"invalid numbered Issue filename: {path}")
    number = int(match.group("number"))
    if not content or not content[0].startswith("# ") or not content[0][2:].strip():
        raise StorageError(
            f"cannot migrate Issue {path}: Markdown must begin with '# Title'"
        )
    if not data:
        return {}, content, True
    meta = data["github-local"]
    try:
        if int(meta["number"]) != number or int(meta["schema"]) != 1:
            raise ValueError("schema or number mismatch")
    except (TypeError, ValueError, KeyError) as exc:
        raise StorageError(
            f"cannot migrate Issue {path}: front matter must use schema 1 "
            "and match its filename number"
        ) from exc
    return data, content, False


def _comment_record(path: Path) -> tuple[dict, list[str], bool]:
    data, content = _frontmatter(path, comment=True, allow_plain=True)
    if data:
        try:
            if int(data["github-local-comment"]["schema"]) != 1:
                raise ValueError("unsupported comment schema")
        except (TypeError, ValueError, KeyError) as exc:
            raise StorageError(
                f"cannot migrate comment {path}: invalid schema"
            ) from exc
    return data, content, not bool(data)


def _render(meta: dict, content: list[str]) -> str:
    return "---\n" + json.dumps(meta, ensure_ascii=False, separators=(",", ":")) + (
        "\n---\n" + "\n".join(content).rstrip() + "\n"
    )


def migration_report(repo: Repository) -> dict:
    """Read-only preview; generates no timestamps, UUIDs or filesystem changes."""
    issues = old_ids = old_comments = plain_issues = plain_comments = 0
    for path in sorted(repo.issues_dir.glob("*.md")):
        if not ISSUE_RE.match(path.name):
            continue
        issues += 1
        data, _, plain = _issue_record(path)
        if plain:
            plain_issues += 1
        if not ISSUE_UUID.fullmatch(str(data.get("github-local", {}).get("id", ""))):
            old_ids += 1
        directory = repo.issues_dir / "comments" / path.name.split("-", 1)[0]
        for comment in sorted(directory.glob("*.md")):
            record, _, plain_comment = _comment_record(comment)
            if plain_comment:
                plain_comments += 1
            if not COMMENT_UUID.fullmatch(
                str(record.get("github-local-comment", {}).get("id", ""))
            ):
                old_comments += 1
    return {
        "repository": f"{repo.owner}/{repo.name}",
        "issues": issues,
        "plainMarkdownIssues": plain_issues,
        "legacyIssueIds": old_ids,
        "plainMarkdownComments": plain_comments,
        "legacyComments": old_comments,
        "legacyExclusions": repo.legacy_exclusions(),
        "gitIdentity": repo.git_repository_id,
        "note": (
            "Legacy plain Markdown receives machine front matter on migration. "
            "Created/updated dates for such records initially use file mtime "
            "(not verified creation dates). Migration never stages, commits or pushes."
        ),
    }


def apply_migration(repo: Repository) -> dict:
    store = IssueStore(repo)
    with FileLock(repo.allocation_lock_path):
        report = migration_report(repo)  # Validate all records before mutating.
        backups: dict[Path, bytes | None] = {}

        def save(path: Path) -> None:
            if path not in backups:
                backups[path] = path.read_bytes() if path.exists() else None

        try:
            for path in sorted(repo.issues_dir.glob("*.md")):
                match = ISSUE_RE.match(path.name)
                if not match:
                    continue
                number = int(match.group("number"))
                data, content, plain = _issue_record(path)

                if plain:
                    modified = _file_modified_time(path)
                    data = {
                        "github-local": {
                            "schema": 1,
                            "id": f"I_gl_{uuid.uuid4().hex}",
                            "number": number,
                            "state": "OPEN",
                            "labels": [],
                            "created_at": modified,
                            "updated_at": modified,
                            "imported_at": _utc_now(),
                            "imported_from": "plain-markdown",
                        }
                    }
                meta = data["github-local"]
                former = str(meta.get("id", ""))
                changed = plain
                if not ISSUE_UUID.fullmatch(former):
                    meta["id"] = f"I_gl_{uuid.uuid4().hex}"
                    changed = True

                if changed:
                    save(path)
                    store._atomic_write(path, _render(data, content))

                directory = repo.issues_dir / "comments" / f"{number:04d}"
                for comment in sorted(directory.glob("*.md")):
                    comment_data, comment_content, plain_comment = _comment_record(comment)
                    if plain_comment:
                        comment_data = {
                            "github-local-comment": {
                                "schema": 1,
                                "issue": number,
                                "number": int(comment.stem),
                                "created_at": _file_modified_time(comment),
                                "imported_at": _utc_now(),
                                "imported_from": "plain-markdown",
                            }
                        }
                    cm = comment_data["github-local-comment"]
                    cid = str(cm.get("id", ""))
                    if not COMMENT_UUID.fullmatch(cid):
                        cid = f"C_gl_{uuid.uuid4().hex}"
                        cm["id"] = cid
                    cm["issue_id"] = meta["id"]
                    target = comment.with_name(f"{cid}.md")
                    if target != comment and target.exists():
                        raise StorageError(f"comment destination already exists: {target}")
                    if (plain_comment or target != comment
                            or _frontmatter(comment, comment=True)[0]
                            ["github-local-comment"].get("issue_id") != meta["id"]):
                        save(comment)
                        save(target)
                        store._atomic_write(
                            target, _render(comment_data, comment_content),
                            new=target != comment
                        )
                        if target != comment:
                            comment.unlink()
            if repo.has_git:
                _git_identity(repo.git_root, initialize=True)
                _ensure_gitignore(repo.git_root)
                report["removedExclusions"] = repo.migrate_exclusions()
        except Exception:
            for path, prior in backups.items():
                if prior is None:
                    path.unlink(missing_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(prior)
            raise

        report["migrated"] = True
        return report
