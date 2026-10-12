import datetime as dt
import hashlib
from pathlib import Path

from fde_workflow_cli import rules
from fde_workflow_cli.model import (
    BaselineType,
    Direction,
    KpiKind,
    Measurement,
    NorthStar,
    PathStatus,
    StageName,
)
from tests.helpers import sample_direction, write_recipe

RECIPE = "select 1\n"


def fingerprint() -> str:
    return hashlib.sha256(RECIPE.encode()).hexdigest()


def measured(
    taken: str,
    baseline: BaselineType | None = None,
    kpi: str = "resolution-time",
    sha: str | None = None,
) -> Measurement:
    day = dt.date.fromisoformat(taken)
    return Measurement(
        kpi=kpi,
        taken=day,
        window_start=day - dt.timedelta(days=27),
        window_end=day,
        value=40,
        baseline=baseline,
        source="Zendesk",
        recipe_sha256=sha or fingerprint(),
    )


def check(tmp_path: Path, direction: Direction, measurements: list[Measurement]) -> set[str]:
    write_recipe(tmp_path, "measures/resolution-time.sql", RECIPE)
    found = rules.check(direction, measurements, tmp_path / ".fde")
    return {f"{issue.level}:{issue.rule}" for issue in found}


BASELINE = measured("2026-09-30", baseline=BaselineType.HISTORICAL)


def test_sample_with_baseline_and_fresh_measurement_has_no_issue(tmp_path: Path) -> None:
    assert check(tmp_path, sample_direction(), [BASELINE, measured("2026-10-05")]) == set()


def test_missing_north_star_and_primary_kpi_are_warnings(tmp_path: Path) -> None:
    direction = sample_direction()
    direction.north_star = None
    assert "warning:N1" in check(tmp_path, direction, [BASELINE])
    direction.north_star = NorthStar(statement="x")
    assert "warning:N1" in check(tmp_path, direction, [BASELINE])


def test_primary_kpi_must_exist_and_be_primary(tmp_path: Path) -> None:
    direction = sample_direction()
    assert direction.north_star is not None
    direction.north_star.primary_kpi = "nope"
    assert "error:N1" in check(tmp_path, direction, [BASELINE])
    direction.north_star.primary_kpi = "resolution-time"
    direction.kpis[0].kind = KpiKind.SECONDARY
    assert "error:K2" in check(tmp_path, direction, [BASELINE])


def test_only_one_primary_kpi(tmp_path: Path) -> None:
    direction = sample_direction()
    direction.kpis.append(direction.kpis[0].model_copy(update={"id": "cost"}))
    write_recipe(tmp_path, "measures/resolution-time.sql", RECIPE)
    found = rules.check(direction, [BASELINE], tmp_path / ".fde")
    assert any(i.rule == "K2" and "cost" in i.message for i in found)


def test_missing_recipe_is_an_error(tmp_path: Path) -> None:
    direction = sample_direction()
    direction.kpis[0].recipe.file = "measures/missing.sql"
    assert "error:M1" in check(tmp_path, direction, [BASELINE])


def test_kpi_without_baseline_warns(tmp_path: Path) -> None:
    assert "warning:K3" in check(tmp_path, sample_direction(), [])


def test_recipe_changed_after_baseline_warns(tmp_path: Path) -> None:
    old = measured("2026-09-30", baseline=BaselineType.LATE, sha="old")
    assert "warning:K4" in check(tmp_path, sample_direction(), [old])


def test_paths_must_target_existing_kpis(tmp_path: Path) -> None:
    direction = sample_direction()
    direction.paths[0].expects = {}
    assert "error:P1" in check(tmp_path, direction, [BASELINE])
    direction.paths[0].expects = {"nope": 1}
    assert "error:P1" in check(tmp_path, direction, [BASELINE])


def test_validated_path_needs_a_measurement_after_activation(tmp_path: Path) -> None:
    direction = sample_direction()
    direction.paths[0].status = PathStatus.VALIDATED
    same_day = measured("2026-10-03")
    assert "error:P2" in check(tmp_path, direction, [BASELINE, same_day])
    later_baseline = measured("2026-10-05", baseline=BaselineType.LATE)
    assert "error:P2" in check(tmp_path, direction, [BASELINE, later_baseline])
    assert "error:P2" not in check(tmp_path, direction, [BASELINE, measured("2026-10-04")])


def test_inferred_items_need_confirmation(tmp_path: Path) -> None:
    direction = sample_direction()
    assert direction.north_star is not None
    direction.north_star.confirmed = False
    direction.paths[0].confirmed = False
    direction.stage.confirmed = False
    write_recipe(tmp_path, "measures/resolution-time.sql", RECIPE)
    found = rules.check(direction, [BASELINE], tmp_path / ".fde")
    assert sum(issue.rule == "C1" for issue in found) == 3


def test_stage_without_gate_criteria_warns(tmp_path: Path) -> None:
    direction = sample_direction()
    direction.stage.gate_criteria = []
    assert "warning:S1" in check(tmp_path, direction, [BASELINE, measured("2026-10-05")])


def test_primary_kpi_must_be_measured_in_mvp(tmp_path: Path) -> None:
    direction = sample_direction()
    assert "warning:S3" in check(tmp_path, direction, [BASELINE])
    direction.stage.current = StageName.POC
    assert "warning:S3" not in check(tmp_path, direction, [BASELINE])


def test_errors_come_first(tmp_path: Path) -> None:
    direction = sample_direction()
    direction.paths[0].expects = {"nope": 1}
    write_recipe(tmp_path, "measures/resolution-time.sql", RECIPE)
    levels = [issue.level for issue in rules.check(direction, [], tmp_path / ".fde")]
    assert levels == sorted(levels, key=lambda level: level != "error")
    assert levels[0] == "error"
