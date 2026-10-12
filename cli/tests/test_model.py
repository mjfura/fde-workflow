import datetime as dt

import pytest
from pydantic import ValidationError

from fde_workflow_cli.model import Direction, Kpi, Measurement, Outcome, StageName, StageState
from tests.helpers import sample_direction


def test_sample_direction_round_trips_through_json() -> None:
    direction = sample_direction()
    assert Direction.model_validate(direction.model_dump(mode="json")) == direction


def test_ids_must_be_kebab_case() -> None:
    data = sample_direction().model_dump(mode="json")
    data["kpis"][0]["id"] = "Resolution Time"
    with pytest.raises(ValidationError, match=r"kpis\.0\.id"):
        Direction.model_validate(data)


def test_ids_must_be_unique() -> None:
    data = sample_direction().model_dump(mode="json")
    data["kpis"].append(data["kpis"][0])
    with pytest.raises(ValidationError, match="duplicate KPI id"):
        Direction.model_validate(data)


def test_unknown_keys_are_rejected() -> None:
    data = sample_direction().model_dump(mode="json")
    data["north_star"]["statment"] = "typo"
    with pytest.raises(ValidationError, match="statment"):
        Direction.model_validate(data)


def test_outcome_is_set_only_when_closed() -> None:
    with pytest.raises(ValidationError, match="outcome"):
        StageState(current=StageName.CLOSED, entered=dt.date(2026, 1, 1))
    with pytest.raises(ValidationError, match="outcome"):
        StageState(current=StageName.MVP, entered=dt.date(2026, 1, 1), outcome=Outcome.COMPLETED)


def test_targets_must_be_finite_numbers() -> None:
    data = sample_direction().model_dump(mode="json")["kpis"][0]
    data["target"] = float("inf")
    with pytest.raises(ValidationError, match="target"):
        Kpi.model_validate(data)


def test_window_ending_counts_the_last_day() -> None:
    kpi = sample_direction().kpis[0]
    assert kpi.window_ending(dt.date(2026, 10, 28)) == (dt.date(2026, 10, 1), dt.date(2026, 10, 28))


def test_measurement_window_must_be_ordered() -> None:
    with pytest.raises(ValidationError, match="window_start"):
        Measurement(
            kpi="resolution-time",
            taken=dt.date(2026, 10, 12),
            window_start=dt.date(2026, 10, 12),
            window_end=dt.date(2026, 10, 1),
            value=1,
            source="x",
            recipe_sha256="abc",
        )
