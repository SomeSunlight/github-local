from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .repository import Repository, RepositoryError
from .storage import IssueNotFound, IssueStore, StorageError
from .version import display_version


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


def _emit_issue(issue, json_value: str | None) -> None:
    fields = _json_fields(json_value)
    if fields is None:
        print(issue.url)
    else:
        print(json.dumps(_select(issue, fields), ensure_ascii=False, separators=(",", ":")))


class _RuntimeVersionAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None) -> None:
        parser._print_message(f"{parser.prog} {display_version()}\n", sys.stdout)
        parser.exit()


def _add_issue_json(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--json", metavar="FIELDS", nargs="?", const="", default=None)


def _add_body_group(
    parser: argparse.ArgumentParser,
    *,
    required: bool = False,
    default: str | None = None,
) -> None:
    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument("--body", "-b", default=default)
    group.add_argument("--body-file", "-F")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="github-local", description="Local GitHub-shaped development workflow")
    parser.add_argument("--version", action=_RuntimeVersionAction, nargs=0)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="initialize github.local metadata in the current Git repository")
    init.add_argument("--owner", default="local")
    init.add_argument("--repo", default=None)
    init.add_argument(
        "--accepted-branch",
        default=None,
        help="branch whose reachable commits represent accepted work (default: inferred main/default branch)",
    )

    issue = sub.add_parser("issue", help="work with local Issues")
    issue_sub = issue.add_subparsers(dest="issue_command", required=True)

    create = issue_sub.add_parser("create", help="create an Issue")
    create.add_argument("--title", "-t", required=True)
    _add_body_group(create, default="")
    _add_issue_json(create)

    list_cmd = issue_sub.add_parser("list", help="list Issues")
    list_cmd.add_argument(
        "--state",
        choices=("open", "closed", "all"),
        default="all",
        help="filter by Issue state (default: all)",
    )
    _add_issue_json(list_cmd)

    view = issue_sub.add_parser("view", help="view an Issue")
    view.add_argument("number", type=int)
    _add_issue_json(view)

    close = issue_sub.add_parser("close", help="close an Issue")
    close.add_argument("number", type=int)
    _add_issue_json(close)

    reopen = issue_sub.add_parser("reopen", help="reopen an Issue")
    reopen.add_argument("number", type=int)
    _add_issue_json(reopen)

    edit = issue_sub.add_parser("edit", help="edit an Issue title or body")
    edit.add_argument("number", type=int)
    edit.add_argument("--title", "-t")
    _add_body_group(edit, default=None)
    _add_issue_json(edit)

    comment = issue_sub.add_parser("comment", help="add a durable Markdown comment to an Issue")
    comment.add_argument("number", type=int)
    _add_body_group(comment, required=True, default=None)

    return parser


def _read_body(args: argparse.Namespace) -> str | None:
    if getattr(args, "body_file", None):
        if args.body_file == "-":
            return sys.stdin.read()
        return Path(args.body_file).read_text(encoding="utf-8")
    return getattr(args, "body", None)


def _run(args: argparse.Namespace) -> int:
    if args.command == "init":
        root = Path.cwd().resolve()
        repo_name = args.repo or root.name
        repo = Repository.initialize(
            root,
            owner=args.owner,
            name=repo_name,
            accepted_branch=args.accepted_branch,
        )
        print(
            f"Initialized github.local for {repo.owner}/{repo.name} in {repo.root} "
            f"(accepted branch: {repo.accepted_branch})"
        )
        return 0

    repo = Repository.discover()
    store = IssueStore(repo)
    store.reconcile_closing_references()

    if args.command == "issue" and args.issue_command == "create":
        issue = store.create(args.title, _read_body(args) or "")
        _emit_issue(issue, args.json)
        return 0

    if args.command == "issue" and args.issue_command == "list":
        wanted = None if args.state == "all" else args.state
        issues = store.list(state=wanted)
        fields = _json_fields(args.json)
        if fields is not None:
            print(json.dumps([_select(item, fields) for item in issues], ensure_ascii=False, separators=(",", ":")))
            return 0
        print("NUMBER  STATE   TITLE")
        for item in issues:
            print(f"{item.number:>6}  {item.state:<6}  {item.title}")
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
        comments = store.comments(issue.number)
        if comments:
            print()
            print("comments:")
            for comment in comments:
                print()
                print(f"[{comment.number}] {comment.created_at}")
                print(comment.body)
        return 0

    if args.command == "issue" and args.issue_command == "close":
        _emit_issue(store.close(args.number), args.json)
        return 0

    if args.command == "issue" and args.issue_command == "reopen":
        _emit_issue(store.reopen(args.number), args.json)
        return 0

    if args.command == "issue" and args.issue_command == "edit":
        issue = store.edit(args.number, title=args.title, body=_read_body(args))
        _emit_issue(issue, args.json)
        return 0

    if args.command == "issue" and args.issue_command == "comment":
        body = _read_body(args)
        if body is None:
            raise StorageError("Issue comment body is required")
        comment = store.comment(args.number, body)
        print(comment.path.as_posix())
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
