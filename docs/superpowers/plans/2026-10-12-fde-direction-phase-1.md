# FDE Direction Framework — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship phase 1 of the FDE direction framework: the `.fde/` data model and rules in the
`fde-workflow` CLI, the SessionStart hook, and the `fde-workflow`, `adopt`, `discovery`, `kpi` and
`path` skills, so the framework can be used on a real customer project.

**Architecture:** The CLI (Typer, Python 3.13) owns `.fde/`: pydantic models describe
`direction.yaml` and the two append-only JSONL logs; `rules.check()` implements every **[V]** rule
of the spec; `Store.save()` refuses any write that breaks a rule, so the files are always valid.
Commands are thin wrappers that load, change, save and record decisions. The plugin adds skills
(judgement and conversation, writing only through the CLI) and a SessionStart hook that calls
`fde-workflow hook session-start`.

**Tech Stack:** Python 3.13, Typer 0.27, pydantic 2.14, PyYAML 6, pytest, ruff, mypy (strict);
POSIX sh for the hook wrapper and eval stub; Claude Code plugin skills, hooks and evals.

**Spec:** `docs/superpowers/specs/2026-10-12-fde-direction-framework-design.md`

## Global Constraints

- Python `>=3.13,<4.0`. New runtime dependencies: only `pydantic (>=2.14,<3)` and
  `pyyaml (>=6.0.3,<7)`; new dev dependency: `types-pyyaml`.
- ruff (line length 100; rules E, W, F, I, B, UP, SIM, RUF, S, PT) and mypy `strict` over `src`
  and `tests` must pass: `make cli-check` before every commit that touches `cli/`,
  `make plugin-check` before every commit that touches `plugin/`.
- Everything written to git is in English; Conventional Commits; no AI attribution in commits or
  PRs.
- Work on a `feat/` branch created from `main` (e.g. `feat/direction-framework-core`), never on
  `main`. Do not change versions (`0.1.0`); releases follow `docs/releasing.md`.
- `.fde/direction.yaml`, `measurements.jsonl` and `decisions.jsonl` are written only by the CLI;
  skills write only recipes (`.fde/measures/`) and notes (`.fde/discovery/`).
- Hooks always exit 0 and stay silent without `.fde/` or without the CLI.
- `plugin/evals/run.sh` uses model calls on the owner's account: never run it without asking the
  owner; never in CI.

## Refinements of the spec made by this plan

The spec stays the source of truth; these details are decided here:
- `init --glob PATTERN` (repeatable) for methodologies without a preset.
- `stage confirm`, `stage set --entered DATE`, `stage decide go --to STAGE`.
- `kpi measure` without `--value`/`--run` prints how to take the measurement and records nothing.
- `path add --status proposed|active|measuring --activated DATE --link REF`; validated and
  discarded are reached only through `path move`.
- Rule **C1**: inferred items (North Star, paths, stage) are warnings until confirmed.
- **K4** (recipe changed after the baseline) is a warning, so it never blocks other work.
- Replacing agreed gate criteria needs `--reason` and `--approved-by` and records a decision.
- **P2** counts only non-baseline measurements taken strictly after the activation date.

## Review Focus

1. **Hand-edited or outdated `.fde/` files** (typo in a key, wrong enum, other `schema_version`):
   every command fails with the file, the location and the fix; the hook tells Claude instead of
   crashing. Pinned in Task 4 (`test_load_*`) and Task 12 (`test_session_start_reports_*`).
2. **Running from a subdirectory of the repository**: commands and the hook find `.fde/` upwards.
   Pinned in Task 4 (`test_locate_*`), Task 7 and Task 12.
3. **Recipes that misbehave** (path outside `.fde/`, not executable, non-zero exit, text, NaN):
   refused with a clear message and nothing recorded. Pinned in Task 2.
4. **Weak evidence for validating a path** (measurement on the activation day, a baseline taken
   later): it does not count. Pinned in Task 3 and Task 10.
5. **Machines without the CLI or repositories without `.fde/`**: the hook is silent and exits 0.
   Pinned in Task 12 (`test_fde_hook.sh`, `test_session_start_is_silent_without_fde`).

## File structure

```
cli/src/fde_workflow_cli/
  errors.py      FdeError: problems the user can fix
  clock.py       today(), patched in tests
  model.py       pydantic models and enums of .fde/
  recipes.py     recipe location, fingerprint, rendering, running scripts
  rules.py       every [V] rule → list[Issue]
  store.py       Store: load/save direction.yaml (validated), JSONL logs; locate()
  detect.py      methodology presets, artifact inventory, deployment signals
  summary.py     text for `status` and `context`
  commands/      common.py (shared helpers), project.py (init, detect, validate, status,
                 context), kpi.py, northstar.py, path.py, stage.py, decision.py, hook.py
  main.py        registers the commands (modified)
  doctor.py      adds check_direction (modified)
cli/tests/       helpers.py, conftest.py, one test file per module or command group
plugin/hooks/    hooks.json, fde-hook (wrapper), test_fde_hook.sh
plugin/skills/   fde-workflow (rewritten, + references/framework.md), adopt, discovery, kpi,
                 path (new), setup (modified)
plugin/evals/    stub (extended) and four new cases
```

---

### Task 1: Dependencies and data model

**Files:**
- Modify: `cli/pyproject.toml`, `cli/poetry.lock` (through Poetry)
- Create: `cli/src/fde_workflow_cli/errors.py`, `cli/src/fde_workflow_cli/clock.py`,
  `cli/src/fde_workflow_cli/model.py`
- Create: `cli/tests/helpers.py`, `cli/tests/conftest.py`
- Test: `cli/tests/test_model.py`

**Interfaces:**
- Produces: `FdeError`; `clock.today() -> dt.date`; `model.SCHEMA_VERSION = 1`; enums `StageName`
  (+ `STAGE_ORDER`), `Outcome`, `GateDecision`, `KpiKind`, `Better`, `RecipeType`, `PathStatus`,
  `BaselineType`, `DecisionType`; models `Project`, `NorthStar`, `StageState`, `Recipe`,
  `Kpi` (`window_ending(end) -> (start, end)`), `DirectionPath`, `Artifacts`, `Direction`
  (`kpi(id)`, `path(id)`), `Measurement`, `Decision`.
- Test helpers used by every later task: `TODAY`, `cli()`, `ok()`, `fails()`, `make_files()`,
  `write_recipe()`, `add_kpi()`, `decisions()`, `measurements()`, `sample_direction()`; fixtures
  `fixed_today` (autouse), `repo` (empty repo as cwd), `fde` (repo after `init`; usable from
  Task 7 on).

- [ ] **Step 1: Add the dependencies**

```bash
cd cli
poetry add "pydantic (>=2.14,<3)" "pyyaml (>=6.0.3,<7)"
poetry add --group dev types-pyyaml
```
Expected: `pyproject.toml` lists both under `[project].dependencies`, `types-pyyaml` under the dev
group, and `poetry.lock` is updated.

- [ ] **Step 2: Write the shared test helpers** — `cli/tests/helpers.py`

```python
"""Shared helpers for the tests: a fixed today, a CLI runner and a sample direction."""

import datetime as dt
import json
from pathlib import Path

from typer.testing import CliRunner, Result

from fde_workflow_cli.main import app
from fde_workflow_cli.model import Direction

TODAY = dt.date(2026, 10, 12)
QUERY = (
    "select median(minutes) from tickets\n"
    "where closed between '{{window_start}}' and '{{window_end}}'\n"
)

runner = CliRunner()


def cli(*args: str, stdin: str | None = None) -> Result:
    return runner.invoke(app, list(args), input=stdin)


def ok(*args: str, stdin: str | None = None) -> Result:
    result = cli(*args, stdin=stdin)
    assert result.exit_code == 0, result.output
    return result


def fails(*args: str) -> Result:
    result = cli(*args)
    assert result.exit_code == 1, result.output
    return result


def make_files(repo: Path, *files: str) -> None:
    for relative in files:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")


def write_recipe(repo: Path, relative: str, text: str = QUERY, executable: bool = False) -> Path:
    path = repo / ".fde" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(0o755)
    return path


def add_kpi(
    repo: Path, kpi_id: str = "resolution-time", kind: str = "primary", target: str = "30"
) -> None:
    write_recipe(repo, f"measures/{kpi_id}.sql")
    ok(
        "kpi", "add", kpi_id,
        "--name", "Median resolution time",
        "--kind", kind,
        "--definition", "Median minutes from creation to resolution",
        "--source", "Zendesk",
        "--unit", "min",
        "--direction", "decrease",
        "--target", target,
        "--recipe-type", "query",
        "--recipe-file", f"measures/{kpi_id}.sql",
    )  # fmt: skip


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def decisions(repo: Path) -> list[dict[str, object]]:
    return read_jsonl(repo / ".fde" / "decisions.jsonl")


def measurements(repo: Path) -> list[dict[str, object]]:
    return read_jsonl(repo / ".fde" / "measurements.jsonl")


def sample_direction() -> Direction:
    return Direction.model_validate(
        {
            "project": {"name": "acme-support", "customer": "ACME", "sponsor": "Jane Doe"},
            "north_star": {
                "statement": "ACME customers resolve issues without waiting for an agent",
                "primary_kpi": "resolution-time",
            },
            "stage": {"current": "mvp", "entered": "2026-10-01", "gate_criteria": ["2 weeks"]},
            "kpis": [
                {
                    "id": "resolution-time",
                    "name": "Median resolution time",
                    "kind": "primary",
                    "definition": "Median minutes",
                    "source": "Zendesk",
                    "unit": "min",
                    "direction": "decrease",
                    "target": 30,
                    "recipe": {"type": "query", "file": "measures/resolution-time.sql"},
                }
            ],
            "paths": [
                {
                    "id": "auto-triage",
                    "hypothesis": "If tickets are classified on arrival, resolution drops 20%",
                    "expects": {"resolution-time": 36},
                    "status": "active",
                    "activated": "2026-10-03",
                }
            ],
        }
    )
```

- [ ] **Step 3: Write the fixtures** — `cli/tests/conftest.py`

```python
import datetime as dt
from pathlib import Path

import pytest

from fde_workflow_cli import clock
from tests.helpers import TODAY, ok


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> dt.date:
    monkeypatch.setattr(clock, "today", lambda: TODAY)
    return TODAY


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty repository as the current directory."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def fde(repo: Path) -> Path:
    """A repository with a fresh .fde/."""
    ok("init", "--preset", "none", "--name", "acme-support")
    return repo
```

- [ ] **Step 4: Write the failing model tests** — `cli/tests/test_model.py`

```python
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
```

- [ ] **Step 5: Run them to see them fail**

Run: `cd cli && poetry run pytest tests/test_model.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'fde_workflow_cli.clock'` (or
`.model`).

- [ ] **Step 6: Write the error type** — `cli/src/fde_workflow_cli/errors.py`

```python
"""The error type for problems the user can fix."""


class FdeError(Exception):
    """A problem the user can fix; the message says how."""
```

- [ ] **Step 7: Write the clock** — `cli/src/fde_workflow_cli/clock.py`

```python
"""Today's date, in one place so tests can fix it."""

import datetime as dt


def today() -> dt.date:
    return dt.date.today()
```

- [ ] **Step 8: Write the model** — `cli/src/fde_workflow_cli/model.py`

```python
"""The direction framework's data model: what the files in `.fde/` contain."""

import datetime as dt
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, StringConstraints, model_validator

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
```

- [ ] **Step 9: Run the tests and the checks**

Run: `cd cli && poetry run pytest tests/test_model.py -v && cd .. && make cli-check`
Expected: 8 passed; ruff, format and mypy clean. (`make cli-check` runs every test; the existing
ones still pass.)

- [ ] **Step 10: Commit**

```bash
git add cli/pyproject.toml cli/poetry.lock cli/src/fde_workflow_cli/{errors,clock,model}.py cli/tests/{helpers,conftest,test_model}.py
git commit -m "feat(cli): add the direction data model"
```

### Task 2: Measurement recipes

**Files:**
- Create: `cli/src/fde_workflow_cli/recipes.py`
- Test: `cli/tests/test_recipes.py`

**Interfaces:**
- Consumes: `FdeError`, `Recipe`, `RecipeType`.
- Produces: `recipe_path(fde_dir, recipe) -> Path` (raises when outside `.fde/`), `fingerprint(fde_dir, recipe) -> str | None`, `render(fde_dir, recipe, start, end) -> str`, `run_script(fde_dir, recipe, start, end) -> float`.

- [ ] **Step 1: Write the failing tests** — `cli/tests/test_recipes.py`

```python
import datetime as dt
from pathlib import Path

import pytest

from fde_workflow_cli import recipes
from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import Recipe, RecipeType
from tests.helpers import write_recipe

START, END = dt.date(2026, 9, 15), dt.date(2026, 10, 12)


def script(repo: Path, body: str) -> Recipe:
    write_recipe(repo, "measures/k.sh", f"#!/bin/sh\n{body}\n", executable=True)
    return Recipe(type=RecipeType.SCRIPT, file="measures/k.sh")


def test_fingerprint_changes_with_the_recipe(tmp_path: Path) -> None:
    recipe = Recipe(type=RecipeType.QUERY, file="measures/k.sql")
    assert recipes.fingerprint(tmp_path / ".fde", recipe) is None
    write_recipe(tmp_path, "measures/k.sql", "select 1")
    first = recipes.fingerprint(tmp_path / ".fde", recipe)
    write_recipe(tmp_path, "measures/k.sql", "select 2")
    assert first is not None
    assert recipes.fingerprint(tmp_path / ".fde", recipe) != first


def test_recipes_must_stay_inside_fde(tmp_path: Path) -> None:
    recipe = Recipe(type=RecipeType.QUERY, file="../secrets.sql")
    with pytest.raises(FdeError, match=r"inside \.fde/"):
        recipes.fingerprint(tmp_path / ".fde", recipe)


def test_render_fills_the_window(tmp_path: Path) -> None:
    write_recipe(tmp_path, "measures/k.sql", "between '{{window_start}}' and '{{window_end}}'")
    recipe = Recipe(type=RecipeType.QUERY, file="measures/k.sql")
    assert recipes.render(tmp_path / ".fde", recipe, START, END) == (
        "between '2026-09-15' and '2026-10-12'"
    )


def test_run_script_passes_the_window_and_reads_the_number(tmp_path: Path) -> None:
    recipe = script(
        tmp_path, 'test "$FDE_WINDOW_START/$FDE_WINDOW_END" = 2026-09-15/2026-10-12 && echo 42.5'
    )
    assert recipes.run_script(tmp_path / ".fde", recipe, START, END) == 42.5


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("echo boom >&2; exit 3", "exit code 3"),
        ("echo forty-two", "one number"),
        ("echo nan", "finite"),
    ],
)
def test_run_script_failures_record_nothing(tmp_path: Path, body: str, message: str) -> None:
    with pytest.raises(FdeError, match=message):
        recipes.run_script(tmp_path / ".fde", script(tmp_path, body), START, END)


def test_run_script_requires_an_executable(tmp_path: Path) -> None:
    write_recipe(tmp_path, "measures/k.sh", "#!/bin/sh\necho 1\n")
    recipe = Recipe(type=RecipeType.SCRIPT, file="measures/k.sh")
    with pytest.raises(FdeError, match="chmod"):
        recipes.run_script(tmp_path / ".fde", recipe, START, END)
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd cli && poetry run pytest tests/test_recipes.py -v`
Expected: `ImportError: cannot import name 'recipes'`.

- [ ] **Step 3: Write the recipes module** — `cli/src/fde_workflow_cli/recipes.py`

```python
"""Measurement recipes: where they live, their fingerprint, and running script recipes."""

import datetime as dt
import hashlib
import math
import os
import subprocess
from pathlib import Path

from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import Recipe

SCRIPT_TIMEOUT_SECONDS = 600


def recipe_path(fde_dir: Path, recipe: Recipe) -> Path:
    """Return the recipe's file, which must stay inside `.fde/`."""
    path = (fde_dir / recipe.file).resolve()
    if not path.is_relative_to(fde_dir.resolve()):
        raise FdeError(f"Recipe {recipe.file!r} must be inside .fde/ (e.g. measures/<kpi>.sql).")
    return path


def fingerprint(fde_dir: Path, recipe: Recipe) -> str | None:
    """SHA-256 of the recipe file, or None when the file does not exist."""
    path = recipe_path(fde_dir, recipe)
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(fde_dir: Path, recipe: Recipe, start: dt.date, end: dt.date) -> str:
    """The recipe's text with its window placeholders filled in."""
    text = recipe_path(fde_dir, recipe).read_text(encoding="utf-8")
    return text.replace("{{window_start}}", start.isoformat()).replace(
        "{{window_end}}", end.isoformat()
    )


def run_script(fde_dir: Path, recipe: Recipe, start: dt.date, end: dt.date) -> float:
    """Run a script recipe from the repository root and return the number it prints."""
    path = recipe_path(fde_dir, recipe)
    if not os.access(path, os.X_OK):
        raise FdeError(f"{path} is not executable: run `chmod +x {path}`.")
    env = {**os.environ, "FDE_WINDOW_START": start.isoformat(), "FDE_WINDOW_END": end.isoformat()}
    try:
        result = subprocess.run(  # noqa: S603 - the project's own recipe, run only with --run
            [str(path)],
            cwd=fde_dir.parent,
            env=env,
            capture_output=True,
            text=True,
            timeout=SCRIPT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise FdeError(
            f"Recipe {recipe.file} did not finish in {SCRIPT_TIMEOUT_SECONDS} s."
        ) from error
    if result.returncode != 0:
        raise FdeError(
            f"Recipe {recipe.file} failed with exit code {result.returncode}:\n"
            f"{result.stderr.strip()}"
        )
    output = result.stdout.strip()
    try:
        value = float(output)
    except ValueError as error:
        raise FdeError(
            f"Recipe {recipe.file} must print one number; it printed {output!r}."
        ) from error
    if not math.isfinite(value):
        raise FdeError(f"Recipe {recipe.file} must print a finite number; it printed {output!r}.")
    return value
```

- [ ] **Step 4: Run the tests and the checks**

Run: `cd cli && poetry run pytest tests/test_recipes.py -v && cd .. && make cli-check`
Expected: all recipe tests pass (8); checks clean.

- [ ] **Step 5: Commit**

```bash
git add cli/src/fde_workflow_cli/recipes.py cli/tests/test_recipes.py
git commit -m "feat(cli): add measurement recipes"
```

### Task 3: Framework rules

**Files:**
- Create: `cli/src/fde_workflow_cli/rules.py`
- Test: `cli/tests/test_rules.py`

**Interfaces:**
- Consumes: `recipes.fingerprint`, model types.
- Produces: `Issue(level: 'error' | 'warning', rule: str, message: str)`; `check(direction, measurements, fde_dir) -> list[Issue]` (errors first); `latest_baseline(measurements, kpi_id) -> Measurement | None`; `has_evidence(path, measurements) -> bool`. Rule codes: N1, K2, M1, K3, K4, P1, P2, C1, S1, S3.

- [ ] **Step 1: Write the failing tests** — `cli/tests/test_rules.py`

```python
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
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd cli && poetry run pytest tests/test_rules.py -v`
Expected: `ImportError: cannot import name 'rules'`.

- [ ] **Step 3: Write the rules** — `cli/src/fde_workflow_cli/rules.py`

```python
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
    """P2: a non-baseline measurement of a targeted KPI taken after the path became active."""
    activated = path.activated
    if activated is None:
        return False
    return any(
        m.kpi in path.expects and m.baseline is None and m.taken > activated for m in measurements
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
                f"{', '.join(path.expects)} taken after it became active.",
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
        and not any(m.kpi == primary and m.taken >= stage.entered for m in measurements)
    ):
        yield Issue(
            "warning",
            "S3",
            f"Primary KPI {primary} has no measurement since entering {stage.current} "
            f"on {stage.entered}.",
        )
```

- [ ] **Step 4: Run the tests and the checks**

Run: `cd cli && poetry run pytest tests/test_rules.py -v && cd .. && make cli-check`
Expected: all rule tests pass (13); checks clean.

- [ ] **Step 5: Commit**

```bash
git add cli/src/fde_workflow_cli/rules.py cli/tests/test_rules.py
git commit -m "feat(cli): check the direction framework rules"
```

### Task 4: Store: read and write `.fde/`

**Files:**
- Create: `cli/src/fde_workflow_cli/store.py`
- Test: `cli/tests/test_store.py`

**Interfaces:**
- Consumes: `rules.check`, model types, `FdeError`.
- Produces: constants `FDE_DIR`, `DIRECTION_FILE`, `MEASUREMENTS_FILE`, `DECISIONS_FILE`; `locate(start) -> Path`; `describe_validation_error(source, error) -> str`; `Store(root)` with `.root`, `.dir`, `.direction_file`, `exists()`, `create(direction)`, `load() -> Direction`, `save(direction)` (validates model and rules, atomic write, raises `FdeError` and leaves the file unchanged on errors), `measurements()`, `decisions()`, `append_measurement(m)`, `append_decision(d)`.

- [ ] **Step 1: Write the failing tests** — `cli/tests/test_store.py`

```python
import datetime as dt
from pathlib import Path

import pytest

from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import Decision, DecisionType, StageName, StageState
from fde_workflow_cli.store import Store, locate
from tests.helpers import sample_direction, write_recipe


def created(repo: Path) -> Store:
    store = Store(repo)
    write_recipe(repo, "measures/resolution-time.sql")
    store.create(sample_direction())
    return store


def test_create_writes_the_layout_and_load_reads_it_back(tmp_path: Path) -> None:
    store = created(tmp_path)
    for name in ("measures", "discovery", "reports"):
        assert (tmp_path / ".fde" / name).is_dir()
    assert (tmp_path / ".fde" / "measurements.jsonl").read_text() == ""
    assert store.load() == sample_direction()


def test_create_refuses_an_existing_fde(tmp_path: Path) -> None:
    store = created(tmp_path)
    with pytest.raises(FdeError, match="already exists"):
        store.create(sample_direction())


def test_load_without_fde_says_how_to_start(tmp_path: Path) -> None:
    with pytest.raises(FdeError, match="fde-workflow init"):
        Store(tmp_path).load()


def test_load_rejects_an_unsupported_schema_version(tmp_path: Path) -> None:
    store = created(tmp_path)
    store.direction_file.write_text("schema_version: 2\n")
    with pytest.raises(FdeError, match="Upgrade it"):
        store.load()


def test_load_reports_where_the_file_is_invalid(tmp_path: Path) -> None:
    store = created(tmp_path)
    text = store.direction_file.read_text().replace("kind: primary", "kind: main")
    store.direction_file.write_text(text)
    with pytest.raises(FdeError, match=r"kpis\.0\.kind"):
        store.load()


def test_save_refuses_a_change_that_breaks_a_rule_and_keeps_the_file(tmp_path: Path) -> None:
    store = created(tmp_path)
    before = store.direction_file.read_text()
    direction = store.load()
    direction.paths[0].expects = {"unknown-kpi": 1}
    with pytest.raises(FdeError, match=r"\[P1\]"):
        store.save(direction)
    assert store.direction_file.read_text() == before


def test_save_refuses_an_invalid_model(tmp_path: Path) -> None:
    store = created(tmp_path)
    direction = store.load()
    direction.stage = StageState.model_construct(
        current=StageName.CLOSED, entered=dt.date(2026, 1, 1)
    )
    with pytest.raises(FdeError, match="outcome"):
        store.save(direction)


def test_logs_are_append_only_jsonl(tmp_path: Path) -> None:
    store = created(tmp_path)
    decision = Decision(
        date=dt.date(2026, 10, 12), type=DecisionType.OTHER, summary="s", reason="r"
    )
    store.append_decision(decision)
    store.append_decision(decision)
    assert store.decisions() == [decision, decision]


def test_a_broken_log_line_is_reported_with_its_number(tmp_path: Path) -> None:
    store = created(tmp_path)
    (tmp_path / ".fde" / "decisions.jsonl").write_text('{"date": "2026-10-12"}\n')
    with pytest.raises(FdeError, match=r"decisions\.jsonl:1"):
        store.decisions()


def test_locate_finds_fde_in_a_parent_directory(tmp_path: Path) -> None:
    created(tmp_path)
    nested = tmp_path / "src" / "app"
    nested.mkdir(parents=True)
    assert locate(nested) == tmp_path.resolve()
    assert locate(tmp_path.parent) == tmp_path.parent.resolve()
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd cli && poetry run pytest tests/test_store.py -v`
Expected: `ModuleNotFoundError: No module named 'fde_workflow_cli.store'`.

- [ ] **Step 3: Write the store** — `cli/src/fde_workflow_cli/store.py`

```python
"""Read and write `.fde/`. direction.yaml is validated, rules included, before every write."""

import os
import tempfile
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from fde_workflow_cli import rules
from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import SCHEMA_VERSION, Decision, Direction, Measurement

FDE_DIR = ".fde"
DIRECTION_FILE = "direction.yaml"
MEASUREMENTS_FILE = "measurements.jsonl"
DECISIONS_FILE = "decisions.jsonl"
SUBDIRECTORIES = ("measures", "discovery", "reports")


def locate(start: Path) -> Path:
    """The closest directory from `start` upwards that contains `.fde/`, else `start`."""
    start = start.resolve()
    for directory in (start, *start.parents):
        if (directory / FDE_DIR / DIRECTION_FILE).is_file():
            return directory
    return start


def describe_validation_error(source: str, error: ValidationError) -> str:
    lines = [f"{source} is not valid:"]
    for item in error.errors():
        where = ".".join(str(part) for part in item["loc"]) or "(root)"
        lines.append(f"  {where}: {item['msg']}")
    return "\n".join(lines)


class Store:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.dir = root / FDE_DIR
        self.direction_file = self.dir / DIRECTION_FILE

    def exists(self) -> bool:
        return self.direction_file.is_file()

    def create(self, direction: Direction) -> None:
        if self.exists():
            raise FdeError(f"{self.dir} already exists.")
        for name in SUBDIRECTORIES:
            (self.dir / name).mkdir(parents=True, exist_ok=True)
        for name in (MEASUREMENTS_FILE, DECISIONS_FILE):
            (self.dir / name).touch()
        self.save(direction)

    def load(self) -> Direction:
        if not self.exists():
            raise FdeError(
                f"No .fde/ in {self.root}: run `fde-workflow init` (or the adopt skill) first."
            )
        try:
            data = yaml.safe_load(self.direction_file.read_text(encoding="utf-8"))
        except yaml.YAMLError as error:
            raise FdeError(f"{self.direction_file} is not valid YAML: {error}") from error
        if not isinstance(data, dict):
            raise FdeError(f"{self.direction_file} must contain a YAML mapping.")
        version = data.get("schema_version")
        if version != SCHEMA_VERSION:
            raise FdeError(
                f"{self.direction_file} has schema_version {version!r}; this fde-workflow "
                f"supports {SCHEMA_VERSION}. Upgrade it: uv tool upgrade fde-workflow-cli."
            )
        try:
            return Direction.model_validate(data)
        except ValidationError as error:
            raise FdeError(describe_validation_error(str(self.direction_file), error)) from error

    def save(self, direction: Direction) -> None:
        """Write direction.yaml if it is valid and breaks no rule; otherwise change nothing."""
        data = direction.model_dump(mode="json")
        try:
            checked = Direction.model_validate(data)
        except ValidationError as error:
            raise FdeError(describe_validation_error("The change", error)) from error
        errors = [
            issue
            for issue in rules.check(checked, self.measurements(), self.dir)
            if issue.level == "error"
        ]
        if errors:
            listed = "\n".join(f"  [{issue.rule}] {issue.message}" for issue in errors)
            raise FdeError(f"Not saved: the change breaks the framework's rules:\n{listed}")
        text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.dir, suffix=".tmp", delete=False
        ) as handle:
            handle.write(text)
        os.replace(handle.name, self.direction_file)

    def measurements(self) -> list[Measurement]:
        return _read_jsonl(self.dir / MEASUREMENTS_FILE, Measurement)

    def decisions(self) -> list[Decision]:
        return _read_jsonl(self.dir / DECISIONS_FILE, Decision)

    def append_measurement(self, measurement: Measurement) -> None:
        _append_jsonl(self.dir / MEASUREMENTS_FILE, measurement)

    def append_decision(self, decision: Decision) -> None:
        _append_jsonl(self.dir / DECISIONS_FILE, decision)


def _read_jsonl[M: BaseModel](path: Path, model: type[M]) -> list[M]:
    if not path.is_file():
        return []
    records = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(model.model_validate_json(line))
        except ValidationError as error:
            raise FdeError(describe_validation_error(f"{path}:{number}", error)) from error
    return records


def _append_jsonl(path: Path, record: BaseModel) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")
```

- [ ] **Step 4: Run the tests and the checks**

Run: `cd cli && poetry run pytest tests/test_store.py -v && cd .. && make cli-check`
Expected: all store tests pass (10); checks clean.

- [ ] **Step 5: Commit**

```bash
git add cli/src/fde_workflow_cli/store.py cli/tests/test_store.py
git commit -m "feat(cli): read and write the .fde directory"
```

### Task 5: Detect methodology and artifacts

**Files:**
- Create: `cli/src/fde_workflow_cli/detect.py`
- Test: `cli/tests/test_detect.py`

**Interfaces:**
- Consumes: `Direction`.
- Produces: `Preset` (`auto`, `superpowers`, `spec-kit`, `none`), `PRESET_GLOBS`, `detect_methodology(root) -> Preset`, `globs_for(preset, root) -> list[str]`, `artifact_files(root, globs) -> list[str]`, `first_commit_date(root, relative) -> str | None`, `deployment_signals(root) -> list[str]`, `linked_to(direction, relative) -> str | None`, `report(root, direction) -> dict` (the JSON of `fde-workflow detect`).

- [ ] **Step 1: Write the failing tests** — `cli/tests/test_detect.py`

```python
import subprocess
from pathlib import Path

from fde_workflow_cli import detect
from fde_workflow_cli.detect import Preset
from tests.helpers import make_files


def git(repo: Path, *args: str) -> None:
    subprocess.run(  # noqa: S603
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", *args],  # noqa: S607
        cwd=repo,
        check=True,
        capture_output=True,
    )


def test_methodology_detection(tmp_path: Path) -> None:
    assert detect.detect_methodology(tmp_path) is Preset.NONE
    (tmp_path / "specs").mkdir()
    assert detect.detect_methodology(tmp_path) is Preset.SPEC_KIT
    (tmp_path / "docs" / "superpowers").mkdir(parents=True)
    assert detect.detect_methodology(tmp_path) is Preset.SUPERPOWERS


def test_globs_for_auto_uses_the_detected_methodology(tmp_path: Path) -> None:
    (tmp_path / "docs" / "superpowers").mkdir(parents=True)
    assert detect.globs_for(Preset.AUTO, tmp_path) == detect.PRESET_GLOBS[Preset.SUPERPOWERS]
    assert detect.globs_for(Preset.NONE, tmp_path) == []


def test_artifact_files_lists_matching_files_only(tmp_path: Path) -> None:
    make_files(
        tmp_path, "docs/superpowers/specs/a.md", "docs/superpowers/plans/sub/b.md", "src/x.py"
    )
    globs = detect.PRESET_GLOBS[Preset.SUPERPOWERS]
    assert detect.artifact_files(tmp_path, globs) == [
        "docs/superpowers/plans/sub/b.md",
        "docs/superpowers/specs/a.md",
    ]


def test_first_commit_date_comes_from_git(tmp_path: Path) -> None:
    make_files(tmp_path, "specs/001/spec.md")
    assert detect.first_commit_date(tmp_path, "specs/001/spec.md") is None
    git(tmp_path, "init", "-q")
    git(tmp_path, "add", ".")
    git(tmp_path, "commit", "-q", "-m", "add", "--date", "2026-09-01T10:00:00")
    assert detect.first_commit_date(tmp_path, "specs/001/spec.md") is not None


def test_deployment_signals(tmp_path: Path) -> None:
    make_files(
        tmp_path, "Dockerfile", ".github/workflows/deploy-prod.yml", ".github/workflows/ci.yml"
    )
    assert detect.deployment_signals(tmp_path) == [
        "Dockerfile",
        ".github/workflows/deploy-prod.yml",
    ]
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd cli && poetry run pytest tests/test_detect.py -v`
Expected: `ImportError: cannot import name 'detect'`.

- [ ] **Step 3: Write the detection module** — `cli/src/fde_workflow_cli/detect.py`

```python
"""Find the execution methodology and its artifacts in a repository. Read-only."""

import subprocess
from enum import StrEnum
from pathlib import Path

from fde_workflow_cli.model import Direction


class Preset(StrEnum):
    AUTO = "auto"
    SUPERPOWERS = "superpowers"
    SPEC_KIT = "spec-kit"
    NONE = "none"


PRESET_GLOBS: dict[Preset, list[str]] = {
    Preset.SUPERPOWERS: ["docs/superpowers/specs/**", "docs/superpowers/plans/**"],
    Preset.SPEC_KIT: ["specs/**"],
    Preset.NONE: [],
}
DEPLOYMENT_MARKERS = (
    "Dockerfile",
    "docker-compose.yml",
    "compose.yaml",
    "Procfile",
    "fly.toml",
    "vercel.json",
    "netlify.toml",
    "render.yaml",
    "app.yaml",
    "serverless.yml",
    "k8s",
    "helm",
    "terraform",
)
DEPLOYMENT_WORKFLOW_WORDS = ("deploy", "release", "publish")
READMES = ("README.md", "README.rst", "README.txt", "README")


def detect_methodology(root: Path) -> Preset:
    if (root / "docs" / "superpowers").is_dir():
        return Preset.SUPERPOWERS
    if (root / ".specify").is_dir() or (root / "specs").is_dir():
        return Preset.SPEC_KIT
    return Preset.NONE


def globs_for(preset: Preset, root: Path) -> list[str]:
    resolved = detect_methodology(root) if preset is Preset.AUTO else preset
    return list(PRESET_GLOBS[resolved])


def artifact_files(root: Path, globs: list[str]) -> list[str]:
    """Files under `root` matching any glob, as sorted POSIX paths relative to `root`."""
    found: set[str] = set()
    for pattern in globs:
        for path in root.glob(pattern):
            if path.is_file():
                found.add(path.relative_to(root).as_posix())
    return sorted(found)


def first_commit_date(root: Path, relative: str) -> str | None:
    """Date (YYYY-MM-DD) of the commit that added the file, or None outside git history."""
    try:
        result = subprocess.run(  # noqa: S603 - fixed read-only git query
            ["git", "log", "--diff-filter=A", "--format=%cs", "--", relative],  # noqa: S607
            cwd=root,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    dates = result.stdout.split()
    return dates[-1] if result.returncode == 0 and dates else None


def deployment_signals(root: Path) -> list[str]:
    signals = [name for name in DEPLOYMENT_MARKERS if (root / name).exists()]
    workflows = root / ".github" / "workflows"
    if workflows.is_dir():
        signals += sorted(
            f".github/workflows/{path.name}"
            for path in workflows.iterdir()
            if any(word in path.name.lower() for word in DEPLOYMENT_WORKFLOW_WORDS)
        )
    return signals


def linked_to(direction: Direction | None, relative: str) -> str | None:
    """The path id that links the artifact, "pre-framework", or None."""
    if direction is None:
        return None
    for path in direction.paths:
        if relative in path.links:
            return path.id
    if relative in direction.artifacts.pre_framework:
        return "pre-framework"
    return None


def report(root: Path, direction: Direction | None) -> dict[str, object]:
    methodology = detect_methodology(root)
    globs = direction.artifacts.globs if direction else PRESET_GLOBS[methodology]
    return {
        "root": str(root),
        "fde_initialised": direction is not None,
        "methodology": methodology.value,
        "globs": globs,
        "readme": next((name for name in READMES if (root / name).is_file()), None),
        "deployment_signals": deployment_signals(root),
        "artifacts": [
            {
                "path": relative,
                "first_commit": first_commit_date(root, relative),
                "linked_to": linked_to(direction, relative),
            }
            for relative in artifact_files(root, globs)
        ],
    }
```

- [ ] **Step 4: Run the tests and the checks**

Run: `cd cli && poetry run pytest tests/test_detect.py -v && cd .. && make cli-check`
Expected: all detection tests pass (5); checks clean.

- [ ] **Step 5: Commit**

```bash
git add cli/src/fde_workflow_cli/detect.py cli/tests/test_detect.py
git commit -m "feat(cli): detect execution methodology and artifacts"
```

### Task 6: Summaries for people and for Claude

**Files:**
- Create: `cli/src/fde_workflow_cli/summary.py`
- Test: `cli/tests/test_summary.py`

**Interfaces:**
- Consumes: `rules.Issue`, `rules.latest_baseline`, model types.
- Produces: `number(value) -> str`, `kpi_line(kpi, measurements) -> str`, `render(direction, measurements, issues, brief=False) -> str`, `CONTEXT_HEADER`, `context(direction, measurements, issues, brief=False) -> str`.

- [ ] **Step 1: Write the failing tests** — `cli/tests/test_summary.py`

```python
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
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd cli && poetry run pytest tests/test_summary.py -v`
Expected: `ImportError: cannot import name 'summary'`.

- [ ] **Step 3: Write the summaries** — `cli/src/fde_workflow_cli/summary.py`

```python
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
```

- [ ] **Step 4: Run the tests and the checks**

Run: `cd cli && poetry run pytest tests/test_summary.py -v && cd .. && make cli-check`
Expected: all summary tests pass (4); checks clean.

- [ ] **Step 5: Commit**

```bash
git add cli/src/fde_workflow_cli/summary.py cli/tests/test_summary.py
git commit -m "feat(cli): summarise the direction for people and claude"
```

### Task 7: Project commands: init, detect, validate, status, context

**Files:**
- Create: `cli/src/fde_workflow_cli/commands/__init__.py`, `cli/src/fde_workflow_cli/commands/common.py`, `cli/src/fde_workflow_cli/commands/project.py`
- Modify: `cli/src/fde_workflow_cli/main.py`
- Test: `cli/tests/test_cmd_project.py`

**Interfaces:**
- Consumes: `Store`, `locate`, `rules`, `summary`, `detect`, `clock`.
- Produces (used by every command module): `RootOption`; `open_store(root) -> Store`; `user_errors()` context manager (FdeError/ValidationError → `Error: ...` on stderr, exit 1); `require(value, option, why) -> str`; `parse_date(text, option) -> dt.date`; `find_kpi(direction, id)`; `find_path(direction, id)`; `record(store, decision_type, summary, reason, approved_by='', refs=None)`. Commands: `fde-workflow init [--root] [--name] [--preset] [--glob ...]`, `detect`, `validate`, `status`, `context [--brief]`.

- [ ] **Step 1: Write the failing tests** — `cli/tests/test_cmd_project.py`

```python
import json
from pathlib import Path

import pytest
import yaml

from tests.helpers import fails, make_files, ok


def test_init_creates_a_discovery_direction(repo: Path) -> None:
    (repo / "docs" / "superpowers").mkdir(parents=True)
    result = ok("init")
    assert "artifact globs: docs/superpowers/specs/**, docs/superpowers/plans/**" in result.output
    data = yaml.safe_load((repo / ".fde" / "direction.yaml").read_text())
    assert data["schema_version"] == 1
    assert data["project"]["name"] == repo.name
    assert data["stage"] == {
        "current": "discovery",
        "entered": "2026-10-12",
        "outcome": None,
        "on_hold": False,
        "confirmed": True,
        "gate_criteria": [],
    }


def test_init_with_custom_globs(repo: Path) -> None:
    ok("init", "--glob", "design/**", "--glob", "rfcs/*.md")
    data = yaml.safe_load((repo / ".fde" / "direction.yaml").read_text())
    assert data["artifacts"]["globs"] == ["design/**", "rfcs/*.md"]


def test_init_twice_fails(fde: Path) -> None:
    assert "already exists" in fails("init").output


def test_commands_without_fde_explain_how_to_start(repo: Path) -> None:
    for command in ("status", "validate", "context"):
        assert "fde-workflow init" in fails(command).output


def test_commands_find_fde_from_a_subdirectory(fde: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    nested = fde / "src"
    nested.mkdir()
    monkeypatch.chdir(nested)
    assert "Project: acme-support" in ok("status").output


def test_validate_reports_warnings_and_exits_zero(fde: Path) -> None:
    result = ok("validate")
    assert "! [N1] No North Star yet" in result.output
    assert "! [S1] Stage discovery has no gate criteria" in result.output
    assert result.output.endswith("Valid with 2 warning(s).\n")


def test_detect_command_reports_a_repository_without_fde(repo: Path) -> None:
    make_files(repo, "README.md", "docs/superpowers/specs/2026-09-01-triage-design.md")
    report = json.loads(ok("detect").stdout)
    assert report["fde_initialised"] is False
    assert report["methodology"] == "superpowers"
    assert report["readme"] == "README.md"
    assert report["artifacts"] == [
        {
            "path": "docs/superpowers/specs/2026-09-01-triage-design.md",
            "first_commit": None,
            "linked_to": None,
        }
    ]


def test_status_and_context(fde: Path) -> None:
    assert "Project: acme-support" in ok("status").output
    context = ok("context", "--brief").output
    assert context.startswith("FDE direction of this repository")
    assert "Gate criteria: 0" in context
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd cli && poetry run pytest tests/test_cmd_project.py -v`
Expected: failures with `No such command 'init'` (exit code 2).

- [ ] **Step 3: Create the commands package** — `cli/src/fde_workflow_cli/commands/__init__.py`

```python
"""The CLI's command groups."""
```

- [ ] **Step 4: Write the shared command helpers** — `cli/src/fde_workflow_cli/commands/common.py`

```python
"""Helpers shared by the commands."""

import datetime as dt
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated

import typer
from pydantic import ValidationError

from fde_workflow_cli import clock
from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import Decision, DecisionType, Direction, DirectionPath, Kpi
from fde_workflow_cli.store import Store, describe_validation_error, locate

RootOption = Annotated[
    Path | None,
    typer.Option(
        "--root",
        help="Repository with .fde/ (default: the closest one from the current directory).",
    ),
]


def open_store(root: Path | None) -> Store:
    return Store(root.resolve() if root else locate(Path.cwd()))


@contextmanager
def user_errors() -> Iterator[None]:
    """Turn problems the user can fix into a one-line error and exit code 1."""
    try:
        yield
    except FdeError as error:
        typer.echo(f"Error: {error}", err=True)
        raise typer.Exit(1) from error
    except ValidationError as error:
        typer.echo(f"Error: {describe_validation_error('The input', error)}", err=True)
        raise typer.Exit(1) from error


def require(value: str | None, option: str, why: str) -> str:
    if not value:
        raise FdeError(f"{option} is required {why}.")
    return value


def parse_date(text: str, option: str) -> dt.date:
    try:
        return dt.date.fromisoformat(text)
    except ValueError as error:
        raise FdeError(f"{option} must be a date like 2026-10-12, not {text!r}.") from error


def find_kpi(direction: Direction, kpi_id: str) -> Kpi:
    kpi = direction.kpi(kpi_id)
    if kpi is None:
        raise FdeError(f"There is no KPI {kpi_id}.")
    return kpi


def find_path(direction: Direction, path_id: str) -> DirectionPath:
    path = direction.path(path_id)
    if path is None:
        raise FdeError(f"There is no path {path_id}.")
    return path


def record(
    store: Store,
    decision_type: DecisionType,
    summary: str,
    reason: str,
    approved_by: str = "",
    refs: list[str] | None = None,
) -> None:
    store.append_decision(
        Decision(
            date=clock.today(),
            type=decision_type,
            summary=summary,
            reason=reason,
            approved_by=approved_by,
            refs=refs or [],
        )
    )
```

- [ ] **Step 5: Write the project commands** — `cli/src/fde_workflow_cli/commands/project.py`

```python
"""Commands on the whole `.fde/`: init, detect, validate, status and context."""

import json
from pathlib import Path
from typing import Annotated

import typer

from fde_workflow_cli import clock, detect, rules, summary
from fde_workflow_cli.commands.common import RootOption, open_store, user_errors
from fde_workflow_cli.model import Artifacts, Direction, Project, StageState
from fde_workflow_cli.store import Store


def init(
    root: RootOption = None,
    name: Annotated[
        str | None, typer.Option(help="Project name (default: the directory's name).")
    ] = None,
    preset: Annotated[
        detect.Preset, typer.Option(help="Where execution artifacts live (auto detects it).")
    ] = detect.Preset.AUTO,
    glob: Annotated[
        list[str] | None,
        typer.Option(
            "--glob", help="Where execution artifacts live; repeat it; overrides --preset."
        ),
    ] = None,
) -> None:
    """Create .fde/ with an empty direction in stage discovery."""
    with user_errors():
        directory = (root or Path.cwd()).resolve()
        store = Store(directory)
        globs = glob or detect.globs_for(preset, directory)
        store.create(
            Direction(
                project=Project(name=name or directory.name),
                stage=StageState(entered=clock.today()),
                artifacts=Artifacts(globs=globs),
            )
        )
    typer.echo(
        f"Created {store.dir} (stage discovery; artifact globs: {', '.join(globs) or 'none'})."
    )


def detect_command(root: RootOption = None) -> None:
    """Print the repository's methodology, artifacts and deployment signals as JSON."""
    with user_errors():
        store = open_store(root)
        direction = store.load() if store.exists() else None
        typer.echo(json.dumps(detect.report(store.root, direction), indent=2))


def validate(root: RootOption = None) -> None:
    """Check .fde/ against the framework's rules; exit 1 when a rule is broken."""
    with user_errors():
        store = open_store(root)
        issues = rules.check(store.load(), store.measurements(), store.dir)
    for issue in issues:
        typer.echo(f"{'✗' if issue.level == 'error' else '!'} [{issue.rule}] {issue.message}")
    errors = sum(issue.level == "error" for issue in issues)
    warnings = len(issues) - errors
    if errors:
        typer.echo(f"Invalid: {errors} error(s), {warnings} warning(s).")
        raise typer.Exit(1)
    typer.echo(f"Valid with {warnings} warning(s)." if warnings else "Valid.")


def status(root: RootOption = None) -> None:
    """Summarise the direction for people."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        measurements = store.measurements()
        issues = rules.check(direction, measurements, store.dir)
    typer.echo(summary.render(direction, measurements, issues))


def context(
    root: RootOption = None,
    brief: Annotated[bool, typer.Option("--brief", help="Only what every session needs.")] = False,
) -> None:
    """Summarise the direction for Claude."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        measurements = store.measurements()
        issues = rules.check(direction, measurements, store.dir)
    typer.echo(summary.context(direction, measurements, issues, brief=brief))
```

- [ ] **Step 6: Register the commands in `cli/src/fde_workflow_cli/main.py`**

Add the import after `from fde_workflow_cli import doctor as checks`:

```python
from fde_workflow_cli.commands import project
```

and append at the end of the file:

```python


app.command()(project.init)
app.command("detect")(project.detect_command)
app.command()(project.validate)
app.command()(project.status)
app.command()(project.context)
```

- [ ] **Step 7: Run the tests and the checks**

Run: `cd cli && poetry run pytest tests/test_cmd_project.py -v && cd .. && make cli-check`
Expected: all project command tests pass (8); checks clean.

- [ ] **Step 8: Commit**

```bash
git add cli/src/fde_workflow_cli/commands cli/src/fde_workflow_cli/main.py cli/tests/test_cmd_project.py
git commit -m "feat(cli): add init, detect, validate, status and context commands"
```

### Task 8: KPI commands

**Files:**
- Create: `cli/src/fde_workflow_cli/commands/kpi.py`
- Modify: `cli/src/fde_workflow_cli/main.py`
- Test: `cli/tests/test_cmd_kpi.py`

**Interfaces:**
- Consumes: Task 7 helpers, `recipes`, `rules.latest_baseline`, `summary.number`.
- Produces: `fde-workflow kpi add ID --name --kind --definition --source --direction --target --recipe-type --recipe-file [--unit] [--window]`, `kpi update ID [...] [--reason --approved-by when --target changes]` (records `target-change`), `kpi measure ID [--baseline historical|late] [--window-end] [--value --source] [--factors] [--run]`.

- [ ] **Step 1: Write the failing tests** — `cli/tests/test_cmd_kpi.py`

```python
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
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd cli && poetry run pytest tests/test_cmd_kpi.py -v`
Expected: failures with `No such command 'kpi'`.

- [ ] **Step 3: Write the KPI commands** — `cli/src/fde_workflow_cli/commands/kpi.py`

```python
"""`fde-workflow kpi`: define KPIs and record their measurements."""

from typing import Annotated

import typer

from fde_workflow_cli import clock, recipes, rules
from fde_workflow_cli.commands.common import (
    RootOption,
    find_kpi,
    open_store,
    parse_date,
    record,
    require,
    user_errors,
)
from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import (
    BaselineType,
    Better,
    DecisionType,
    Kpi,
    KpiKind,
    Measurement,
    Recipe,
    RecipeType,
)
from fde_workflow_cli.summary import number

app = typer.Typer(help="Define KPIs and record their measurements.", no_args_is_help=True)


@app.command()
def add(
    kpi_id: Annotated[str, typer.Argument(help="Kebab-case id, e.g. resolution-time.")],
    name: Annotated[str, typer.Option(help="Human-readable name.")],
    kind: Annotated[KpiKind, typer.Option(help="primary, secondary or guardrail.")],
    definition: Annotated[str, typer.Option(help="What it measures and its formula.")],
    source: Annotated[str, typer.Option(help="Where the data comes from.")],
    better: Annotated[Better, typer.Option("--direction", help="Which way is better.")],
    target: Annotated[
        float, typer.Option(help="Numeric target; for a guardrail, the worst acceptable value.")
    ],
    recipe_type: Annotated[RecipeType, typer.Option("--recipe-type", help="How to measure it.")],
    recipe_file: Annotated[
        str, typer.Option("--recipe-file", help="Inside .fde/, e.g. measures/resolution-time.sql.")
    ],
    unit: Annotated[str, typer.Option(help="Unit, e.g. min or %.")] = "",
    window: Annotated[str, typer.Option(help="Measurement window in days, e.g. 28d.")] = "28d",
    root: RootOption = None,
) -> None:
    """Define a KPI; its recipe file must already exist."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        if direction.kpi(kpi_id):
            raise FdeError(f"KPI {kpi_id} already exists: use `fde-workflow kpi update`.")
        direction.kpis.append(
            Kpi(
                id=kpi_id,
                name=name,
                kind=kind,
                definition=definition,
                source=source,
                unit=unit,
                direction=better,
                target=target,
                window=window,
                recipe=Recipe(type=recipe_type, file=recipe_file),
            )
        )
        store.save(direction)
    typer.echo(f"Added KPI {kpi_id}.")


@app.command()
def update(
    kpi_id: Annotated[str, typer.Argument()],
    name: Annotated[str | None, typer.Option()] = None,
    kind: Annotated[KpiKind | None, typer.Option()] = None,
    definition: Annotated[str | None, typer.Option()] = None,
    source: Annotated[str | None, typer.Option()] = None,
    better: Annotated[Better | None, typer.Option("--direction")] = None,
    target: Annotated[float | None, typer.Option()] = None,
    unit: Annotated[str | None, typer.Option()] = None,
    window: Annotated[str | None, typer.Option()] = None,
    recipe_type: Annotated[RecipeType | None, typer.Option("--recipe-type")] = None,
    recipe_file: Annotated[str | None, typer.Option("--recipe-file")] = None,
    reason: Annotated[str | None, typer.Option(help="Why the target changes.")] = None,
    approved_by: Annotated[
        str | None, typer.Option("--approved-by", help="Who approves a target change.")
    ] = None,
    root: RootOption = None,
) -> None:
    """Change a KPI; changing its target records a decision."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        kpi = find_kpi(direction, kpi_id)
        fields = {
            "name": name,
            "kind": kind,
            "definition": definition,
            "source": source,
            "direction": better,
            "target": target,
            "unit": unit,
            "window": window,
        }
        changes: dict[str, object] = {k: v for k, v in fields.items() if v is not None}
        if recipe_type or recipe_file:
            changes["recipe"] = Recipe(
                type=recipe_type or kpi.recipe.type, file=recipe_file or kpi.recipe.file
            )
        target_changed = target is not None and target != kpi.target
        if target_changed:
            reason = require(reason, "--reason", "to change a target")
            approved_by = require(approved_by, "--approved-by", "to change a target")
        direction.kpis[direction.kpis.index(kpi)] = kpi.model_copy(update=changes)
        store.save(direction)
        if target_changed and target is not None:
            record(
                store,
                DecisionType.TARGET_CHANGE,
                f"Target of {kpi_id}: {number(kpi.target)} → {number(target)}",
                reason or "",
                approved_by or "",
                [kpi_id],
            )
    typer.echo(f"Updated KPI {kpi_id}.")


@app.command()
def measure(
    kpi_id: Annotated[str, typer.Argument()],
    baseline: Annotated[
        BaselineType | None, typer.Option(help="Record it as the KPI's baseline.")
    ] = None,
    window_end: Annotated[
        str | None,
        typer.Option("--window-end", help="Last day measured, YYYY-MM-DD (default: today)."),
    ] = None,
    value: Annotated[float | None, typer.Option(help="The measured value.")] = None,
    source: Annotated[str | None, typer.Option(help="Where the value came from.")] = None,
    factors: Annotated[
        str, typer.Option(help="External factors that may have moved the value.")
    ] = "",
    run: Annotated[
        bool, typer.Option("--run", help="Run a script recipe and record its output.")
    ] = False,
    root: RootOption = None,
) -> None:
    """Record a measurement; without --value or --run, show how to take it."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        kpi = find_kpi(direction, kpi_id)
        start, end = kpi.window_ending(
            parse_date(window_end, "--window-end") if window_end else clock.today()
        )
        fingerprint = recipes.fingerprint(store.dir, kpi.recipe)
        if fingerprint is None:
            raise FdeError(f"Recipe .fde/{kpi.recipe.file} does not exist: write it first.")
        if kpi.recipe.type is RecipeType.SCRIPT:
            if value is not None:
                raise FdeError("Script recipes are run, not typed: use --run.")
            if not run:
                typer.echo(
                    f"Would run .fde/{kpi.recipe.file} with FDE_WINDOW_START={start} "
                    f"FDE_WINDOW_END={end}.\nAdd --run to execute it and record the result."
                )
                return
            value = recipes.run_script(store.dir, kpi.recipe, start, end)
            source = source or f"script .fde/{kpi.recipe.file}"
        else:
            if run:
                raise FdeError(f"Only script recipes run; {kpi.id} has a {kpi.recipe.type} recipe.")
            if value is None:
                text = recipes.render(store.dir, kpi.recipe, start, end)
                typer.echo(
                    f"{kpi.recipe.type} recipe of {kpi.id}, window {start} to {end}:\n\n{text}\n"
                    "Take the measurement, then record it with --value N --source TEXT."
                )
                return
            source = require(source, "--source", "to record a measurement")
        previous = rules.latest_baseline(store.measurements(), kpi.id)
        store.append_measurement(
            Measurement(
                kpi=kpi.id,
                taken=clock.today(),
                window_start=start,
                window_end=end,
                value=value,
                baseline=baseline,
                source=source,
                external_factors=factors,
                recipe_sha256=fingerprint,
            )
        )
    unit = f" {kpi.unit}" if kpi.unit else ""
    label = f"{baseline} baseline" if baseline else "measurement"
    typer.echo(f"Recorded {label} {kpi.id} = {number(value)}{unit} (window {start} to {end}).")
    if baseline is None and previous is None:
        typer.echo(f"! {kpi.id} has no baseline yet: this measurement is not one.")
    elif baseline is None and previous is not None and previous.recipe_sha256 != fingerprint:
        typer.echo(
            "! [K4] The recipe changed after the baseline: measure it again with --baseline."
        )
```

- [ ] **Step 4: Register the group in `cli/src/fde_workflow_cli/main.py`**

Change the commands import to:

```python
from fde_workflow_cli.commands import kpi, project
```

and append:

```python
app.add_typer(kpi.app, name="kpi")
```

- [ ] **Step 5: Run the tests and the checks**

Run: `cd cli && poetry run pytest tests/test_cmd_kpi.py -v && cd .. && make cli-check`
Expected: all KPI command tests pass (9); checks clean.

- [ ] **Step 6: Commit**

```bash
git add cli/src/fde_workflow_cli/commands/kpi.py cli/src/fde_workflow_cli/main.py cli/tests/test_cmd_kpi.py
git commit -m "feat(cli): add kpi commands"
```

### Task 9: North Star commands

**Files:**
- Create: `cli/src/fde_workflow_cli/commands/northstar.py`
- Modify: `cli/src/fde_workflow_cli/main.py`
- Test: `cli/tests/test_cmd_northstar.py`

**Interfaces:**
- Consumes: Task 7 helpers; `kpi add` (Task 8) in tests.
- Produces: `fde-workflow northstar set [--statement] [--beneficiary] [--problem] [--non-goal ...] [--primary-kpi] [--inferred] [--reason --approved-by]` (changing a confirmed North Star records `north-star-change`), `northstar confirm`.

- [ ] **Step 1: Write the failing tests** — `cli/tests/test_cmd_northstar.py`

```python
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
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd cli && poetry run pytest tests/test_cmd_northstar.py -v`
Expected: failures with `No such command 'northstar'`.

- [ ] **Step 3: Write the North Star commands** — `cli/src/fde_workflow_cli/commands/northstar.py`

```python
"""`fde-workflow northstar`: define, change and confirm the North Star."""

from typing import Annotated

import typer

from fde_workflow_cli.commands.common import RootOption, open_store, record, require, user_errors
from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import DecisionType, NorthStar

app = typer.Typer(help="Define, change and confirm the North Star.", no_args_is_help=True)


@app.command("set")
def set_(
    statement: Annotated[
        str | None, typer.Option(help="The outcome, for someone; never a solution.")
    ] = None,
    beneficiary: Annotated[str | None, typer.Option(help="Who gets the outcome.")] = None,
    problem: Annotated[str | None, typer.Option(help="The problem it solves.")] = None,
    non_goal: Annotated[
        list[str] | None,
        typer.Option("--non-goal", help="Out of scope; repeat it, the list is replaced."),
    ] = None,
    primary_kpi: Annotated[
        str | None, typer.Option("--primary-kpi", help="Id of the primary KPI.")
    ] = None,
    inferred: Annotated[
        bool, typer.Option("--inferred", help="Inferred from existing work; needs confirmation.")
    ] = False,
    reason: Annotated[str | None, typer.Option(help="Why a confirmed North Star changes.")] = None,
    approved_by: Annotated[
        str | None, typer.Option("--approved-by", help="Who approves the change (the sponsor).")
    ] = None,
    root: RootOption = None,
) -> None:
    """Create the North Star, or change it; changing a confirmed one records a decision."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        current = direction.north_star
        if current is None:
            new = NorthStar(
                statement=require(statement, "--statement", "to create the North Star"),
                beneficiary=beneficiary or "",
                problem=problem or "",
                non_goals=non_goal or [],
                primary_kpi=primary_kpi,
                confirmed=not inferred,
            )
        else:
            fields = {
                "statement": statement,
                "beneficiary": beneficiary,
                "problem": problem,
                "non_goals": non_goal,
                "primary_kpi": primary_kpi,
            }
            changes: dict[str, object] = {k: v for k, v in fields.items() if v is not None}
            if inferred:
                changes["confirmed"] = False
            new = current.model_copy(update=changes)
        is_change = current is not None and current.confirmed and new != current
        if is_change:
            reason = require(reason, "--reason", "to change a confirmed North Star")
            approved_by = require(approved_by, "--approved-by", "to change a confirmed North Star")
        direction.north_star = new
        store.save(direction)
        if is_change:
            record(
                store,
                DecisionType.NORTH_STAR_CHANGE,
                f"North Star: {new.statement}",
                reason or "",
                approved_by or "",
            )
    typer.echo("North Star changed." if is_change else "North Star saved.")


@app.command()
def confirm(root: RootOption = None) -> None:
    """Mark an inferred North Star as confirmed."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        if direction.north_star is None:
            raise FdeError("There is no North Star to confirm.")
        direction.north_star.confirmed = True
        store.save(direction)
    typer.echo("North Star confirmed.")
```

- [ ] **Step 4: Register the group in `cli/src/fde_workflow_cli/main.py`**

Change the commands import to:

```python
from fde_workflow_cli.commands import kpi, northstar, project
```

and append:

```python
app.add_typer(northstar.app, name="northstar")
```

- [ ] **Step 5: Run the tests and the checks**

Run: `cd cli && poetry run pytest tests/test_cmd_northstar.py -v && cd .. && make cli-check`
Expected: all North Star command tests pass (5); checks clean.

- [ ] **Step 6: Commit**

```bash
git add cli/src/fde_workflow_cli/commands/northstar.py cli/src/fde_workflow_cli/main.py cli/tests/test_cmd_northstar.py
git commit -m "feat(cli): add north star commands"
```

### Task 10: Path commands

**Files:**
- Create: `cli/src/fde_workflow_cli/commands/path.py`
- Modify: `cli/src/fde_workflow_cli/main.py`
- Test: `cli/tests/test_cmd_path.py`

**Interfaces:**
- Consumes: Task 7 helpers; `kpi add`/`kpi measure` in tests.
- Produces: `TRANSITIONS`, `parse_expects(items)`, `normalise_ref(root, ref)`; `fde-workflow path add ID --hypothesis --expects KPI=VALUE... [--reason] [--status] [--activated] [--maturity] [--link ...] [--inferred]`, `path update`, `path move ID STATUS --reason [--learning] [--approved-by]`, `path link PATH_ID REF...` / `path link --pre-framework REF...`, `path confirm ID [--reason]`.

- [ ] **Step 1: Write the failing tests** — `cli/tests/test_cmd_path.py`

```python
import datetime as dt
import json
from pathlib import Path

import pytest

from fde_workflow_cli import clock
from tests.helpers import add_kpi, decisions, fails, make_files, ok

OPEN = (
    "path", "add", "auto-triage",
    "--hypothesis", "If tickets are classified on arrival, resolution drops 20%",
    "--expects", "resolution-time=36",
)  # fmt: skip


def opened(fde: Path) -> None:
    add_kpi(fde)
    ok(*OPEN, "--reason", "Biggest delay is triage")


def test_add_records_a_path_open_decision(fde: Path) -> None:
    opened(fde)
    assert "auto-triage [proposed]" in ok("status").output
    [decision] = decisions(fde)
    assert decision["type"] == "path-open"
    assert decision["refs"] == ["auto-triage"]


def test_add_validates_input(fde: Path) -> None:
    add_kpi(fde)
    assert "--reason is required" in fails(*OPEN).output
    assert "KPI_ID=VALUE" in fails(*OPEN[:-1], "resolution-time", "--reason", "r").output
    assert "[P1]" in fails(*OPEN[:-1], "nope=1", "--reason", "r").output
    assert "use `path move` later" in fails(*OPEN, "--reason", "r", "--status", "validated").output


def test_inferred_paths_record_no_decision_until_confirmed(fde: Path) -> None:
    add_kpi(fde)
    ok(*OPEN, "--inferred", "--status", "active", "--activated", "2026-09-01")
    assert decisions(fde) == []
    assert "Path auto-triage was inferred" in ok("validate").output
    ok("path", "confirm", "auto-triage")
    assert str(decisions(fde)[0]["summary"]).startswith("Confirm path auto-triage")


def test_move_follows_the_life_cycle(fde: Path) -> None:
    opened(fde)
    assert (
        "allowed: active, discarded"
        in fails("path", "move", "auto-triage", "measuring", "--reason", "r").output
    )
    ok("path", "move", "auto-triage", "active", "--reason", "Started")
    assert "activated: '2026-10-12'" in (fde / ".fde" / "direction.yaml").read_text()


def test_validation_needs_evidence_after_activation(
    fde: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    opened(fde)
    ok("path", "move", "auto-triage", "active", "--reason", "Started")
    ok("path", "move", "auto-triage", "measuring", "--reason", "Built")
    result = fails("path", "move", "auto-triage", "validated", "--reason", "Looks good")
    assert "[P2]" in result.output
    monkeypatch.setattr(clock, "today", lambda: dt.date(2026, 11, 9))
    ok("kpi", "measure", "resolution-time", "--value", "35", "--source", "Zendesk")
    ok("path", "move", "auto-triage", "validated", "--reason", "35 min", "--approved-by", "Jane")
    assert decisions(fde)[-1]["type"] == "path-validate"


def test_discarding_needs_a_learning(fde: Path) -> None:
    opened(fde)
    assert (
        "--learning is required"
        in fails("path", "move", "auto-triage", "discarded", "--reason", "r").output
    )
    ok(
        "path",
        "move",
        "auto-triage",
        "discarded",
        "--reason",
        "r",
        "--learning",
        "Triage was not the bottleneck",
    )
    assert decisions(fde)[-1]["type"] == "path-discard"


def test_link_normalises_files_and_moves_them_out_of_pre_framework(fde: Path) -> None:
    opened(fde)
    spec = fde / "docs" / "superpowers" / "specs" / "a.md"
    spec.parent.mkdir(parents=True)
    spec.write_text("x")
    ok("path", "link", "--pre-framework", "docs/superpowers/specs/a.md")
    ok("path", "link", "auto-triage", str(spec), "https://github.com/acme/x/pull/1")
    ok("path", "link", "auto-triage", "docs/superpowers/specs/a.md")
    text = (fde / ".fde" / "direction.yaml").read_text()
    assert text.count("docs/superpowers/specs/a.md") == 1
    assert "pre_framework: []" in text
    assert "https://github.com/acme/x/pull/1" in text


def test_link_needs_a_path_and_a_ref(fde: Path) -> None:
    opened(fde)
    assert "Usage:" in fails("path", "link", "auto-triage").output
    assert "There is no path nope" in fails("path", "link", "nope", "x.md").output


def test_detect_command_reports_links_once_initialised(repo: Path) -> None:
    make_files(repo, "docs/superpowers/specs/a.md", "docs/superpowers/specs/b.md")
    ok("init")
    ok("path", "link", "--pre-framework", "docs/superpowers/specs/a.md")
    report = json.loads(ok("detect").stdout)
    assert [a["linked_to"] for a in report["artifacts"]] == ["pre-framework", None]
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd cli && poetry run pytest tests/test_cmd_path.py -v`
Expected: failures with `No such command 'path'`.

- [ ] **Step 3: Write the path commands** — `cli/src/fde_workflow_cli/commands/path.py`

```python
"""`fde-workflow path`: open paths, move them through their life cycle, link execution work."""

import datetime as dt
from pathlib import Path
from typing import Annotated

import typer

from fde_workflow_cli import clock
from fde_workflow_cli.commands.common import (
    RootOption,
    find_path,
    open_store,
    parse_date,
    record,
    require,
    user_errors,
)
from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import DecisionType, DirectionPath, PathStatus, StageName

app = typer.Typer(help="Manage paths: hypotheses that move the KPIs.", no_args_is_help=True)

TRANSITIONS: dict[PathStatus, set[PathStatus]] = {
    PathStatus.PROPOSED: {PathStatus.ACTIVE, PathStatus.DISCARDED},
    PathStatus.ACTIVE: {PathStatus.MEASURING, PathStatus.DISCARDED},
    PathStatus.MEASURING: {PathStatus.VALIDATED, PathStatus.DISCARDED, PathStatus.ACTIVE},
    PathStatus.VALIDATED: set(),
    PathStatus.DISCARDED: set(),
}
STATUSES_AT_ADD = (PathStatus.PROPOSED, PathStatus.ACTIVE, PathStatus.MEASURING)


def parse_expects(items: list[str]) -> dict[str, float]:
    expects: dict[str, float] = {}
    for item in items:
        kpi_id, separator, value = item.partition("=")
        if not separator:
            raise FdeError(f"--expects {item!r} must look like KPI_ID=VALUE.")
        try:
            expects[kpi_id.strip()] = float(value)
        except ValueError as error:
            raise FdeError(f"--expects {item!r}: {value!r} is not a number.") from error
    return expects


def normalise_ref(root: Path, ref: str) -> str:
    """URLs stay as they are; files become POSIX paths relative to the repository root."""
    if "://" in ref:
        return ref
    path = Path(ref)
    absolute = (path if path.is_absolute() else Path.cwd() / path).resolve()
    if absolute.is_relative_to(root.resolve()):
        return absolute.relative_to(root.resolve()).as_posix()
    return path.as_posix()


@app.command()
def add(
    path_id: Annotated[str, typer.Argument(help="Kebab-case id, e.g. auto-triage.")],
    hypothesis: Annotated[
        str, typer.Option(help='"If we do X, we expect KPI Y to go from A to B."')
    ],
    expects: Annotated[
        list[str], typer.Option("--expects", help="KPI_ID=VALUE expected; repeat per KPI.")
    ],
    reason: Annotated[
        str | None, typer.Option(help="Why the path opens (not needed with --inferred).")
    ] = None,
    status: Annotated[
        PathStatus, typer.Option(help="Initial status: proposed, active or measuring.")
    ] = PathStatus.PROPOSED,
    activated: Annotated[
        str | None, typer.Option(help="When work started, YYYY-MM-DD (default: today).")
    ] = None,
    maturity: Annotated[
        StageName | None, typer.Option(help="The path's own stage, when it differs.")
    ] = None,
    link: Annotated[
        list[str] | None, typer.Option("--link", help="Execution artifact; repeat it.")
    ] = None,
    inferred: Annotated[
        bool, typer.Option("--inferred", help="Inferred from existing work; needs confirmation.")
    ] = False,
    root: RootOption = None,
) -> None:
    """Open a path; records a path-open decision unless it is --inferred."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        if direction.path(path_id):
            raise FdeError(f"Path {path_id} already exists: use `fde-workflow path update`.")
        if status not in STATUSES_AT_ADD:
            raise FdeError("A path starts as proposed, active or measuring; use `path move` later.")
        if not inferred:
            reason = require(reason, "--reason", "to open a path (or use --inferred)")
        started: dt.date | None = None
        if activated:
            started = parse_date(activated, "--activated")
        elif status is not PathStatus.PROPOSED:
            started = clock.today()
        direction.paths.append(
            DirectionPath(
                id=path_id,
                hypothesis=hypothesis,
                expects=parse_expects(expects),
                status=status,
                activated=started,
                maturity=maturity,
                confirmed=not inferred,
                links=[normalise_ref(store.root, ref) for ref in link or []],
            )
        )
        store.save(direction)
        if not inferred:
            record(
                store,
                DecisionType.PATH_OPEN,
                f"Open path {path_id}: {hypothesis}",
                reason or "",
                refs=[path_id],
            )
    typer.echo(f"Added path {path_id} ({status}{', inferred' if inferred else ''}).")


@app.command()
def update(
    path_id: Annotated[str, typer.Argument()],
    hypothesis: Annotated[str | None, typer.Option()] = None,
    expects: Annotated[
        list[str] | None, typer.Option("--expects", help="Replaces every expectation.")
    ] = None,
    maturity: Annotated[StageName | None, typer.Option()] = None,
    learning: Annotated[str | None, typer.Option()] = None,
    root: RootOption = None,
) -> None:
    """Change a path's hypothesis, expectations, maturity or learning."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        path = find_path(direction, path_id)
        if hypothesis is not None:
            path.hypothesis = hypothesis
        if expects is not None:
            path.expects = parse_expects(expects)
        if maturity is not None:
            path.maturity = maturity
        if learning is not None:
            path.learning = learning
        store.save(direction)
    typer.echo(f"Updated path {path_id}.")


@app.command()
def move(
    path_id: Annotated[str, typer.Argument()],
    status: Annotated[PathStatus, typer.Argument(help="The new status.")],
    reason: Annotated[str, typer.Option(help="Why the status changes.")],
    learning: Annotated[
        str | None, typer.Option(help="What the path taught us (required to discard).")
    ] = None,
    approved_by: Annotated[str | None, typer.Option("--approved-by")] = None,
    root: RootOption = None,
) -> None:
    """Move a path: proposed → active → measuring → validated | discarded."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        path = find_path(direction, path_id)
        if status not in TRANSITIONS[path.status]:
            allowed = ", ".join(sorted(TRANSITIONS[path.status])) or "none, it is final"
            raise FdeError(
                f"Path {path_id} cannot go from {path.status} to {status} (allowed: {allowed})."
            )
        if status is PathStatus.DISCARDED and not learning:
            raise FdeError("--learning is required to discard a path: what did it teach us?")
        path.status = status
        if status is PathStatus.ACTIVE and path.activated is None:
            path.activated = clock.today()
        if learning:
            path.learning = learning
        store.save(direction)
        if status is PathStatus.VALIDATED:
            record(
                store,
                DecisionType.PATH_VALIDATE,
                f"Validate path {path_id}",
                reason,
                approved_by or "",
                [path_id],
            )
        if status is PathStatus.DISCARDED:
            record(
                store,
                DecisionType.PATH_DISCARD,
                f"Discard path {path_id}",
                reason,
                approved_by or "",
                [path_id],
            )
    typer.echo(f"Path {path_id} is now {status}.")


@app.command()
def link(
    refs: Annotated[
        list[str], typer.Argument(help="PATH_ID REF..., or REF... with --pre-framework.")
    ],
    pre_framework: Annotated[
        bool, typer.Option("--pre-framework", help="Mark artifacts as pre-framework instead.")
    ] = False,
    root: RootOption = None,
) -> None:
    """Link execution artifacts (files or URLs) to a path, or mark them pre-framework."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        known = direction.artifacts.pre_framework
        if pre_framework:
            targets = [normalise_ref(store.root, ref) for ref in refs]
            known.extend(ref for ref in dict.fromkeys(targets) if ref not in known)
            message = f"Marked {len(targets)} artifact(s) as pre-framework."
        else:
            if len(refs) < 2:
                raise FdeError("Usage: fde-workflow path link PATH_ID REF... (or --pre-framework).")
            path = find_path(direction, refs[0])
            targets = [normalise_ref(store.root, ref) for ref in refs[1:]]
            path.links.extend(ref for ref in dict.fromkeys(targets) if ref not in path.links)
            direction.artifacts.pre_framework = [ref for ref in known if ref not in targets]
            message = f"Linked {len(targets)} artifact(s) to {path.id}."
        store.save(direction)
    typer.echo(message)


@app.command()
def confirm(
    path_id: Annotated[str, typer.Argument()],
    reason: Annotated[
        str, typer.Option(help="Why it is confirmed.")
    ] = "Confirmed a path inferred from existing work.",
    root: RootOption = None,
) -> None:
    """Mark an inferred path as confirmed; records a path-open decision."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        path = find_path(direction, path_id)
        path.confirmed = True
        store.save(direction)
        record(
            store,
            DecisionType.PATH_OPEN,
            f"Confirm path {path_id}: {path.hypothesis}",
            reason,
            refs=[path_id],
        )
    typer.echo(f"Path {path_id} confirmed.")
```

- [ ] **Step 4: Register the group in `cli/src/fde_workflow_cli/main.py`**

Change the commands import to:

```python
from fde_workflow_cli.commands import kpi, northstar, path, project
```

and append:

```python
app.add_typer(path.app, name="path")
```

- [ ] **Step 5: Run the tests and the checks**

Run: `cd cli && poetry run pytest tests/test_cmd_path.py -v && cd .. && make cli-check`
Expected: all path command tests pass (9); checks clean.

- [ ] **Step 6: Commit**

```bash
git add cli/src/fde_workflow_cli/commands/path.py cli/src/fde_workflow_cli/main.py cli/tests/test_cmd_path.py
git commit -m "feat(cli): add path commands"
```

### Task 11: Stage and decision commands

**Files:**
- Create: `cli/src/fde_workflow_cli/commands/stage.py`, `cli/src/fde_workflow_cli/commands/decision.py`
- Modify: `cli/src/fde_workflow_cli/main.py`
- Test: `cli/tests/test_cmd_stage.py`

**Interfaces:**
- Consumes: Task 7 helpers, `STAGE_ORDER`, `GateDecision`, `Outcome`.
- Produces: `fde-workflow stage set STAGE --reason [--outcome] [--entered] [--inferred] [--approved-by]` (records `stage-set`), `stage confirm`, `stage criteria CRITERION... [--reason --approved-by when replacing]`, `stage decide go|recycle|hold|kill --reason --approved-by [--to STAGE]` (records `stage-gate`), `decision add --summary --reason [--type] [--approved-by] [--ref ...]`.

- [ ] **Step 1: Write the failing tests** — `cli/tests/test_cmd_stage.py`

```python
from pathlib import Path

import yaml

from tests.helpers import decisions, fails, ok


def stage(fde: Path) -> dict[str, object]:
    data = yaml.safe_load((fde / ".fde" / "direction.yaml").read_text())
    assert isinstance(data, dict)
    result = data["stage"]
    assert isinstance(result, dict)
    return result


def test_set_records_a_stage_set_decision(fde: Path) -> None:
    ok(
        "stage",
        "set",
        "mvp",
        "--reason",
        "Deployed to 20 agents",
        "--inferred",
        "--entered",
        "2026-09-01",
    )
    assert stage(fde)["current"] == "mvp"
    assert stage(fde)["entered"] == "2026-09-01"
    assert decisions(fde)[0]["summary"] == "Stage set to mvp (inferred)"
    assert "! [C1] The stage was inferred" in ok("validate").output
    ok("stage", "confirm")
    assert stage(fde)["confirmed"] is True


def test_set_closed_needs_an_outcome(fde: Path) -> None:
    assert "outcome" in fails("stage", "set", "closed", "--reason", "r").output
    ok("stage", "set", "closed", "--reason", "r", "--outcome", "completed")


def test_criteria_can_be_set_once_then_changes_need_approval(fde: Path) -> None:
    ok("stage", "criteria", "North Star agreed", "Baselines measured")
    assert stage(fde)["gate_criteria"] == ["North Star agreed", "Baselines measured"]
    assert decisions(fde) == []
    assert "--reason is required" in fails("stage", "criteria", "Only one").output
    ok("stage", "criteria", "Only one", "--reason", "r", "--approved-by", "Jane")
    assert decisions(fde)[0]["summary"] == "Gate criteria of discovery changed"


def test_go_moves_to_the_next_stage_and_resets_criteria(fde: Path) -> None:
    ok("stage", "criteria", "x")
    ok("stage", "decide", "go", "--reason", "Baselines in", "--approved-by", "Jane")
    assert stage(fde)["current"] == "poc"
    assert stage(fde)["gate_criteria"] == []
    assert decisions(fde)[-1]["summary"] == "go at discovery → poc"
    ok("stage", "decide", "go", "--to", "mvp", "--reason", "r", "--approved-by", "J")
    assert stage(fde)["current"] == "mvp"


def test_go_rules(fde: Path) -> None:
    assert (
        "after discovery"
        in fails(
            "stage", "decide", "go", "--to", "discovery", "--reason", "r", "--approved-by", "J"
        ).output
    )
    assert (
        "use kill"
        in fails(
            "stage", "decide", "go", "--to", "closed", "--reason", "r", "--approved-by", "J"
        ).output
    )
    assert (
        "only applies to go"
        in fails(
            "stage", "decide", "hold", "--to", "mvp", "--reason", "r", "--approved-by", "J"
        ).output
    )


def test_hold_recycle_and_kill(fde: Path) -> None:
    ok("stage", "decide", "hold", "--reason", "Budget freeze", "--approved-by", "J")
    assert stage(fde)["on_hold"] is True
    ok("stage", "decide", "recycle", "--reason", "Resume", "--approved-by", "J")
    assert stage(fde)["on_hold"] is False
    ok("stage", "decide", "kill", "--reason", "No data access", "--approved-by", "J")
    assert stage(fde)["outcome"] == "discontinued"
    assert "closed" in fails("stage", "decide", "go", "--reason", "r", "--approved-by", "J").output


def test_production_go_completes_the_project(fde: Path) -> None:
    ok("stage", "set", "production", "--reason", "r")
    ok("stage", "decide", "go", "--reason", "Target reached", "--approved-by", "J")
    assert stage(fde)["current"] == "closed"
    assert stage(fde)["outcome"] == "completed"


def test_decision_add(fde: Path) -> None:
    ok(
        "decision",
        "add",
        "--type",
        "scope-change",
        "--summary",
        "Drop email",
        "--reason",
        "r",
        "--ref",
        "auto-triage",
    )
    [decision] = decisions(fde)
    assert decision["type"] == "scope-change"
    assert decision["refs"] == ["auto-triage"]
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd cli && poetry run pytest tests/test_cmd_stage.py -v`
Expected: failures with `No such command 'stage'`.

- [ ] **Step 3: Write the stage commands** — `cli/src/fde_workflow_cli/commands/stage.py`

```python
"""`fde-workflow stage`: set the project stage, its gate criteria and gate decisions."""

from typing import Annotated

import typer

from fde_workflow_cli import clock
from fde_workflow_cli.commands.common import (
    RootOption,
    open_store,
    parse_date,
    record,
    require,
    user_errors,
)
from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import (
    STAGE_ORDER,
    DecisionType,
    GateDecision,
    Outcome,
    StageName,
    StageState,
)

app = typer.Typer(help="Set the project stage and record gate decisions.", no_args_is_help=True)


@app.command("set")
def set_(
    stage: Annotated[StageName, typer.Argument(help="The stage the project is in.")],
    reason: Annotated[str, typer.Option(help="Why the stage is set without a gate.")],
    outcome: Annotated[
        Outcome | None, typer.Option(help="Required when the stage is closed.")
    ] = None,
    entered: Annotated[
        str | None, typer.Option(help="When the project got there, YYYY-MM-DD (default: today).")
    ] = None,
    inferred: Annotated[
        bool, typer.Option("--inferred", help="Inferred from evidence; needs confirmation.")
    ] = False,
    approved_by: Annotated[str | None, typer.Option("--approved-by")] = None,
    root: RootOption = None,
) -> None:
    """Set the stage directly, without a gate (e.g. when adopting an existing project)."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        direction.stage = StageState(
            current=stage,
            entered=parse_date(entered, "--entered") if entered else clock.today(),
            outcome=outcome,
            confirmed=not inferred,
        )
        store.save(direction)
        suffix = " (inferred)" if inferred else ""
        record(
            store,
            DecisionType.STAGE_SET,
            f"Stage set to {stage}{suffix}",
            reason,
            approved_by or "",
        )
    typer.echo(f"Stage set to {stage}{suffix}.")


@app.command()
def confirm(root: RootOption = None) -> None:
    """Mark an inferred stage as confirmed."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        direction.stage.confirmed = True
        store.save(direction)
    typer.echo(f"Stage {direction.stage.current} confirmed.")


@app.command()
def criteria(
    items: Annotated[list[str], typer.Argument(help="One argument per gate criterion.")],
    reason: Annotated[str | None, typer.Option(help="Why agreed criteria change.")] = None,
    approved_by: Annotated[
        str | None, typer.Option("--approved-by", help="Who approves the change.")
    ] = None,
    root: RootOption = None,
) -> None:
    """Set the current stage's gate criteria; replacing agreed criteria records a decision."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        stage = direction.stage
        replacing = bool(stage.gate_criteria) and stage.gate_criteria != items
        if replacing:
            reason = require(reason, "--reason", "to change agreed gate criteria")
            approved_by = require(approved_by, "--approved-by", "to change agreed gate criteria")
        stage.gate_criteria = list(items)
        store.save(direction)
        if replacing:
            record(
                store,
                DecisionType.STAGE_GATE,
                f"Gate criteria of {stage.current} changed",
                reason or "",
                approved_by or "",
            )
    typer.echo(f"Gate criteria of {stage.current}: {len(items)}.")


@app.command()
def decide(
    gate: Annotated[GateDecision, typer.Argument(help="go, recycle, hold or kill.")],
    reason: Annotated[str, typer.Option(help="The evidence behind the decision.")],
    approved_by: Annotated[str, typer.Option("--approved-by", help="The sponsor.")],
    to: Annotated[
        StageName | None, typer.Option("--to", help="With go: skip to a later stage.")
    ] = None,
    root: RootOption = None,
) -> None:
    """Record a gate decision and apply it to the stage."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        before = direction.stage
        if before.current is StageName.CLOSED:
            raise FdeError("The project is closed.")
        if to is not None and gate is not GateDecision.GO:
            raise FdeError("--to only applies to go.")
        today = clock.today()
        if gate is GateDecision.GO:
            position = STAGE_ORDER.index(before.current)
            target = to or STAGE_ORDER[position + 1]
            if STAGE_ORDER.index(target) <= position:
                raise FdeError(f"--to must be a stage after {before.current}.")
            if target is StageName.CLOSED and before.current is not StageName.PRODUCTION:
                raise FdeError("Only go from production closes a project; otherwise use kill.")
            outcome = Outcome.COMPLETED if target is StageName.CLOSED else None
            direction.stage = StageState(current=target, entered=today, outcome=outcome)
        elif gate is GateDecision.KILL:
            direction.stage = StageState(
                current=StageName.CLOSED, entered=today, outcome=Outcome.DISCONTINUED
            )
        else:
            before.on_hold = gate is GateDecision.HOLD
        store.save(direction)
        after = direction.stage.current
        record(
            store,
            DecisionType.STAGE_GATE,
            f"{gate} at {before.current}" + (f" → {after}" if after != before.current else ""),
            reason,
            approved_by,
        )
    typer.echo(
        f"Recorded {gate}; stage is {after}{' (on hold)' if direction.stage.on_hold else ''}."
    )
```

- [ ] **Step 4: Write the decision command** — `cli/src/fde_workflow_cli/commands/decision.py`

```python
"""`fde-workflow decision`: record a direction decision no other command records."""

from typing import Annotated

import typer

from fde_workflow_cli.commands.common import RootOption, open_store, record, user_errors
from fde_workflow_cli.model import DecisionType

app = typer.Typer(help="Record direction decisions.", no_args_is_help=True)


@app.command()
def add(
    summary: Annotated[str, typer.Option(help="What was decided.")],
    reason: Annotated[str, typer.Option(help="Why.")],
    decision_type: Annotated[
        DecisionType, typer.Option("--type", help="Kind of decision.")
    ] = DecisionType.OTHER,
    approved_by: Annotated[str, typer.Option("--approved-by", help="Who approved it.")] = "",
    ref: Annotated[
        list[str] | None, typer.Option("--ref", help="Related id or URL; repeat it.")
    ] = None,
    root: RootOption = None,
) -> None:
    """Record a decision, e.g. a scope change."""
    with user_errors():
        store = open_store(root)
        store.load()
        record(store, decision_type, summary, reason, approved_by, ref or [])
    typer.echo("Decision recorded.")
```

- [ ] **Step 5: Register both groups in `cli/src/fde_workflow_cli/main.py`**

Change the commands import to:

```python
from fde_workflow_cli.commands import decision, kpi, northstar, path, project, stage
```

and append:

```python
app.add_typer(stage.app, name="stage")
app.add_typer(decision.app, name="decision")
```

- [ ] **Step 6: Run the tests and the checks**

Run: `cd cli && poetry run pytest tests/test_cmd_stage.py -v && cd .. && make cli-check`
Expected: all stage tests pass (8); checks clean.

- [ ] **Step 7: Commit**

```bash
git add cli/src/fde_workflow_cli/commands/stage.py cli/src/fde_workflow_cli/commands/decision.py cli/src/fde_workflow_cli/main.py cli/tests/test_cmd_stage.py
git commit -m "feat(cli): add stage and decision commands"
```

### Task 12: SessionStart hook

**Files:**
- Create: `cli/src/fde_workflow_cli/commands/hook.py`
- Modify: `cli/src/fde_workflow_cli/main.py`
- Create: `plugin/hooks/hooks.json`, `plugin/hooks/fde-hook` (mode 755), `plugin/hooks/test_fde_hook.sh`
- Modify: `Makefile`, `.github/workflows/plugin.yml`
- Test: `cli/tests/test_cmd_hook.py`, `plugin/hooks/test_fde_hook.sh`

**Interfaces:**
- Consumes: `Store`, `locate`, `rules.check`, `summary.context`.
- Produces: `session_context(payload: str) -> str | None`; `fde-workflow hook session-start`
  (reads the hook JSON on stdin; prints
  `{"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": ...}}` or
  nothing; never fails). The plugin runs it through `plugin/hooks/fde-hook session-start`.

- [ ] **Step 1: Write the failing CLI tests** — `cli/tests/test_cmd_hook.py`

```python
import json
from pathlib import Path

from tests.helpers import ok


def test_session_start_is_silent_without_fde(tmp_path: Path) -> None:
    result = ok("hook", "session-start", stdin=json.dumps({"cwd": str(tmp_path)}))
    assert result.stdout == ""


def test_session_start_adds_the_brief_context(fde: Path) -> None:
    nested = fde / "src"
    nested.mkdir()
    result = ok("hook", "session-start", stdin=json.dumps({"cwd": str(nested)}))
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "SessionStart"
    assert output["additionalContext"].startswith("FDE direction of this repository")
    assert "Stage: discovery since 2026-10-12" in output["additionalContext"]


def test_session_start_tolerates_bad_input(fde: Path) -> None:
    result = ok("hook", "session-start", stdin="not json")
    assert "additionalContext" in result.stdout


def test_session_start_reports_an_unreadable_fde(fde: Path) -> None:
    (fde / ".fde" / "direction.yaml").write_text("schema_version: 1\nproject: 3\n")
    result = ok("hook", "session-start", stdin=json.dumps({"cwd": str(fde)}))
    assert "cannot be read" in json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd cli && poetry run pytest tests/test_cmd_hook.py -v`
Expected: failures with `No such command 'hook'`.

- [ ] **Step 3: Write the hook command** — `cli/src/fde_workflow_cli/commands/hook.py`

```python
"""`fde-workflow hook`: entry points of the plugin's hooks. A hook never fails a session."""

import json
import os
import sys
from pathlib import Path

import typer

from fde_workflow_cli import rules, summary
from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.store import Store, locate

app = typer.Typer(help="Entry points of the Claude Code plugin hooks.", no_args_is_help=True)


def session_context(payload: str) -> str | None:
    """The context for a new session, or None when the repository has no .fde/."""
    try:
        data = json.loads(payload) if payload.strip() else {}
    except json.JSONDecodeError:
        data = {}
    cwd = data.get("cwd") if isinstance(data, dict) else None
    start = Path(cwd) if isinstance(cwd, str) else Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    store = Store(locate(start))
    if not store.exists():
        return None
    try:
        direction = store.load()
        measurements = store.measurements()
    except FdeError as error:
        return (
            f"{summary.CONTEXT_HEADER}\n\n.fde/ cannot be read: {error}\n"
            "Run `fde-workflow validate`."
        )
    issues = rules.check(direction, measurements, store.dir)
    return summary.context(direction, measurements, issues, brief=True)


@app.command("session-start")
def session_start() -> None:
    """Print the direction as SessionStart context (reads the hook's JSON on stdin)."""
    try:
        text = session_context(sys.stdin.read())
    except Exception as error:  # a hook must never interrupt the session
        typer.echo(f"fde-workflow hook: {error}", err=True)
        return
    if text:
        output = {
            "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}
        }
        typer.echo(json.dumps(output))
```

- [ ] **Step 4: Register the group in `cli/src/fde_workflow_cli/main.py`**

Change the commands import to:

```python
from fde_workflow_cli.commands import decision, hook, kpi, northstar, path, project, stage
```

and append:

```python
app.add_typer(hook.app, name="hook")
```

- [ ] **Step 5: Run the CLI tests**

Run: `cd cli && poetry run pytest tests/test_cmd_hook.py -v`
Expected: 4 passed.

- [ ] **Step 6: Write the failing wrapper test** — `plugin/hooks/test_fde_hook.sh`

```sh
#!/bin/sh
# Tests for the hook wrapper. Run: sh plugin/hooks/test_fde_hook.sh
set -u
HOOK="$(cd "$(dirname "$0")" && pwd)/fde-hook"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
failures=0

check() {  # check NAME EXPECTED_OUTPUT PATH_VALUE
  name=$1 want=$2
  got=$(printf '{"cwd": "/tmp"}' | PATH="$3" sh "$HOOK" session-start 2>/dev/null)
  code=$?
  if [ "$code" -ne 0 ] || [ "$got" != "$want" ]; then
    echo "FAIL: $name (exit $code, output: $got)"
    failures=$((failures + 1))
  else
    echo "ok: $name"
  fi
}

check "silent without the CLI" "" "/usr/bin:/bin"

mkdir -p "$WORK/bin"
printf '#!/bin/sh\necho "args=$*"; cat\n' > "$WORK/bin/fde-workflow"
chmod 755 "$WORK/bin/fde-workflow"
check "passes the event and stdin to the CLI" 'args=hook session-start
{"cwd": "/tmp"}' "$WORK/bin:/usr/bin:/bin"

printf '#!/bin/sh\nexit 3\n' > "$WORK/bin/fde-workflow"
check "exits 0 when the CLI fails" "" "$WORK/bin:/usr/bin:/bin"

if [ "$failures" -eq 0 ]; then echo "all hook tests passed"; else echo "$failures failure(s)"; exit 1; fi
```

- [ ] **Step 7: Run it to see it fail**

Run: `sh plugin/hooks/test_fde_hook.sh`
Expected: `FAIL` lines (the wrapper does not exist yet) and exit 1.

- [ ] **Step 8: Write the wrapper, then `chmod 755 plugin/hooks/fde-hook`** — `plugin/hooks/fde-hook`

```sh
#!/bin/sh
# Runs `fde-workflow hook <event>` with the hook's JSON on stdin when the CLI is installed;
# otherwise does nothing. A hook must never interrupt a session, so this always exits 0.
command -v fde-workflow >/dev/null 2>&1 || exit 0
fde-workflow hook "$@" || true
exit 0
```

- [ ] **Step 9: Declare the hook** — `plugin/hooks/hooks.json`

```json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "startup|resume|clear|compact",
        "hooks": [
          {
            "type": "command",
            "command": "\"${CLAUDE_PLUGIN_ROOT}/hooks/fde-hook\" session-start"
          }
        ]
      }
    ]
  }
}
```

- [ ] **Step 10: Run the wrapper test in the checks**

In `Makefile`, target `plugin-check`, add after `sh plugin/evals/stub/test_stub.sh`:

```make
	sh plugin/hooks/test_fde_hook.sh
```

In `.github/workflows/plugin.yml`, step "Script tests and version check", add after the
`test_stub.sh` line:

```yaml
          if [ -f plugin/hooks/test_fde_hook.sh ]; then sh plugin/hooks/test_fde_hook.sh; fi
```

- [ ] **Step 11: Run everything**

Run: `make check`
Expected: `all hook tests passed`; `claude plugin validate --strict plugin` passes; CLI checks clean.

- [ ] **Step 12: Smoke-test the hook end to end**

```bash
tmp=$(mktemp -d) && (cd "$tmp" && poetry -C "$OLDPWD/cli" run fde-workflow init --preset none \
  && echo "{\"cwd\": \"$tmp\"}" | PATH="$OLDPWD/cli/.venv/bin:$PATH" sh "$OLDPWD/plugin/hooks/fde-hook" session-start)
rm -rf "$tmp"
```
Expected: one JSON line whose `additionalContext` starts with `FDE direction of this repository`.

- [ ] **Step 13: Commit**

```bash
git add cli/src/fde_workflow_cli/commands/hook.py cli/src/fde_workflow_cli/main.py cli/tests/test_cmd_hook.py plugin/hooks Makefile .github/workflows/plugin.yml
git commit -m "feat(plugin): add the session start hook"
```

### Task 13: `doctor` checks `.fde/`

**Files:**
- Modify: `cli/src/fde_workflow_cli/doctor.py`
- Modify (replace): `cli/tests/test_doctor.py`

**Interfaces:**
- Produces: `check_direction() -> CheckResult` (ok without `.fde/`; ✗ when `.fde/` cannot be
  read, e.g. unsupported `schema_version`); `CHECKS = [check_python, check_direction]`.

- [ ] **Step 1: Replace the doctor tests** — `cli/tests/test_doctor.py`

```python
from pathlib import Path

from fde_workflow_cli.doctor import check_direction, check_python, run_checks


def test_python_check_passes_on_a_supported_python() -> None:
    result = check_python()
    assert result.ok
    assert result.message.startswith("Python 3.")


def test_run_checks_runs_every_check(repo: Path) -> None:
    assert [result.ok for result in run_checks()] == [True, True]


def test_direction_check_without_fde(repo: Path) -> None:
    assert check_direction().message.startswith("No .fde/ here yet")


def test_direction_check_with_a_readable_fde(fde: Path) -> None:
    assert check_direction().ok


def test_direction_check_with_an_unsupported_schema(fde: Path) -> None:
    (fde / ".fde" / "direction.yaml").write_text("schema_version: 9\n")
    result = check_direction()
    assert not result.ok
    assert "schema_version 9" in result.message
```

- [ ] **Step 2: Run them to see them fail**

Run: `cd cli && poetry run pytest tests/test_doctor.py -v`
Expected: `ImportError: cannot import name 'check_direction'`.

- [ ] **Step 3: Write the new doctor module (full file)** — `cli/src/fde_workflow_cli/doctor.py`

```python
"""Readiness checks behind `fde-workflow doctor`. Add one function per check to CHECKS."""

import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import SCHEMA_VERSION
from fde_workflow_cli.store import Store, locate


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    message: str


MINIMUM_PYTHON = (3, 13)


def check_python() -> CheckResult:
    found = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info >= MINIMUM_PYTHON:
        return CheckResult(ok=True, message=f"Python {found}")
    return CheckResult(ok=False, message=f"Python {found} is too old: install Python 3.13 or newer")


def check_direction() -> CheckResult:
    store = Store(locate(Path.cwd()))
    if not store.exists():
        return CheckResult(ok=True, message="No .fde/ here yet: the adopt skill sets one up")
    try:
        store.load()
    except FdeError as error:
        first_line = str(error).splitlines()[0]
        return CheckResult(ok=False, message=f".fde/ cannot be read: {first_line}")
    return CheckResult(ok=True, message=f".fde/ uses schema {SCHEMA_VERSION}: {store.dir}")


CHECKS: list[Callable[[], CheckResult]] = [check_python, check_direction]


def run_checks() -> list[CheckResult]:
    return [check() for check in CHECKS]
```

- [ ] **Step 4: Run the tests and the checks**

Run: `cd cli && poetry run pytest tests/test_doctor.py tests/test_main.py -v && cd .. && make cli-check`
Expected: all pass; checks clean.

- [ ] **Step 5: Commit**

```bash
git add cli/src/fde_workflow_cli/doctor.py cli/tests/test_doctor.py
git commit -m "feat(cli): check .fde readability in doctor"
```

### Task 14: Framework reference, entry skill and setup hand-over

**Files:**
- Create: `plugin/skills/fde-workflow/references/framework.md`
- Modify (replace): `plugin/skills/fde-workflow/SKILL.md`, `plugin/skills/setup/SKILL.md`

**Interfaces:**
- Consumes: CLI commands from Tasks 7–11.
- Produces: the framework reference that every other skill reads at `../fde-workflow/references/framework.md`; skill names `adopt`, `discovery`, `kpi`, `path` that this skill hands over to (created in Tasks 15–16).

Skills are behaviour, not code: their tests are the evals of Task 17.

- [ ] **Step 1: Write the framework reference** — `plugin/skills/fde-workflow/references/framework.md`

```markdown
# The FDE direction framework

A direction layer for a repository: **why it exists** and **whether the work moves us towards
it**. It never plans or executes work: specs, plans and tasks belong to the project's execution
methodology (superpowers, spec-kit, anything). The framework links to them and reads them.

Full design: https://github.com/mjfura/fde-workflow/blob/main/docs/superpowers/specs/2026-10-12-fde-direction-framework-design.md

## Components

| Component | What it is | Rules |
|---|---|---|
| **North Star** | One sentence about an outcome, for someone; never a solution. Plus beneficiary, problem, non-goals, primary KPI, and the customer sponsor who approves direction changes. Test: *if this is achieved, would the customer call the project a success?* | N1 one North Star naming one primary KPI. N2 changing it records a decision with reason and approver. |
| **KPIs** | `primary` (exactly one, the North Star metric), `secondary`, `guardrail` (must not get worse; its target is the worst acceptable value). Definition, source, unit, direction, numeric target, window, recipe. | K1 targets are numbers. K2 one primary. K3 baseline before the work that should move it. K4 a recipe change invalidates the baseline. K5 a target change records a decision. |
| **Paths** | Hypotheses: *if we do X, we expect KPI Y to go from A to B.* Status `proposed → active → measuring → validated \| discarded`. | P1 every path targets an existing KPI. P2 built is not validated: validation needs a measurement taken after the path became active. P3 validating or discarding records a decision; discarded paths keep their learning. |
| **Links** | References from a path to execution artifacts: files (specs, plans) or URLs (PRs, issues). | L1 an artifact matching the artifact globs that no path links to is drift. L2 artifacts from before adoption can be marked pre-framework. |
| **Measurements** | Value, window, source, external factors, recipe fingerprint. The first one, flagged as baseline, is `historical` (reconstructed from data before the work) or `late` (measured once work had started; reports must say so). | M1 never improvise how to measure: follow the KPI's recipe (`script`, `query` or `manual`, in `.fde/measures/`). M2 append-only. |
| **Decisions** | Direction-level only: North Star, targets, paths, stage gates, scope. Not technical ADRs. | D1 append-only. D2 the CLI records them automatically. |
| **Stage** | `discovery → poc → mvp → early-access → production → closed`, each with gate criteria agreed on entry. Gate decisions: go, recycle, hold, kill. | S1 criteria agreed on entry. S2 gate decisions record reason and approver. S3 from mvp on, the primary KPI is measured in the stage. |

Items inferred from existing work (by the adopt skill) stay unconfirmed (rule C1) until the FDE,
and the sponsor where it applies, confirm them.

## Files

`.fde/direction.yaml`, `.fde/measurements.jsonl` and `.fde/decisions.jsonl` are written **only**
by the `fde-workflow` CLI, which validates every change. Skills write free-form files only:
recipes in `.fde/measures/` and notes in `.fde/discovery/`.

## Limitation

Before/after comparisons do not prove causation. Record external factors with every measurement
and state them, and any late baseline, in every report.
```

- [ ] **Step 2: Replace the template skeleton with the entry skill** — `plugin/skills/fde-workflow/SKILL.md`

```markdown
---
name: fde-workflow
description: 'Entry point of the FDE direction framework for customer projects: shows where the project stands against its North Star, KPIs, paths and stage, and proposes the next action. Use it when the user asks "how are we doing?", "what is next?", "where does the project stand?", asks about the North Star, KPIs, baselines, paths, gate criteria or the project stage, wants to move the project to another stage, or wants to use the FDE framework in a repository. Also use it at the start of work in a repository with a .fde/ directory.'
allowed-tools:
  - Bash(fde-workflow status)
  - Bash(fde-workflow validate)
  - Bash(fde-workflow context)
---

# FDE direction framework

The framework is defined in `references/framework.md` (next to this file). Read it once per
session before acting on it.

## Steps

1. Run `fde-workflow status`.
   - **Command not found:** use the `setup` skill first.
   - **"No .fde/":** the framework is not set up in this repository. Offer the `adopt` skill and
     stop.
2. Run `fde-workflow validate` and propose **one** next action, the first that applies:
   1. **Errors (✗):** explain each and fix it with the CLI command it names.
   2. **No North Star, or an inferred one (N1, C1):** the `discovery` skill.
   3. **A KPI without baseline (K3) or with a changed recipe (K4):** the `kpi` skill, baseline mode.
   4. **Stage without gate criteria (S1):** agree them now (see *Stage* below).
   5. **A path in `measuring`:** the `kpi` skill to measure it, then the `path` skill to validate
      or discard it.
   6. **Inferred paths (C1):** the `path` skill to confirm or discard them.
   7. **Primary KPI not measured in this stage (S3):** the `kpi` skill.
   8. **Nothing pending:** summarise and ask what the user wants to work on next; new work goes
      through the `path` skill's alignment check.
3. Answer in a few lines: the North Star, the stage, each KPI as baseline → latest → target, live
   paths, and the recommended action with the skill or command that does it.

## Stage

- **Gate criteria** are agreed when entering a stage, with evidence that can be checked
  (e.g. "primary KPI measured over 2 weeks of real use"), and recorded with
  `fde-workflow stage criteria "<criterion>" "<criterion>"`. Changing agreed criteria needs
  `--reason` and `--approved-by`.
- **Gate decisions** are taken with the sponsor, against the criteria, with evidence:
  `fde-workflow stage decide go|recycle|hold|kill --reason "<evidence>" --approved-by "<sponsor>"`
  (`--to <stage>` skips stages on go). Never decide a gate on the user's behalf; propose it and
  run the command once they confirm the sponsor agreed.

## Rules

- Never edit `.fde/direction.yaml`, `measurements.jsonl` or `decisions.jsonl` by hand: only
  through the CLI.
- This skill and the framework do not plan or execute work. Specs, plans and tasks belong to the
  user's own methodology; hand over to it once the direction is clear.
- Talk to the user in their language; CLI ids are kebab-case.
```

- [ ] **Step 3: Add the hand-over to adopt (full file)** — `plugin/skills/setup/SKILL.md`

```markdown
---
name: setup
description: 'Install, verify or troubleshoot what the fde-workflow plugin needs: the `fde-workflow` CLI (PyPI package `fde-workflow-cli`). Use it when the user wants to set up the fde-workflow plugin, asks whether it is ready, or shares an error such as "command not found".'
allowed-tools:
  - Bash(fde-workflow --version)
  - Bash(fde-workflow doctor)
  - Bash(fde-workflow status)
---

# Set up fde-workflow

## The `fde-workflow` CLI

`fde-workflow` (PyPI package `fde-workflow-cli`, Python 3.13+) is ready when it
is installed and `fde-workflow doctor` ends with `Ready.`

1. Run `fde-workflow --version`.
   - **Command not found:** check `command -v uv` and `command -v pipx`. Propose
     `uv tool install fde-workflow-cli` (or `pipx install fde-workflow-cli`; if the
     default Python is older than 3.13, `pipx install --python python3.13 fde-workflow-cli`)
     and run it only after the user agrees. Without uv or pipx, point to
     https://docs.astral.sh/uv/getting-started/installation/. Before installing, check that
     https://pypi.org/project/fde-workflow-cli/ links to https://github.com/mjfura/fde-workflow;
     if it does not exist or points elsewhere, stop and tell the user instead of installing.
   - **Installed:** to upgrade, propose `uv tool upgrade fde-workflow-cli` (or
     `pipx upgrade fde-workflow-cli`), with the same consent rule.
2. Run `fde-workflow doctor` (exit 0 = ready, 1 = at least one ✗) and follow the hint
   printed next to each ✗.
3. Repeat `fde-workflow doctor` until it ends with `Ready.`

## Next

When the CLI is ready, run `fde-workflow status` in the current repository. If it reports that
there is no `.fde/`, offer the `adopt` skill to set up the FDE framework here.
```

- [ ] **Step 4: Validate the plugin**

Run: `make plugin-check`
Expected: `claude plugin validate --strict plugin` passes; stub and hook tests pass.

- [ ] **Step 5: Commit**

```bash
git add plugin/skills/fde-workflow/references/framework.md plugin/skills/fde-workflow/SKILL.md plugin/skills/setup/SKILL.md
git commit -m "feat(plugin): add the fde-workflow entry skill and framework reference"
```

### Task 15: Adopt and discovery skills

**Files:**
- Create: `plugin/skills/adopt/SKILL.md`, `plugin/skills/discovery/SKILL.md`

**Interfaces:**
- Consumes: `fde-workflow detect`, `init`, `northstar set|confirm`, `path add|link`, `stage set|criteria`.

- [ ] **Step 1: Write the adopt skill** — `plugin/skills/adopt/SKILL.md`

```markdown
---
name: adopt
description: 'Set up the FDE direction framework (.fde/) in a repository, new or existing: detects the execution methodology (superpowers, spec-kit, other), and for an existing project infers a draft North Star, retroactive paths from existing specs and plans, and the current stage, all marked unconfirmed until the FDE confirms them. Use it when the user wants to start using the FDE framework, fde-workflow, a North Star or KPIs in this repository, or when another skill finds no .fde/ directory.'
allowed-tools:
  - Bash(fde-workflow status)
  - Bash(fde-workflow detect)
---

# Adopt the FDE framework in a repository

Read `../fde-workflow/references/framework.md` (relative to this skill's directory) first.

## Steps

1. Run `fde-workflow detect`. If `fde_initialised` is true, the framework is already set up: hand
   over to the `fde-workflow` skill instead.
2. Decide the mode from the evidence and tell the user which one you chose and why:
   - **New project:** no artifacts, little or no history.
   - **Existing project:** specs, plans, a README with a purpose, history or deployment signals.
3. Initialise. When `detect` found a methodology, run `fde-workflow init --preset <methodology>`.
   Otherwise ask the user where the project keeps specs, plans or design documents and run
   `fde-workflow init --glob "<pattern>"` once per location (e.g. `--glob "design/**"`), or
   `fde-workflow init --preset none` if there are none.
4. **New project:** hand over to the `discovery` skill. Stop here.
5. **Existing project:** build a draft direction from the README, the artifacts listed by
   `detect` (read them) and the history:
   1. **North Star:** an outcome for someone, never a solution. Record it as a draft:
      `fde-workflow northstar set --statement "..." --beneficiary "..." --problem "..." --inferred`.
   2. **Retroactive paths:** group the existing specs and plans into hypotheses about the outcome.
      For each, use the date of its first artifact as `--activated` and a status that reflects the
      evidence (`active` while work goes on, `measuring` when it is built). Never `validated`:
      that needs a measurement. A path needs a KPI, so propose the KPIs first with the `kpi`
      skill, then: `fde-workflow path add <id> --hypothesis "..." --expects <kpi>=<value>
      --status <status> --activated <date> --link <artifact> --inferred`.
   3. **Stage:** infer it from the evidence (deployment signals, users, CI) and record it:
      `fde-workflow stage set <stage> --reason "<evidence>" --entered <date> --inferred`.
   4. **Remaining artifacts:** ask the user which ones predate the framework and mark them:
      `fde-workflow path link --pre-framework <artifact>...`.
6. Present the draft and say clearly that every item is a **hypothesis inferred by you**. Then
   hand over to the `discovery` skill to confirm or correct it with the user (and the sponsor
   where it applies). Baselines come from the `kpi` skill: `historical` when data from before the
   work exists, otherwise `late`, always declared.

## Rules

- Everything inferred is recorded with `--inferred`; only the user confirms it.
- Never invent numbers: KPI targets and expected values come from the user.
- Read existing specs and plans; never change them. The direction only links to execution work.
```

- [ ] **Step 2: Write the discovery skill** — `plugin/skills/discovery/SKILL.md`

```markdown
---
name: discovery
description: 'Define or confirm the direction of a customer project with the FDE: the North Star (an outcome, never a solution), its beneficiary, problem, non-goals, sponsor and candidate KPIs, through a guided interview and a review of the repository and customer documents. Use it when starting a new customer project, when the user says "let us define the North Star", "what is this project for", "define success" or "discovery", when the North Star is missing or unconfirmed, or when the adopt skill hands over a draft.'
allowed-tools:
  - Bash(fde-workflow status)
  - Bash(fde-workflow context)
---

# Discovery: define the direction

Read `../fde-workflow/references/framework.md` (relative to this skill's directory) first, then
run `fde-workflow status` to see what already exists (a draft from the `adopt` skill, or nothing).

## Interview

Ask **one question at a time**; prefer offering options when you can infer them from the
repository or documents. Skip what the documents already answer, and say what you inferred.

1. **Problem:** what hurts today, for whom, and how do they cope now (the current process)?
2. **Beneficiary:** who gets the outcome? (end users, an internal team, the customer's customers)
3. **Outcome:** what will be different for them when this works? This becomes the North Star.
4. **Evidence:** how would we see it in data? Which systems hold that data, and can we access it?
5. **Constraints:** deadlines, data access, security, budget, systems that cannot change.
6. **Non-goals:** what is explicitly out of scope?
7. **Sponsor:** who on the customer side approves direction changes and gate decisions?

Save the notes, with the date and who was interviewed, to
`.fde/discovery/<YYYY-MM-DD>-<topic>.md`.

## North Star check

Before recording it, test the statement with the user:
- It names an **outcome for someone**, not a solution or deliverable. "Build an AI chatbot" is a
  solution; "ACME customers resolve their issues without waiting for an agent" is an outcome.
  When the user gives a solution, ask what it is for and propose an outcome version.
- *If this is achieved, would the customer call the project a success?*
- It can be measured by one primary KPI.

## Record

1. Propose KPIs from the evidence answers: exactly one primary, the secondary ones that add nuance,
   and guardrails (cost, errors, satisfaction) that must not get worse. Define each with the `kpi`
   skill; it writes the recipe and measures the baseline.
2. Record the North Star once the user agrees on the wording:
   `fde-workflow northstar set --statement "..." --beneficiary "..." --problem "..."
   --non-goal "..." --primary-kpi <id>`. Draft from `adopt`: update it the same way, then
   `fde-workflow northstar confirm` when the user confirms it.
3. Agree the gate criteria of the current stage (see the `fde-workflow` skill, *Stage*).
4. Finish with `fde-workflow status` and a short summary.

## Rules

- Never record a North Star, KPI or target the user has not agreed to.
- A confirmed North Star only changes with a reason and the sponsor's approval
  (`--reason`, `--approved-by`).
```

- [ ] **Step 3: Validate the plugin**

Run: `make plugin-check`
Expected: `claude plugin validate --strict plugin` passes; stub and hook tests pass.

- [ ] **Step 4: Commit**

```bash
git add plugin/skills/adopt/SKILL.md plugin/skills/discovery/SKILL.md
git commit -m "feat(plugin): add the adopt and discovery skills"
```

### Task 16: KPI and path skills

**Files:**
- Create: `plugin/skills/kpi/SKILL.md`, `plugin/skills/path/SKILL.md`

**Interfaces:**
- Consumes: `fde-workflow kpi add|update|measure`, `path add|update|move|link|confirm`, `context`.

- [ ] **Step 1: Write the kpi skill** — `plugin/skills/kpi/SKILL.md`

```markdown
---
name: kpi
description: 'Define the KPIs of a customer project and measure them with reproducible recipes: baselines (historical or late), current values, and the measurement that validates a path, always recording external factors. Use it when the user wants to define, change or measure a KPI or metric, asks for a baseline, asks "how is KPI X doing?", or when a path is ready to be measured.'
allowed-tools:
  - Bash(fde-workflow status)
  - Bash(fde-workflow context)
---

# KPIs: define and measure

Read `../fde-workflow/references/framework.md` (relative to this skill's directory) first.

## Define a KPI

1. Agree with the user, one question at a time: what it measures and its formula, the data source,
   the unit, which direction is better, a **numeric target** (for a guardrail, the worst
   acceptable value), the window (e.g. `28d`) and the kind (`primary`, `secondary`, `guardrail`).
2. Write the **recipe** in `.fde/measures/<kpi-id>.<ext>`; it fixes how the KPI is measured, so
   the baseline and later measurements are comparable:
   - `script` (e.g. `.sh`, `.py`): an executable that prints **one number** on stdout and reads
     the window from `FDE_WINDOW_START` and `FDE_WINDOW_END` (ISO dates). Make it executable.
   - `query` (e.g. `.sql`): a query with `{{window_start}}` and `{{window_end}}` placeholders, for
     a tool that has access to the data (an MCP server or a database client).
   - `manual` (`.md`): a written procedure a person follows, saying where the value comes from.
   Show the recipe to the user before saving it.
3. Record it: `fde-workflow kpi add <id> --name "..." --kind <kind> --definition "..."
   --source "..." --unit "..." --direction increase|decrease --target <n> --window <n>d
   --recipe-type <type> --recipe-file measures/<file>`.
4. Changing a target later needs a reason and the sponsor's approval:
   `fde-workflow kpi update <id> --target <n> --reason "..." --approved-by "..."`.

## Measure a KPI

1. Run `fde-workflow kpi measure <id> [--window-end YYYY-MM-DD]` without a value: it prints the
   recipe for that window, or the script it would run. It records nothing.
2. Take the measurement **by following the recipe, never another way**:
   - `script`: ask the user before running it, then
     `fde-workflow kpi measure <id> --run [--window-end ...]`.
   - `query`: run the printed query with a tool that can reach the data. If none can, ask the user
     to run it and give you the result.
   - `manual`: walk the user through the procedure and ask for the value and where it came from.
3. **Always ask about external factors**: anything outside the project that may have moved the
   value (seasonality, another initiative, an outage, a pricing change). Record "none known" only
   if the user says so.
4. Record it: `fde-workflow kpi measure <id> --value <n> --source "..." --factors "..."
   [--window-end ...]` (`--run` already records script results; add `--factors` to that call).

## Baselines

A baseline is the first measurement, recorded with `--baseline historical|late`:
- **historical**: the window ends **before the work that should move the KPI started**; use
  `--window-end` with a date before that start (ask for it, or take it from the earliest
  linked artifact). Preferred, when the data exists.
- **late**: the data from before is gone, so it is measured now. Tell the user that reports will
  say so, because it misses any impact achieved before it.
Explain the choice to the user and let them decide. When the recipe changed after the baseline
(`[K4]`), measure the baseline again with the new recipe.

## Rules

- Never invent or estimate a value. No access to the data means asking the user.
- Never edit `.fde/measurements.jsonl` by hand; only `fde-workflow kpi measure` writes it.
- Report every result against baseline and target, with its external factors.
```

- [ ] **Step 2: Write the path skill** — `plugin/skills/path/SKILL.md`

```markdown
---
name: path
description: 'Manage the paths of a customer project, the hypotheses that move its KPIs: check that new work (a feature, spec, plan or brainstorm in any methodology, such as superpowers or spec-kit) serves a path, open, link, measure, validate or discard paths, and confirm inferred ones. Use it when the user starts new work or a new feature, asks whether something is aligned with the North Star, says "let us open a path", "this is built", "we are dropping X", or when a spec or plan was just written.'
allowed-tools:
  - Bash(fde-workflow status)
  - Bash(fde-workflow context)
---

# Paths: hypotheses that move the KPIs

Read `../fde-workflow/references/framework.md` (relative to this skill's directory) first, then
run `fde-workflow context`.

## Alignment check for new work

When the user starts new work, before or alongside their own methodology (e.g. a superpowers
brainstorm), ask which path it serves, proposing the most likely one from `context`:
- **An existing path:** continue; link the spec, plan or PR once it exists.
- **A new path:** open it (below). It needs a KPI it should move.
- **None:** say plainly that it is outside the direction (drift) and let the user decide whether
  to do it anyway. Do not block the work.
Then hand over to the user's methodology: this skill never writes specs or plans.

## Open a path

1. Phrase it as a hypothesis with the user: *"If we do X, we expect KPI Y to go from A to B."*
   Every targeted KPI must exist (define it first with the `kpi` skill) and have a baseline before
   the work starts.
2. `fde-workflow path add <id> --hypothesis "..." --expects <kpi>=<value> --reason "..."`
   (repeat `--expects` per KPI).

## Link execution work

`fde-workflow path link <path-id> <file-or-url>...` for specs, plans, PRs and issues. Artifacts
from before the framework: `fde-workflow path link --pre-framework <file>...`.

## Life cycle

`fde-workflow path move <id> <status> --reason "..."`:
- `active` when work starts; `measuring` when it is built and in use.
- In `measuring`, measure its KPIs with the `kpi` skill. Then:
  - `validated` only when a measurement taken after the path became active shows the effect;
    otherwise the CLI refuses ([P2]). Never move a path to validated because it is built,
    deployed or "looks good": measure first.
  - `discarded` when the evidence says no or priorities change, with what it taught us:
    `--learning "..."`. Discarded paths stay as learning.
- Add `--approved-by "..."` when the sponsor took the decision.

## Inferred paths

Paths from the `adopt` skill are unconfirmed hypotheses. Review each with the user: confirm it
(`fde-workflow path confirm <id>`), correct it (`fde-workflow path update <id> ...`), or discard it.

## Rules

- Expected values and hypotheses come from the user; never invent them.
- Never edit `.fde/direction.yaml` by hand.
```

- [ ] **Step 3: Validate the plugin**

Run: `make plugin-check`
Expected: `claude plugin validate --strict plugin` passes; stub and hook tests pass.

- [ ] **Step 4: Commit**

```bash
git add plugin/skills/kpi/SKILL.md plugin/skills/path/SKILL.md
git commit -m "feat(plugin): add the kpi and path skills"
```

### Task 17: Evals for the direction skills

**Files:**
- Modify (replace): `plugin/evals/stub/fde-workflow`, `plugin/evals/stub/test_stub.sh`
- Create: four cases in `plugin/evals/`, each with `case.yaml`, `fixture.sh` (mode 755),
  `prompt.md` and `graders/*.md`

**Interfaces:**
- Consumes: the skills of Tasks 14–16. The stub fakes every command they call, per
  `EVAL_SCENARIO`: `fresh`, `kpi-no-baseline`, `path-measuring`, `brownfield` (plus the existing
  `ready`, `missing`, `not-ready`).

- [ ] **Step 1: Extend the stub tests** — `plugin/evals/stub/test_stub.sh`

```sh
#!/bin/sh
# Tests for the fake fde-workflow CLI used by the plugin evals.
# Run: sh plugin/evals/stub/test_stub.sh
set -u
STUB="$(cd "$(dirname "$0")" && pwd)/fde-workflow"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cd "$WORK" || exit 1
export EVAL_STUB_LOG="$WORK/calls.log"
failures=0

check() {  # check NAME EXPECTED_EXIT EXPECTED_SUBSTRING SCENARIO ARGS...
  name=$1 want_exit=$2 want_text=$3 scenario=$4
  shift 4
  out=$(EVAL_SCENARIO="$scenario" sh "$STUB" "$@" 2>&1)
  got_exit=$?
  if [ "$got_exit" -ne "$want_exit" ] || ! printf '%s' "$out" | grep -qF -- "$want_text"; then
    echo "FAIL: $name (exit $got_exit, want $want_exit; want text: $want_text)"
    printf '%s\n' "$out" | sed 's/^/    /'
    failures=$((failures + 1))
  else
    echo "ok: $name"
  fi
}

check "version" 0 "fde-workflow 0.1.0" ready --version
check "missing is command not found" 127 "command not found" missing --version
check "doctor ready" 0 "Ready." ready doctor
check "doctor not ready" 1 "Not ready: 1 problem(s)." not-ready doctor
check "unknown command" 2 "No such command" ready nope
check "no .fde before adoption" 1 "No .fde/" brownfield status
check "fresh status" 0 "No North Star yet" fresh status
check "detect lists specs" 0 "answer-suggestions-design.md" brownfield detect
check "measure shows the recipe" 0 "Take the measurement" kpi-no-baseline kpi measure resolution-time
check "measure records a value" 0 "Recorded." kpi-no-baseline kpi measure resolution-time --value 45 --source s
check "validated needs evidence" 1 "[P2]" path-measuring path move auto-triage validated --reason r
check "validate lists warnings" 0 "[K3]" kpi-no-baseline validate
if grep -qF "fde-workflow doctor" "$EVAL_STUB_LOG"; then
  echo "ok: calls are logged"
else
  echo "FAIL: calls are logged"; failures=$((failures + 1))
fi

if [ "$failures" -eq 0 ]; then echo "all stub tests passed"; else echo "$failures failure(s)"; exit 1; fi
```

- [ ] **Step 2: Run them to see them fail**

Run: `sh plugin/evals/stub/test_stub.sh`
Expected: `FAIL` for the new scenarios and exit 1.

- [ ] **Step 3: Replace the stub** — `plugin/evals/stub/fde-workflow`

```sh
#!/bin/sh
# Fake fde-workflow CLI for the plugin evals: never does real work. EVAL_SCENARIO selects
# the behaviour; every call is appended to EVAL_STUB_LOG.
#   ready | missing | not-ready   setup scenarios (CLI readiness)
#   fresh                         .fde/ just initialised: no North Star, no KPIs
#   kpi-no-baseline               North Star and a primary KPI with a query recipe, no baseline
#   path-measuring                path auto-triage built and in measuring, no measurement since
#   brownfield                    no .fde/ yet; superpowers specs and plans exist
scenario="${EVAL_SCENARIO:-ready}"
printf 'fde-workflow %s\n' "$*" >> "${EVAL_STUB_LOG:-./stub-calls.log}" 2>/dev/null || true

if [ "$scenario" = missing ]; then
  echo "sh: fde-workflow: command not found" >&2
  exit 127
fi

no_fde() {
  echo "Error: No .fde/ in $(pwd): run \`fde-workflow init\` (or the adopt skill) first." >&2
  exit 1
}

status() {
  case "$scenario" in
    fresh)
      printf '%s\n' "Project: acme-support" "North Star: not defined" \
        "Stage: discovery since 2026-10-12" "KPIs: none" "Paths: none" "Issues:" \
        "  ! [N1] No North Star yet: define it with the discovery skill." \
        "  ! [S1] Stage discovery has no gate criteria: agree them with the sponsor now, not when leaving the stage." ;;
    kpi-no-baseline)
      printf '%s\n' "Project: acme-support · sponsor Jane Doe" \
        "North Star: ACME customers resolve their issues without waiting for an agent" \
        "  Primary KPI: resolution-time" "Stage: discovery since 2026-10-01" \
        "  Gate: North Star agreed and every KPI has a baseline" "KPIs:" \
        "  resolution-time (primary): no baseline → target ≤ 30 min" "Paths: none" "Issues:" \
        "  ! [K3] KPI resolution-time has no baseline: measure it before work that should move it starts." ;;
    path-measuring)
      printf '%s\n' "Project: acme-support · sponsor Jane Doe" \
        "North Star: ACME customers resolve their issues without waiting for an agent" \
        "  Primary KPI: resolution-time" "Stage: mvp since 2026-10-01" \
        "  Gate: Primary KPI measured over 2 weeks of real use" "KPIs:" \
        "  resolution-time (primary): baseline 45 min (historical) → target ≤ 30 min" "Paths:" \
        "  auto-triage [measuring]: If tickets are classified on arrival, median resolution time drops 20% (resolution-time → 36)" \
        "Issues:" \
        "  ! [S3] Primary KPI resolution-time has no measurement since entering mvp on 2026-10-01." ;;
    brownfield) no_fde ;;
    *) no_fde ;;
  esac
}

case "${1:-}" in
  --version) echo "fde-workflow 0.1.0" ;;
  doctor)
    echo "✓ Python 3.13.2"
    if [ "$scenario" = not-ready ]; then
      echo "✗ Example check failed: follow the hint printed on this line"
      echo "Not ready: 1 problem(s)."
      exit 1
    fi
    echo "✓ No .fde/ here yet: the adopt skill sets one up"
    echo "Ready."
    ;;
  status) status ;;
  context)
    if [ "$scenario" = brownfield ] || [ "$scenario" = ready ] || [ "$scenario" = not-ready ]; then no_fde; fi
    echo "FDE direction of this repository (.fde/). Keep the work aligned with it; change it only through the fde-workflow skills and CLI."
    echo
    status
    ;;
  validate)
    status | sed -n 's/^  \([!✗]\)/\1/p'
    echo "Valid with 1 warning(s)."
    ;;
  detect)
    if [ "$scenario" = brownfield ]; then
      cat <<'JSON'
{
  "root": ".",
  "fde_initialised": false,
  "methodology": "superpowers",
  "globs": ["docs/superpowers/specs/**", "docs/superpowers/plans/**"],
  "readme": "README.md",
  "deployment_signals": ["Dockerfile", ".github/workflows/deploy.yml"],
  "artifacts": [
    {"path": "docs/superpowers/plans/2026-08-20-auto-triage.md", "first_commit": "2026-08-20", "linked_to": null},
    {"path": "docs/superpowers/specs/2026-08-18-auto-triage-design.md", "first_commit": "2026-08-18", "linked_to": null},
    {"path": "docs/superpowers/specs/2026-09-10-answer-suggestions-design.md", "first_commit": "2026-09-10", "linked_to": null}
  ]
}
JSON
    else
      echo '{"root": ".", "fde_initialised": true, "methodology": "superpowers", "globs": [], "readme": null, "deployment_signals": [], "artifacts": []}'
    fi
    ;;
  kpi)
    if [ "${2:-}" = measure ] && ! printf '%s' "$*" | grep -q -- '--value'; then
      printf '%s\n' "query recipe of resolution-time, window 2026-09-15 to 2026-10-12:" "" \
        "select median(minutes_to_resolution) from zendesk.tickets" \
        "where solved_at between '2026-09-15' and '2026-10-12'" "" \
        "Take the measurement, then record it with --value N --source TEXT."
    else
      echo "Recorded."
    fi
    ;;
  path)
    if [ "${2:-}" = move ] && [ "${4:-}" = validated ] && [ "$scenario" = path-measuring ]; then
      echo "Error: Not saved: the change breaks the framework's rules:" >&2
      echo "  [P2] Path auto-triage cannot be validated without evidence: it needs a measurement of resolution-time taken after it became active." >&2
      exit 1
    fi
    echo "Saved."
    ;;
  init|northstar|stage|decision) echo "Saved." ;;
  hook) ;;
  ""|--help|-h) echo "Usage: fde-workflow [OPTIONS] COMMAND [ARGS]...  Commands: doctor init detect validate status context northstar kpi path stage decision hook" ;;
  *) echo "Error: No such command '$1'." >&2; exit 2 ;;
esac
```

- [ ] **Step 4: Run the stub tests**

Run: `sh plugin/evals/stub/test_stub.sh`
Expected: `all stub tests passed`.

- [ ] **Step 5: Write the case `discovery-reframes-a-solution`** (then `chmod 755 plugin/evals/discovery-reframes-a-solution/fixture.sh`)

`plugin/evals/discovery-reframes-a-solution/case.yaml`

```yaml
schema_version: "1.1"
name: discovery-reframes-a-solution
context:
  scaffold_script: fixture.sh
```

`plugin/evals/discovery-reframes-a-solution/fixture.sh`

```sh
#!/usr/bin/env bash
# Workspace for the plugin evals. run.sh puts the fake fde-workflow first on PATH; the
# eval sandbox only reads and executes files inside the workspace, so the stub is copied into ./bin.
set -eu
stub=$(command -v fde-workflow)
grep -q "Fake fde-workflow CLI" "$stub" || { echo "refusing: $stub is not the fake fde-workflow" >&2; exit 1; }
mkdir -p bin
cp "$stub" bin/fde-workflow && chmod 755 bin/fde-workflow
```

`plugin/evals/discovery-reframes-a-solution/prompt.md`

```markdown
---
max_turns: 20
allowed_tools: [Read, Glob, Grep, Bash, Skill, AskUserQuestion]
append_system_prompt: "Eval environment: the fde-workflow CLI is installed at ./bin/fde-workflow (relative to the working directory). Run `./bin/fde-workflow` instead of `fde-workflow`."
env:
  EVAL_SCENARIO: fresh
---

Let's define the North Star of this project: build an AI chatbot for ACME's support team.
```

`plugin/evals/discovery-reframes-a-solution/graders/asks-for-the-outcome.md`

```markdown
---
type: regex
pattern: '(?i)(outcome|resultado|for whom|para qui[eé]n|what .*for|para qu[eé])'
---
```

`plugin/evals/discovery-reframes-a-solution/graders/does-not-record-a-solution.md`

```markdown
---
type: tool_used
tool: Bash
input_match: 'northstar set'
min: 0
max: 0
---
```

`plugin/evals/discovery-reframes-a-solution/graders/skill-fired.md`

```markdown
---
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?discovery"'
---
```

- [ ] **Step 6: Write the case `kpi-baseline-declares-type-and-factors`** (then `chmod 755 plugin/evals/kpi-baseline-declares-type-and-factors/fixture.sh`)

`plugin/evals/kpi-baseline-declares-type-and-factors/case.yaml`

```yaml
schema_version: "1.1"
name: kpi-baseline-declares-type-and-factors
context:
  scaffold_script: fixture.sh
```

`plugin/evals/kpi-baseline-declares-type-and-factors/fixture.sh`

```sh
#!/usr/bin/env bash
# Workspace for the plugin evals. run.sh puts the fake fde-workflow first on PATH; the
# eval sandbox only reads and executes files inside the workspace, so the stub is copied into ./bin.
set -eu
stub=$(command -v fde-workflow)
grep -q "Fake fde-workflow CLI" "$stub" || { echo "refusing: $stub is not the fake fde-workflow" >&2; exit 1; }
mkdir -p bin
cp "$stub" bin/fde-workflow && chmod 755 bin/fde-workflow
```

`plugin/evals/kpi-baseline-declares-type-and-factors/prompt.md`

```markdown
---
max_turns: 20
allowed_tools: [Read, Glob, Grep, Bash, Skill, AskUserQuestion]
append_system_prompt: "Eval environment: the fde-workflow CLI is installed at ./bin/fde-workflow (relative to the working directory). Run `./bin/fde-workflow` instead of `fde-workflow`."
env:
  EVAL_SCENARIO: kpi-no-baseline
---

Measure the baseline of resolution-time.
```

`plugin/evals/kpi-baseline-declares-type-and-factors/graders/asks-about-external-factors.md`

```markdown
---
type: regex
pattern: '(?i)(external factor|factores externos)'
---
```

`plugin/evals/kpi-baseline-declares-type-and-factors/graders/explains-the-baseline-type.md`

```markdown
---
type: regex
pattern: '(?i)(historical|hist[oó]rico).*(late|tard[ií]o)|(late|tard[ií]o).*(historical|hist[oó]rico)'
---
```

`plugin/evals/kpi-baseline-declares-type-and-factors/graders/invents-no-value.md`

```markdown
---
type: tool_used
tool: Bash
input_match: 'kpi measure .*--value'
min: 0
max: 0
---
```

`plugin/evals/kpi-baseline-declares-type-and-factors/graders/shows-the-recipe.md`

```markdown
---
type: tool_used
tool: Bash
input_match: 'kpi measure resolution-time'
min: 1
---
```

`plugin/evals/kpi-baseline-declares-type-and-factors/graders/skill-fired.md`

```markdown
---
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?kpi"'
---
```

- [ ] **Step 7: Write the case `path-validates-only-with-evidence`** (then `chmod 755 plugin/evals/path-validates-only-with-evidence/fixture.sh`)

`plugin/evals/path-validates-only-with-evidence/case.yaml`

```yaml
schema_version: "1.1"
name: path-validates-only-with-evidence
context:
  scaffold_script: fixture.sh
```

`plugin/evals/path-validates-only-with-evidence/fixture.sh`

```sh
#!/usr/bin/env bash
# Workspace for the plugin evals. run.sh puts the fake fde-workflow first on PATH; the
# eval sandbox only reads and executes files inside the workspace, so the stub is copied into ./bin.
set -eu
stub=$(command -v fde-workflow)
grep -q "Fake fde-workflow CLI" "$stub" || { echo "refusing: $stub is not the fake fde-workflow" >&2; exit 1; }
mkdir -p bin
cp "$stub" bin/fde-workflow && chmod 755 bin/fde-workflow
```

`plugin/evals/path-validates-only-with-evidence/prompt.md`

```markdown
---
max_turns: 20
allowed_tools: [Read, Glob, Grep, Bash, Skill, AskUserQuestion]
append_system_prompt: "Eval environment: the fde-workflow CLI is installed at ./bin/fde-workflow (relative to the working directory). Run `./bin/fde-workflow` instead of `fde-workflow`."
env:
  EVAL_SCENARIO: path-measuring
---

auto-triage is built and deployed and the agents love it. Mark the path as validated.
```

`plugin/evals/path-validates-only-with-evidence/graders/asks-for-a-measurement.md`

```markdown
---
type: regex
pattern: '(?i)(measur|medi)'
---
```

`plugin/evals/path-validates-only-with-evidence/graders/does-not-validate.md`

```markdown
---
type: tool_used
tool: Bash
input_match: 'path move auto-triage validated'
min: 0
max: 0
---
```

`plugin/evals/path-validates-only-with-evidence/graders/skill-fired.md`

```markdown
---
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?path"'
---
```

- [ ] **Step 8: Write the case `adopt-infers-an-unconfirmed-draft`** (then `chmod 755 plugin/evals/adopt-infers-an-unconfirmed-draft/fixture.sh`)

`plugin/evals/adopt-infers-an-unconfirmed-draft/case.yaml`

```yaml
schema_version: "1.1"
name: adopt-infers-an-unconfirmed-draft
context:
  scaffold_script: fixture.sh
```

`plugin/evals/adopt-infers-an-unconfirmed-draft/fixture.sh`

```sh
#!/usr/bin/env bash
# Workspace for the plugin evals. run.sh puts the fake fde-workflow first on PATH; the
# eval sandbox only reads and executes files inside the workspace, so the stub is copied into ./bin.
set -eu
stub=$(command -v fde-workflow)
grep -q "Fake fde-workflow CLI" "$stub" || { echo "refusing: $stub is not the fake fde-workflow" >&2; exit 1; }
mkdir -p bin
cp "$stub" bin/fde-workflow && chmod 755 bin/fde-workflow
mkdir -p docs/superpowers/specs docs/superpowers/plans
cat > README.md <<'MD'
# acme-support-ai
AI assistance for ACME's support agents: ticket triage and answer suggestions.
MD
printf '# Auto-triage design\nClassify incoming tickets so they reach the right queue at once.\n' > docs/superpowers/specs/2026-08-18-auto-triage-design.md
printf '# Auto-triage plan\n- [x] Classifier\n- [x] Routing\n' > docs/superpowers/plans/2026-08-20-auto-triage.md
printf '# Answer suggestions design\nSuggest replies to agents from past resolved tickets.\n' > docs/superpowers/specs/2026-09-10-answer-suggestions-design.md
```

`plugin/evals/adopt-infers-an-unconfirmed-draft/prompt.md`

```markdown
---
max_turns: 20
allowed_tools: [Read, Glob, Grep, Bash, Skill, AskUserQuestion]
append_system_prompt: "Eval environment: the fde-workflow CLI is installed at ./bin/fde-workflow (relative to the working directory). Run `./bin/fde-workflow` instead of `fde-workflow`."
env:
  EVAL_SCENARIO: brownfield
---

I want to start using the FDE framework in this existing project.
```

`plugin/evals/adopt-infers-an-unconfirmed-draft/graders/never-records-unmarked-inferences.md`

```markdown
---
type: tool_used
tool: Bash
input_match: '(northstar set|path add|stage set)(?!.*--inferred)'
min: 0
max: 0
---
```

`plugin/evals/adopt-infers-an-unconfirmed-draft/graders/presents-a-draft.md`

```markdown
---
type: regex
pattern: '(?i)(hypothes|hip[oó]tesis|inferred|inferid|draft|borrador|unconfirmed|sin confirmar)'
---
```

`plugin/evals/adopt-infers-an-unconfirmed-draft/graders/runs-detect.md`

```markdown
---
type: tool_used
tool: Bash
input_match: 'fde-workflow detect'
min: 1
---
```

`plugin/evals/adopt-infers-an-unconfirmed-draft/graders/skill-fired.md`

```markdown
---
type: tool_used
tool: Skill
input_match: '"skill"\s*:\s*"(?:[\w-]+:)?adopt"'
---
```

- [ ] **Step 9: Validate**

Run: `make plugin-check`
Expected: passes (the eval files are data; `claude plugin validate --strict plugin` accepts them).

- [ ] **Step 10: Commit**

```bash
git add plugin/evals
git commit -m "test(plugin): add evals for the direction skills"
```

- [ ] **Step 11: Ask the owner before running the evals**

`plugin/evals/run.sh` uses model calls on the owner's account. Ask; only with an explicit yes run
`sh plugin/evals/run.sh --runs 1` and report the per-grader results. Never run it in CI.

### Task 18: Documentation and descriptions

**Files:**
- Modify: `README.md`, `plugin/README.md`, `cli/README.md`, `plugin/.claude-plugin/plugin.json`,
  `.claude-plugin/marketplace.json`, `cli/pyproject.toml`, `catalog-info.yaml`

- [ ] **Step 1: Replace the template description everywhere**

The description `Marketplace with a plugin for working with FDE frameworks, best practices and
workflow conventions for FDE roles.` appears in `plugin/.claude-plugin/plugin.json`,
`.claude-plugin/marketplace.json` (twice), `cli/pyproject.toml`, `catalog-info.yaml` and the first
paragraph of `README.md`. Replace each with:

```
Direction framework for FDE customer projects: North Star, KPIs with baselines, paths, stages and decisions, on top of any execution methodology.
```

Also add `"fde"`, `"north-star"`, `"kpi"` to `keywords` in `plugin/.claude-plugin/plugin.json`.

- [ ] **Step 2: Replace the plugin README** — `plugin/README.md`

````markdown
# fde-workflow plugin for Claude Code

Direction framework for FDE customer projects: a North Star, KPIs with baselines, paths, stages
and decisions, on top of any execution methodology (superpowers, spec-kit or none).

## Install

In a Claude Code session:

```
/plugin marketplace add mjfura/fde-workflow
/plugin install fde-workflow@fde-workflow
```

Then ask Claude to set it up, or run `/fde-workflow:setup`.

## Skills

| Skill | Use it for |
|---|---|
| `fde-workflow:fde-workflow` | Where the project stands and the next action; stage gates |
| `fde-workflow:adopt` | Set up the framework in a new or existing repository |
| `fde-workflow:discovery` | Define or confirm the North Star, non-goals, sponsor and KPIs |
| `fde-workflow:kpi` | Define KPIs with measurement recipes; measure baselines and progress |
| `fde-workflow:path` | Check new work against the paths; open, link, validate or discard paths |
| `fde-workflow:setup` | Install and check what the plugin needs: the `fde-workflow` CLI |

Claude picks them automatically; you can also call them as slash commands.

## Hooks

`SessionStart` adds the repository's direction (North Star, stage, KPIs, live paths, pending
issues) to every session in a repository with `.fde/`. It does nothing elsewhere, or when the CLI
is not installed.

## Development

See the [repository README](../README.md) and the
[design](../docs/superpowers/specs/2026-10-12-fde-direction-framework-design.md).
````

- [ ] **Step 3: Replace the CLI README** — `cli/README.md`

````markdown
# fde-workflow-cli

Command line tool of the `fde-workflow` Claude Code plugin: it reads and writes a repository's
FDE direction in `.fde/` and enforces the framework's rules.

```sh
uv tool install fde-workflow-cli    # or: pipx install fde-workflow-cli
fde-workflow --version
fde-workflow doctor                 # checks that everything is ready
```

| Command | Purpose |
|---|---|
| `init`, `detect` | Set up `.fde/`; inspect a repository's methodology and artifacts |
| `status`, `context`, `validate` | Summaries for people and for Claude; rule checks |
| `northstar set\|confirm` | The North Star |
| `kpi add\|update\|measure` | KPIs, their recipes and measurements |
| `path add\|update\|move\|link\|confirm` | Paths and their links to execution work |
| `stage set\|confirm\|criteria\|decide` | The project stage and its gates |
| `decision add` | Other direction decisions |
| `hook session-start` | Entry point of the plugin's SessionStart hook |

Run `fde-workflow <command> --help` for the options. Requires Python 3.13 or newer. Source and
plugin: https://github.com/mjfura/fde-workflow
````

- [ ] **Step 4: Update the repository README**

In `README.md`, in the *Layout* table, add after the `docs/releasing.md` row:

```markdown
| `docs/superpowers/` | Design specs and implementation plans |
```

- [ ] **Step 5: Run every check**

Run: `make check`
Expected: all checks pass.

- [ ] **Step 6: Commit**

```bash
git add README.md plugin/README.md cli/README.md plugin/.claude-plugin/plugin.json .claude-plugin/marketplace.json cli/pyproject.toml catalog-info.yaml
git commit -m "docs: describe the direction framework plugin and cli"
```

- [ ] **Step 7: Try it on a scratch repository**

```bash
tmp=$(mktemp -d) && cd "$tmp" && git init -q
F="poetry -C $OLDPWD/cli run fde-workflow"
$F init && $F status && $F validate && $F context --brief && $F doctor
cd "$OLDPWD" && rm -rf "$tmp"
```
Expected: `init` creates `.fde/`; `validate` reports the N1 and S1 warnings and exits 0; `doctor`
ends with `Ready.`. Then try the plugin interactively with `claude --plugin-dir ./plugin` in a
scratch repository and ask "I want to use the FDE framework here".
