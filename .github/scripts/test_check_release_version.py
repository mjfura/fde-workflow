"""Tests for check_release_version.py. Run: python3 -m unittest discover -s .github/scripts -p 'test_*.py'"""

import json
import tempfile
import unittest
from pathlib import Path

from check_release_version import check, declared_versions, tag_to_version


class TagToVersionTest(unittest.TestCase):
    def test_final_release(self) -> None:
        self.assertEqual(tag_to_version("v1.2.3"), "1.2.3")

    def test_release_candidate_uses_the_canonical_form(self) -> None:
        self.assertEqual(tag_to_version("v0.2.0-rc.1"), "0.2.0rc1")

    def test_invalid_tags(self) -> None:
        for tag in ("vnope", "v01.2.3", "v1.2.3+local", "v0.2.0rc1", "1.2.3", "v1.2"):
            with self.subTest(tag=tag):
                self.assertIsNone(tag_to_version(tag))


class CheckTest(unittest.TestCase):
    def test_matching_versions_pass(self) -> None:
        self.assertIsNone(check([("plugin.json", "0.1.0"), ("cli/pyproject.toml", "0.1.0")]))

    def test_a_mismatch_names_where_it_is(self) -> None:
        error = check([("plugin.json", "0.1.0"), ("plugin/.mcp.json (x)", "0.0.9")])
        self.assertIn("plugin/.mcp.json (x)", error or "")

    def test_versions_must_match_the_tag(self) -> None:
        self.assertIn("does not match", check([("plugin.json", "0.1.0")], "v0.1.1") or "")

    def test_release_candidate_tag_matches_canonical_versions(self) -> None:
        self.assertIsNone(check([("plugin.json", "0.2.0rc1")], "v0.2.0-rc.1"))

    def test_invalid_tag_fails(self) -> None:
        self.assertIn("vX.Y.Z", check([("plugin.json", "0.1.0")], "v1.2") or "")

    def test_non_canonical_version_fails(self) -> None:
        self.assertIn("not valid", check([("plugin.json", "0.2.0-rc.1")]) or "")


class DeclaredVersionsTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(tempfile.mkdtemp())
        self._write("plugin/.claude-plugin/plugin.json", json.dumps({"name": "x", "version": "0.1.0"}))

    def _write(self, rel: str, text: str) -> None:
        path = self.root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)

    def test_plugin_only(self) -> None:
        self.assertEqual(declared_versions(self.root), [("plugin/.claude-plugin/plugin.json", "0.1.0")])

    def test_discovers_packages_and_mcp_pins(self) -> None:
        self._write("cli/pyproject.toml", '[project]\nversion = "0.1.0"\n')
        self._write("mcp/pyproject.toml", '[project]\nversion = "0.1.0"\n')
        servers = {"mcpServers": {"x": {"command": "uvx", "args": ["--from", "x-mcp==0.0.9", "x-mcp"]}}}
        self._write("plugin/.mcp.json", json.dumps(servers))
        self.assertEqual(
            declared_versions(self.root),
            [
                ("plugin/.claude-plugin/plugin.json", "0.1.0"),
                ("cli/pyproject.toml", "0.1.0"),
                ("mcp/pyproject.toml", "0.1.0"),
                ("plugin/.mcp.json (x)", "0.0.9"),
            ],
        )


if __name__ == "__main__":
    unittest.main()
