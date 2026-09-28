from __future__ import annotations

import json
import tempfile
import threading
import unittest
from pathlib import Path

from github_local.repository import Repository
from github_local.storage import IssueStore, StorageError, slugify


class StorageTests(unittest.TestCase):
    def make_repo(self):
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / ".git").mkdir()
        repo = Repository.initialize(root, owner="acme", name="demo")
        counter = {"n": 0}

        def clock():
            counter["n"] += 1
            return f"2026-09-28T18:00:{counter['n']:02d}Z"

        return temp, root, repo, IssueStore(repo, clock=clock)

    def test_create_list_view_survives_new_store_instance(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)
        created = store.create("First issue", "Body äöü")
        self.assertEqual(1, created.number)
        self.assertEqual("Body äöü", created.body)
        restarted = IssueStore(repo)
        listed = restarted.list()
        self.assertEqual([1], [i.number for i in listed])
        viewed = restarted.get(1)
        self.assertEqual("First issue", viewed.title)
        self.assertEqual("Body äöü", viewed.body)
        self.assertEqual("issues/0001-first-issue.md", viewed.path.as_posix())

    def test_numbers_are_monotonic(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)
        self.assertEqual(1, store.create("One").number)
        self.assertEqual(2, store.create("Two").number)
        self.assertEqual(3, store.create("Three").number)

    def test_concurrent_creation_has_unique_numbers(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)
        results = []
        errors = []
        barrier = threading.Barrier(12)

        def worker(index):
            try:
                barrier.wait()
                issue = IssueStore(repo).create(f"Concurrent {index}")
                results.append(issue.number)
            except BaseException as exc:  # surfaced below
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual([], errors)
        self.assertEqual(list(range(1, 13)), sorted(results))
        self.assertEqual(12, len(list((root / "issues").glob("*.md"))))
        self.assertEqual([], list((root / "issues").glob(".issue-*.tmp")))

    def test_windows_reserved_slug_is_avoided(self):
        self.assertEqual("issue-con", slugify("CON"))
        self.assertEqual("issue-prn", slugify("PRN"))

    def test_corrupt_metadata_fails_explicitly(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)
        path = root / "issues" / "0001-broken.md"
        path.write_text("---\nnot-json\n---\n# Broken\n", encoding="utf-8")
        with self.assertRaisesRegex(StorageError, "invalid Issue metadata"):
            store.list()

    def test_filename_number_must_match_metadata(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)
        metadata = {"github-local":{"schema":1,"id":"I_x","number":9,"state":"OPEN","created_at":"x","updated_at":"x"}}
        path = root / "issues" / "0001-wrong.md"
        path.write_text(f"---\n{json.dumps(metadata)}\n---\n# Wrong\n", encoding="utf-8")
        with self.assertRaisesRegex(StorageError, "does not match filename"):
            store.list()


if __name__ == "__main__":
    unittest.main()
