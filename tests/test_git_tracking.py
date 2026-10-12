from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from github_local.repository import Repository
from github_local.storage import IssueStore, StorageError
from github_local.reconcile import collision_report, apply_reconciliation
from github_local.migration import migration_report, apply_migration, _frontmatter, _issue_record


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
        preview = subprocess.run(
            [sys.executable, "-m", "github_local.cli", "issue", "reconcile",
             "-R", ".", "--dry-run", "--json", "--source-branch", "Windows"],
            cwd=a, text=True, capture_output=True, check=True,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
        )
        self.assertEqual(2, json.loads(preview.stdout)["collisions"][0]["rename"][0]["to"])
        self.assertEqual(1, len(collision_report(repo)["collisions"]))
        command = subprocess.run(
            [sys.executable, "-m", "github_local.cli", "issue", "reconcile",
             "-R", ".", "--yes", "--json", "--source-branch", "Windows"],
            cwd=a, text=True, capture_output=True, check=True,
            env={**os.environ, "PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")},
        )
        applied = json.loads(command.stdout)
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

    def test_nested_f2_plain_markdown_migration_preserves_issue_and_comment(self):
        """Owner regression: nested F2 has only human-authored numbered Markdown."""
        _, root, parent = self.project()
        nested = root / "F2"
        nested.mkdir()
        repo = Repository.initialize(nested, owner="acme", name="F2")
        (root / "F1").mkdir()
        f1 = Repository.initialize(root / "F1", owner="acme", name="F1")
        IssueStore(f1).create("Other team's Issue")  # Must not affect F2 metadata.
        source = nested / "issues" / "0004-abc.md"
        original = "# abc\n\n## Why\nA reason.\n\n## Scope\nA change.\n\n## Out of scope\nNone.\n"
        source.write_text(original, encoding="utf-8")
        comment_dir = nested / "issues" / "comments" / "0004"
        comment_dir.mkdir(parents=True)
        comment = comment_dir / "0001.md"
        comment.write_text("Original discussion\n\nSecond paragraph.\n", encoding="utf-8")
        unrelated = nested / "issues" / "scratch.md"
        unrelated.write_text("# A note, not a numbered Issue\n", encoding="utf-8")

        before = self.git(root, "status", "--porcelain")
        preview = migration_report(repo)
        self.assertEqual(1, preview["issues"])
        self.assertEqual(1, preview["plainMarkdownIssues"])
        self.assertEqual(1, preview["legacyIssueIds"])
        self.assertEqual(1, preview["plainMarkdownComments"])
        self.assertEqual(1, preview["legacyComments"])
        self.assertEqual(original, source.read_text(encoding="utf-8"))
        self.assertEqual("Original discussion\n\nSecond paragraph.\n", comment.read_text())
        self.assertEqual(before, self.git(root, "status", "--porcelain"))

        applied = apply_migration(repo)
        self.assertTrue(applied["migrated"])
        result = IssueStore(repo).get(4)
        self.assertEqual(4, result.number)
        self.assertEqual("abc", result.title)
        self.assertEqual("## Why\nA reason.\n\n## Scope\nA change.\n\n## Out of scope\nNone.", result.body)
        self.assertEqual("OPEN", result.state)
        self.assertRegex(result.issue_id, r"^I_gl_[0-9a-f]{32}$")
        meta = json.loads(source.read_text(encoding="utf-8").splitlines()[1])
        self.assertEqual("plain-markdown", meta["github-local"]["imported_from"])
        comments = IssueStore(repo).comments(4)
        self.assertEqual(1, len(comments))
        self.assertEqual("Original discussion\n\nSecond paragraph.", comments[0].body)
        self.assertRegex(comments[0].path.name, r"^0001-original-discussion-[0-9a-f]{8}[.]md$")
        self.assertFalse(comment.exists())
        self.assertEqual("# A note, not a numbered Issue\n", unrelated.read_text())
        self.assertEqual({}, IssueStore(repo)._collision_groups())

        # Running migration twice must not generate new IDs or touch the data.
        after = source.read_bytes()
        comment_after = (nested / comments[0].path).read_bytes()
        again = migration_report(repo)
        self.assertEqual(0, again["plainMarkdownIssues"])
        self.assertEqual(0, again["legacyIssueIds"])
        self.assertEqual(0, again["plainMarkdownComments"])
        self.assertEqual(0, again["legacyComments"])
        apply_migration(repo)
        self.assertEqual(after, source.read_bytes())
        self.assertEqual(comment_after, (nested / comments[0].path).read_bytes())
        self.assertEqual(result.issue_id, IssueStore(repo).get(4).issue_id)

    def test_migration_rejects_malformed_structured_metadata(self):
        with tempfile.TemporaryDirectory() as workspace:
            path = Path(workspace) / "0004-abc.md"
            path.write_text('---\n{"github-local": invalid}\n---\n# abc\n',
                            encoding="utf-8")
            with self.assertRaisesRegex(StorageError,
                                        r"invalid JSON in front matter at line 2, column"):
                _frontmatter(path)
            path.write_text('---\n{"title": "abc"}\n---\n# abc\n',
                            encoding="utf-8")
            with self.assertRaisesRegex(StorageError,
                                        r"must contain the 'github-local' metadata object"):
                _frontmatter(path)
            path.write_text('---\n{"github-local": {"schema": 1}}\n---\n# abc\n',
                            encoding="utf-8")
            with self.assertRaisesRegex(StorageError,
                                        r"must use schema 1 and match its filename number"):
                _issue_record(path)
            self.assertEqual(
                {"schema": 1}, _frontmatter(path)[0]["github-local"]
            )

    def test_plain_markdown_without_issue_heading_fails_without_touching_content(self):
        _, root, repo = self.project()
        path = root / "issues" / "0004-abc.md"
        original = "## Why\nMissing top-level title.\n"
        path.write_text(original, encoding="utf-8")
        with self.assertRaisesRegex(StorageError, "expected a numbered Issue filename"):
            migration_report(repo)
        self.assertEqual(original, path.read_text(encoding="utf-8"))

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


    def test_hidden_git_exclude_refuses_write_until_migrated(self):
        _, root, repo = self.project()
        excluded = root / ".git" / "info" / "exclude"
        excluded.write_text("/issues/\n/.github-local/\n", encoding="utf-8")
        with self.assertRaisesRegex(Exception, "ignored by Git"):
            IssueStore(repo).create("Invisible")
        self.assertEqual(0, len(list((root / "issues").glob("*.md"))))
        self.assertTrue(repo.ignored_durable_paths())
        self.assertEqual(2, len(repo.legacy_exclusions()))
        apply_migration(repo)
        self.assertEqual([], repo.ignored_durable_paths())
        self.assertEqual(1, IssueStore(repo).create("Visible").number)

    def test_custom_gitignore_must_not_hide_issue_storage(self):
        _, root, repo = self.project()
        ignore = root / ".gitignore"
        ignore.write_text(ignore.read_text(encoding="utf-8") + "\n/issues/\n",
                          encoding="utf-8")
        with self.assertRaisesRegex(Exception, "ignored by Git"):
            IssueStore(repo).create("Should fail")
        self.assertTrue(repo.ignored_durable_paths())
        self.assertTrue(repo.git_repository_id)

    def test_two_nested_issue_repositories_share_numbers_and_identity(self):
        _, root, _ = self.project()
        one = root / "a"
        two = root / "b"
        one.mkdir()
        two.mkdir()
        ra = Repository.initialize(one, owner="acme", name="a")
        rb = Repository.initialize(two, owner="acme", name="b")
        a = IssueStore(ra).create("A")
        b = IssueStore(rb).create("B")
        self.assertEqual((1, 2), (a.number, b.number))
        self.assertNotEqual(a.issue_id, b.issue_id)
        self.assertEqual(ra.git_repository_id, rb.git_repository_id)
        self.assertEqual([1], [i.number for i in IssueStore(ra).list()])
        self.assertEqual([2], [i.number for i in IssueStore(rb).list()])


if __name__ == "__main__":
    unittest.main()
