from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch

from github_local.cli import main
from github_local.version import display_version, installed_git_origin, release_version
from github_local.version_check import (
    InstallIdentity,
    VersionCheck,
    _github_coordinates,
    _identity,
    _read_json,
    check_remote_version,
)

LOCAL_SHA = "a" * 40
REMOTE_SHA = "b" * 40
SELF_URL = "https://github.com/SomeSunlight/github-local.git"


class InstalledProvenanceTests(unittest.TestCase):
    def _distribution(self, payload):
        dist = Mock()
        dist.read_text.return_value = payload
        return dist

    def test_git_url_install_exposes_exact_origin_and_requested_branch(self):
        payload = json.dumps({
            "url": SELF_URL,
            "vcs_info": {"vcs": "git", "commit_id": LOCAL_SHA,
                         "requested_revision": "main"},
        })
        with patch("github_local.version.distribution", return_value=self._distribution(payload)):
            self.assertEqual(installed_git_origin(), (SELF_URL, LOCAL_SHA, "main"))
            with patch("github_local.version._project_root", return_value=None):
                self.assertEqual(display_version(), f"{release_version()} (main@aaaaaaa)")
        with patch("github_local.version_check._project_root", return_value=None):
            with patch("github_local.version_check.installed_git_origin", return_value=(SELF_URL, LOCAL_SHA, "main")):
                self.assertEqual(_identity(), InstallIdentity(SELF_URL, LOCAL_SHA, "main"))

    def test_malformed_or_non_git_metadata_has_no_installed_identity(self):
        cases = [
            None, "{bad", "[]", '{"vcs_info":{}}',
            json.dumps({"url": SELF_URL, "vcs_info": {"vcs": "hg", "commit_id": LOCAL_SHA}}),
            json.dumps({"url": SELF_URL, "vcs_info": {"vcs": "git", "commit_id": "bad"}}),
            json.dumps({"url": SELF_URL, "vcs_info": {"vcs": "git", "commit_id": LOCAL_SHA,
                                                       "requested_revision": "main\nheader:token"}}),
        ]
        for raw in cases:
            with self.subTest(raw=raw):
                with patch("github_local.version.distribution", return_value=self._distribution(raw)):
                    self.assertIsNone(installed_git_origin())

    def test_installed_commit_without_branch_uses_remote_default(self):
        with patch("github_local.version_check._project_root", return_value=None):
            with patch("github_local.version_check.installed_git_origin", return_value=(SELF_URL, LOCAL_SHA, None)):
                self.assertEqual(_identity(), InstallIdentity(SELF_URL, LOCAL_SHA, None))

    def test_offline_version_never_calls_network_or_local_issue_repo(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            with patch("github_local.version_check._read_json", side_effect=AssertionError("network")):
                with redirect_stdout(io.StringIO()) as output:
                    with self.assertRaises(SystemExit) as exited:
                        main(["--version"])
                    self.assertEqual(exited.exception.code, 0)
        self.assertIn(f"github-local {release_version()}", output.getvalue())

    def test_checkout_identity_uses_tool_root_not_process_cwd(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
            (root / "test.txt").write_text("yes\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "test.txt"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-qm", "baseline"], check=True)
            subprocess.run(["git", "-C", str(root), "remote", "add", "origin", SELF_URL], check=True)
            commit = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
            before = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"], text=True)
            with patch("github_local.version_check._read_json", return_value={"commit": {"sha": commit}}):
                outcome = check_remote_version(project_root=root)
            after = subprocess.check_output(["git", "-C", str(root), "status", "--porcelain"], text=True)
            self.assertEqual(outcome.status, "up to date")
            self.assertEqual(before, after)
            self.assertEqual(_identity(project_root=root).commit, commit)


class RemoteVersionCheckTests(unittest.TestCase):
    origin = InstallIdentity(SELF_URL, LOCAL_SHA, "main")

    def _check(self, remote=REMOTE_SHA, relation="ahead", branch=None, source=None):
        with patch("github_local.version_check._identity", return_value=source or self.origin):
            def reply(url):
                if "/branches/" in url:
                    return {"commit": {"sha": remote}}
                if "/compare/" in url:
                    return {"status": relation}
                return {"default_branch": "main"}
            with patch("github_local.version_check._read_json", side_effect=reply) as read:
                result = check_remote_version(branch=branch)
        return result, [c.args[0] for c in read.call_args_list]

    def test_equal_commit_skips_extra_compare(self):
        result, urls = self._check(remote=LOCAL_SHA)
        self.assertEqual(result.status, "up to date")
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(len(urls), 1)

    def test_comparison_direction_matches_contextcanon(self):
        for relation, expected in [
            ("ahead", "behind"), ("behind", "ahead"),
            ("diverged", "diverged"), ("identical", "up to date"),
        ]:
            with self.subTest(relation=relation):
                result, urls = self._check(relation=relation)
                self.assertEqual(result.status, expected)
                self.assertEqual(result.exit_code, 0 if expected == "up to date" else 1)
                self.assertIn("/compare/" + LOCAL_SHA + "..." + REMOTE_SHA, urls[-1])

    def test_default_and_explicit_branch(self):
        identity = InstallIdentity(SELF_URL, LOCAL_SHA, None)
        result, urls = self._check(source=identity)
        self.assertEqual(result.status, "behind")
        self.assertTrue(urls[0].endswith("/SomeSunlight/github-local"))
        self.assertIn("/branches/main", urls[1])
        result, urls = self._check(branch="my/branch")
        self.assertEqual(result.status, "behind")
        self.assertIn("/branches/my%2Fbranch", urls[0])

    def test_invalid_branch_or_remote_never_sends_request(self):
        for identity, branch in [
            (None, None),
            (InstallIdentity("https://other.example/tool", LOCAL_SHA, "main"), None),
            (InstallIdentity("https://github.com/owner/other-repo.git", LOCAL_SHA, "main"), None),
            (self.origin, "main\nAuthorization:secret"),
        ]:
            with self.subTest(identity=identity, branch=branch):
                with patch("github_local.version_check._identity", return_value=identity):
                    with patch("github_local.version_check._read_json", side_effect=AssertionError("network")):
                        result = check_remote_version(branch=branch)
                        self.assertEqual(result.status, "unknown")
                        self.assertEqual(result.exit_code, 2)

    def test_http_failure_never_reports_up_to_date(self):
        for exception in [OSError("offline"), ValueError("invalid payload"), KeyError("sha")]:
            with self.subTest(exception=exception):
                with patch("github_local.version_check._identity", return_value=self.origin):
                    with patch("github_local.version_check._read_json", side_effect=exception):
                        self.assertEqual(check_remote_version().status, "unknown")

    def test_public_url_validation(self):
        self.assertEqual(_github_coordinates("git@github.com:SomeSunlight/github-local.git"),
                         ("SomeSunlight", "github-local"))
        self.assertEqual(_github_coordinates("ssh://git@github.com/SomeSunlight/github-local"),
                         ("SomeSunlight", "github-local"))
        for url in [
            "https://github.com.evil.example/SomeSunlight/github-local",
            "https://github.com:invalid/SomeSunlight/github-local",
            "https://example.com/SomeSunlight/github-local",
            "https://someone:secret@github.com/SomeSunlight/github-local",
        ]:
            with self.subTest(url=url):
                self.assertIsNone(_github_coordinates(url))

    def test_bounded_and_invalid_json_response(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.read.return_value = b'{"commit":{"sha":"valid"}}'
        with patch("github_local.version_check.urlopen", return_value=response) as op:
            self.assertEqual(_read_json("https://api.github.com/hello")["commit"]["sha"], "valid")
            self.assertEqual(op.call_args.kwargs["timeout"], 5)
            response.read.assert_called_with(2_000_001)
        response.read.return_value = b"x" * 2_000_001
        with patch("github_local.version_check.urlopen", return_value=response):
            with self.assertRaises(ValueError):
                _read_json("https://api.github.com/hello")

    def test_cli_requires_no_local_issue_repo_selection(self):
        result = VersionCheck("github-local 0.1.0 (git@aaaaaaa)", "main@bbbbbbb", "behind")
        with patch("github_local.version_check.check_remote_version", return_value=result) as check:
            with redirect_stdout(io.StringIO()) as output:
                self.assertEqual(main(["version", "check", "--branch", "main"]), 1)
        check.assert_called_once_with(branch="main")
        self.assertIn("Installed: github-local", output.getvalue())
        self.assertIn("Remote:    main@bbbbbbb", output.getvalue())
        self.assertIn("Status:    behind", output.getvalue())
        with patch("github_local.version_check.check_remote_version",
                   return_value=VersionCheck("github-local 0.1.0", "unavailable", "unknown")):
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["version", "check"]), 2)


if __name__ == "__main__":
    unittest.main()
