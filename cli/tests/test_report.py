import datetime as dt

from fde_workflow_cli import report
from fde_workflow_cli.model import BaselineType, Decision, DecisionType, Measurement
from fde_workflow_cli.report import ReportKind
from tests.helpers import sample_direction


def measured(
    value: float, taken: str, baseline: BaselineType | None = None, factors: str = ""
) -> Measurement:
    day = dt.date.fromisoformat(taken)
    return Measurement(
        kpi="resolution-time",
        taken=day,
        window_start=day - dt.timedelta(days=27),
        window_end=day,
        value=value,
        baseline=baseline,
        source="Zendesk",
        external_factors=factors,
        recipe_sha256="x",
    )


def decision(day: str, summary: str) -> Decision:
    return Decision(
        date=dt.date.fromisoformat(day), type=DecisionType.OTHER, summary=summary, reason="r"
    )


def test_report_lists_kpis_against_baseline_and_target() -> None:
    measurements = [
        measured(45, "2026-09-30", BaselineType.HISTORICAL),
        measured(28, "2026-11-01", factors="Holiday season"),
    ]
    text = report.render(ReportKind.STATUS, sample_direction(), measurements, [], [], [], None)
    assert text.startswith("# Status report: acme-support")
    assert (
        "| resolution-time | primary | 45 min (historical, 2026-09-30) | 28 min (2026-11-01) "
        "| ≤ 30 min | -17 min (-37.8%) | yes |"
    ) in text
    assert "- resolution-time, 2026-11-01: Holiday season" in text
    assert "| auto-triage | active |" in text


def test_report_declares_late_baselines_and_the_limitation() -> None:
    measurements = [measured(45, "2026-10-12", BaselineType.LATE)]
    text = report.render(ReportKind.CLOSE, sample_direction(), measurements, [], [], [], None)
    assert text.startswith("# Closing report: acme-support")
    assert "resolution-time: the baseline is late" in text
    assert "do not prove causation" in text


def test_status_report_lists_decisions_since_a_date() -> None:
    decisions = [decision("2026-10-01", "Old"), decision("2026-10-10", "New")]
    since = dt.date(2026, 10, 5)
    text = report.render(ReportKind.STATUS, sample_direction(), [], decisions, [], [], since)
    assert "New" in text
    assert "Old" not in text
    assert "## Decisions since 2026-10-05" in text


def test_table_cells_cannot_break_the_table() -> None:
    direction = sample_direction()
    direction.paths[0].hypothesis = "a | b\nc"
    text = report.render(ReportKind.STATUS, direction, [], [], [], [], None)
    assert "a \\| b c" in text
