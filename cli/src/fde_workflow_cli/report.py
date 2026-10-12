"""Markdown reports of a direction: a status report for the sponsor and the closing value report."""

import datetime as dt
from enum import StrEnum

from fde_workflow_cli import clock
from fde_workflow_cli.model import BaselineType, Better, Decision, Direction, Kpi, Measurement
from fde_workflow_cli.rules import Issue, latest_baseline
from fde_workflow_cli.summary import clean, number

LIMITATION = (
    "Before/after comparisons do not prove causation: the external factors recorded with each "
    "measurement are listed above."
)


class ReportKind(StrEnum):
    STATUS = "status"
    CLOSE = "close"


TITLES = {ReportKind.STATUS: "Status report", ReportKind.CLOSE: "Closing report"}


def cell(text: str) -> str:
    """Text that fits in one Markdown table cell."""
    return clean(text).replace("|", "\\|")


def _latest(measurements: list[Measurement], kpi_id: str) -> Measurement | None:
    return next((m for m in reversed(measurements) if m.kpi == kpi_id and m.baseline is None), None)


def _kpi_row(kpi: Kpi, measurements: list[Measurement]) -> str:
    unit = f" {cell(kpi.unit)}" if kpi.unit else ""
    baseline = latest_baseline(measurements, kpi.id)
    latest = _latest(measurements, kpi.id)
    sign = "≤" if kpi.direction is Better.DECREASE else "≥"
    columns = [
        kpi.id,
        str(kpi.kind),
        f"{number(baseline.value)}{unit} ({baseline.baseline}, {baseline.taken})"
        if baseline
        else "—",
        f"{number(latest.value)}{unit} ({latest.taken})" if latest else "—",
        f"{sign} {number(kpi.target)}{unit}",
    ]
    if baseline and latest:
        delta = latest.value - baseline.value
        change = f"{delta:+g}{unit}"
        if baseline.value:
            change += f" ({delta / baseline.value:+.1%})"
        columns.append(change)
    else:
        columns.append("—")
    if latest:
        met = (
            latest.value <= kpi.target
            if kpi.direction is Better.DECREASE
            else latest.value >= kpi.target
        )
        columns.append("yes" if met else "no")
    else:
        columns.append("—")
    return "| " + " | ".join(columns) + " |"


def render(
    kind: ReportKind,
    direction: Direction,
    measurements: list[Measurement],
    decisions: list[Decision],
    issues: list[Issue],
    drift: list[str],
    since: dt.date | None,
) -> str:
    project = direction.project
    lines = [f"# {TITLES[kind]}: {cell(project.name)} — {clock.today()}", ""]
    if project.customer:
        lines.append(f"- Customer: {cell(project.customer)}")
    if project.sponsor:
        lines.append(f"- Sponsor: {cell(project.sponsor)}")

    lines += ["", "## North Star", ""]
    north_star = direction.north_star
    if north_star is None:
        lines.append("Not defined yet.")
    else:
        lines.append(cell(north_star.statement) + ("" if north_star.confirmed else " (inferred)"))
        lines.append("")
        if north_star.beneficiary:
            lines.append(f"- Beneficiary: {cell(north_star.beneficiary)}")
        if north_star.problem:
            lines.append(f"- Problem: {cell(north_star.problem)}")
        lines += [f"- Non-goal: {cell(goal)}" for goal in north_star.non_goals]
        lines.append(f"- Primary KPI: {north_star.primary_kpi or 'not set'}")

    stage = direction.stage
    lines += ["", "## Stage", "", f"{stage.current} since {stage.entered}"]
    if stage.outcome:
        lines[-1] += f" ({stage.outcome})"
    if stage.on_hold:
        lines[-1] += " (on hold)"
    if stage.gate_criteria:
        lines += ["", "Gate criteria:"] + [f"- {cell(item)}" for item in stage.gate_criteria]

    lines += ["", "## KPIs", ""]
    if direction.kpis:
        lines += [
            "| KPI | Kind | Baseline | Latest | Target | Change | Target met |",
            "|---|---|---|---|---|---|---|",
        ]
        lines += [_kpi_row(kpi, measurements) for kpi in direction.kpis]
        factors = [m for m in measurements if m.external_factors]
        if factors:
            lines += ["", "External factors:"]
            lines += [f"- {m.kpi}, {m.taken}: {cell(m.external_factors)}" for m in factors]
    else:
        lines.append("None defined yet.")

    lines += ["", "## Paths", ""]
    if direction.paths:
        lines += [
            "| Path | Status | Hypothesis | Expects | Links | Learning |",
            "|---|---|---|---|---|---|",
        ]
        for path in direction.paths:
            expects = ", ".join(f"{k} → {number(v)}" for k, v in path.expects.items())
            lines.append(
                f"| {path.id} | {path.status} | {cell(path.hypothesis)} | {expects} "
                f"| {len(path.links)} | {cell(path.learning or '')} |"
            )
    else:
        lines.append("None yet.")

    lines += ["", "## Drift", ""]
    lines += [f"- {item}" for item in drift] if drift else ["None."]

    shown = [d for d in decisions if since is None or d.date >= since]
    lines += ["", f"## Decisions since {since}" if since else "## Decisions", ""]
    for item in shown:
        approved = f" (approved by {cell(item.approved_by)})" if item.approved_by else ""
        lines.append(
            f"- {item.date} · {item.type} · {cell(item.summary)} — {cell(item.reason)}{approved}"
        )
    if not shown:
        lines.append("None.")

    if issues:
        lines += ["", "## Open issues", ""]
        lines += [f"- [{issue.rule}] {cell(issue.message)}" for issue in issues]

    lines += ["", "## Notes", ""]
    for kpi in direction.kpis:
        baseline = latest_baseline(measurements, kpi.id)
        if baseline and baseline.baseline is BaselineType.LATE:
            lines.append(
                f"- {kpi.id}: the baseline is late (measured on {baseline.taken}, after the work "
                "started), so impact achieved before it is not captured."
            )
    lines.append(f"- {LIMITATION}")
    return "\n".join(lines) + "\n"
