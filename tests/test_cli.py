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

    def run_cli(self, *args, input_text=None):
        return subprocess.run(
            [sys.executable, "-m", "github_local.cli", *args],
            cwd=self.root, env=self.env, text=True, input=input_text,
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
        self.assertIn("Visible note", view.stdout)

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


if __name__ == "__main__":
    unittest.main()
