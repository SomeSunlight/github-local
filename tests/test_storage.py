from __future__ import annotations

import json
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from github_local.repository import Repository, RepositoryError
from github_local.storage import IssueStore, StorageError, slugify


class StorageTests(unittest.TestCase):
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
        workspace = Path(temp.name)
        root = workspace / "main"
        root.mkdir()
        self.git(root, "init", "-q", "-b", "main")
        repo = Repository.initialize(root, owner="acme", name="demo")
        counter = {"n": 0}

        def clock():
            counter["n"] += 1
            return f"2026-09-28T18:00:{counter['n']:02d}Z"

        return temp, root, repo, IssueStore(repo, clock=clock)

    def commit_base(self, root: Path) -> None:
        self.git(root, "config", "user.email", "test@example.com")
        self.git(root, "config", "user.name", "Test")
        (root / "README.md").write_text("base\n", encoding="utf-8")
        self.git(root, "add", "README.md")
        self.git(root, "commit", "-qm", "base")

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

    def test_branch_switch_keeps_one_untracked_issue_backlog(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)
        self.commit_base(root)
        store.create("Before branch switch")
        self.git(root, "switch", "-q", "-c", "feature")
        discovered = Repository.discover(root)
        self.assertEqual(root.resolve(), discovered.workflow_root)
        self.assertEqual([1], [item.number for item in IssueStore(discovered).list()])
        self.assertEqual(2, IssueStore(discovered).create("On feature").number)
        self.git(root, "switch", "-q", "main")
        self.assertEqual([1, 2], [item.number for item in IssueStore(Repository.discover(root)).list()])
        status = self.git(root, "status", "--short").stdout
        self.assertNotIn("issues/", status)

    def test_linked_worktree_uses_primary_issue_store_and_shared_allocator(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)
        self.commit_base(root)
        self.assertEqual(1, store.create("Primary").number)

        linked = root.parent / "linked"
        self.git(root, "worktree", "add", "-q", "-b", "feature", str(linked))
        linked_repo = Repository.discover(linked)
        self.assertEqual(linked.resolve(), linked_repo.root)
        self.assertEqual(root.resolve(), linked_repo.workflow_root)
        self.assertEqual(repo.config_dir, linked_repo.config_dir)
        self.assertEqual(root / "issues", linked_repo.issues_dir)

        created = IssueStore(linked_repo).create("Linked")
        self.assertEqual(2, created.number)
        self.assertEqual("issues/0002-linked.md", created.path.as_posix())
        self.assertEqual([1, 2], [item.number for item in IssueStore(repo).list()])

    def test_concurrent_creation_across_worktrees_has_unique_numbers(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)
        self.commit_base(root)
        linked = root.parent / "linked"
        self.git(root, "worktree", "add", "-q", "-b", "feature", str(linked))
        linked_repo = Repository.discover(linked)

        results = []
        errors = []
        barrier = threading.Barrier(12)

        def worker(index):
            try:
                barrier.wait()
                target_repo = repo if index % 2 == 0 else linked_repo
                issue = IssueStore(target_repo).create(f"Cross worktree {index}")
                results.append(issue.number)
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(12)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual([], errors)
        self.assertEqual(list(range(1, 13)), sorted(results))
        self.assertEqual(12, len(list((root / "issues").glob("*.md"))))

    def test_legacy_visible_config_remains_readable_without_migration(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.git(root, "init", "-q", "-b", "main")
        legacy = root / ".github-local" / "config.json"
        legacy.parent.mkdir()
        legacy.write_text(
            json.dumps({"schema": 1, "owner": "acme", "repository": "demo"}) + "\n",
            encoding="utf-8",
        )

        repo = Repository.discover(root)
        self.assertEqual("acme", repo.owner)
        self.assertEqual("demo", repo.name)
        self.assertTrue(repo.repository_id.startswith("R_gl_legacy_"))
        self.assertEqual(legacy.resolve(), repo.config_path.resolve())
        self.assertEqual(1, json.loads(legacy.read_text(encoding="utf-8"))["schema"])

    def test_issue_repository_can_exist_without_git(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name) / "company"
        nested = root / "product" / "src"
        nested.mkdir(parents=True)

        repo = Repository.initialize(root, owner="acme", name="company")
        self.assertFalse(repo.has_git)
        created = IssueStore(repo).create("Company backlog")
        self.assertEqual(1, created.number)

        discovered = Repository.discover(nested)
        self.assertEqual(root.resolve(), discovered.workflow_root)
        self.assertEqual(repo.repository_id, discovered.repository_id)
        self.assertEqual([1], [item.number for item in IssueStore(discovered).list()])

    def test_tracked_issues_are_rejected_explicitly(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.git(root, "init", "-q", "-b", "main")
        issues = root / "issues"
        issues.mkdir()
        (issues / "0001-tracked.md").write_text("# tracked\n", encoding="utf-8")
        self.git(root, "add", "issues/0001-tracked.md")

        with self.assertRaisesRegex(RepositoryError, "outside ordinary Git branch tracking"):
            Repository.initialize(root, owner="acme", name="demo")

    def test_close_reopen_and_state_filter(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)
        first = store.create("One")
        second = store.create("Two")
        self.assertEqual("CLOSED", store.close(first.number).state)
        self.assertEqual([2], [item.number for item in store.list(state="open")])
        self.assertEqual([1], [item.number for item in store.list(state="closed")])
        self.assertEqual("OPEN", store.reopen(first.number).state)
        self.assertEqual([1, 2], [item.number for item in store.list(state="open")])

    def test_edit_preserves_identity_and_comments(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)
        created = store.create("Old title", "Old body")
        comment = store.comment(created.number, "Keep this discussion")
        edited = store.edit(created.number, title="New title", body="New body")
        self.assertEqual(created.issue_id, edited.issue_id)
        self.assertEqual(created.number, edited.number)
        self.assertEqual("New title", edited.title)
        self.assertEqual("New body", edited.body)
        self.assertEqual("issues/0001-new-title.md", edited.path.as_posix())
        self.assertFalse((root / "issues" / "0001-old-title.md").exists())
        comments = IssueStore(repo).comments(created.number)
        self.assertEqual(1, len(comments))
        self.assertEqual(comment.body, comments[0].body)

    def test_comments_are_visible_markdown_and_survive_restart(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)
        issue = store.create("Discuss")
        first = store.comment(issue.number, "First comment")
        second = store.comment(issue.number, "Second\n\nMarkdown comment")
        self.assertEqual("issues/comments/0001/0001.md", first.path.as_posix())
        self.assertEqual("issues/comments/0001/0002.md", second.path.as_posix())
        restarted = IssueStore(repo)
        self.assertEqual(
            ["First comment", "Second\n\nMarkdown comment"],
            [item.body for item in restarted.comments(issue.number)],
        )

    def test_auto_close_only_after_explicit_reference_reaches_accepted_branch(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)
        self.commit_base(root)
        store.reconcile_closing_references()
        issue = store.create("Close after acceptance")

        self.git(root, "switch", "-q", "-c", "feature")
        self.git(root, "commit", "--allow-empty", "-qm", "Fixes #1")
        self.assertEqual([], store.reconcile_closing_references())
        self.assertEqual("OPEN", store.get(issue.number).state)

        self.git(root, "switch", "-q", "main")
        self.git(root, "merge", "--ff-only", "-q", "feature")
        self.assertEqual([1], store.reconcile_closing_references())
        closed = store.get(issue.number)
        self.assertEqual("CLOSED", closed.state)

    def test_plain_issue_mention_never_auto_closes(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)
        self.commit_base(root)
        store.reconcile_closing_references()
        issue = store.create("Explicit references only")

        self.git(root, "commit", "--allow-empty", "-qm", "Discuss #1")
        self.assertEqual([], store.reconcile_closing_references())
        self.assertEqual("OPEN", store.get(issue.number).state)

        self.git(root, "commit", "--allow-empty", "-qm", "Closes #1")
        self.assertEqual([1], store.reconcile_closing_references())
        self.assertEqual("CLOSED", store.get(issue.number).state)

    def test_reopen_is_not_undone_by_an_old_closing_commit(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)
        self.commit_base(root)
        store.reconcile_closing_references()
        issue = store.create("May reopen")
        self.git(root, "commit", "--allow-empty", "-qm", "Resolves #1")
        self.assertEqual([1], store.reconcile_closing_references())
        self.assertEqual("OPEN", store.reopen(issue.number).state)
        self.assertEqual([], store.reconcile_closing_references())
        self.assertEqual("OPEN", store.get(issue.number).state)

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


    def test_labels_filter_search_edit_and_legacy_compatibility(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)

        first = store.create(
            "Parser bug",
            "Fails on UTF-8 input",
            labels=["bug", "priority:high", "BUG"],
        )
        second = store.create("Parser guide", "Document the parser", labels=["docs"])

        self.assertEqual(("bug", "priority:high"), first.labels)
        self.assertEqual([1], [item.number for item in store.list(labels=["BUG"])])
        self.assertEqual(
            [1],
            [item.number for item in store.list(labels=["bug", "priority:high"])],
        )
        self.assertEqual([1, 2], [item.number for item in store.list(search="parser")])
        self.assertEqual([1], [item.number for item in store.list(search="UTF-8")])
        self.assertEqual([2], [item.number for item in store.list(search="DOCS")])

        edited = store.edit(
            first.number,
            add_labels=["ready", "Priority:High"],
            remove_labels=["BUG"],
        )
        self.assertEqual(("priority:high", "ready"), edited.labels)

        path = root / second.path
        lines = path.read_text(encoding="utf-8").splitlines()
        metadata = json.loads(lines[1])
        metadata["github-local"].pop("labels")
        lines[1] = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        self.assertEqual((), IssueStore(repo).get(second.number).labels)


    def test_deleted_issue_numbers_are_never_reused(self):
        temp, root, repo, store = self.make_repo()
        self.addCleanup(temp.cleanup)
        self.assertEqual(1, store.create("One").number)
        self.assertEqual(2, store.create("Two").number)
        store.delete(2)
        self.assertEqual(3, store.create("Three").number)
        store.delete_all()
        self.assertEqual(4, store.create("Four").number)

    def test_nested_repository_requires_qualified_closing_reference(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.git(root, "init", "-q", "-b", "main")
        self.git(root, "config", "user.email", "test@example.com")
        self.git(root, "config", "user.name", "Test")
        (root / "README.md").write_text("base\n", encoding="utf-8")
        self.git(root, "add", "README.md")
        self.git(root, "commit", "-qm", "base")

        product = root / "product-a"
        product.mkdir()
        repo = Repository.initialize(product, owner="acme", name="product-a")
        store = IssueStore(repo)
        issue = store.create("Nested close")
        store.reconcile_closing_references()

        self.git(root, "commit", "--allow-empty", "-qm", "Fixes #1")
        self.assertEqual([], store.reconcile_closing_references())
        self.assertEqual("OPEN", store.get(issue.number).state)

        self.git(root, "commit", "--allow-empty", "-qm", "Fixes acme/product-a#1")
        self.assertEqual([1], store.reconcile_closing_references())
        self.assertEqual("CLOSED", store.get(issue.number).state)


if __name__ == "__main__":
    unittest.main()
