"""Explicit migration of legacy local-only Markdown into ordinary Git files."""
from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

from .repository import Repository, _ensure_gitignore, _git_identity
from .storage import FileLock, IssueStore, ISSUE_RE, StorageError


ISSUE_UUID = re.compile(r"^I_gl_[0-9a-f]{32}$")
COMMENT_UUID = re.compile(r"^C_gl_[0-9a-f]{32}$")


def _frontmatter(path: Path) -> tuple[dict, list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    try:
        if not lines or lines[0] != "---":
            raise ValueError("missing metadata")
        end = lines.index("---", 1)
        return json.loads("\n".join(lines[1:end])), lines[end + 1:]
    except (ValueError, KeyError, TypeError) as exc:
        raise StorageError(f"invalid legacy Issue file: {path}") from exc


def _render(meta: dict, content: list[str]) -> str:
    return "---\n" + json.dumps(meta, ensure_ascii=False, separators=(",", ":")) + (
        "\n---\n" + "\n".join(content).rstrip() + "\n"
    )


def migration_report(repo: Repository) -> dict:
    files = list(repo.issues_dir.glob("*.md"))
    issues = 0
    old_ids = 0
    old_comments = 0
    for path in files:
        if not ISSUE_RE.match(path.name):
            continue
        issues += 1
        data, _ = _frontmatter(path)
        if not ISSUE_UUID.fullmatch(str(data["github-local"]["id"])):
            old_ids += 1
        directory = repo.issues_dir / "comments" / path.name.split("-", 1)[0]
        for comment in directory.glob("*.md"):
            meta, _ = _frontmatter(comment)
            if not COMMENT_UUID.fullmatch(str(meta["github-local-comment"].get("id", ""))):
                old_comments += 1
    return {
        "repository": f"{repo.owner}/{repo.name}",
        "issues": issues,
        "legacyIssueIds": old_ids,
        "legacyComments": old_comments,
        "legacyExclusions": repo.legacy_exclusions(),
        "gitIdentity": repo.git_repository_id,
        "note": (
            "Migration never invokes git add/commit/push. Inspect 'git status', "
            "then commit Issues and .github-local/config.json, git-identity.json and .gitignore."
        ),
    }


def apply_migration(repo: Repository) -> dict:
    store = IssueStore(repo)
    with FileLock(repo.allocation_lock_path):
        report = migration_report(repo)
        backups: dict[Path, bytes | None] = {}
        def save(path: Path) -> None:
            if path not in backups:
                backups[path] = path.read_bytes() if path.exists() else None
        try:
            for path in sorted(repo.issues_dir.glob("*.md")):
                if not ISSUE_RE.match(path.name):
                    continue
                data, content = _frontmatter(path)
                meta = data["github-local"]
                former = str(meta["id"])
                if not ISSUE_UUID.fullmatch(former):
                    meta["id"] = f"I_gl_{uuid.uuid4().hex}"
                    save(path)
                    store._atomic_write(path, _render(data, content))
                directory = repo.issues_dir / "comments" / f"{int(meta['number']):04d}"
                for comment in sorted(directory.glob("*.md")):
                    comment_data, comment_content = _frontmatter(comment)
                    cm = comment_data["github-local-comment"]
                    cid = str(cm.get("id", ""))
                    if not COMMENT_UUID.fullmatch(cid):
                        cid = f"C_gl_{uuid.uuid4().hex}"
                        cm["id"] = cid
                    if cm.get("issue_id") != meta["id"]:
                        cm["issue_id"] = meta["id"]
                    target = comment.with_name(f"{cid}.md")
                    if target != comment and target.exists():
                        raise StorageError(f"comment destination already exists: {target}")
                    save(comment)
                    save(target)
                    store._atomic_write(target, _render(comment_data, comment_content),
                                        new=target != comment)
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
