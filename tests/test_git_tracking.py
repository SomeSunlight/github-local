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

