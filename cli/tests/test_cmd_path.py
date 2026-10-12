import datetime as dt
import json
from pathlib import Path

import pytest

from fde_workflow_cli import clock
from tests.helpers import add_kpi, decisions, fails, make_files, ok

OPEN = (
    "path", "add", "auto-triage",
    "--hypothesis", "If tickets are classified on arrival, resolution drops 20%",
    "--expects", "resolution-time=36",
)  # fmt: skip


def opened(fde: Path) -> None:
    add_kpi(fde)
    ok(*OPEN, "--reason", "Biggest delay is triage")


def test_add_records_a_path_open_decision(fde: Path) -> None:
    opened(fde)
    assert "auto-triage [proposed]" in ok("status").output
    [decision] = decisions(fde)
    assert decision["type"] == "path-open"
    assert decision["refs"] == ["auto-triage"]


def test_add_validates_input(fde: Path) -> None:
    add_kpi(fde)
    assert "--reason is required" in fails(*OPEN).output
    assert "KPI_ID=VALUE" in fails(*OPEN[:-1], "resolution-time", "--reason", "r").output
    assert "[P1]" in fails(*OPEN[:-1], "nope=1", "--reason", "r").output
    assert "use `path move` later" in fails(*OPEN, "--reason", "r", "--status", "validated").output


def test_inferred_paths_record_no_decision_until_confirmed(fde: Path) -> None:
    add_kpi(fde)
    ok(*OPEN, "--inferred", "--status", "active", "--activated", "2026-09-01")
    assert decisions(fde) == []
    assert "Path auto-triage was inferred" in ok("validate").output
    ok("path", "confirm", "auto-triage")
    assert str(decisions(fde)[0]["summary"]).startswith("Confirm path auto-triage")


def test_move_follows_the_life_cycle(fde: Path) -> None:
    opened(fde)
    assert (
        "allowed: active, discarded"
        in fails("path", "move", "auto-triage", "measuring", "--reason", "r").output
    )
    ok("path", "move", "auto-triage", "active", "--reason", "Started")
    assert "activated: '2026-10-12'" in (fde / ".fde" / "direction.yaml").read_text()


def test_validation_needs_evidence_after_activation(
    fde: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened(fde)
    ok("path", "move", "auto-triage", "active", "--reason", "Started")
    ok("path", "move", "auto-triage", "measuring", "--reason", "Built")
    result = fails("path", "move", "auto-triage", "validated", "--reason", "Looks good")
    assert "[P2]" in result.output
    monkeypatch.setattr(clock, "today", lambda: dt.date(2026, 11, 9))
    ok("kpi", "measure", "resolution-time", "--value", "35", "--source", "Zendesk")
    ok("path", "move", "auto-triage", "validated", "--reason", "35 min", "--approved-by", "Jane")
    assert decisions(fde)[-1]["type"] == "path-validate"


def test_discarding_needs_a_learning(fde: Path) -> None:
    opened(fde)
    assert (
        "--learning is required"
        in fails("path", "move", "auto-triage", "discarded", "--reason", "r").output
    )
    ok(
        "path",
        "move",
        "auto-triage",
        "discarded",
        "--reason",
        "r",
        "--learning",
        "Triage was not the bottleneck",
    )
    assert decisions(fde)[-1]["type"] == "path-discard"


def test_link_normalises_files_and_moves_them_out_of_pre_framework(fde: Path) -> None:
    opened(fde)
    spec = fde / "docs" / "superpowers" / "specs" / "a.md"
    spec.parent.mkdir(parents=True)
    spec.write_text("x")
    ok("path", "link", "--pre-framework", "docs/superpowers/specs/a.md")
    ok("path", "link", "auto-triage", str(spec), "https://github.com/acme/x/pull/1")
    ok("path", "link", "auto-triage", "docs/superpowers/specs/a.md")
    text = (fde / ".fde" / "direction.yaml").read_text()
    assert text.count("docs/superpowers/specs/a.md") == 1
    assert "pre_framework: []" in text
    assert "https://github.com/acme/x/pull/1" in text


def test_link_needs_a_path_and_a_ref(fde: Path) -> None:
    opened(fde)
    assert "Usage:" in fails("path", "link", "auto-triage").output
    assert "There is no path nope" in fails("path", "link", "nope", "x.md").output


def test_detect_command_reports_links_once_initialised(repo: Path) -> None:
    make_files(repo, "docs/superpowers/specs/a.md", "docs/superpowers/specs/b.md")
    ok("init")
    ok("path", "link", "--pre-framework", "docs/superpowers/specs/a.md")
    report = json.loads(ok("detect").stdout)
    assert [a["linked_to"] for a in report["artifacts"]] == ["pre-framework", None]
