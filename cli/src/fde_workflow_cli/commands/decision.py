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
