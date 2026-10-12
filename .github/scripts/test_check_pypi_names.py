"""Tests for check_pypi_names.py, without network. Run: python3 -m unittest discover -s .github/scripts -p 'test_*.py'"""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any

from check_pypi_names import check_name, discover, github_repository, main

REPO_URL = "https://github.com/acme/team-weather"
REPO = "acme/team-weather"
NAME = "weather-kit-mcp"


def provenance(repository: str = REPO, kind: str = "GitHub") -> dict[str, Any]:
    """An Integrity API answer, shaped like PyPI's (checked against sigstore and pip-audit)."""
    publisher = {
        "kind": kind,
        "repository": repository,
        "workflow": "release.yml",
        "environment": "pypi",
    }
    return {"version": 1, "attestation_bundles": [{"publisher": publisher, "attestations": [{}]}]}


def files(version: str, wheel: Any = None, sdist: Any = None) -> dict[str, Any]:
    """The wheel and sdist of a release, mapped to their provenance (None: no provenance)."""
    stem = NAME.replace("-", "_")
    return {f"{stem}-{version}-py3-none-any.whl": wheel, f"{stem}-{version}.tar.gz": sdist}


def attested(version: str, repository: str = REPO) -> dict[str, Any]:
    return files(version, provenance(repository), provenance(repository))


class FakePyPI:
    """A fetch over a fake PyPI project; any URL it does not know answers 404 (None)."""

    def __init__(
        self,
        releases: dict[str, dict[str, Any]] | None = None,
        latest: str | None = None,
        project_urls: dict[str, str] | None = None,
        yanked: tuple[str, ...] = (),
    ) -> None:
        self.documents: dict[str, Any] = {}
        self.requested: list[str] = []
        if not releases:
            return
        latest = latest or list(releases)[-1]
        for version, release in releases.items():
            urls = [{"filename": name, "yanked": version in yanked} for name in release]
            info = {"name": NAME, "version": version, "project_urls": project_urls}
            self.documents[f"https://pypi.org/pypi/{NAME}/{version}/json"] = {
                "info": info,
                "urls": urls,
            }
            if version == latest:
                self.documents[f"https://pypi.org/pypi/{NAME}/json"] = {"info": info, "urls": urls}
            for filename, document in release.items():
                url = f"https://pypi.org/integrity/{NAME}/{version}/{filename}/provenance"
                if document is not None:
                    self.documents[url] = document

    def __call__(self, url: str) -> Any:
        self.requested.append(url)
        return self.documents.get(url)


def unreachable(url: str) -> None:
    raise OSError("network is unreachable")


class CheckNameTest(unittest.TestCase):
    def assert_fails(self, fetch: FakePyPI, pinned: str | None = None, reason: str = "") -> str:
        ok, message = check_name(NAME, REPO, fetch, pinned)
        self.assertFalse(ok, message)
        self.assertTrue(message.startswith(f"::error::{NAME} exists on PyPI but "), message)
        self.assertIn(reason, message)
        return message

    def test_a_name_not_on_pypi_yet_passes(self) -> None:
        ok, message = check_name(NAME, REPO, FakePyPI(), pinned="0.1.0")
        self.assertTrue(ok)
        self.assertEqual(
            message,
            f"{NAME}: not on PyPI yet (publish the first release soon; see docs/releasing.md)",
        )

    def test_every_file_attested_from_this_repository_passes(self) -> None:
        fetch = FakePyPI({"0.2.0": files("0.2.0", provenance("Acme/Team-Weather"), provenance())})
        ok, message = check_name(NAME, REPO, fetch)
        self.assertTrue(ok, message)
        self.assertIn("every file of 0.2.0 published from acme/team-weather", message)
        self.assertEqual(sum("/integrity/" in url for url in fetch.requested), 2)

    def test_one_unattested_file_fails(self) -> None:
        fetch = FakePyPI({"0.2.0": files("0.2.0", provenance(), None)})
        self.assert_fails(fetch, reason="weather_kit_mcp-0.2.0.tar.gz has no provenance")

    def test_one_file_from_another_repository_fails(self) -> None:
        fetch = FakePyPI({"0.2.0": files("0.2.0", provenance(), provenance("someone/else"))})
        message = self.assert_fails(fetch, reason="published from github:someone/else")
        self.assertIn("(see docs/releasing.md) before using the plugin", message)

    def test_provenance_from_another_platform_fails(self) -> None:
        fetch = FakePyPI({"0.2.0": files("0.2.0", provenance(kind="GitLab"), provenance())})
        self.assert_fails(fetch, reason="published from gitlab:acme/team-weather")

    def test_self_declared_project_urls_are_not_enough(self) -> None:
        urls = {"Homepage": REPO_URL, "Repository": f"{REPO_URL}.git"}
        fetch = FakePyPI({"0.2.0": files("0.2.0")}, project_urls=urls)
        self.assert_fails(fetch, reason="no verified Trusted Publishing provenance")

    def test_a_release_without_files_fails(self) -> None:
        self.assert_fails(FakePyPI({"0.2.0": {}}), reason="version 0.2.0 has no files")

    def test_the_pinned_version_is_verified_too(self) -> None:
        fetch = FakePyPI({"0.1.0": attested("0.1.0"), "0.2.0": attested("0.2.0")})
        ok, message = check_name(NAME, REPO, fetch, pinned="0.1.0")
        self.assertTrue(ok, message)
        self.assertIn("every file of 0.2.0 and 0.1.0", message)

    def test_a_pinned_version_from_another_repository_fails(self) -> None:
        fetch = FakePyPI({"0.1.0": attested("0.1.0", "someone/else"), "0.2.0": attested("0.2.0")})
        self.assert_fails(fetch, pinned="0.1.0", reason="weather_kit_mcp-0.1.0-py3-none-any.whl")

    def test_a_pinned_version_missing_from_an_existing_project_fails(self) -> None:
        fetch = FakePyPI({"0.2.0": attested("0.2.0", "someone/else")})
        self.assert_fails(fetch, pinned="0.3.0", reason="published from github:someone/else")

    def test_a_pinned_version_missing_from_an_unattested_project_fails(self) -> None:
        self.assert_fails(FakePyPI({"0.2.0": files("0.2.0")}), "0.3.0", "has no provenance")

    def test_a_pending_release_of_this_repository_passes_with_a_warning(self) -> None:
        ok, message = check_name(NAME, REPO, FakePyPI({"0.2.0": attested("0.2.0")}), "0.3.0")
        self.assertTrue(ok, message)
        self.assertIn(
            f"\n::warning::{NAME} 0.3.0, the version pinned in plugin/.mcp.json, is not on PyPI yet",
            message,
        )

    def test_yanked_releases_are_reported_but_do_not_decide(self) -> None:
        fetch = FakePyPI({"0.2.0": attested("0.2.0")}, yanked=("0.2.0",))
        ok, message = check_name(NAME, REPO, fetch)
        self.assertTrue(ok, message)
        self.assertIn("0.2.0 is yanked", message)
        fetch = FakePyPI({"0.2.0": files("0.2.0")}, yanked=("0.2.0",))
        self.assert_fails(fetch, reason="has no provenance")

    def test_a_network_error_fails(self) -> None:
        ok, message = check_name(NAME, REPO, unreachable)
        self.assertFalse(ok)
        self.assertTrue(message.startswith(f"::error::Could not check {NAME} on PyPI"))

    def test_an_unexpected_answer_fails(self) -> None:
        ok, message = check_name(NAME, REPO, lambda url: {"unexpected": True})
        self.assertFalse(ok)
        self.assertTrue(message.startswith("::error::"))


class GithubRepositoryTest(unittest.TestCase):
    def test_parses_github_urls(self) -> None:
        for url in (
            REPO_URL,
            f"{REPO_URL}/",
            f"{REPO_URL}.git",
            "HTTPS://GitHub.com/acme/team-weather",
        ):
            with self.subTest(url=url):
                self.assertEqual((github_repository(url) or "").lower(), REPO)

    def test_rejects_other_urls(self) -> None:
        for url in (
            "",
            "https://gitlab.com/acme/x",
            "https://github.com/acme",
            f"{REPO_URL}/issues",
        ):
            with self.subTest(url=url):
                self.assertIsNone(github_repository(url))


def write_repo(
    root: Path, packages: tuple[str, ...], repository: str | None = REPO_URL, pin: str = "0.1.0"
) -> None:
    manifest: dict[str, str] = {"name": "weather-kit", "version": "0.1.0"}
    if repository is not None:
        manifest["repository"] = repository
    (root / "plugin" / ".claude-plugin").mkdir(parents=True)
    (root / "plugin" / ".claude-plugin" / "plugin.json").write_text(json.dumps(manifest))
    for package in packages:
        (root / package).mkdir()
        (root / package / "pyproject.toml").write_text(
            f'[project]\nname = "weather-kit-{package}"\nversion = "0.1.0"\n'
        )
    if "mcp" in packages:
        server = {"command": "uvx", "args": ["--from", f"weather_kit.MCP=={pin}", NAME]}
        (root / "plugin" / ".mcp.json").write_text(json.dumps({"mcpServers": {"x": server}}))


def run_main(root: Path, fetch: Any) -> tuple[int, str]:
    output = io.StringIO()
    with contextlib.redirect_stdout(output):
        code = main(root, fetch)
    return code, output.getvalue()


class DiscoverAndMainTest(unittest.TestCase):
    def test_discovers_every_package_the_repository_and_the_pins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(root, ("cli", "mcp"))
            self.assertEqual(
                discover(root),
                (["weather-kit-cli", "weather-kit-mcp"], REPO_URL, {"weather-kit-mcp": "0.1.0"}),
            )

    def test_without_packages_there_is_nothing_to_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(root, ())
            self.assertEqual(discover(root), ([], REPO_URL, {}))
            code, output = run_main(root, unreachable)
            self.assertEqual(code, 0)
            self.assertIn("no PyPI names to check", output)

    def test_main_checks_the_pinned_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(root, ("cli", "mcp"), pin="0.1.0")
            fetch = FakePyPI(
                {"0.1.0": attested("0.1.0", "someone/else"), "0.2.0": attested("0.2.0")}
            )
            code, output = run_main(root, fetch)
            self.assertEqual(code, 1)
            self.assertIn("weather-kit-cli: not on PyPI yet", output)
            self.assertIn(f"::error::{NAME} exists on PyPI but is not published from", output)

    def test_main_passes_when_every_name_is_free_or_ours(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(root, ("cli", "mcp"), pin="0.2.0")
            code, output = run_main(root, FakePyPI({"0.2.0": attested("0.2.0")}))
            self.assertEqual(code, 0, output)

    def test_main_fails_for_a_pin_that_is_not_a_declared_package(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(root, ("cli", "mcp"))
            server = {"command": "uvx", "args": ["--from", "stranger-pkg==2.0.0", "stranger-pkg"]}
            (root / "plugin" / ".mcp.json").write_text(json.dumps({"mcpServers": {"x": server}}))
            fetch = FakePyPI()
            code, output = run_main(root, fetch)
            self.assertEqual(code, 1)
            self.assertIn("::error::plugin/.mcp.json pins stranger-pkg==2.0.0", output)
            self.assertIn("update plugin/.mcp.json to the renamed package", output)
            self.assertEqual(fetch.requested, [])

    def test_main_accepts_a_pin_spelled_differently_from_the_declared_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(root, ("mcp",))
            self.assertEqual(discover(root)[2], {NAME: "0.1.0"})
            code, output = run_main(root, FakePyPI())
            self.assertEqual(code, 0, output)
            self.assertNotIn("pins", output)

    def test_main_fails_for_a_pin_when_no_package_is_declared(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            write_repo(root, ())
            server = {"command": "uvx", "args": ["--from", f"{NAME}==0.1.0", NAME]}
            (root / "plugin" / ".mcp.json").write_text(json.dumps({"mcpServers": {"x": server}}))
            code, output = run_main(root, unreachable)
            self.assertEqual(code, 1)
            self.assertIn(f"::error::plugin/.mcp.json pins {NAME}==0.1.0", output)

    def test_main_fails_without_a_github_repository(self) -> None:
        for repository in (None, "https://example.com/acme/team-weather"):
            with self.subTest(repository=repository), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                write_repo(root, ("cli",), repository=repository)
                code, output = run_main(root, FakePyPI())
                self.assertEqual(code, 1)
                self.assertIn("::error::", output)


if __name__ == "__main__":
    unittest.main()
