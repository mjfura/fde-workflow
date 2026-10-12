from pathlib import Path

from tests.helpers import add_kpi, decisions, fails, ok


def test_creating_the_north_star_records_no_decision(fde: Path) -> None:
    add_kpi(fde)
    ok(
        "northstar", "set",
        "--statement", "ACME customers resolve issues without waiting",
        "--beneficiary", "ACME customers",
        "--non-goal", "Replace Zendesk",
        "--primary-kpi", "resolution-time",
    )  # fmt: skip
    assert "North Star: ACME customers resolve issues without waiting" in ok("status").output
    assert decisions(fde) == []


def test_creating_needs_a_statement(fde: Path) -> None:
    assert "--statement is required" in fails("northstar", "set", "--problem", "x").output


def test_changing_a_confirmed_north_star_needs_reason_and_approver(fde: Path) -> None:
    ok("northstar", "set", "--statement", "First")
    assert "--reason is required" in fails("northstar", "set", "--statement", "Second").output
    ok("northstar", "set", "--statement", "Second", "--reason", "Pivot", "--approved-by", "Jane")
    [decision] = decisions(fde)
    assert decision["type"] == "north-star-change"
    assert decision["summary"] == "North Star: Second"
    assert decision["approved_by"] == "Jane"


def test_an_inferred_north_star_changes_freely_until_confirmed(fde: Path) -> None:
    ok("northstar", "set", "--statement", "Draft", "--inferred")
    assert "! [C1] The North Star was inferred" in ok("validate").output
    ok("northstar", "set", "--statement", "Better draft")
    ok("northstar", "confirm")
    assert "[C1]" not in ok("validate").output
    assert decisions(fde) == []


def test_primary_kpi_must_exist(fde: Path) -> None:
    result = fails("northstar", "set", "--statement", "x", "--primary-kpi", "nope")
    assert "[N1]" in result.output
