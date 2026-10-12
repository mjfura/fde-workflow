"""Commands of the fde-workflow command line tool."""

from importlib.metadata import version
from typing import Annotated

import typer

from fde_workflow_cli import doctor as checks
from fde_workflow_cli.commands import decision, hook, kpi, northstar, path, project, stage

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


app.command()(project.init)
app.command("detect")(project.detect_command)
app.command()(project.validate)
app.command()(project.status)
app.command()(project.context)
app.add_typer(kpi.app, name="kpi")
app.add_typer(northstar.app, name="northstar")
app.add_typer(path.app, name="path")
app.add_typer(stage.app, name="stage")
app.add_typer(decision.app, name="decision")
app.add_typer(hook.app, name="hook")
