from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .changes import ChangeError, ChangeStore
from .reconcile import apply_reconciliation, collision_report
from .repository import Repository, RepositoryError
from .storage import IssueNotFound, IssueStore, StorageError
from .version import display_version


JSON_FIELDS = {"id", "number", "state", "title", "body", "labels", "createdAt", "updatedAt", "path", "url"}
CHANGE_JSON_FIELDS = {"issue", "branch", "head", "current", "relation"}


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


def _change_json_fields(value: str | None) -> list[str] | None:
    if value is None:
        return None
    fields = [field.strip() for field in value.split(",") if field.strip()]
    unknown = sorted(set(fields) - CHANGE_JSON_FIELDS)
    if unknown:
        raise ValueError(f"unknown Change JSON field(s): {', '.join(unknown)}")
    return fields or sorted(CHANGE_JSON_FIELDS)


def _select_change(change, fields: list[str]) -> dict[str, object]:
    data = change.to_dict()
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


def _add_repo_selector(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--repo",
        "-R",
        dest="repo_selector",
        default=argparse.SUPPRESS,
        metavar="PATH",
        help="select a local Issue repository by path; use '.' for the local environment",
    )


def _examples(*commands: str) -> str:
    return "Examples:\n  " + "\n  ".join(commands)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="github-local",
        description="Local GitHub-shaped development workflow",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_examples(
            "github-local issue init",
            'github-local issue create -R . --title "Add validation" --label bug',
            "github-local issue list -R .",
        ),
    )
    parser.add_argument("--version", action=_RuntimeVersionAction, nargs=0)
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser(
        "init",
        help="initialize a local Issue repository in the current directory (compatibility alias)",
    )
    init.add_argument("--owner", default="local")
    init.add_argument("--repo", default=None)
    init.add_argument("--accepted-branch", default=None)

    issue = sub.add_parser(
        "issue",
        help="work with local Issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_examples(
            "github-local issue init",
            "github-local issue list -R .",
            'github-local issue create -R . --title "Add validation" --label bug',
            "github-local issue view -R . 12 --comments",
            "github-local issue develop -R . 12 --checkout",
        ),
    )
    _add_repo_selector(issue)
    issue_sub = issue.add_subparsers(dest="issue_command", required=True)

    issue_init = issue_sub.add_parser(
        "init",
        help="initialize a local Issue repository in the current directory",
    )
    issue_init.add_argument("--owner", default="local")
    issue_init.add_argument("--name", default=None)
    issue_init.add_argument("--accepted-branch", default=None)

    deinit = issue_sub.add_parser(
        "deinit",
        help="remove local Issue repository metadata",
    )
    _add_repo_selector(deinit)
    deinit.add_argument(
        "--delete-issues",
        action="store_true",
        help="delete all Issues before deinitializing",
    )
    deinit.add_argument("--yes", action="store_true", help="skip destructive confirmation")

    create = issue_sub.add_parser(
        "create",
        help="create an Issue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_examples(
            'github-local issue create -R . --title "Fix parser" --body "Reject invalid input." --label bug',
            'github-local issue create -R . --title "Fix parser" --label bug --json number,title,labels',
        ),
    )
    _add_repo_selector(create)
    create.add_argument("--title", "-t", required=True)
    create.add_argument("--label", "-l", action="append", default=None, help="add a label by name")
    _add_body_group(create, default="")
    _add_issue_json(create)

    list_cmd = issue_sub.add_parser(
        "list",
        aliases=["ls"],
        help="list Issues",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_examples(
            "github-local issue list -R .",
            "github-local issue list -R . --label bug --search parser",
            "github-local issue list -R . --state all --json number,state,title,labels",
        ),
    )
    _add_repo_selector(list_cmd)
    list_cmd.add_argument(
        "--state",
        "-s",
        choices=("open", "closed", "all"),
        default="open",
        help="filter by Issue state (default: open)",
    )
    list_cmd.add_argument("--label", "-l", action="append", default=None, help="filter by label")
    list_cmd.add_argument("--search", "-S", default=None, help="search Issue title, body, and labels")
    _add_issue_json(list_cmd)

    view = issue_sub.add_parser("view", help="view an Issue")
    _add_repo_selector(view)
    view.add_argument("number", type=int)
    view.add_argument("--comments", "-c", action="store_true", help="view Issue comments")
    _add_issue_json(view)

    close = issue_sub.add_parser("close", help="close an Issue")
    _add_repo_selector(close)
    close.add_argument("number", type=int)
    close.add_argument("--comment", "-c", help="leave a closing comment")
    _add_issue_json(close)

    reopen = issue_sub.add_parser("reopen", help="reopen an Issue")
    _add_repo_selector(reopen)
    reopen.add_argument("number", type=int)
    reopen.add_argument("--comment", "-c", help="add a reopening comment")
    _add_issue_json(reopen)

    edit = issue_sub.add_parser("edit", help="edit an Issue title or body")
    _add_repo_selector(edit)
    edit.add_argument("number", type=int)
    edit.add_argument("--title", "-t")
    edit.add_argument("--add-label", action="append", default=None, help="add a label by name")
    edit.add_argument("--remove-label", action="append", default=None, help="remove a label by name")
    _add_body_group(edit, default=None)
    _add_issue_json(edit)

    comment = issue_sub.add_parser("comment", help="add a durable Markdown comment to an Issue")
    _add_repo_selector(comment)
    comment.add_argument("number", type=int)
    _add_body_group(comment, required=True, default=None)

    delete = issue_sub.add_parser("delete", help="delete an Issue or all Issues")
    _add_repo_selector(delete)
    delete.add_argument("number", type=int, nargs="?")
    delete.add_argument("--all", action="store_true", help="delete all Issues (github.local extension)")
    delete.add_argument("--yes", action="store_true", help="confirm deletion without prompting")

    status = issue_sub.add_parser("status", help="inspect selected repository and Git Issue collisions")
    _add_repo_selector(status)
    status.add_argument("--json", action="store_true", help="print structured diagnostics")

    reconcile = issue_sub.add_parser(
        "reconcile", help="review and repair post-merge duplicate Issue numbers"
    )
    _add_repo_selector(reconcile)
    reconcile.add_argument("--keep-id", help="immutable Issue ID which retains its old number")
    reconcile.add_argument("--source-branch", help="provenance label for renamed Issues")
    reconcile.add_argument("--dry-run", action="store_true", help="preview without writing")
    reconcile.add_argument("--yes", action="store_true", help="confirm the proposed renumbering")
    reconcile.add_argument("--json", action="store_true", help="print machine-readable plan")

    migrate = issue_sub.add_parser(
        "migrate", help="adopt legacy ignored Issue files for normal Git tracking"
    )
    _add_repo_selector(migrate)
    migrate.add_argument("--yes", action="store_true", help="confirm migration")
    migrate.add_argument("--dry-run", action="store_true", help="show migration impact")

    develop = issue_sub.add_parser(
        "develop",
        help="manage linked Git branches for an Issue",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=_examples(
            "github-local issue develop -R . 12 --checkout",
            "github-local issue develop -R . --list 12 --json branch,head,current,relation",
        ),
    )
    _add_repo_selector(develop)
    develop.add_argument("number", type=int)
    develop.add_argument("--base", "-b", default=None, help="Git branch/ref to create the new branch from")
    develop.add_argument("--checkout", "-c", action="store_true", help="checkout the branch after creating or linking it")
    develop.add_argument("--list", "-l", action="store_true", help="list linked branches for the Issue")
    develop.add_argument("--name", "-n", default=None, help="name of the branch to create or adopt")
    develop.add_argument("--json", metavar="FIELDS", nargs="?", const="", default=None)

    return parser


def _read_body(args: argparse.Namespace) -> str | None:
    if getattr(args, "body_file", None):
        if args.body_file == "-":
            return sys.stdin.read()
        return Path(args.body_file).read_text(encoding="utf-8")
    return getattr(args, "body", None)


def _initialize_here(owner: str, name: str | None, accepted_branch: str | None) -> Repository:
    root = Path.cwd().resolve()
    return Repository.initialize(
        root,
        owner=owner,
        name=name or root.name,
        accepted_branch=accepted_branch,
    )


def _selected_repository(args: argparse.Namespace) -> Repository:
    value = getattr(args, "repo_selector", None)
    if value is None:
        raise ValueError(
            "Issue repository required; use -R/--repo PATH (use '-R .' for the local environment)"
        )
    selector = Path(value)
    if not selector.is_absolute():
        selector = Path.cwd() / selector
    return Repository.discover(selector)


def _confirm(message: str) -> bool:
    try:
        answer = input(f"{message} [y/N] ").strip().casefold()
    except EOFError:
        return False
    return answer in {"y", "yes"}


def _run(args: argparse.Namespace) -> int:
    if args.command == "init":
        repo = _initialize_here(args.owner, args.repo, args.accepted_branch)
        branch = f", accepted branch {repo.accepted_branch}" if repo.accepted_branch else ""
        print(
            f"Initialized local Issue repository {repo.owner}/{repo.name} "
            f"at {repo.workflow_root} ({repo.repository_id}{branch})"
        )
        return 0

    if args.command == "issue" and args.issue_command == "init":
        repo = _initialize_here(args.owner, args.name, args.accepted_branch)
        branch = f", accepted branch {repo.accepted_branch}" if repo.accepted_branch else ""
        print(
            f"Initialized local Issue repository {repo.owner}/{repo.name} "
            f"at {repo.workflow_root} ({repo.repository_id}{branch})"
        )
        return 0

    repo = _selected_repository(args)
    store = IssueStore(repo)

    if args.command == "issue" and args.issue_command == "status":
        diag = {
            "repository": f"{repo.owner}/{repo.name}",
            "root": str(repo.workflow_root),
            "gitRoot": str(repo.git_root) if repo.has_git else None,
            "gitIdentity": repo.git_repository_id,
            "issueStore": str(repo.issues_dir),
            "legacyExclusions": repo.legacy_exclusions(),
            "ignoredDurablePaths": repo.ignored_durable_paths(),
            "collisions": collision_report(repo)["collisions"],
            "capabilities": {"issues": True, "changes": repo.has_git,
                             "pullRequests": False, "reviews": False},
        }
        if args.json:
            print(json.dumps(diag, ensure_ascii=False, indent=2))
        else:
            for key, value in diag.items():
                print(f"{key}: {value}")
        return 0

    if args.command == "issue" and args.issue_command == "reconcile":
        report = collision_report(repo, keep_id=args.keep_id,
                                  source_branch=args.source_branch)
        if not args.json:
            for entry in report["collisions"]:
                print(f"Collision #{entry['number']}: keep {entry['keep']['id']}")
                for change in entry["rename"]:
                    print(f"  rename {change['id']}: #{change['from']} -> #{change['to']}")
            print(report["note"])
            for number, hits in report["references"].items():
                if hits:
                    print(f"  #{number}: {len(hits)} possible text references (review manually)")
            if not report["collisions"]:
                print("No Issue number collisions.")
        if not args.dry_run and report["collisions"]:
            if not args.yes and not _confirm(
                "Rename the proposed Issues and their UUID-matched comments? "
                "Free-text references will NOT be changed."
            ):
                print("Aborted.")
                return 1
            report = apply_reconciliation(repo, keep_id=args.keep_id,
                                          source_branch=args.source_branch)
        if args.json:
            print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    if args.command == "issue" and args.issue_command == "migrate":
        from .migration import migration_report, apply_migration
        report = migration_report(repo)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        if args.dry_run:
            return 0
        if not args.yes and not _confirm(
            "Remove legacy hidden Git excludes and adopt canonical Issue files? "
            "Git commit/push remains your responsibility."
        ):
            print("Aborted.")
            return 1
        print(json.dumps(apply_migration(repo), ensure_ascii=False, indent=2))
        return 0

    if args.command == "issue" and args.issue_command == "deinit":
        count = store.count()
        if count and not args.delete_issues:
            raise RepositoryError(
                f"{repo.owner}/{repo.name} contains {count} Issue(s); "
                "rerun with --delete-issues to remove them explicitly"
            )
        if count and args.delete_issues:
            if not args.yes and not _confirm(
                f"Delete ALL {count} Issue(s) from {repo.owner}/{repo.name} and deinitialize it?"
            ):
                print("Aborted.")
                return 1
            store.delete_all()
        repo.deinitialize()
        print(f"Deinitialized local Issue repository {repo.owner}/{repo.name}")
        return 0

    if args.command == "issue" and args.issue_command == "delete":
        if args.all and args.number is not None:
            raise ValueError("issue delete accepts either <number> or --all, not both")
        if not args.all and args.number is None:
            raise ValueError("issue delete requires <number> or --all")
        if args.all:
            count = store.count()
            if not count:
                print("No Issues to delete.")
                return 0
            if not args.yes and not _confirm(
                f"Delete ALL {count} Issue(s) from {repo.owner}/{repo.name}?"
            ):
                print("Aborted.")
                return 1
            deleted = store.delete_all()
            print(f"Deleted {deleted} Issue(s) from {repo.owner}/{repo.name}.")
            return 0

        issue = store.get(args.number)
        if not args.yes and not _confirm(
            f"Delete Issue #{issue.number} from {repo.owner}/{repo.name}: {issue.title!r}?"
        ):
            print("Aborted.")
            return 1
        store.delete(issue.number)
        print(f"Deleted Issue #{issue.number}.")
        return 0

    store.reconcile_closing_references()
    changes = ChangeStore(repo, store)

    if args.command == "issue" and args.issue_command == "create":
        issue = store.create(args.title, _read_body(args) or "", labels=args.label)
        _emit_issue(issue, args.json)
        return 0

    if args.command == "issue" and args.issue_command in ("list", "ls"):
        wanted = None if args.state == "all" else args.state
        issues = store.list(state=wanted, labels=args.label, search=args.search)
        fields = _json_fields(args.json)
        if fields is not None:
            print(json.dumps([_select(item, fields) for item in issues], ensure_ascii=False, separators=(",", ":")))
            return 0
        print("NUMBER  STATE   TITLE  LABELS")
        for item in issues:
            labels = ", ".join(item.labels)
            print(f"{item.number:>6}  {item.state:<6}  {item.title}  {labels}")
        return 0

    if args.command == "issue" and args.issue_command == "view":
        issue = store.get(args.number)
        fields = _json_fields(args.json)
        if fields is not None:
            print(json.dumps(_select(issue, fields), ensure_ascii=False, separators=(",", ":")))
            return 0
        print(f"#{issue.number} {issue.title}")
        print(f"repository: {repo.owner}/{repo.name}")
        print(f"state: {issue.state}")
        if issue.labels:
            print(f"labels: {', '.join(issue.labels)}")
        print(f"file:  {issue.path.as_posix()}")
        if issue.body:
            print()
            print(issue.body)
        if args.comments:
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
        issue = store.close(args.number)
        if args.comment:
            store.comment(args.number, args.comment)
        _emit_issue(issue, args.json)
        return 0

    if args.command == "issue" and args.issue_command == "reopen":
        issue = store.reopen(args.number)
        if args.comment:
            store.comment(args.number, args.comment)
        _emit_issue(issue, args.json)
        return 0

    if args.command == "issue" and args.issue_command == "edit":
        issue = store.edit(
            args.number,
            title=args.title,
            body=_read_body(args),
            add_labels=args.add_label,
            remove_labels=args.remove_label,
        )
        _emit_issue(issue, args.json)
        return 0

    if args.command == "issue" and args.issue_command == "comment":
        body = _read_body(args)
        if body is None:
            raise StorageError("Issue comment body is required")
        comment = store.comment(args.number, body)
        print(comment.path.as_posix())
        return 0

    if args.command == "issue" and args.issue_command == "develop":
        if args.list:
            if args.name is not None or args.base is not None or args.checkout:
                raise ValueError("--list cannot be combined with --name, --base, or --checkout")
            linked = changes.list(args.number)
            fields = _change_json_fields(args.json)
            if fields is not None:
                print(json.dumps([_select_change(item, fields) for item in linked], ensure_ascii=False, separators=(",", ":")))
                return 0
            if not linked:
                print(f"No development branches linked to Issue #{args.number}.")
                return 0
            print("BRANCH  HEAD     CURRENT  RELATION")
            for item in linked:
                current = "yes" if item.current else ""
                print(f"{item.branch}  {item.head[:7]}  {current:<7}  {item.relation}")
            return 0

        change = changes.develop(
            args.number,
            name=args.name,
            base=args.base,
            checkout=args.checkout,
        )
        fields = _change_json_fields(args.json)
        if fields is None:
            print(change.branch)
        else:
            print(json.dumps(_select_change(change, fields), ensure_ascii=False, separators=(",", ":")))
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
    except (StorageError, ChangeError) as exc:
        print(f"github-local: error: {exc}", file=sys.stderr)
        return 5


if __name__ == "__main__":
    raise SystemExit(main())
