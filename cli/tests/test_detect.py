import subprocess
from pathlib import Path

from fde_workflow_cli import detect
from fde_workflow_cli.detect import Preset
from tests.helpers import make_files


def git(repo: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],  # noqa: S607
        cwd=repo,
        check=True,
        capture_output=True,
    )


def test_methodology_detection(tmp_path: Path) -> None:
    assert detect.detect_methodology(tmp_path) is Preset.NONE
    (tmp_path / "specs").mkdir()
    assert detect.detect_methodology(tmp_path) is Preset.SPEC_KIT
    (tmp_path / "docs" / "superpowers").mkdir(parents=True)
    assert detect.detect_methodology(tmp_path) is Preset.SUPERPOWERS


def test_globs_for_auto_uses_the_detected_methodology(tmp_path: Path) -> None:
    (tmp_path / "docs" / "superpowers").mkdir(parents=True)
    assert detect.globs_for(Preset.AUTO, tmp_path) == detect.PRESET_GLOBS[Preset.SUPERPOWERS]
    assert detect.globs_for(Preset.NONE, tmp_path) == []


def test_artifact_files_lists_matching_files_only(tmp_path: Path) -> None:
    make_files(
        tmp_path, "docs/superpowers/specs/a.md", "docs/superpowers/plans/sub/b.md", "src/x.py"
    )
    globs = detect.PRESET_GLOBS[Preset.SUPERPOWERS]
    assert detect.artifact_files(tmp_path, globs) == [
        "docs/superpowers/plans/sub/b.md",
        "docs/superpowers/specs/a.md",
    ]


def test_first_commit_date_comes_from_git(tmp_path: Path) -> None:
    make_files(tmp_path, "specs/001/spec.md")
    assert detect.first_commit_date(tmp_path, "specs/001/spec.md") is None
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "add", "--date", "2026-09-01T10:00:00")
    assert detect.first_commit_date(tmp_path, "specs/001/spec.md") is not None


def test_deployment_signals(tmp_path: Path) -> None:
    make_files(
        tmp_path, "Dockerfile", ".github/workflows/deploy-prod.yml", ".github/workflows/ci.yml"
    )
    assert detect.deployment_signals(tmp_path) == [
        "Dockerfile",
        ".github/workflows/deploy-prod.yml",
    ]
