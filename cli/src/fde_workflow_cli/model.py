"""The direction framework's data model: what the files in `.fde/` contain."""

import datetime as dt
from enum import StrEnum
from pathlib import PurePosixPath
from typing import Annotated, Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    FiniteFloat,
    StringConstraints,
    field_validator,
    model_validator,
)

SCHEMA_VERSION = 1

Identifier = Annotated[str, StringConstraints(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")]
Window = Annotated[str, StringConstraints(pattern=r"^[1-9][0-9]*d$")]


class StageName(StrEnum):
    DISCOVERY = "discovery"
    POC = "poc"
    MVP = "mvp"
    EARLY_ACCESS = "early-access"
    PRODUCTION = "production"
    CLOSED = "closed"


STAGE_ORDER: list[StageName] = list(StageName)


class Outcome(StrEnum):
    COMPLETED = "completed"
    DISCONTINUED = "discontinued"


class GateDecision(StrEnum):
    GO = "go"
    RECYCLE = "recycle"
    HOLD = "hold"
    KILL = "kill"


class KpiKind(StrEnum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    GUARDRAIL = "guardrail"


class Better(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"


class RecipeType(StrEnum):
    SCRIPT = "script"
    QUERY = "query"
    MANUAL = "manual"


class PathStatus(StrEnum):
    PROPOSED = "proposed"
    ACTIVE = "active"
    MEASURING = "measuring"
    VALIDATED = "validated"
    DISCARDED = "discarded"


class BaselineType(StrEnum):
    HISTORICAL = "historical"
    LATE = "late"


class DecisionType(StrEnum):
    NORTH_STAR_CHANGE = "north-star-change"
    TARGET_CHANGE = "target-change"
    PATH_OPEN = "path-open"
    PATH_VALIDATE = "path-validate"
    PATH_DISCARD = "path-discard"
    STAGE_GATE = "stage-gate"
    STAGE_SET = "stage-set"
    SCOPE_CHANGE = "scope-change"
    OTHER = "other"


class Record(BaseModel):
    """Base of every model: unknown keys are errors, so typos in hand-edited files surface."""

    model_config = ConfigDict(extra="forbid")


class Project(Record):
    name: str = Field(min_length=1)
    customer: str = ""
    sponsor: str = ""


class NorthStar(Record):
    statement: str = Field(min_length=1)
    beneficiary: str = ""
    problem: str = ""
    non_goals: list[str] = Field(default_factory=list)
    primary_kpi: Identifier | None = None
    confirmed: bool = True


class StageState(Record):
    current: StageName = StageName.DISCOVERY
    entered: dt.date
    outcome: Outcome | None = None
    on_hold: bool = False
    confirmed: bool = True
    gate_criteria: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _outcome_only_when_closed(self) -> Self:
        if (self.current is StageName.CLOSED) != (self.outcome is not None):
            raise ValueError("outcome must be set when, and only when, the stage is closed")
        return self


class Recipe(Record):
    type: RecipeType
    file: str = Field(min_length=1)


class Kpi(Record):
    id: Identifier
    name: str = Field(min_length=1)
    kind: KpiKind
    definition: str = Field(min_length=1)
    source: str = Field(min_length=1)
    unit: str = ""
    direction: Better
    target: FiniteFloat
    window: Window = "28d"
    recipe: Recipe

    def window_ending(self, end: dt.date) -> tuple[dt.date, dt.date]:
        """The measurement window (first day, last day) that ends on `end`."""
        days = int(self.window.removesuffix("d"))
        return end - dt.timedelta(days=days - 1), end


class DirectionPath(Record):
    id: Identifier
    hypothesis: str = Field(min_length=1)
    expects: dict[Identifier, FiniteFloat]
    status: PathStatus = PathStatus.PROPOSED
    activated: dt.date | None = None
    maturity: StageName | None = None
    confirmed: bool = True
    links: list[str] = Field(default_factory=list)
    learning: str | None = None


class Artifacts(Record):
    globs: list[str] = Field(default_factory=list)
    pre_framework: list[str] = Field(default_factory=list)

    @field_validator("globs")
    @classmethod
    def _globs_stay_inside_the_repository(cls, globs: list[str]) -> list[str]:
        for pattern in globs:
            path = PurePosixPath(pattern)
            if not pattern or path.is_absolute() or ".." in path.parts:
                raise ValueError(f"{pattern!r} must be a relative pattern inside the repository")
        return globs


class Direction(Record):
    schema_version: int = SCHEMA_VERSION
    project: Project
    north_star: NorthStar | None = None
    stage: StageState
    kpis: list[Kpi] = Field(default_factory=list)
    paths: list[DirectionPath] = Field(default_factory=list)
    artifacts: Artifacts = Field(default_factory=Artifacts)

    @model_validator(mode="after")
    def _ids_are_unique(self) -> Self:
        for label, ids in (
            ("KPI", [k.id for k in self.kpis]),
            ("path", [p.id for p in self.paths]),
        ):
            duplicates = sorted({i for i in ids if ids.count(i) > 1})
            if duplicates:
                raise ValueError(f"duplicate {label} id(s): {', '.join(duplicates)}")
        return self

    def kpi(self, kpi_id: str) -> Kpi | None:
        return next((k for k in self.kpis if k.id == kpi_id), None)

    def path(self, path_id: str) -> DirectionPath | None:
        return next((p for p in self.paths if p.id == path_id), None)


class Measurement(Record):
    kpi: Identifier
    taken: dt.date
    window_start: dt.date
    window_end: dt.date
    value: FiniteFloat
    baseline: BaselineType | None = None
    source: str = Field(min_length=1)
    external_factors: str = ""
    recipe_sha256: str

    @model_validator(mode="after")
    def _window_is_ordered(self) -> Self:
        if self.window_start > self.window_end:
            raise ValueError("window_start must not be after window_end")
        return self


class Decision(Record):
    date: dt.date
    type: DecisionType
    summary: str = Field(min_length=1)
    reason: str = Field(min_length=1)
    approved_by: str = ""
    refs: list[str] = Field(default_factory=list)
