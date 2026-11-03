from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from github_local.fs_cleanup import CleanupError, remove_empty_directory, remove_owned_tree
from github_local.repository import Repository
from github_local.storage import IssueStore


class CleanupTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.work = self.root / "project"
        self.work.mkdir()
        subprocess.run(["git", "-C", str(self.work), "init", "-q", "-b", "main"],
                       check=True)
        self.repo = Repository.initialize(self.work, owner="test", name="demo")
        self.store = IssueStore(self.repo)

    def test_transient_lock_retries_then_succeeds(self):
        owned = self.root / "owned"
        owned.mkdir()
        (owned / "disposable.txt").write_text("test", encoding="utf-8")
        real = shutil.rmtree
        calls = []

        def flaky(path):
            calls.append(path)
            if len(calls) == 1:
                raise PermissionError("simulated AV lock")
            real(path)

        with patch("github_local.fs_cleanup.shutil.rmtree", side_effect=flaky):
            self.assertTrue(remove_owned_tree(owned, delays=(0, 0)))
        self.assertEqual(2, len(calls))
        self.assertTrue(remove_owned_tree(owned, delays=(0,)))

    def test_persistent_lock_of_fileless_skeleton_is_benign(self):
        owned = self.root / "orphan"
        (owned / "references" / "deep").mkdir(parents=True)
        with patch("github_local.fs_cleanup.shutil.rmtree", side_effect=PermissionError("held")):
            with patch("github_local.fs_cleanup.Path.rmdir", side_effect=PermissionError("held")):
                self.assertTrue(remove_owned_tree(owned, delays=(0,)))
        self.assertTrue(owned.exists())
        self.assertTrue(remove_owned_tree(owned, delays=(0,)))
        self.assertTrue(remove_empty_directory(owned, delays=(0,)))

    def test_locked_comments_preserve_authoritative_issue(self):
        issue = self.store.create("Keep")
        self.store.comment(issue.number, "Important discussion")
        with patch("github_local.fs_cleanup.shutil.rmtree", side_effect=PermissionError("held")):
            with self.assertRaisesRegex(CleanupError, "still contains files"):
                self.store.delete(issue.number)
        self.assertEqual(issue.issue_id, self.store.get(issue.number).issue_id)
        self.assertEqual(1, len(self.store.comments(issue.number)))

    def test_delete_all_tolerates_fileless_remainder(self):
        self.store.create("One")
        self.store.create("Two")

        def partial(path):
            # The files are deleted, but Windows prevents the final directory
            # removal. The next operation must not be blocked by this.
            for file in Path(path).rglob("*"):
                if file.is_file():
                    file.unlink()
            raise PermissionError("directory handle held")

        with patch("github_local.fs_cleanup.shutil.rmtree", side_effect=partial):
            self.assertEqual(2, self.store.delete_all())
        self.assertEqual([], self.store.list())
        self.assertEqual(3, self.store.create("Next").number)

    def test_deinitialize_tolerates_empty_nested_comments(self):
        skeleton = self.repo.issues_dir / "comments" / "0001" / "deep"
        skeleton.mkdir(parents=True)
        self.repo.deinitialize()
        self.assertFalse(self.repo.config_path.exists())
        self.assertFalse(any(self.repo.issues_dir.rglob("*")))

    def test_deinitialize_rejects_unknown_file(self):
        skeleton = self.repo.issues_dir / "comments" / "0001"
        skeleton.mkdir(parents=True)
        (skeleton / "unknown.txt").write_text("keep", encoding="utf-8")
        with self.assertRaisesRegex(Exception, "still contains Issues"):
            self.repo.deinitialize()
        self.assertTrue(self.repo.config_path.exists())

    def test_reparse_and_symlink_paths_are_not_traversed(self):
        external = self.root / "external"
        external.mkdir()
        (external / "keep.txt").write_text("valuable", encoding="utf-8")
        owned = self.root / "owned"
        owned.mkdir()
        try:
            (owned / "link").symlink_to(external, target_is_directory=True)
        except OSError:
            self.skipTest("directory symlinks not available")
        with self.assertRaises(CleanupError):
            remove_owned_tree(owned, delays=(0,))
        self.assertTrue((external / "keep.txt").exists())


if __name__ == "__main__":
    unittest.main()
