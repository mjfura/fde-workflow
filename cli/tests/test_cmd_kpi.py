from pathlib import Path

from tests.helpers import add_kpi, cli, decisions, fails, measurements, ok, write_recipe


def test_add_needs_an_existing_recipe(fde: Path) -> None:
    result = fails(
        "kpi", "add", "cost",
        "--name", "Cost", "--kind", "guardrail", "--definition", "EUR per ticket",
        "--source", "Billing", "--direction", "decrease", "--target", "5",
        "--recipe-type", "manual", "--recipe-file", "measures/cost.md",
    )  # fmt: skip
    assert "[M1]" in result.output


def test_add_rejects_duplicates_and_a_second_primary(fde: Path) -> None:
    add_kpi(fde)
    write_recipe(fde, "measures/resolution-time.sql")
    assert "already exists" in fails(
        "kpi", "add", "resolution-time", "--name", "x", "--kind", "primary",
        "--definition", "x", "--source", "x", "--direction", "decrease", "--target", "1",
        "--recipe-type", "query", "--recipe-file", "measures/resolution-time.sql",
    ).output  # fmt: skip
    write_recipe(fde, "measures/csat.sql")
    assert "[K2]" in fails(
        "kpi", "add", "csat", "--name", "CSAT", "--kind", "primary",
        "--definition", "x", "--source", "x", "--direction", "increase", "--target", "4.5",
        "--recipe-type", "query", "--recipe-file", "measures/csat.sql",
    ).output  # fmt: skip


def test_changing_a_target_needs_reason_and_approver(fde: Path) -> None:
    add_kpi(fde)
    ok("kpi", "update", "resolution-time", "--name", "Renamed")
    assert decisions(fde) == []
    assert (
        "--reason is required" in fails("kpi", "update", "resolution-time", "--target", "25").output
    )
    ok("kpi", "update", "resolution-time", "--target", "25", "--reason", "r", "--approved-by", "J")
    [decision] = decisions(fde)
    assert decision["type"] == "target-change"
    assert decision["summary"] == "Target of resolution-time: 30 → 25"


def test_measure_a_query_recipe_shows_it_then_records_the_value(fde: Path) -> None:
    add_kpi(fde)
    shown = ok("kpi", "measure", "resolution-time", "--window-end", "2026-09-30").output
    assert "closed between '2026-09-03' and '2026-09-30'" in shown
    assert measurements(fde) == []
    recorded = ok(
        "kpi", "measure", "resolution-time", "--baseline", "historical",
        "--window-end", "2026-09-30", "--value", "45", "--source", "Zendesk export",
        "--factors", "Holiday season",
    ).output  # fmt: skip
    assert "Recorded historical baseline resolution-time = 45 min" in recorded
    [measurement] = measurements(fde)
    assert measurement["taken"] == "2026-10-12"
    assert measurement["window_start"] == "2026-09-03"
    assert measurement["baseline"] == "historical"
    assert measurement["external_factors"] == "Holiday season"
    assert len(str(measurement["recipe_sha256"])) == 64


def test_measure_query_needs_a_source_and_cannot_run(fde: Path) -> None:
    add_kpi(fde)
    assert (
        "--source is required" in fails("kpi", "measure", "resolution-time", "--value", "1").output
    )
    assert "Only script recipes run" in fails("kpi", "measure", "resolution-time", "--run").output


def test_measure_a_script_recipe_only_with_run(fde: Path) -> None:
    write_recipe(fde, "measures/uptime.sh", "#!/bin/sh\necho 99.5\n", executable=True)
    ok(
        "kpi", "add", "uptime", "--name", "Uptime", "--kind", "guardrail",
        "--definition", "% of minutes up", "--source", "Monitoring", "--unit", "%",
        "--direction", "increase", "--target", "99", "--recipe-type", "script",
        "--recipe-file", "measures/uptime.sh", "--window", "7d",
    )  # fmt: skip
    assert "Add --run" in ok("kpi", "measure", "uptime", "--baseline", "late").output
    assert measurements(fde) == []
    assert "run, not typed" in fails("kpi", "measure", "uptime", "--value", "1").output
    ok("kpi", "measure", "uptime", "--baseline", "late", "--run")
    [measurement] = measurements(fde)
    assert measurement["value"] == 99.5
    assert measurement["source"] == "script .fde/measures/uptime.sh"


def test_measure_warns_without_baseline_and_after_recipe_change(fde: Path) -> None:
    add_kpi(fde)
    args = ("kpi", "measure", "resolution-time", "--value", "40", "--source", "s")
    assert "has no baseline yet" in ok(*args).output
    ok(*args, "--baseline", "late")
    write_recipe(fde, "measures/resolution-time.sql", "select 2\n")
    assert "[K4]" in ok(*args).output


def test_validate_exits_one_on_errors(fde: Path) -> None:
    add_kpi(fde)
    (fde / ".fde" / "measures" / "resolution-time.sql").unlink()
    result = cli("validate")
    assert result.exit_code == 1
    assert "✗ [M1]" in result.output
    assert "Invalid: 1 error(s)" in result.output


def test_status_and_context_show_kpis(fde: Path) -> None:
    add_kpi(fde)
    assert "resolution-time (primary): no baseline → target ≤ 30 min" in ok("status").output
    context = ok("context", "--brief").output
    assert context.startswith("FDE direction of this repository")
    assert "Gate criteria: 0" in context
