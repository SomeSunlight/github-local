from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from github_local.repository import Repository
from github_local.storage import IssueStore, StorageError
from github_local.reconcile import collision_report, apply_reconciliation
from github_local.migration import migration_report, apply_migration


class GitTrackedWorkflowTests(unittest.TestCase):
    def git(self, root: Path, *args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(root), *args], check=True, text=True,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        ).stdout.strip()

    def configure(self, root: Path) -> None:
        self.git(root, "config", "user.email", "test@example.com")
        self.git(root, "config", "user.name", "Test")

    def checkpoint(self, root: Path, message: str) -> None:
        self.git(root, "add", "-A")
        self.git(root, "commit", "-qm", message)

    def project(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        a = Path(tmp.name) / "a"
        a.mkdir()
        self.git(a, "init", "-q", "-b", "main")
        self.configure(a)
        repo = Repository.initialize(a, owner="acme", name="demo")
        self.checkpoint(a, "add workflow configuration")
        return Path(tmp.name), a, repo

    def test_clone_retains_identity_and_issue_history(self):
        parent, a, repo = self.project()
        first = IssueStore(repo).create("First")
        self.checkpoint(a, "first Issue")
        b = parent / "b"
        self.git(parent, "clone", "-q", str(a), str(b))
        self.configure(b)
        other = Repository.discover(b)
        self.assertEqual(repo.git_repository_id, other.git_repository_id)
        self.assertEqual(first.issue_id, IssueStore(other).get(1).issue_id)
        created = IssueStore(other).create("Second")
        self.assertEqual(2, created.number)
        self.assertNotEqual(first.issue_id, created.issue_id)

    def test_merging_independent_clones_then_renumbering_preserves_data(self):
        parent, a, repo = self.project()
        b = parent / "b"
        self.git(parent, "clone", "-q", str(a), str(b))
        self.configure(b)
        store_a = IssueStore(repo)
        store_b = IssueStore(Repository.discover(b))
        one = store_a.create("Original bug")
        store_a.comment(1, "Discussion from A")
        self.checkpoint(a, "original work")
        two = store_b.create("Imported enhancement")
        store_b.comment(1, "Discussion from B")
        (b / "notes.md").write_text("See #1 for details.\n", encoding="utf-8")
        self.checkpoint(b, "imported work")
        self.assertNotEqual(one.issue_id, two.issue_id)
        self.git(a, "remote", "add", "peer", str(b))
        self.git(a, "fetch", "-q", "peer", "main")
        self.git(a, "merge", "-q", "--no-ff", "-m", "merge independent clone", "peer/main")
        report = collision_report(repo, source_branch="Windows")
        self.assertEqual(1, len(report["collisions"]))
        self.assertEqual(one.issue_id, report["collisions"][0]["keep"]["id"])
        self.assertEqual(2, report["collisions"][0]["rename"][0]["to"])
        with self.assertRaisesRegex(StorageError, "duplicate Issue numbers"):
            IssueStore(repo).create("Should wait for repair")
        applied = apply_reconciliation(repo, source_branch="Windows")
        self.assertTrue(applied["applied"])
        self.assertEqual(one.issue_id, store_a.get(1).issue_id)
        self.assertEqual(two.issue_id, store_a.get(2).issue_id)
        self.assertIn("from #1 of branch Windows", store_a.get(2).body)
        self.assertEqual(["Discussion from B"],
                         [c.body for c in store_a.comments(2)])
        self.assertEqual(["Discussion from A"],
                         [c.body for c in store_a.comments(1)])
        self.assertEqual("See #1 for details.", (a / "notes.md").read_text().strip())
        self.assertTrue(self.git(a, "status", "--porcelain"))
        self.checkpoint(a, "reconcile post-merge numbering")
        self.assertEqual("", self.git(a, "status", "--porcelain"))

    def test_adopt_legacy_ignored_issues_without_index_mutation(self):
        _, root, repo = self.project()
        store = IssueStore(repo)
        issue = store.create("Legacy")
        comment = store.comment(issue.number, "Old comment")
        issue_file = root / issue.path
        lines = issue_file.read_text(encoding="utf-8").splitlines()
        meta = json.loads(lines[1])
        meta["github-local"]["id"] = "I_gl_" + "a" * 16
        lines[1] = json.dumps(meta, separators=(",", ":"))
        issue_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        original_comment = root / comment.path
        legacy_comment = original_comment.with_name("0001.md")
        lines = original_comment.read_text(encoding="utf-8").splitlines()
        cmeta = json.loads(lines[1])
        del cmeta["github-local-comment"]["id"]
        del cmeta["github-local-comment"]["issue_id"]
        lines[1] = json.dumps(cmeta, separators=(",", ":"))
        legacy_comment.write_text("\n".join(lines) + "\n", encoding="utf-8")
        original_comment.unlink()
        exclude = root / ".git" / "info" / "exclude"
        exclude.write_text("/issues/\n/.github-local/\n", encoding="utf-8")
        self.assertEqual(2, len(repo.legacy_exclusions()))
        before = self.git(root, "ls-files", "--", "issues")
        self.assertEqual("", before)
        preview = migration_report(repo)
        self.assertEqual(1, preview["legacyIssueIds"])
        self.assertEqual(1, preview["legacyComments"])
        applied = apply_migration(repo)
        self.assertTrue(applied["migrated"])
        self.assertEqual([], repo.legacy_exclusions())
        self.assertEqual("", self.git(root, "ls-files", "--", "issues"))
        self.assertRegex(store.get(1).issue_id, r"^I_gl_[0-9a-f]{32}$")
        self.assertEqual(1, len(store.comments(1)))
        self.assertIn("issues/", self.git(root, "status", "--short"))
        self.checkpoint(root, "Git-track migrated workflow state")
        self.assertEqual("", self.git(root, "status", "--porcelain"))

    def test_comments_from_parallel_branches_use_unique_filenames(self):
        _, root, repo = self.project()
        issue = IssueStore(repo).create("Shared")
        self.checkpoint(root, "one shared Issue")
        self.git(root, "branch", "feature")
        first = IssueStore(repo).comment(issue.number, "main comment")
        self.checkpoint(root, "main discussion")
        self.git(root, "switch", "-q", "feature")
        branch_repo = Repository.discover(root)
        second = IssueStore(branch_repo).comment(issue.number, "feature comment")
        self.checkpoint(root, "feature discussion")
        self.assertNotEqual(first.path, second.path)
        self.git(root, "switch", "-q", "main")
        self.git(root, "merge", "-q", "--no-ff", "-m", "merge comments", "feature")
        bodies = {entry.body for entry in IssueStore(repo).comments(issue.number)}
        self.assertEqual({"main comment", "feature comment"}, bodies)

    def test_status_has_no_side_effects(self):
        _, root, repo = self.project()
        self.assertEqual("", self.git(root, "status", "--porcelain"))
        self.assertEqual([], collision_report(repo)["collisions"])
        self.assertEqual("", self.git(root, "status", "--porcelain"))


if __name__ == "__main__":
    unittest.main()
