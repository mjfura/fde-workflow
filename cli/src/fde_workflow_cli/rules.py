"""The framework's rules (spec §2), checked over a whole `.fde/`."""

from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from fde_workflow_cli import recipes
from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import (
    Direction,
    DirectionPath,
    KpiKind,
    Measurement,
    PathStatus,
    StageName,
)

STAGES_THAT_MEASURE = (StageName.MVP, StageName.EARLY_ACCESS, StageName.PRODUCTION)


@dataclass(frozen=True)
class Issue:
    level: Literal["error", "warning"]
    rule: str
    message: str


def check(direction: Direction, measurements: list[Measurement], fde_dir: Path) -> list[Issue]:
    """Every broken rule, errors first. Errors block writes; warnings are reported."""
    issues = [
        *_north_star(direction),
        *_kpis(direction, measurements, fde_dir),
        *_paths(direction, measurements),
        *_stage(direction, measurements),
    ]
    return sorted(issues, key=lambda issue: issue.level != "error")


def latest_baseline(measurements: list[Measurement], kpi_id: str) -> Measurement | None:
    """The KPI's most recently recorded baseline (files keep recording order)."""
    baselines = [m for m in measurements if m.kpi == kpi_id and m.baseline is not None]
    return baselines[-1] if baselines else None


def has_evidence(path: DirectionPath, measurements: list[Measurement]) -> bool:
    """P2: a non-baseline measurement of a targeted KPI whose whole window follows activation."""
    activated = path.activated
    if activated is None:
        return False
    return any(
        m.kpi in path.expects and m.baseline is None and m.window_start > activated
        for m in measurements
    )


def _north_star(direction: Direction) -> Iterator[Issue]:
    north_star = direction.north_star
    if north_star is None:
        yield Issue("warning", "N1", "No North Star yet: define it with the discovery skill.")
        return
    if not north_star.confirmed:
        yield Issue(
            "warning",
            "C1",
            "The North Star was inferred and is not confirmed: "
            "`fde-workflow northstar confirm` once the FDE and the sponsor agree.",
        )
    if north_star.primary_kpi is None:
        yield Issue("warning", "N1", "The North Star has no primary KPI yet.")
        return
    kpi = direction.kpi(north_star.primary_kpi)
    if kpi is None:
        yield Issue(
            "error", "N1", f"The North Star's primary KPI {north_star.primary_kpi} does not exist."
        )
    elif kpi.kind is not KpiKind.PRIMARY:
        yield Issue(
            "error",
            "K2",
            f"The North Star's primary KPI {kpi.id} has kind {kpi.kind}, not primary.",
        )


def _kpis(direction: Direction, measurements: list[Measurement], fde_dir: Path) -> Iterator[Issue]:
    primaries = [kpi.id for kpi in direction.kpis if kpi.kind is KpiKind.PRIMARY]
    if len(primaries) > 1:
        yield Issue("error", "K2", f"Only one KPI can be primary; found {', '.join(primaries)}.")
    for kpi in direction.kpis:
        try:
            current = recipes.fingerprint(fde_dir, kpi.recipe)
        except FdeError as error:
            yield Issue("error", "M1", f"KPI {kpi.id}: {error}")
            continue
        if current is None:
            yield Issue(
                "error",
                "M1",
                f"KPI {kpi.id}: recipe .fde/{kpi.recipe.file} does not exist; write it first.",
            )
            continue
        baseline = latest_baseline(measurements, kpi.id)
        if baseline is None:
            yield Issue(
                "warning",
                "K3",
                f"KPI {kpi.id} has no baseline: measure it before work that should move it starts.",
            )
        elif baseline.recipe_sha256 != current:
            yield Issue(
                "warning",
                "K4",
                f"KPI {kpi.id}: the recipe changed after the baseline, so comparisons are not "
                "valid; measure the baseline again with --baseline.",
            )


def _paths(direction: Direction, measurements: list[Measurement]) -> Iterator[Issue]:
    for path in direction.paths:
        if not path.expects:
            yield Issue("error", "P1", f"Path {path.id} targets no KPI.")
        for kpi_id in path.expects:
            if direction.kpi(kpi_id) is None:
                yield Issue("error", "P1", f"Path {path.id} targets unknown KPI {kpi_id}.")
        if path.status is PathStatus.VALIDATED and not has_evidence(path, measurements):
            yield Issue(
                "error",
                "P2",
                f"Path {path.id} cannot be validated without evidence: it needs a measurement of "
                f"{', '.join(path.expects)} whose window starts after it became active.",
            )
        if not path.confirmed:
            yield Issue(
                "warning",
                "C1",
                f"Path {path.id} was inferred and is not confirmed: `fde-workflow path confirm`.",
            )


def _stage(direction: Direction, measurements: list[Measurement]) -> Iterator[Issue]:
    stage = direction.stage
    if not stage.confirmed:
        yield Issue(
            "warning",
            "C1",
            "The stage was inferred and is not confirmed: `fde-workflow stage confirm`.",
        )
    if stage.current is StageName.CLOSED:
        return
    if not stage.gate_criteria:
        yield Issue(
            "warning",
            "S1",
            f"Stage {stage.current} has no gate criteria: agree them with the sponsor now, "
            "not when leaving the stage.",
        )
    primary = direction.north_star.primary_kpi if direction.north_star else None
    if (
        stage.current in STAGES_THAT_MEASURE
        and primary is not None
        and not any(m.kpi == primary and m.window_end >= stage.entered for m in measurements)
    ):
        yield Issue(
            "warning",
            "S3",
            f"Primary KPI {primary} has no measurement since entering {stage.current} "
            f"on {stage.entered}.",
        )
