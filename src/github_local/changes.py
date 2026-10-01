from __future__ import annotations

import re

from .models import IssueChange
from .repository import Repository, _git, _git_optional, _run_git
from .storage import IssueStore, slugify


CONVENTIONAL_BRANCH_RE = re.compile(r"^issue-(?P<number>[0-9]+)(?:-|$)")
BRANCH_ISSUE_KEY = "github-local-issue"


class ChangeError(RuntimeError):
    pass


def conventional_branch_name(number: int, title: str) -> str:
    return f"issue-{number}-{slugify(title)}"


def _branch_config_key(branch: str) -> str:
    return f"branch.{branch}.{BRANCH_ISSUE_KEY}"


class ChangeStore:
    def __init__(self, repository: Repository, issues: IssueStore) -> None:
        self.repository = repository
        self.issues = issues

    def develop(
        self,
        number: int,
        *,
        name: str | None = None,
        base: str | None = None,
        checkout: bool = False,
    ) -> IssueChange:
        issue = self.issues.get(number)
        target = name or conventional_branch_name(number, issue.title)
        self._validate_branch(target)
        if target == self.repository.accepted_branch:
            raise ChangeError(
                f"refusing to link accepted branch {target!r} to Issue #{number}"
            )

        current = self._current_branch()
        head = self._branch_head(target)
        explicit = self._explicit_issue(target) if head is not None else None
        if explicit is not None and explicit != number:
            raise ChangeError(
                f"branch {target!r} is already linked to Issue #{explicit}"
            )

        if head is None:
            base_ref = base or self.repository.accepted_ref
            base_head = _git_optional(
                self.repository.workflow_root,
                "rev-parse",
                "--verify",
                base_ref,
            )
            if base_head is None:
                raise ChangeError(f"base Git ref does not exist: {base_ref!r}")

            if checkout:
                self._require_clean_worktree()
                completed = _run_git(
                    self.repository.root,
                    "switch",
                    "-c",
                    target,
                    base_ref,
                )
            else:
                completed = _run_git(
                    self.repository.root,
                    "branch",
                    target,
                    base_ref,
                )
            if completed.returncode != 0:
                self._raise_git_error(completed)
        elif checkout and current != target:
            self._require_clean_worktree()
            completed = _run_git(self.repository.root, "switch", target)
            if completed.returncode != 0:
                self._raise_git_error(completed)

        explicit = self._explicit_issue(target)
        if explicit is None:
            completed = _run_git(
                self.repository.root,
                "config",
                "--local",
                _branch_config_key(target),
                str(number),
            )
            if completed.returncode != 0:
                self._raise_git_error(completed)

        return self._change_for_branch(target, expected_issue=number)

    def list(self, number: int) -> list[IssueChange]:
        self.issues.get(number)
        current = self._current_branch()
        changes: list[IssueChange] = []

        output = _git(
            self.repository.workflow_root,
            "for-each-ref",
            "--format=%(refname:short)%00%(objectname)",
            "refs/heads",
        )
        for line in output.splitlines():
            if "\x00" not in line:
                continue
            branch, head = line.split("\x00", 1)
            explicit = self._explicit_issue(branch)
            if explicit is not None:
                if explicit == number:
                    changes.append(
                        IssueChange(
                            issue=number,
                            branch=branch,
                            head=head,
                            current=branch == current,
                            relation="explicit",
                        )
                    )
                continue

            match = CONVENTIONAL_BRANCH_RE.match(branch)
            if match and int(match.group("number")) == number:
                changes.append(
                    IssueChange(
                        issue=number,
                        branch=branch,
                        head=head,
                        current=branch == current,
                        relation="convention",
                    )
                )

        return sorted(changes, key=lambda item: item.branch)

    def _change_for_branch(self, branch: str, *, expected_issue: int) -> IssueChange:
        head = self._branch_head(branch)
        if head is None:
            raise ChangeError(f"development branch disappeared: {branch}")
        explicit = self._explicit_issue(branch)
        if explicit != expected_issue:
            raise ChangeError(
                f"branch {branch!r} is not linked to Issue #{expected_issue}"
            )
        return IssueChange(
            issue=expected_issue,
            branch=branch,
            head=head,
            current=branch == self._current_branch(),
            relation="explicit",
        )

    def _explicit_issue(self, branch: str) -> int | None:
        value = _git_optional(
            self.repository.workflow_root,
            "config",
            "--local",
            "--get",
            _branch_config_key(branch),
        )
        if value is None:
            return None
        try:
            return int(value)
        except ValueError as exc:
            raise ChangeError(
                f"invalid github.local Issue link on branch {branch!r}: {value!r}"
            ) from exc

    def _branch_head(self, branch: str) -> str | None:
        return _git_optional(
            self.repository.workflow_root,
            "show-ref",
            "--verify",
            "--hash",
            f"refs/heads/{branch}",
        )

    def _current_branch(self) -> str | None:
        return _git_optional(
            self.repository.root,
            "symbolic-ref",
            "--quiet",
            "--short",
            "HEAD",
        )

    def _validate_branch(self, branch: str) -> None:
        completed = _run_git(
            self.repository.root,
            "check-ref-format",
            "--branch",
            branch,
        )
        if completed.returncode != 0:
            raise ChangeError(f"invalid Git branch name: {branch!r}")

    def _require_clean_worktree(self) -> None:
        status = _git(self.repository.root, "status", "--porcelain")
        if status:
            raise ChangeError(
                "working tree has uncommitted changes; commit or stash them before switching development branches"
            )

    def _raise_git_error(self, completed) -> None:
        detail = completed.stderr.strip() or completed.stdout.strip() or "Git command failed"
        raise ChangeError(detail)
