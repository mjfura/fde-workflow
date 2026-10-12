"""Commands of the fde-workflow command line tool."""

from importlib.metadata import version
from typing import Annotated

import typer

from fde_workflow_cli import doctor as checks

COMMAND = "fde-workflow"
DIST_NAME = "fde-workflow-cli"

app = typer.Typer(no_args_is_help=True, add_completion=False)


def _print_version(value: bool) -> None:
    if value:
        typer.echo(f"{COMMAND} {version(DIST_NAME)}")
        raise typer.Exit()


@app.callback()
def main(
    show_version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_print_version,
            is_eager=True,
            help="Show the version and exit.",
        ),
    ] = False,
) -> None:
    """Command line tool of the fde-workflow Claude Code plugin."""


@app.command()
def doctor() -> None:
    """Check that fde-workflow is ready to use."""
    results = checks.run_checks()
    for result in results:
        typer.echo(f"{'✓' if result.ok else '✗'} {result.message}")
    problems = sum(not result.ok for result in results)
    if problems:
        typer.echo(f"Not ready: {problems} problem(s).")
        raise typer.Exit(1)
    typer.echo("Ready.")
