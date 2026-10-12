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
