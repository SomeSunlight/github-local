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
    # git ls-tree does not support :(glob) pathspecs (unlike ls-files).
    listing = _git_optional(repo.git_root, "ls-tree", "-r", "--name-only",
                            parent) or ""
    ids = set()
    for name in listing.splitlines():
        relative = Path(name)
        if relative.parent.name != "issues" or relative.suffix != ".md":
            continue
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


def collision_report(
    repo: Repository, *, keep_id: str | list[str] | None = None,
    source_branch: str | None = None,
) -> dict:
    """Preview collisions; never select a winner by arbitrary path ordering.

    A first-parent Git merge can identify a single retained record. After a
    migration of historically independent Issue folders there is no such
    evidence: the owner must explicitly select one Issue per duplicated number.
    """
    store = IssueStore(repo)
    conflicts = store._collision_groups()
    if not conflicts:
        return {"collisions": [], "references": {}, "note": "No collisions.",
                "manualChoiceRequired": False}

    choices = [keep_id] if isinstance(keep_id, str) else list(keep_id or [])
    if len(set(choices)) != len(choices):
        raise StorageError("the same --keep-id was supplied more than once")
    available = {
        issue_id: number
        for number, items in conflicts.items()
        for _, issue_id in items
    }
    for issue_id in choices:
        if issue_id not in available:
            raise StorageError(f"unknown --keep-id: {issue_id}")
    explicit: dict[int, str] = {}
    for issue_id in choices:
        number = available[issue_id]
        if number in explicit:
            raise StorageError(
                f"more than one --keep-id supplied for collision #{number}; "
                "choose exactly one Issue to keep this number"
            )
        explicit[number] = issue_id

    first_parent = _first_parent_ids(repo)
    next_number = store._next_number()
    results = []
    for number, items in sorted(conflicts.items()):
        candidates = []
        for path, issue_id in sorted(items, key=lambda x: (str(x[0]), x[1])):
            _, title, _ = _record(path)
            base = repo.git_root if repo.has_git else repo.workflow_root
            candidates.append({
                "id": issue_id,
                "path": str(path),
                "relativePath": path.relative_to(base).as_posix(),
                "title": title,
            })

        chosen_id = explicit.get(number)
        selection = "explicit" if chosen_id else "manual"
        if chosen_id is None:
            # First-parent ancestry is evidence only when one record, not
            # multiple ambiguous records, is present in that parent.
            from_parent = [item for item in items if item[1] in first_parent]
            if len(from_parent) == 1:
                chosen_id = from_parent[0][1]
                selection = "first-parent"

        keep = next((candidate for candidate in candidates
                     if candidate["id"] == chosen_id), None)
        changes = []
        if keep is not None:
            for candidate in candidates:
                if candidate["id"] == keep["id"]:
                    continue
                changes.append({
                    "id": candidate["id"],
                    "path": candidate["path"],
                    "relativePath": candidate["relativePath"],
                    "title": candidate["title"],
                    "from": number,
                    "to": next_number,
                    "source_branch": source_branch,
                })
                next_number += 1

        results.append({
            "number": number,
            "candidates": candidates,
            "keep": keep,
            "selection": selection,
            "manualChoiceRequired": keep is None,
            "rename": changes,
        })
    return {
        "collisions": results,
        "references": {str(n): _references(repo, n) for n in sorted(conflicts)},
        "manualChoiceRequired": any(r["manualChoiceRequired"] for r in results),
        "note": (
            "Duplicates may result from former per-folder Issue numbering or "
            "independent Git clones. A missing branch name is not proof of "
            "a Git merge. Text references, historic Git commits and external "
            "documents must be reviewed manually."
        ),
    }


def _associated_comments(issue_path: Path, issue_id: str, old: int,
                         new: int) -> list[tuple[Path, Path, dict, list[str]]]:
    source = issue_path.parent / "comments" / f"{old:04d}"
    target = issue_path.parent / "comments" / f"{new:04d}"
    if not source.is_dir():
        return []
    edits = []
    for path in sorted(source.glob("*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        try:
            end = lines.index("---", 1)
            data = json.loads("\n".join(lines[1:end]))
            meta = data["github-local-comment"]
        except (ValueError, KeyError, TypeError) as exc:
            raise StorageError(f"invalid comment: {path}") from exc
        if not meta.get("issue_id"):
            raise StorageError(
                f"cannot assign legacy comment {path} to one of two Issues "
                f"numbered #{old}; manual attribution is required"
            )
        if meta["issue_id"] == issue_id:
            data["github-local-comment"]["issue"] = new
            edits.append((path, target / path.name, data, lines[end + 1:]))
    return edits


def apply_reconciliation(repo: Repository, *, keep_id: str | list[str] | None = None,
                         source_branch: str | None = None) -> dict:
    repo.ensure_trackable()
    if repo.has_git and _git_optional(repo.git_root, "ls-files", "-u"):
        raise StorageError("resolve ordinary Git merge conflicts before reconciling Issues")

    with FileLock(repo.allocation_lock_path):
        report = collision_report(repo, keep_id=keep_id,
                                  source_branch=source_branch)
        if report["manualChoiceRequired"]:
            pending = ", ".join(f"#{item['number']}" for item in report["collisions"]
                                if item["manualChoiceRequired"])
            raise StorageError(
                f"no unambiguous Issue to keep for {pending}; "
                "choose one --keep-id per unresolved collision before applying"
            )
        plan = []
        for collision in report["collisions"]:
            for change in collision["rename"]:
                source = Path(change["path"])
                old, new = change["from"], change["to"]
                record, title, body = _record(source)
                target = source.with_name(f"{new:04d}-{slugify(title)}.md")
                if target.exists():
                    raise StorageError(f"reconciliation target exists: {target}")
                comments = _associated_comments(source, change["id"], old, new)
                for _, dest, _, _ in comments:
                    if dest.exists():
                        raise StorageError(f"comment target exists: {dest}")
                plan.append((source, target, record, title, body, comments, change))
        originals: dict[Path, bytes | None] = {}
        def backup(path: Path) -> None:
            if path not in originals:
                originals[path] = path.read_bytes() if path.exists() else None
        try:
            for src, dst, record, title, body, comments, change in plan:
                backup(src)
                backup(dst)
                date = _utc_now()
                entry = record["github-local"]
                entry.setdefault("renames", []).append({
                    "at": date, "from": change["from"],
                    "source_branch": change["source_branch"],
                    "original_path": str(src.relative_to(
                        repo.git_root if repo.has_git else repo.workflow_root)),
                })
                entry["number"] = change["to"]
                entry["updated_at"] = date
                if change["source_branch"]:
                    annotation = (
                        f"Renamed on {date} from #{change['from']} "
                        f"of branch {change['source_branch']}."
                    )
                else:
                    annotation = (
                        f"Renamed on {date} from #{change['from']} "
                        f"(source branch not recorded; original path "
                        f"{change['relativePath']})."
                    )
                local = IssueStore(Repository.discover(src.parent.parent))
                local._write_issue(dst, record, title,
                                   body.rstrip() + "\n\n---\n\n> " + annotation, new=True)
                for source_comment, target_comment, data, lines in comments:
                    backup(source_comment)
                    backup(target_comment)
                    new_text = "---\n" + json.dumps(
                        data, ensure_ascii=False, separators=(",", ":")
                    ) + "\n---\n" + "\n".join(lines).rstrip() + "\n"
                    local._atomic_write(target_comment, new_text, new=True)
                    source_comment.unlink()
                src.unlink()
            if plan:
                IssueStore(repo)._write_issue_state(
                    max(entry["to"] for *_, entry in plan) + 1
                )
                # Skip previously merged ambiguous Fixes #N messages; later
                # explicit references still work after collision repair.
                if repo.has_git and repo.accepted_head():
                    IssueStore(repo)._write_closing_state(repo.accepted_head())
        except Exception:
            for path, data in originals.items():
                if data is None:
                    path.unlink(missing_ok=True)
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
            raise
        report["applied"] = bool(plan)
        return report
