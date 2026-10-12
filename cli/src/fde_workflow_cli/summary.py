"""Plain-text summaries of a direction: for people (`status`) and for Claude (`context`)."""

from fde_workflow_cli.model import Better, Direction, Kpi, Measurement, PathStatus
from fde_workflow_cli.rules import Issue, latest_baseline

LIVE_PATHS = (PathStatus.PROPOSED, PathStatus.ACTIVE, PathStatus.MEASURING)
BRIEF_ISSUES = 3
CONTEXT_HEADER = (
    "FDE direction of this repository (.fde/). Keep the work aligned with it; change it only "
    "through the fde-workflow skills and CLI."
)


def number(value: float) -> str:
    return f"{value:g}"


def kpi_line(kpi: Kpi, measurements: list[Measurement]) -> str:
    unit = f" {kpi.unit}" if kpi.unit else ""
    baseline = latest_baseline(measurements, kpi.id)
    latest = next(
        (m for m in reversed(measurements) if m.kpi == kpi.id and m.baseline is None), None
    )
    values = [
        f"baseline {number(baseline.value)}{unit} ({baseline.baseline})"
        if baseline
        else "no baseline"
    ]
    if latest:
        values.append(f"latest {number(latest.value)}{unit} on {latest.taken}")
    sign = "≤" if kpi.direction is Better.DECREASE else "≥"
    values.append(f"target {sign} {number(kpi.target)}{unit}")
    return f"{kpi.id} ({kpi.kind}): " + " → ".join(values)


def render(
    direction: Direction, measurements: list[Measurement], issues: list[Issue], brief: bool = False
) -> str:
    project = direction.project
    header = f"Project: {project.name}"
    if project.customer:
        header += f" · customer {project.customer}"
    if project.sponsor:
        header += f" · sponsor {project.sponsor}"
    lines = [header]

    north_star = direction.north_star
    if north_star is None:
        lines.append("North Star: not defined")
    else:
        inferred = "" if north_star.confirmed else " (inferred)"
        lines.append(f"North Star: {north_star.statement}{inferred}")
        lines.append(f"  Primary KPI: {north_star.primary_kpi or 'not set'}")
        if north_star.non_goals and not brief:
            lines.append(f"  Non-goals: {'; '.join(north_star.non_goals)}")

    stage = direction.stage
    stage_line = f"Stage: {stage.current} since {stage.entered}"
    if stage.outcome:
        stage_line += f" ({stage.outcome})"
    if stage.on_hold:
        stage_line += " (on hold)"
    if not stage.confirmed:
        stage_line += " (inferred)"
    lines.append(stage_line)
    if brief:
        lines.append(f"  Gate criteria: {len(stage.gate_criteria)}")
    else:
        lines += [f"  Gate: {criterion}" for criterion in stage.gate_criteria]

    lines.append("KPIs:" if direction.kpis else "KPIs: none")
    lines += [f"  {kpi_line(kpi, measurements)}" for kpi in direction.kpis]

    paths = [p for p in direction.paths if not brief or p.status in LIVE_PATHS]
    lines.append("Paths:" if paths else "Paths: none")
    for path in paths:
        inferred = "" if path.confirmed else " (inferred)"
        expects = ", ".join(f"{kpi_id} → {number(v)}" for kpi_id, v in path.expects.items())
        lines.append(f"  {path.id} [{path.status}]{inferred}: {path.hypothesis} ({expects})")

    shown = issues[:BRIEF_ISSUES] if brief else issues
    if shown:
        lines.append("Issues:")
        lines += [
            f"  {'✗' if issue.level == 'error' else '!'} [{issue.rule}] {issue.message}"
            for issue in shown
        ]
        if len(issues) > len(shown):
            lines.append(f"  … {len(issues) - len(shown)} more: run `fde-workflow validate`.")
    return "\n".join(lines)


def context(
    direction: Direction, measurements: list[Measurement], issues: list[Issue], brief: bool = False
) -> str:
    return f"{CONTEXT_HEADER}\n\n{render(direction, measurements, issues, brief)}"
