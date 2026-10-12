from __future__ import annotations

import json
import re
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from github_local.version import (
    display_version, git_provenance, installed_git_provenance, release_version,
)


class RuntimeVersionTests(unittest.TestCase):
    def _project(self, root: Path, version: str = "9.8.7") -> Path:
        (root / "pyproject.toml").write_text(
            "[project]\n"
            'name = "github-local"\n'
            f'version = "{version}"\n',
            encoding="utf-8",
        )
        return root

    def _git_project(self, root: Path) -> Path:
        self._project(root)
        subprocess.run(["git", "init", "-q", "-b", "main", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "test@example.com"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Test"], check=True)
        subprocess.run(["git", "-C", str(root), "add", "pyproject.toml"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "initial"], check=True)
        return root

    def test_release_version_reads_pyproject(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(Path(tmp), "1.2.3")
            self.assertEqual("1.2.3", release_version(root))

    def test_non_git_tree_uses_plain_release_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._project(Path(tmp))
            self.assertIsNone(git_provenance(root))
            self.assertEqual("9.8.7", display_version(root))

    def test_git_checkout_reports_branch_and_short_commit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._git_project(Path(tmp))
            provenance = git_provenance(root)
            self.assertIsNotNone(provenance)
            self.assertRegex(provenance, r"^main@[0-9a-f]{7}$")

    def test_dirty_checkout_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._git_project(Path(tmp))
            (root / "dirty.txt").write_text("changed\n", encoding="utf-8")
            provenance = git_provenance(root)
            self.assertIsNotNone(provenance)
            self.assertRegex(provenance, r"^main@[0-9a-f]{7}, dirty$")

    def test_uv_git_install_uses_pep610_branch_and_resolved_commit(self):
        sha = "a" * 40
        dist = Mock()
        dist.read_text.return_value = json.dumps({
            "url": "https://github.com/SomeSunlight/github-local.git",
            "vcs_info": {
                "vcs": "git",
                "requested_revision": "issue-20-git-tracked-workflow-state",
                "commit_id": sha,
            },
        })
        with patch("github_local.version.distribution", return_value=dist):
            self.assertEqual(
                "issue-20-git-tracked-workflow-state@aaaaaaa",
                installed_git_provenance(),
            )
            with patch("github_local.version._project_root", return_value=None):
                with patch("github_local.version.distribution_version", return_value="0.1.0"):
                    self.assertEqual(
                        "0.1.0 (issue-20-git-tracked-workflow-state@aaaaaaa)",
                        display_version(),
                    )

    def test_uv_git_install_at_commit_labels_it_detached(self):
        sha = "b" * 40
        dist = Mock()
        dist.read_text.return_value = json.dumps({
            "url": "https://github.com/SomeSunlight/github-local.git",
            "vcs_info": {
                "vcs": "git", "requested_revision": sha,
                "commit_id": sha,
            },
        })
        with patch("github_local.version.distribution", return_value=dist):
            self.assertEqual("detached@bbbbbbb", installed_git_provenance())

    def test_installed_release_archive_does_not_invent_git_provenance(self):
        dist = Mock()
        for metadata in (
            None,
            '{"url":"https://example.test/wheel.whl","archive_info":{}}',
            '{"url":"https://example.test/repo","vcs_info":{"vcs":"hg","commit_id":"aa"}}',
            '{"url":"https://example.test/repo","vcs_info":{"vcs":"git","commit_id":"invalid"}}',
            '{"url":"https://example.test/repo","vcs_info":{"vcs":"git"}}',
            "{not-json",
        ):
            with self.subTest(metadata=metadata):
                dist.read_text.return_value = metadata
                with patch("github_local.version.distribution", return_value=dist):
                    self.assertIsNone(installed_git_provenance())

    def test_installed_git_provenance_does_not_override_explicit_checkout(self):
        sha = "a" * 40
        dist = Mock()
        dist.read_text.return_value = json.dumps({
            "url": "https://example.test/tool.git",
            "vcs_info": {
                "vcs": "git", "requested_revision": "other",
                "commit_id": sha,
            },
        })
        with tempfile.TemporaryDirectory() as tmp:
            root = self._git_project(Path(tmp))
            with patch("github_local.version.distribution", return_value=dist):
                displayed = display_version(root)
                self.assertRegex(displayed, r"^9[.]8[.]7 [(]main@[a-f0-9]{7}[)]$")
                dist.read_text.assert_not_called()

    def test_detached_head_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._git_project(Path(tmp))
            subprocess.run(["git", "-C", str(root), "checkout", "-q", "--detach", "HEAD"], check=True)
            provenance = git_provenance(root)
            self.assertIsNotNone(provenance)
            self.assertRegex(provenance, r"^detached@[0-9a-f]{7}$")


if __name__ == "__main__":
    unittest.main()
