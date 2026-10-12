"""Owner regression: migration of independently numbered nested Issue stores."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from github_local.migration import apply_migration
from github_local.reconcile import apply_reconciliation, collision_report
from github_local.repository import Repository
from github_local.storage import IssueStore, StorageError


class MigratedNestedCollisionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "P1-LF"
        self.root.mkdir()
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "tester@example.com")
        self.git("config", "user.name", "Tester")
        self.root_repo = Repository.initialize(self.root, owner="acme", name="P1")
        self.git("add", "-A")
        self.git("commit", "-qm", "initialize")
        (self.root / "F2").mkdir()
        (self.root / "doc").mkdir()
        self.f2 = Repository.initialize(self.root / "F2", owner="acme", name="F2")
        self.doc = Repository.initialize(self.root / "doc", owner="acme", name="doc")
        # All these were legitimate independently numbered Issues before
        # github-local switched from per-folder to per-Git number allocation.
        records = [
            (self.f2, 1, "Finalize positioning contract"),
            (self.f2, 2, "Update positioning samples"),
            (self.doc, 1, "New parameter BusinessDataModel"),
            (self.root_repo, 2, "AMS-6345 positioning systems"),
            (self.root_repo, 5, "Already unique Issue"),
        ]
        for owner, number, title in records:
            path = owner.issues_dir / f"{number:04d}-{title.lower().replace(' ', '-')}.md"
            path.write_text(f"# {title}\n\n## Why\nLegacy content.\n", encoding="utf-8")
        for owner in [self.root_repo, self.f2, self.doc]:
            apply_migration(owner)
        self.expected_ids = {
            (owner.repository_id, item.number): item.issue_id
            for owner in (self.root_repo, self.f2, self.doc)
            for item in IssueStore(owner).list()
        }

    def git(self, *args):
        return subprocess.run(["git", "-C", str(self.root), *args],
                              check=True, text=True, capture_output=True).stdout.strip()

    def cli(self, *args, input_text=None):
        return subprocess.run(
            [sys.executable, "-m", "github_local.cli", *args],
            cwd=self.root, text=True, input=input_text, capture_output=True,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
        )

    def test_status_warns_without_arbitrary_keeper_or_side_effects(self):
        initial = self.git("status", "--porcelain")
        response = self.cli("status", "-R", ".")
        self.assertEqual(0, response.returncode, response.stderr)
        self.assertTrue(response.stdout.startswith(
            "ACTION REQUIRED: 2 duplicate Issue numbers (#1, #2)"
        ), response.stdout)
        self.assertIn("4", response.stdout)  # four competing Issue records
        self.assertIn("F2/issues/0001-", response.stdout)
        self.assertIn("doc/issues/0001-", response.stdout)
        self.assertIn("issues/0002-", response.stdout)
        self.assertIn("keep requires owner decision", response.stdout)
        self.assertIn("No files have been changed by status.", response.stdout)
        self.assertNotIn("source_branch: unknown", response.stdout)
        self.assertEqual(initial, self.git("status", "--porcelain"))

        machine = self.cli("status", "-R", ".", "--json")
        self.assertEqual(0, machine.returncode, machine.stderr)
        data = json.loads(machine.stdout)
        self.assertFalse(data["ok"])
        self.assertTrue(data["actionRequired"])
        self.assertEqual(2, data["collisionCount"])
        self.assertEqual(4, data["affectedIssues"])
        self.assertEqual([1, 2], [x["number"] for x in data["collisions"]])
        self.assertTrue(all(x["keep"] is None for x in data["collisions"]))
        self.assertTrue(all(x["manualChoiceRequired"] for x in data["collisions"]))
        self.assertTrue(all(len(x["candidates"]) == 2 for x in data["collisions"]))

        preview = self.cli("issue", "reconcile", "-R", ".", "--dry-run")
        self.assertEqual(0, preview.returncode, preview.stderr)
        self.assertIn("no automatic renumbering", preview.stdout)
        self.assertEqual(initial, self.git("status", "--porcelain"))

    def test_yes_alone_cannot_rename_ambiguous_migrated_issues(self):
        initial = self.git("status", "--porcelain")
        attempt = self.cli("issue", "reconcile", "-R", ".", "--yes")
        self.assertNotEqual(0, attempt.returncode)
        self.assertIn("--keep-id", attempt.stderr)
        self.assertEqual(initial, self.git("status", "--porcelain"))
        with self.assertRaisesRegex(StorageError, "choose one --keep-id"):
            apply_reconciliation(self.root_repo)

    def test_owner_selects_each_keeper_and_preserves_issues(self):
        # Sorted choices: #1 F2/doc, #2 F2/root. Pick doc #1 and root #2.
        response = self.cli("issue", "reconcile", "-R", ".", input_text="2\n2\ny\n")
        self.assertEqual(0, response.returncode, response.stderr + response.stdout)
        self.assertIn("Proposed renumbering after your selection:", response.stdout)
        self.assertIn("#6", response.stdout)
        self.assertIn("#7", response.stdout)
        self.assertEqual([1], [i.number for i in IssueStore(self.doc).list()])
        self.assertEqual([2, 5], [i.number for i in IssueStore(self.root_repo).list()])
        self.assertEqual([6, 7], [i.number for i in IssueStore(self.f2).list()])
        self.assertEqual(
            self.expected_ids[(self.f2.repository_id, 1)],
            IssueStore(self.f2).get(6).issue_id,
        )
        self.assertEqual(
            self.expected_ids[(self.f2.repository_id, 2)],
            IssueStore(self.f2).get(7).issue_id,
        )
        self.assertIn("from #1 (source branch not recorded", IssueStore(self.f2).get(6).body)
        self.assertIn("from #2 (source branch not recorded", IssueStore(self.f2).get(7).body)
        self.assertEqual({}, IssueStore(self.root_repo)._collision_groups())
        after = self.cli("status", "-R", ".")
        self.assertEqual(0, after.returncode, after.stderr)
        self.assertTrue(after.stdout.startswith("OK: no Issue number collisions"))
        self.assertTrue(self.git("status", "--porcelain"))

    def test_batch_explicit_keepers_and_invalid_selections(self):
        doc_id = IssueStore(self.doc).get(1).issue_id
        root_id = IssueStore(self.root_repo).get(2).issue_id
        f2_first_id = IssueStore(self.f2).get(1).issue_id

        with self.assertRaisesRegex(StorageError, "more than one --keep-id"):
            collision_report(self.root_repo, keep_id=[doc_id, f2_first_id])

        selected = collision_report(self.root_repo, keep_id=[doc_id, root_id])
        self.assertFalse(selected["manualChoiceRequired"])
        self.assertEqual([6, 7],
                         [item["to"] for group in selected["collisions"]
                          for item in group["rename"]])
        response = self.cli(
            "issue", "reconcile", "-R", ".",
            "--keep-id", doc_id, "--keep-id", root_id, "--yes", "--json",
        )
        self.assertEqual(0, response.returncode, response.stderr)
        self.assertTrue(json.loads(response.stdout)["applied"])
        self.assertEqual([6, 7], [i.number for i in IssueStore(self.f2).list()])


if __name__ == "__main__":
    unittest.main()
