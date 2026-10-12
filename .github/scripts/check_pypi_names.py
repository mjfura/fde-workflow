"""Check that the PyPI names of the repository's packages are free or published from it.

Usage, from the repository root:
  python3 .github/scripts/check_pypi_names.py

The plugin installs and runs its packages from PyPI by name, so a name registered by someone else
would make the plugin run their code. A name that is not on PyPI yet passes (publish the first
release soon). A name on PyPI passes only when every file (each wheel and the sdist) of the
versions installers fetch has Trusted Publishing provenance, verified by PyPI, from this GitHub
repository. Those versions are the latest release (what `uv tool install` and `pipx install`
pick) and, for a package pinned in plugin/.mcp.json, the pinned version. A pinned version that is
not on PyPI only passes, with a warning, when the latest release is verified from this repository
(a release PR waiting for its tag). Project URLs are declared by whoever uploads, so they prove
nothing.
release.yml publishes with Trusted Publishing, which attaches that provenance automatically.

Every `<name>==<version>` pin in plugin/.mcp.json must name a distribution declared in cli/ or
mcp/ (compared in PEP 503 canonical form); otherwise the plugin would run a package that is never
checked, for example after the owner renames the package in mcp/pyproject.toml and forgets the pin.

Distributions are read from cli/pyproject.toml and mcp/pyproject.toml when they exist, pins from
plugin/.mcp.json, and the repository from plugin/.claude-plugin/plugin.json (`repository`).
Standard library only."""

import json
import re
import sys
import tomllib
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

PLUGIN_MANIFEST = "plugin/.claude-plugin/plugin.json"
MCP_CONFIG = "plugin/.mcp.json"
PYPI_JSON_URL = "https://pypi.org/pypi/{project}/json"
PYPI_VERSION_JSON_URL = "https://pypi.org/pypi/{project}/{version}/json"
PROVENANCE_URL = "https://pypi.org/integrity/{project}/{version}/{filename}/provenance"
GITHUB_URL = re.compile(r"https?://github\.com/([^/\s]+)/([^/\s]+?)(?:\.git)?/?", re.IGNORECASE)
PIN = re.compile(r"([A-Za-z0-9._-]+)==(.+)")
TIMEOUT_SECONDS = 10

# Returns the JSON document at a PyPI URL, or None when PyPI answers 404.
# Raises OSError (or ValueError for an unreadable answer) when PyPI cannot be asked.
Fetch = Callable[[str], Any]


def fetch_json(url: str) -> Any:
    """GET a PyPI JSON document; None when it does not exist."""
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise


def github_repository(url: str) -> str | None:
    """Return `owner/repo` for a GitHub repository URL, or None for any other URL."""
    match = GITHUB_URL.fullmatch(url.strip())
    return f"{match.group(1)}/{match.group(2)}" if match else None


def quote(part: str) -> str:
    return urllib.parse.quote(part, safe="")


def canonical(name: str) -> str:
    """PEP 503 normalized distribution name."""
    return re.sub(r"[-_.]+", "-", name).lower()


def provenance_url(project: str, version: str, filename: str) -> str:
    """URL of PyPI's Integrity API provenance for one file of a release."""
    return PROVENANCE_URL.format(
        project=quote(project), version=quote(version), filename=quote(filename)
    )


def file_publishers(provenance: Any) -> list[str]:
    """Return one `kind:repository` entry (lowercase) per attestation bundle of a file."""
    publishers = []
    for bundle in provenance.get("attestation_bundles") or []:
        publisher = bundle.get("publisher") or {}
        publishers.append(f"{publisher.get('kind')}:{publisher.get('repository')}".lower())
    return publishers


def unverified_file(
    project: str, version: str, files: list[Any], repository: str, fetch: Fetch
) -> str | None:
    """Return why one version is not verified, or None when every file is attested from here."""
    if not files:
        return f"version {version} has no files"
    expected = f"github:{repository}".lower()
    for file in files:
        filename = file["filename"]
        provenance = fetch(provenance_url(project, version, filename))
        publishers = [] if provenance is None else file_publishers(provenance)
        if not publishers:
            return f"{filename} has no provenance"
        if any(publisher != expected for publisher in publishers):
            return f"{filename} was published from {', '.join(sorted(set(publishers)))}"
    return None


def check_name(
    name: str, repository: str, fetch: Fetch, pinned: str | None = None
) -> tuple[bool, str]:
    """Return (ok, message) for one distribution; `repository` is `owner/repo`.

    `pinned` is the version plugin/.mcp.json pins for this distribution, if any. A pinned version
    missing from an existing project is an error, except while a release of this repository is
    pending: the latest release is verified from this repository and the release PR already pins
    the next version (docs/releasing.md). That case passes with a warning.
    """
    try:
        metadata = fetch(PYPI_JSON_URL.format(project=quote(name)))
        if metadata is None:
            return True, (
                f"{name}: not on PyPI yet (publish the first release soon; see docs/releasing.md)"
            )
        project, latest = metadata["info"]["name"], metadata["info"]["version"]
        releases = [(latest, metadata.get("urls") or [])]
        pinned_missing = False
        if pinned is not None and pinned != latest:
            pinned_metadata = fetch(
                PYPI_VERSION_JSON_URL.format(project=quote(name), version=quote(pinned))
            )
            if pinned_metadata is None:
                pinned_missing = True
            else:
                releases.append((pinned, pinned_metadata.get("urls") or []))
        notes = []
        for version, files in releases:
            reason = unverified_file(project, version, files, repository, fetch)
            if reason is not None:
                return False, (
                    f"::error::{name} exists on PyPI but is not published from {repository} "
                    f"(no verified Trusted Publishing provenance: {reason}): rename the package "
                    "(see docs/releasing.md) before using the plugin"
                )
            if any(file.get("yanked") for file in files):
                notes.append(f"{version} is yanked")
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        return False, f"::error::Could not check {name} on PyPI ({error!r}): retry later"
    versions = " and ".join(version for version, _ in releases)
    suffix = f"; note: {', '.join(notes)}" if notes else ""
    message = (
        f"{name}: on PyPI, every file of {versions} published from {repository} "
        f"(Trusted Publishing){suffix}"
    )
    if pinned_missing:
        message += (
            f"\n::warning::{name} {pinned}, the version pinned in {MCP_CONFIG}, is not on PyPI "
            "yet: tag the release right after merging (see docs/releasing.md); until then the "
            "plugin's MCP server cannot start"
        )
    return True, message


def discover(root: Path) -> tuple[list[str], str, dict[str, str]]:
    """Return the repository's distribution names, its repository URL and the .mcp.json pins.

    Pins map the canonical distribution name to the pinned version.
    """
    names = []
    for package in ("cli", "mcp"):
        pyproject = root / package / "pyproject.toml"
        if pyproject.is_file():
            names.append(str(tomllib.loads(pyproject.read_text())["project"]["name"]))
    manifest = json.loads((root / PLUGIN_MANIFEST).read_text())
    pins = {}
    mcp_config = root / MCP_CONFIG
    if mcp_config.is_file():
        for server in json.loads(mcp_config.read_text()).get("mcpServers", {}).values():
            for arg in server.get("args", []):
                pin = PIN.fullmatch(str(arg))
                if pin:
                    pins[canonical(pin.group(1))] = pin.group(2)
    return names, str(manifest.get("repository") or ""), pins


def undeclared_pins(names: list[str], pins: dict[str, str]) -> list[str]:
    """Return the canonical names pinned in plugin/.mcp.json that no package here declares."""
    declared = {canonical(name) for name in names}
    return sorted(pin for pin in pins if pin not in declared)


def main(root: Path, fetch: Fetch = fetch_json) -> int:
    names, url, pins = discover(root)
    stray = undeclared_pins(names, pins)
    for pin in stray:
        print(
            f"::error::{MCP_CONFIG} pins {pin}=={pins[pin]}, which is not a package declared in "
            "cli/ or mcp/ pyproject.toml, so it would run a package that is never checked on "
            f"PyPI: update {MCP_CONFIG} to the renamed package (see docs/releasing.md)"
        )
    if stray:
        return 1
    if not names:
        print("No packages in cli/ or mcp/: no PyPI names to check.")
        return 0
    repository = github_repository(url)
    if repository is None:
        print(f"::error::The repository in {PLUGIN_MANIFEST} is not a GitHub URL: {url!r}")
        return 1
    ok = True
    for name in names:
        name_ok, message = check_name(name, repository, fetch, pins.get(canonical(name)))
        print(message)
        ok = ok and name_ok
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(Path.cwd()))
