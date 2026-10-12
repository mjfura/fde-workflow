import json
from pathlib import Path

import pytest
import yaml

from tests.helpers import fails, make_files, ok


def test_init_creates_a_discovery_direction(repo: Path) -> None:
    (repo / "docs" / "superpowers").mkdir(parents=True)
    result = ok("init")
    assert "artifact globs: docs/superpowers/specs/**, docs/superpowers/plans/**" in result.output
    data = yaml.safe_load((repo / ".fde" / "direction.yaml").read_text())
    assert data["schema_version"] == 1
    assert data["project"]["name"] == repo.name
    assert data["stage"] == {
        "current": "discovery",
        "entered": "2026-10-12",
        "outcome": None,
        "on_hold": False,
        "confirmed": True,
        "gate_criteria": [],
    }


def test_init_with_custom_globs(repo: Path) -> None:
    ok("init", "--glob", "design/**", "--glob", "rfcs/*.md")
    data = yaml.safe_load((repo / ".fde" / "direction.yaml").read_text())
    assert data["artifacts"]["globs"] == ["design/**", "rfcs/*.md"]


def test_init_twice_fails(fde: Path) -> None:
    assert "already exists" in fails("init").output


def test_commands_without_fde_explain_how_to_start(repo: Path) -> None:
    for command in ("status", "validate", "context"):
        assert "fde-workflow init" in fails(command).output


def test_commands_find_fde_from_a_subdirectory(fde: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    nested = fde / "src"
    nested.mkdir()
    monkeypatch.chdir(nested)
    assert "Project: acme-support" in ok("status").output


def test_validate_reports_warnings_and_exits_zero(fde: Path) -> None:
    result = ok("validate")
    assert "! [N1] No North Star yet" in result.output
    assert "! [S1] Stage discovery has no gate criteria" in result.output
    assert result.output.endswith("Valid with 2 warning(s).\n")


def test_detect_command_reports_a_repository_without_fde(repo: Path) -> None:
    make_files(repo, "README.md", "docs/superpowers/specs/2026-09-01-triage-design.md")
    report = json.loads(ok("detect").stdout)
    assert report["fde_initialised"] is False
    assert report["methodology"] == "superpowers"
    assert report["readme"] == "README.md"
    assert report["artifacts"] == [
        {
            "path": "docs/superpowers/specs/2026-09-01-triage-design.md",
            "first_commit": None,
            "linked_to": None,
        }
    ]


def test_status_and_context(fde: Path) -> None:
    assert "Project: acme-support" in ok("status").output
    context = ok("context", "--brief").output
    assert context.startswith("FDE direction of this repository")
    assert "Gate criteria: 0" in context
