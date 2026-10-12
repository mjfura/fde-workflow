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
    reason: Annotated[
        str | None,
        typer.Option(help="Why a new baseline replaces one measured with the same recipe."),
    ] = None,
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
        if end > clock.today():
            raise FdeError(f"--window-end {end} is in the future.")
        fingerprint = recipes.fingerprint(store.dir, kpi.recipe)
        if fingerprint is None:
            raise FdeError(f"Recipe .fde/{kpi.recipe.file} does not exist: write it first.")
        previous = rules.latest_baseline(store.measurements(), kpi.id)
        rebaseline_reason: str | None = None
        if baseline is not None and previous is not None:
            if previous.recipe_sha256 == fingerprint:
                rebaseline_reason = require(
                    reason, "--reason", "to replace a baseline measured with the same recipe"
                )
            else:
                rebaseline_reason = reason or "The recipe changed after the previous baseline."
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
        if rebaseline_reason is not None:
            record(
                store,
                DecisionType.BASELINE_CHANGE,
                f"New {baseline} baseline of {kpi.id}: {number(value)}",
                rebaseline_reason,
                refs=[kpi.id],
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
