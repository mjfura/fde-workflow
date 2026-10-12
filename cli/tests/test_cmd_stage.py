from pathlib import Path

import yaml

from tests.helpers import decisions, fails, ok


def stage(fde: Path) -> dict[str, object]:
    data = yaml.safe_load((fde / ".fde" / "direction.yaml").read_text())
    assert isinstance(data, dict)
    result = data["stage"]
    assert isinstance(result, dict)
    return result


def test_set_records_a_stage_set_decision(fde: Path) -> None:
    ok(
        "stage",
        "set",
        "mvp",
        "--reason",
        "Deployed to 20 agents",
        "--inferred",
        "--entered",
        "2026-09-01",
    )
    assert stage(fde)["current"] == "mvp"
    assert stage(fde)["entered"] == "2026-09-01"
    assert decisions(fde)[0]["summary"] == "Stage set to mvp (inferred)"
    assert "! [C1] The stage was inferred" in ok("validate").output
    ok("stage", "confirm")
    assert stage(fde)["confirmed"] is True


def test_set_closed_needs_an_outcome(fde: Path) -> None:
    assert "outcome" in fails("stage", "set", "closed", "--reason", "r").output
    ok("stage", "set", "closed", "--reason", "r", "--outcome", "completed")


def test_criteria_can_be_set_once_then_changes_need_approval(fde: Path) -> None:
    ok("stage", "criteria", "North Star agreed", "Baselines measured")
    assert stage(fde)["gate_criteria"] == ["North Star agreed", "Baselines measured"]
    assert decisions(fde) == []
    assert "--reason is required" in fails("stage", "criteria", "Only one").output
    ok("stage", "criteria", "Only one", "--reason", "r", "--approved-by", "Jane")
    assert decisions(fde)[0]["summary"] == "Gate criteria of discovery changed"


def test_go_moves_to_the_next_stage_and_resets_criteria(fde: Path) -> None:
    ok("stage", "criteria", "x")
    ok("stage", "decide", "go", "--reason", "Baselines in", "--approved-by", "Jane")
    assert stage(fde)["current"] == "poc"
    assert stage(fde)["gate_criteria"] == []
    assert decisions(fde)[-1]["summary"] == "go at discovery → poc"
    ok("stage", "decide", "go", "--to", "mvp", "--reason", "r", "--approved-by", "J")
    assert stage(fde)["current"] == "mvp"


def test_go_rules(fde: Path) -> None:
    assert (
        "after discovery"
        in fails(
            "stage", "decide", "go", "--to", "discovery", "--reason", "r", "--approved-by", "J"
        ).output
    )
    assert (
        "use kill"
        in fails(
            "stage", "decide", "go", "--to", "closed", "--reason", "r", "--approved-by", "J"
        ).output
    )
    assert (
        "only applies to go"
        in fails(
            "stage", "decide", "hold", "--to", "mvp", "--reason", "r", "--approved-by", "J"
        ).output
    )


def test_hold_recycle_and_kill(fde: Path) -> None:
    ok("stage", "decide", "hold", "--reason", "Budget freeze", "--approved-by", "J")
    assert stage(fde)["on_hold"] is True
    ok("stage", "decide", "recycle", "--reason", "Resume", "--approved-by", "J")
    assert stage(fde)["on_hold"] is False
    ok("stage", "decide", "kill", "--reason", "No data access", "--approved-by", "J")
    assert stage(fde)["outcome"] == "discontinued"
    assert "closed" in fails("stage", "decide", "go", "--reason", "r", "--approved-by", "J").output


def test_production_go_completes_the_project(fde: Path) -> None:
    ok("stage", "set", "production", "--reason", "r")
    ok("stage", "decide", "go", "--reason", "Target reached", "--approved-by", "J")
    assert stage(fde)["current"] == "closed"
    assert stage(fde)["outcome"] == "completed"


def test_decision_add(fde: Path) -> None:
    ok(
        "decision",
        "add",
        "--type",
        "scope-change",
        "--summary",
        "Drop email",
        "--reason",
        "r",
        "--ref",
        "auto-triage",
    )
    [decision] = decisions(fde)
    assert decision["type"] == "scope-change"
    assert decision["refs"] == ["auto-triage"]


def test_confirming_the_stage_records_one_decision(fde: Path) -> None:
    ok("stage", "set", "mvp", "--reason", "Deployed", "--inferred")
    ok("stage", "confirm", "--approved-by", "Jane")
    assert "already confirmed" in ok("stage", "confirm").output
    assert [d["summary"] for d in decisions(fde)] == [
        "Stage set to mvp (inferred)",
        "Confirm stage mvp",
    ]
