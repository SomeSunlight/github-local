from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", "-b", "main", str(self.root)], check=True)
        src = Path(__file__).resolve().parents[1] / "src"
        self.env = dict(os.environ, PYTHONPATH=str(src))

    def tearDown(self):
        self.temp.cleanup()

    def run_cli(self, *args, input_text=None, cwd=None, select_repo=True):
        argv = list(args)
        if (
            select_repo
            and len(argv) >= 2
            and argv[0] == "issue"
            and argv[1] not in ("init", "--help", "-h")
            and "-R" not in argv
            and "--repo" not in argv
        ):
            argv[2:2] = ["-R", "."]
        return subprocess.run(
            [sys.executable, "-m", "github_local.cli", *argv],
            cwd=cwd or self.root, env=self.env, text=True, input=input_text,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )

    def test_vertical_cli_slice_with_json(self):
        init = self.run_cli("init", "--owner", "acme", "--repo", "demo")
        self.assertEqual(0, init.returncode, init.stderr)
        create = self.run_cli(
            "issue", "create", "--title", "Überprüfung", "--body", "Markdown body",
            "--json", "number,title,state,path,url",
        )
        self.assertEqual(0, create.returncode, create.stderr)
        payload = json.loads(create.stdout)
        self.assertEqual(1, payload["number"])
        self.assertEqual("Überprüfung", payload["title"])
        self.assertEqual("OPEN", payload["state"])
        self.assertTrue(payload["path"].startswith("issues/0001-"))
        self.assertEqual("github-local://acme/demo/issues/1", payload["url"])

        listing = self.run_cli("issue", "list", "--json", "number,title,state")
        self.assertEqual(0, listing.returncode, listing.stderr)
        self.assertEqual([{"number": 1, "title": "Überprüfung", "state": "OPEN"}], json.loads(listing.stdout))

        view = self.run_cli("issue", "view", "1", "--json", "number,title,body")
        self.assertEqual(0, view.returncode, view.stderr)
        self.assertEqual({"number": 1, "title": "Überprüfung", "body": "Markdown body"}, json.loads(view.stdout))

    def test_issue_lifecycle_cli(self):
        self.assertEqual(0, self.run_cli("init", "--owner", "acme", "--repo", "demo").returncode)
        created = self.run_cli(
            "issue", "create", "--title", "Old title", "--body", "Old body",
            "--json", "number,state,title",
        )
        self.assertEqual(0, created.returncode, created.stderr)
        self.assertEqual(
            {"number": 1, "state": "OPEN", "title": "Old title"},
            json.loads(created.stdout),
        )

        comment = self.run_cli("issue", "comment", "1", "--body", "Visible note")
        self.assertEqual(0, comment.returncode, comment.stderr)
        self.assertEqual("issues/comments/0001/0001.md", comment.stdout.strip())

        edited = self.run_cli(
            "issue", "edit", "1", "--title", "New title", "--body", "New body",
            "--json", "number,state,title,body,path",
        )
        self.assertEqual(0, edited.returncode, edited.stderr)
        payload = json.loads(edited.stdout)
        self.assertEqual("New title", payload["title"])
        self.assertEqual("New body", payload["body"])
        self.assertEqual("issues/0001-new-title.md", payload["path"])

        closed = self.run_cli("issue", "close", "1", "--json", "number,state")
        self.assertEqual(0, closed.returncode, closed.stderr)
        self.assertEqual({"number": 1, "state": "CLOSED"}, json.loads(closed.stdout))

        open_list = self.run_cli("issue", "list", "--state", "open", "--json", "number")
        self.assertEqual([], json.loads(open_list.stdout))
        closed_list = self.run_cli("issue", "list", "--state", "closed", "--json", "number")
        self.assertEqual([{"number": 1}], json.loads(closed_list.stdout))

        reopened = self.run_cli("issue", "reopen", "1", "--json", "number,state")
        self.assertEqual(0, reopened.returncode, reopened.stderr)
        self.assertEqual({"number": 1, "state": "OPEN"}, json.loads(reopened.stdout))

        view = self.run_cli("issue", "view", "1")
        self.assertEqual(0, view.returncode, view.stderr)
        self.assertIn("New body", view.stdout)
        self.assertNotIn("Visible note", view.stdout)

        view_with_comments = self.run_cli("issue", "view", "1", "--comments")
        self.assertEqual(0, view_with_comments.returncode, view_with_comments.stderr)
        self.assertIn("Visible note", view_with_comments.stdout)

    def test_issue_develop_matches_gh_shape(self):
        subprocess.run(["git", "-C", str(self.root), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(self.root), "config", "user.name", "Test"], check=True)
        (self.root / "README.md").write_text("base\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(self.root), "add", "README.md"], check=True)
        subprocess.run(["git", "-C", str(self.root), "commit", "-qm", "base"], check=True)

        self.assertEqual(0, self.run_cli("init", "--owner", "acme", "--repo", "demo").returncode)
        created = self.run_cli(
            "issue", "create", "--title", "Implement thing", "--json", "number",
        )
        self.assertEqual({"number": 1}, json.loads(created.stdout))

        develop = self.run_cli(
            "issue", "develop", "1", "--json", "issue,branch,current,relation",
        )
        self.assertEqual(0, develop.returncode, develop.stderr)
        self.assertEqual(
            {
                "issue": 1,
                "branch": "issue-1-implement-thing",
                "current": False,
                "relation": "explicit",
            },
            json.loads(develop.stdout),
        )
        self.assertEqual(
            "main",
            subprocess.run(
                ["git", "-C", str(self.root), "branch", "--show-current"],
                check=True, text=True, stdout=subprocess.PIPE,
            ).stdout.strip(),
        )

        linked = self.run_cli(
            "issue", "develop", "--list", "1", "--json", "branch,current,relation",
        )
        self.assertEqual(
            [{
                "branch": "issue-1-implement-thing",
                "current": False,
                "relation": "explicit",
            }],
            json.loads(linked.stdout),
        )

        checkout = self.run_cli(
            "issue", "develop", "1", "--checkout",
            "--json", "branch,current,relation",
        )
        self.assertEqual(
            {
                "branch": "issue-1-implement-thing",
                "current": True,
                "relation": "explicit",
            },
            json.loads(checkout.stdout),
        )

        subprocess.run(
            ["git", "-C", str(self.root), "branch", "-m", "renamed/change"],
            check=True,
        )
        renamed = self.run_cli(
            "issue", "develop", "--list", "1", "--json", "branch,current,relation",
        )
        self.assertEqual(
            [{
                "branch": "renamed/change",
                "current": True,
                "relation": "explicit",
            }],
            json.loads(renamed.stdout),
        )

    def test_issue_list_defaults_to_open_and_ls_alias_matches(self):
        self.assertEqual(0, self.run_cli("init", "--owner", "acme", "--repo", "demo").returncode)
        self.run_cli("issue", "create", "--title", "Open one")
        self.run_cli("issue", "create", "--title", "Closed one")
        self.run_cli("issue", "close", "2")

        listing = self.run_cli("issue", "list", "--json", "number,state")
        self.assertEqual([{"number": 1, "state": "OPEN"}], json.loads(listing.stdout))

        alias = self.run_cli("issue", "ls", "--state", "all", "--json", "number,state")
        self.assertEqual(
            [
                {"number": 1, "state": "OPEN"},
                {"number": 2, "state": "CLOSED"},
            ],
            json.loads(alias.stdout),
        )

    def test_close_and_reopen_comment_flags_use_durable_comments(self):
        self.assertEqual(0, self.run_cli("init", "--owner", "acme", "--repo", "demo").returncode)
        self.run_cli("issue", "create", "--title", "Lifecycle")

        closed = self.run_cli("issue", "close", "1", "--comment", "Done for now")
        self.assertEqual(0, closed.returncode, closed.stderr)
        reopened = self.run_cli("issue", "reopen", "1", "--comment", "Needs more work")
        self.assertEqual(0, reopened.returncode, reopened.stderr)

        view = self.run_cli("issue", "view", "1", "--comments")
        self.assertIn("Done for now", view.stdout)
        self.assertIn("Needs more work", view.stdout)

    def test_version_is_available_without_repository_initialization(self):
        result = self.run_cli("--version")
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual("", result.stderr)
        self.assertRegex(
            result.stdout.strip(),
            r"^github-local 0\.1\.0(?: \((?:[^@()]+|detached)@[0-9a-f]{7}(?:, dirty)?\))?$",
        )

    def test_not_initialized_is_stable_exit_code(self):
        result = self.run_cli("issue", "list")
        self.assertEqual(3, result.returncode)
        self.assertIn("not initialized", result.stderr)

    def test_unknown_json_field_is_usage_error(self):
        self.assertEqual(0, self.run_cli("init").returncode)
        result = self.run_cli("issue", "list", "--json", "number,nope")
        self.assertEqual(2, result.returncode)
        self.assertIn("unknown JSON field", result.stderr)

    def test_missing_issue_is_stable_exit_code(self):
        self.assertEqual(0, self.run_cli("init").returncode)
        result = self.run_cli("issue", "view", "99")
        self.assertEqual(4, result.returncode)
        self.assertIn("Issue #99 not found", result.stderr)


    def test_issue_labels_and_search_match_gh_flag_names(self):
        self.assertEqual(0, self.run_cli("init", "--owner", "acme", "--repo", "demo").returncode)

        created = self.run_cli(
            "issue", "create",
            "--title", "Parser bug",
            "--body", "Fails on UTF-8 input",
            "--label", "bug,priority:high",
            "--json", "number,labels",
        )
        self.assertEqual(0, created.returncode, created.stderr)
        self.assertEqual(
            {"number": 1, "labels": ["bug", "priority:high"]},
            json.loads(created.stdout),
        )
        second = self.run_cli(
            "issue", "create",
            "--title", "Parser guide",
            "--body", "Document the parser",
            "--label", "docs",
        )
        self.assertEqual(0, second.returncode, second.stderr)

        by_label = self.run_cli(
            "issue", "list",
            "--label", "BUG",
            "--label", "priority:high",
            "--json", "number,labels",
        )
        self.assertEqual(0, by_label.returncode, by_label.stderr)
        self.assertEqual(
            [{"number": 1, "labels": ["bug", "priority:high"]}],
            json.loads(by_label.stdout),
        )

        by_search = self.run_cli(
            "issue", "list", "-S", "parser", "--json", "number",
        )
        self.assertEqual(0, by_search.returncode, by_search.stderr)
        self.assertEqual([{"number": 1}, {"number": 2}], json.loads(by_search.stdout))

        edited = self.run_cli(
            "issue", "edit", "1",
            "--remove-label", "BUG",
            "--add-label", "ready",
            "--json", "number,labels",
        )
        self.assertEqual(0, edited.returncode, edited.stderr)
        self.assertEqual(
            {"number": 1, "labels": ["priority:high", "ready"]},
            json.loads(edited.stdout),
        )

        missing = self.run_cli(
            "issue", "list", "-l", "bug", "--json", "number",
        )
        self.assertEqual(0, missing.returncode, missing.stderr)
        self.assertEqual([], json.loads(missing.stdout))


    def test_help_surfaces_include_concise_supported_examples(self):
        cases = [
            (
                ("--help",),
                [
                    "Examples:",
                    "github-local init --owner local --repo my-project",
                    'github-local issue create -R . --title "Add validation" --label bug',
                    "github-local issue list -R .",
                ],
            ),
            (
                ("issue", "--help"),
                [
                    "Examples:",
                    "github-local issue list",
                    "github-local issue view 12 --comments",
                    "github-local issue develop -R . 12 --checkout",
                ],
            ),
            (
                ("issue", "create", "--help"),
                [
                    "Examples:",
                    'github-local issue create --title "Fix parser" --body "Reject invalid input." --label bug',
                    '--json number,title,labels',
                ],
            ),
            (
                ("issue", "list", "--help"),
                [
                    "Examples:",
                    "github-local issue list -R . --label bug --search parser",
                    "github-local issue list -R . --state all --json number,state,title,labels",
                ],
            ),
            (
                ("issue", "develop", "--help"),
                [
                    "Examples:",
                    "github-local issue develop 12 --checkout",
                    "github-local issue develop -R . --list 12 --json branch,head,current,relation",
                ],
            ),
        ]

        for argv, expected in cases:
            with self.subTest(argv=argv):
                result = self.run_cli(*argv)
                self.assertEqual(0, result.returncode, result.stderr)
                for text in expected:
                    self.assertIn(text, result.stdout)


    def test_issue_commands_require_explicit_repository_selection(self):
        self.assertEqual(0, self.run_cli("issue", "init", "--name", "demo").returncode)
        result = self.run_cli(
            "issue", "list",
            select_repo=False,
        )
        self.assertEqual(2, result.returncode)
        self.assertIn("--repo", result.stderr)

    def test_nested_local_issue_repositories_have_independent_numbering(self):
        product = self.root / "product-a"
        extension = product / "extension-x"
        extension.mkdir(parents=True)

        product_init = self.run_cli(
            "issue", "init", "--owner", "acme", "--name", "product-a",
            cwd=product,
        )
        self.assertEqual(0, product_init.returncode, product_init.stderr)
        extension_init = self.run_cli(
            "issue", "init", "--owner", "acme", "--name", "extension-x",
            cwd=extension,
        )
        self.assertEqual(0, extension_init.returncode, extension_init.stderr)

        product_issue = self.run_cli(
            "issue", "create", "--title", "Product work", "--json", "number,url",
            cwd=product,
        )
        extension_issue = self.run_cli(
            "issue", "create", "--title", "Extension work", "--json", "number,url",
            cwd=extension,
        )
        self.assertEqual(0, product_issue.returncode, product_issue.stderr)
        self.assertEqual(0, extension_issue.returncode, extension_issue.stderr)
        product_payload = json.loads(product_issue.stdout)
        extension_payload = json.loads(extension_issue.stdout)
        self.assertEqual(1, product_payload["number"])
        self.assertEqual(1, extension_payload["number"])
        self.assertNotEqual(product_payload["url"], extension_payload["url"])

        from_extension = self.run_cli(
            "issue", "list", "-R", "..", "--json", "number,title",
            cwd=extension,
            select_repo=False,
        )
        self.assertEqual(
            [{"number": 1, "title": "Product work"}],
            json.loads(from_extension.stdout),
        )

    def test_bulk_delete_and_deinit_are_confirmed_cli_operations(self):
        self.assertEqual(0, self.run_cli("issue", "init", "--name", "demo").returncode)
        self.run_cli("issue", "create", "--title", "One")
        self.run_cli("issue", "create", "--title", "Two")

        aborted = self.run_cli(
            "issue", "delete", "--all",
            input_text="n\n",
        )
        self.assertEqual(1, aborted.returncode)
        self.assertEqual(
            [{"number": 1}, {"number": 2}],
            json.loads(self.run_cli(
                "issue", "list", "--state", "all", "--json", "number"
            ).stdout),
        )

        deleted = self.run_cli(
            "issue", "delete", "--all",
            input_text="y\n",
        )
        self.assertEqual(0, deleted.returncode, deleted.stderr)
        self.assertIn("Deleted 2 Issue(s)", deleted.stdout)

        deinit = self.run_cli("issue", "deinit")
        self.assertEqual(0, deinit.returncode, deinit.stderr)
        self.assertFalse((self.root / ".github-local" / "config.json").exists())


if __name__ == "__main__":
    unittest.main()
