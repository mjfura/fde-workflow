import datetime as dt

from fde_workflow_cli import summary
from fde_workflow_cli.model import BaselineType, Measurement, PathStatus
from fde_workflow_cli.rules import Issue
from tests.helpers import sample_direction


def measured(value: float, taken: str, baseline: BaselineType | None = None) -> Measurement:
    day = dt.date.fromisoformat(taken)
    return Measurement(
        kpi="resolution-time",
        taken=day,
        window_start=day,
        window_end=day,
        value=value,
        baseline=baseline,
        source="Zendesk",
        recipe_sha256="x",
    )


def test_kpi_line_shows_baseline_latest_and_target() -> None:
    kpi = sample_direction().kpis[0]
    line = summary.kpi_line(
        kpi, [measured(45, "2026-09-30", BaselineType.HISTORICAL), measured(40, "2026-10-10")]
    )
    assert line == (
        "resolution-time (primary): baseline 45 min (historical) → latest 40 min on 2026-10-10"
        " → target ≤ 30 min"
    )
    assert summary.kpi_line(kpi, []) == "resolution-time (primary): no baseline → target ≤ 30 min"


def test_render_lists_every_part_of_the_direction() -> None:
    text = summary.render(sample_direction(), [], [Issue("warning", "K3", "no baseline")])
    assert "Project: acme-support · customer ACME · sponsor Jane Doe" in text
    assert "North Star: ACME customers resolve issues without waiting for an agent" in text
    assert "Stage: mvp since 2026-10-01" in text
    assert "  Gate: 2 weeks" in text
    assert "auto-triage [active]" in text
    assert "! [K3] no baseline" in text


def test_brief_render_hides_closed_paths_and_caps_issues() -> None:
    direction = sample_direction()
    direction.paths[0].status = PathStatus.DISCARDED
    issues = [Issue("warning", "K3", f"issue {n}") for n in range(5)]
    text = summary.render(direction, [], issues, brief=True)
    assert "auto-triage" not in text
    assert "issue 2" in text
    assert "issue 3" not in text
    assert "2 more: run `fde-workflow validate`" in text


def test_context_starts_with_the_header() -> None:
    assert summary.context(sample_direction(), [], []).startswith(summary.CONTEXT_HEADER)
