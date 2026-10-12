"""Find the execution methodology and its artifacts in a repository. Read-only."""

import subprocess
from enum import StrEnum
from pathlib import Path

from fde_workflow_cli.model import Direction


class Preset(StrEnum):
    AUTO = "auto"
    SUPERPOWERS = "superpowers"
    SPEC_KIT = "spec-kit"
    NONE = "none"


PRESET_GLOBS: dict[Preset, list[str]] = {
    Preset.SUPERPOWERS: ["docs/superpowers/specs/**", "docs/superpowers/plans/**"],
    Preset.SPEC_KIT: ["specs/**"],
    Preset.NONE: [],
}
DEPLOYMENT_MARKERS = (
    "Dockerfile",
    "docker-compose.yml",
    "compose.yaml",
    "Procfile",
    "fly.toml",
    "vercel.json",
    "netlify.toml",
    "render.yaml",
    "app.yaml",
    "serverless.yml",
    "k8s",
    "helm",
    "terraform",
)
DEPLOYMENT_WORKFLOW_WORDS = ("deploy", "release", "publish")
READMES = ("README.md", "README.rst", "README.txt", "README")


def detect_methodology(root: Path) -> Preset:
    if (root / "docs" / "superpowers").is_dir():
        return Preset.SUPERPOWERS
    if (root / ".specify").is_dir() or (root / "specs").is_dir():
        return Preset.SPEC_KIT
    return Preset.NONE


def globs_for(preset: Preset, root: Path) -> list[str]:
    resolved = detect_methodology(root) if preset is Preset.AUTO else preset
    return list(PRESET_GLOBS[resolved])


def artifact_files(root: Path, globs: list[str]) -> list[str]:
    """Files under `root` matching any glob, as sorted POSIX paths relative to `root`."""
    found: set[str] = set()
    for pattern in globs:
        for path in root.glob(pattern):
            if path.is_file():
                found.add(path.relative_to(root).as_posix())
    return sorted(found)


def first_commit_date(root: Path, relative: str) -> str | None:
    """Date (YYYY-MM-DD) of the commit that added the file, or None outside git history."""
    try:
        result = subprocess.run(  # noqa: S603 - fixed read-only git query
            ["git", "log", "--diff-filter=A", "--format=%cs", "--", relative],  # noqa: S607
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    dates = result.stdout.split()
    return dates[-1] if result.returncode == 0 and dates else None


def deployment_signals(root: Path) -> list[str]:
    signals = [name for name in DEPLOYMENT_MARKERS if (root / name).exists()]
    workflows = root / ".github" / "workflows"
    if workflows.is_dir():
        signals += sorted(
            f".github/workflows/{path.name}"
            for path in workflows.iterdir()
            if any(word in path.name.lower() for word in DEPLOYMENT_WORKFLOW_WORDS)
        )
    return signals


def linked_to(direction: Direction | None, relative: str) -> str | None:
    """The path id that links the artifact, "pre-framework", or None."""
    if direction is None:
        return None
    for path in direction.paths:
        if relative in path.links:
            return path.id
    if relative in direction.artifacts.pre_framework:
        return "pre-framework"
    return None


def report(root: Path, direction: Direction | None) -> dict[str, object]:
    methodology = detect_methodology(root)
    globs = direction.artifacts.globs if direction else PRESET_GLOBS[methodology]
    return {
        "root": str(root),
        "fde_initialised": direction is not None,
        "methodology": methodology.value,
        "globs": globs,
        "readme": next((name for name in READMES if (root / name).is_file()), None),
        "deployment_signals": deployment_signals(root),
        "artifacts": [
            {
                "path": relative,
                "first_commit": first_commit_date(root, relative),
                "linked_to": linked_to(direction, relative),
            }
            for relative in artifact_files(root, globs)
        ],
    }
