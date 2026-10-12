"""Explicit post-merge Issue number collision reconciliation."""
from __future__ import annotations


import json
import re
from pathlib import Path

from .repository import Repository, _git_optional
from .storage import FileLock, IssueStore, StorageError, _utc_now, slugify


def _record(path: Path) -> tuple[dict, str, str]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "---":
        raise StorageError(f"invalid Issue front matter: {path}")
    try:
        end = lines.index("---", 1)
        record = json.loads("\n".join(lines[1:end]))
        meta = record["github-local"]
        number, issue_id = int(meta["number"]), str(meta["id"])
        if not issue_id or not path.name.startswith(f"{number:04d}-"):
            raise ValueError("invalid identity")
        if not lines[end + 1].startswith("# "):
            raise ValueError("missing title")
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise StorageError(f"invalid Issue record: {path}") from exc
    return record, lines[end + 1][2:].strip(), "\n".join(lines[end + 2:]).strip()


def _first_parent_ids(repo: Repository) -> set[str]:
    """Prefer first-parent Issues when HEAD is a normal merge commit."""
    if not repo.has_git:
        return set()
    line = _git_optional(repo.git_root, "rev-list", "--parents", "-n", "1", "HEAD")
    if not line or len(line.split()) < 3:
        return set()
    parent = line.split()[1]
    listing = _git_optional(repo.git_root, "ls-tree", "-r", "--name-only",
                            parent, "--", ":(glob)**/issues/*.md") or ""
    ids = set()
    for name in listing.splitlines():
        raw = _git_optional(repo.git_root, "show", f"{parent}:{name}")
        if not raw:
            continue
        try:
            lines = raw.splitlines()
            end = lines.index("---", 1)
            ids.add(str(json.loads("\n".join(lines[1:end]))["github-local"]["id"]))
        except (ValueError, KeyError, IndexError, TypeError):
            pass
    return ids


def _references(repo: Repository, number: int) -> list[str]:
    if not repo.has_git:
        return []
    # Advisory only: no plain #N reference can be rewritten with certainty.
    result = _git_optional(repo.git_root, "grep", "-n", "-E",
                           rf"#{number}([^0-9]|$)", "--", "*.md", "**/*.md")
    return (result or "").splitlines()


def collision_report(repo: Repository, *, keep_id: str | None = None,
                     source_branch: str | None = None) -> dict:
    store = IssueStore(repo)
    conflicts = store._collision_groups()
    parents = _first_parent_ids(repo)
    if not conflicts:
        return {"collisions": [], "references": {}, "note": "No collisions."}
    if keep_id and not any(keep_id == ident for group in conflicts.values() for _, ident in group):
        raise StorageError(f"unknown --keep-id: {keep_id}")
    next_number = store._next_number()
    results = []
    for number, items in sorted(conflicts.items()):
        parents_here = [entry for entry in items if entry[1] in parents]
        ordered = sorted(parents_here or items, key=lambda x: (str(x[0]), x[1]))
        keep = next((item for item in items if item[1] == keep_id), ordered[0])
        moved = []
        for path, issue_id in sorted(items, key=lambda x: str(x[0])):
            if (path, issue_id) == keep:
                continue
            moved.append({
                "id": issue_id, "path": str(path), "from": number,
                "to": next_number, "source_branch": source_branch or "unknown",
            })
            next_number += 1
        results.append({
            "number": number,
            "keep": {"id": keep[1], "path": str(keep[0])},
            "rename": moved,
        })
    return {
        "collisions": results,
        "references": {str(n): _references(repo, n) for n in sorted(conflicts)},
        "note": "Text references, past Git commits and external documents must be reviewed manually.",
    }

