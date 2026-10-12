"""Check that every version in the repository is the same, and that it matches a release tag.

Usage, from the repository root:
  python3 .github/scripts/check_release_version.py           # every version equals plugin.json's
  python3 .github/scripts/check_release_version.py vX.Y.Z    # every version equals the tag

Versions are read from plugin/.claude-plugin/plugin.json, from cli/pyproject.toml and
mcp/pyproject.toml when they exist, and from every `<package>==<version>` argument in
plugin/.mcp.json. Standard library only.
"""

import json
import re
import sys
import tomllib
from pathlib import Path

# git-workflow tags: vX.Y.Z or vX.Y.Z-rc.N, numbers without leading zeros.
TAG_PATTERN = re.compile(r"v(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:-rc\.(0|[1-9]\d*))?")
# The canonical PEP 440 form of those tags: X.Y.Z or X.Y.ZrcN.
VERSION_PATTERN = re.compile(r"(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)(?:rc(0|[1-9]\d*))?")
PIN_PATTERN = re.compile(r"[A-Za-z0-9._-]+==(.+)")
PLUGIN_MANIFEST = "plugin/.claude-plugin/plugin.json"


def tag_to_version(tag: str) -> str | None:
    """Return the canonical version of a release tag, or None when the tag is not valid."""
    match = TAG_PATTERN.fullmatch(tag)
    if not match:
        return None
    major, minor, patch, rc = match.groups()
    return f"{major}.{minor}.{patch}" + (f"rc{rc}" if rc is not None else "")


def declared_versions(root: Path) -> list[tuple[str, str]]:
    """Return (where, version) for every version declared in the repository."""
    manifest = json.loads((root / PLUGIN_MANIFEST).read_text())
    versions = [(PLUGIN_MANIFEST, str(manifest["version"]))]
    for package in ("cli", "mcp"):
        pyproject = root / package / "pyproject.toml"
        if pyproject.is_file():
            project = tomllib.loads(pyproject.read_text())["project"]
            versions.append((f"{package}/pyproject.toml", str(project["version"])))
    mcp_config = root / "plugin" / ".mcp.json"
    if mcp_config.is_file():
        servers = json.loads(mcp_config.read_text()).get("mcpServers", {})
        for name, server in servers.items():
            for arg in server.get("args", []):
                pin = PIN_PATTERN.fullmatch(str(arg))
                if pin:
                    versions.append((f"plugin/.mcp.json ({name})", pin.group(1)))
    return versions


def check(versions: list[tuple[str, str]], tag: str | None = None) -> str | None:
    """Return an error message, or None when every version is valid and they all match."""
    for where, version in versions:
        if not VERSION_PATTERN.fullmatch(version):
            return f"Version {version} in {where} is not valid: use X.Y.Z or X.Y.ZrcN"
    if tag is None:
        expected, source = versions[0][1], versions[0][0]
    else:
        tag_version = tag_to_version(tag)
        if tag_version is None:
            return f"Tag {tag} is not a valid version: use vX.Y.Z or vX.Y.Z-rc.N"
        expected, source = tag_version, f"tag {tag}"
    for where, version in versions:
        if version != expected:
            return f"Version {version} in {where} does not match {expected} ({source})"
    return None


def main(argv: list[str]) -> int:
    versions = declared_versions(Path.cwd())
    error = check(versions, argv[0] if argv else None)
    if error:
        print(f"::error::{error}")
        return 1
    print(f"Version {versions[0][1]} everywhere: {', '.join(where for where, _ in versions)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
