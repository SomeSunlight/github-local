from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from github_local.changes import ChangeError, ChangeStore
from github_local.repository import Repository
from github_local.storage import IssueStore


class ChangeTests(unittest.TestCase):
    def git(self, root: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def make_repo(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        self.git(root, "init", "-q", "-b", "main")
        self.git(root, "config", "user.email", "test@example.com")
        self.git(root, "config", "user.name", "Test")
        (root / "README.md").write_text("base\n", encoding="utf-8")
        self.git(root, "add", "README.md")
        self.git(root, "commit", "-qm", "base")
        repo = Repository.initialize(root, owner="acme", name="demo")
        issues = IssueStore(repo)
        return temp, root, repo, issues, ChangeStore(repo, issues)

    def test_develop_creates_conventional_branch_and_explicit_link(self):
        temp, root, repo, issues, changes = self.make_repo()
        self.addCleanup(temp.cleanup)
        issue = issues.create("First change")
        main_head = self.git(root, "rev-parse", "main").stdout.strip()

        change = changes.develop(issue.number)

        self.assertEqual("issue-1-first-change", change.branch)
        self.assertEqual(main_head, change.head)
        self.assertFalse(change.current)
        self.assertEqual("explicit", change.relation)
        self.assertEqual(
            "1",
            self.git(
                root,
                "config",
                "--get",
                "branch.issue-1-first-change.github-local-issue",
            ).stdout.strip(),
        )
        self.assertEqual(
            repo.repository_id,
            self.git(
                root,
                "config",
                "--get",
                "branch.issue-1-first-change.github-local-repository",
            ).stdout.strip(),
        )

    def test_develop_can_use_explicit_base_and_checkout(self):
        temp, root, repo, issues, changes = self.make_repo()
        self.addCleanup(temp.cleanup)
        issue = issues.create("Base branch")
        self.git(root, "branch", "release", "main")
        release_head = self.git(root, "rev-parse", "release").stdout.strip()

        change = changes.develop(
            issue.number,
            name="custom-change",
            base="release",
            checkout=True,
        )

        self.assertEqual("custom-change", change.branch)
        self.assertEqual(release_head, change.head)
        self.assertTrue(change.current)

    def test_native_branch_rename_preserves_explicit_link(self):
        temp, root, repo, issues, changes = self.make_repo()
        self.addCleanup(temp.cleanup)
        issue = issues.create("Rename me")
        changes.develop(issue.number, checkout=True)
        self.git(root, "branch", "-m", "renamed/change")

        linked = changes.list(issue.number)

        self.assertEqual(1, len(linked))
        self.assertEqual("renamed/change", linked[0].branch)
        self.assertEqual("explicit", linked[0].relation)
        self.assertTrue(linked[0].current)

    def test_legacy_conventional_branch_is_discovered_and_can_be_adopted(self):
        temp, root, repo, issues, changes = self.make_repo()
        self.addCleanup(temp.cleanup)
        issue = issues.create("Legacy")
        self.git(root, "branch", "issue-1-legacy", "main")

        linked = changes.list(issue.number)
        self.assertEqual(1, len(linked))
        self.assertEqual("convention", linked[0].relation)

        adopted = changes.develop(issue.number, name="issue-1-legacy", checkout=True)
        self.assertEqual("explicit", adopted.relation)
        self.assertTrue(adopted.current)

    def test_branch_linked_to_other_issue_is_rejected_before_switch(self):
        temp, root, repo, issues, changes = self.make_repo()
        self.addCleanup(temp.cleanup)
        first = issues.create("One")
        second = issues.create("Two")
        changes.develop(first.number, name="shared-change")

        with self.assertRaisesRegex(ChangeError, "already linked to Issue #1"):
            changes.develop(second.number, name="shared-change")

        self.assertEqual(
            "main",
            self.git(root, "branch", "--show-current").stdout.strip(),
        )

    def test_link_is_shared_across_linked_worktrees(self):
        temp, root, repo, issues, changes = self.make_repo()
        self.addCleanup(temp.cleanup)
        issue = issues.create("Shared relation")
        changes.develop(issue.number)

        linked = root.parent / f"{root.name}-linked"
        self.git(root, "worktree", "add", "-q", "-b", "observer", str(linked), "main")
        linked_repo = Repository.discover(linked)
        linked_issues = IssueStore(linked_repo)
        linked_changes = ChangeStore(linked_repo, linked_issues)

        found = linked_changes.list(issue.number)
        self.assertEqual(1, len(found))
        self.assertEqual("issue-1-shared-relation", found[0].branch)
        self.assertEqual("explicit", found[0].relation)
        self.assertFalse(found[0].current)


    def test_nested_issue_repositories_get_distinct_default_branches(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.git(root, "init", "-q", "-b", "main")
        self.git(root, "config", "user.email", "test@example.com")
        self.git(root, "config", "user.name", "Test")
        (root / "README.md").write_text("base\n", encoding="utf-8")
        self.git(root, "add", "README.md")
        self.git(root, "commit", "-qm", "base")

        product_root = root / "product-a"
        extension_root = product_root / "extension-x"
        extension_root.mkdir(parents=True)

        product_repo = Repository.initialize(product_root, owner="acme", name="product-a")
        extension_repo = Repository.initialize(extension_root, owner="acme", name="extension-x")
        product_issues = IssueStore(product_repo)
        extension_issues = IssueStore(extension_repo)
        product_issues.create("Same number")
        extension_issues.create("Same number")

        product_change = ChangeStore(product_repo, product_issues).develop(1)
        extension_change = ChangeStore(extension_repo, extension_issues).develop(1)

        self.assertEqual("issue-product-a-1-same-number", product_change.branch)
        self.assertEqual("issue-extension-x-1-same-number", extension_change.branch)
        self.assertNotEqual(product_change.branch, extension_change.branch)


if __name__ == "__main__":
    unittest.main()
