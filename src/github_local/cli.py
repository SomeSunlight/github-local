from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .repository import Repository, RepositoryError
from .storage import IssueNotFound, IssueStore, StorageError


JSON_FIELDS = {"id", "number", "state", "title", "body", "createdAt", "updatedAt", "path", "url"}


def _json_fields(value: str | None) -> list[str] | None:
    if value is None:
        return None
    fields = [field.strip() for field in value.split(",") if field.strip()]
    unknown = sorted(set(fields) - JSON_FIELDS)
    if unknown:
        raise ValueError(f"unknown JSON field(s): {', '.join(unknown)}")
    return fields or sorted(JSON_FIELDS)


def _select(issue, fields: list[str]) -> dict[str, object]:
    data = issue.to_dict()
    return {field: data[field] for field in fields}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="github-local", description="Local GitHub-shaped development workflow")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="initialize github.local metadata in the current Git repository")
    init.add_argument("--owner", default="local")
    init.add_argument("--repo", default=None)

    issue = sub.add_parser("issue", help="work with local Issues")
    issue_sub = issue.add_subparsers(dest="issue_command", required=True)

    create = issue_sub.add_parser("create", help="create an Issue")
    create.add_argument("--title", "-t", required=True)
    body_group = create.add_mutually_exclusive_group()
    body_group.add_argument("--body", "-b", default="")
    body_group.add_argument("--body-file", "-F")
    create.add_argument("--json", metavar="FIELDS", nargs="?", const="", default=None)

    list_cmd = issue_sub.add_parser("list", help="list Issues")
    list_cmd.add_argument("--json", metavar="FIELDS", nargs="?", const="", default=None)

    view = issue_sub.add_parser("view", help="view an Issue")
    view.add_argument("number", type=int)
    view.add_argument("--json", metavar="FIELDS", nargs="?", const="", default=None)

    return parser


def _read_body(args: argparse.Namespace) -> str:
    if getattr(args, "body_file", None):
        if args.body_file == "-":
            return sys.stdin.read()
        return Path(args.body_file).read_text(encoding="utf-8")
    return getattr(args, "body", "")


def _run(args: argparse.Namespace) -> int:
    if args.command == "init":
        root = Path.cwd().resolve()
        repo_name = args.repo or root.name
        repo = Repository.initialize(root, owner=args.owner, name=repo_name)
        print(f"Initialized github.local for {repo.owner}/{repo.name} in {repo.root}")
        return 0

    repo = Repository.discover()
    store = IssueStore(repo)

    if args.command == "issue" and args.issue_command == "create":
        issue = store.create(args.title, _read_body(args))
        fields = _json_fields(args.json)
        if fields is None:
            print(issue.url)
        else:
            print(json.dumps(_select(issue, fields), ensure_ascii=False, separators=(",", ":")))
        return 0

    if args.command == "issue" and args.issue_command == "list":
        issues = store.list()
        fields = _json_fields(args.json)
        if fields is not None:
            print(json.dumps([_select(item, fields) for item in issues], ensure_ascii=False, separators=(",", ":")))
            return 0
        print("NUMBER  STATE  TITLE")
        for item in issues:
            print(f"{item.number:>6}  {item.state:<5}  {item.title}")
        return 0

    if args.command == "issue" and args.issue_command == "view":
        issue = store.get(args.number)
        fields = _json_fields(args.json)
        if fields is not None:
            print(json.dumps(_select(issue, fields), ensure_ascii=False, separators=(",", ":")))
            return 0
        print(f"#{issue.number} {issue.title}")
        print(f"state: {issue.state}")
        print(f"file:  {issue.path.as_posix()}")
        if issue.body:
            print()
            print(issue.body)
        return 0

    raise AssertionError("unreachable")


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
        return _run(args)
    except ValueError as exc:
        print(f"github-local: error: {exc}", file=sys.stderr)
        return 2
    except RepositoryError as exc:
        print(f"github-local: error: {exc}", file=sys.stderr)
        return 3
    except IssueNotFound as exc:
        print(f"github-local: error: {exc}", file=sys.stderr)
        return 4
    except StorageError as exc:
        print(f"github-local: error: {exc}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
