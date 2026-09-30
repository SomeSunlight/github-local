from __future__ import annotations

import re
import subprocess
import tempfile
import unittest
from pathlib import Path

from github_local.version import display_version, git_provenance, release_version


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

    def test_detached_head_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._git_project(Path(tmp))
            subprocess.run(["git", "-C", str(root), "checkout", "-q", "--detach", "HEAD"], check=True)
            provenance = git_provenance(root)
            self.assertIsNotNone(provenance)
            self.assertRegex(provenance, r"^detached@[0-9a-f]{7}$")


if __name__ == "__main__":
    unittest.main()
