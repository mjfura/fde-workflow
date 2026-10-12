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
def confirm(
    reason: Annotated[
        str, typer.Option(help="Why it is confirmed.")
    ] = "Confirmed a North Star inferred from existing work.",
    approved_by: Annotated[str, typer.Option("--approved-by", help="Who agreed it.")] = "",
    root: RootOption = None,
) -> None:
    """Mark an inferred North Star as confirmed; records a decision."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        north_star = direction.north_star
        if north_star is None:
            raise FdeError("There is no North Star to confirm.")
        if north_star.confirmed:
            typer.echo("North Star already confirmed.")
            return
        north_star.confirmed = True
        store.save(direction)
        record(
            store,
            DecisionType.NORTH_STAR_CHANGE,
            f"Confirm North Star: {north_star.statement}",
            reason,
            approved_by,
        )
    typer.echo("North Star confirmed.")
