"""`fde-workflow portfolio`: every repository on this machine that uses the framework."""

from pathlib import Path
from typing import Annotated

import typer

from fde_workflow_cli import registry, rules, summary
from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.store import Store

app = typer.Typer(
    help="Every repository on this machine that uses the framework.",
    invoke_without_command=True,
)


def project_line(root: Path) -> str:
    store = Store(root)
    if not store.exists():
        return f"{root} · no .fde/ any more: `fde-workflow portfolio forget {root}`"
    try:
        direction = store.load()
        measurements = store.measurements()
    except FdeError as error:
        return f"{root} · .fde/ cannot be read: {str(error).splitlines()[0]}"
    issues = rules.check(direction, measurements, store.dir)
    errors = sum(issue.level == "error" for issue in issues)
    primary_id = direction.north_star.primary_kpi if direction.north_star else None
    primary = direction.kpi(primary_id) if primary_id else None
    kpi = summary.kpi_line(primary, measurements) if primary else "no primary KPI"
    due = len(rules.due_kpis(direction, measurements))
    stage = str(direction.stage.current) + (" (on hold)" if direction.stage.on_hold else "")
    return (
        f"{summary.clean(direction.project.name)} · {stage} · {kpi} · {due} due · "
        f"{errors} error(s), {len(issues) - errors} warning(s) · {root}"
    )


@app.callback()
def show(ctx: typer.Context) -> None:
    """One line per project: stage, primary KPI, due KPIs, errors and warnings."""
    if ctx.invoked_subcommand:
        return
    projects = registry.registered()
    if not projects:
        typer.echo("No projects registered yet: run `fde-workflow init` in a repository.")
    for root in projects:
        typer.echo(project_line(root))


@app.command()
def forget(
    path: Annotated[Path, typer.Argument(help="The repository to remove from the portfolio.")],
) -> None:
    """Remove a repository from the portfolio (its .fde/ is not touched)."""
    if registry.forget(path):
        typer.echo(f"Forgot {path.resolve()}.")
    else:
        typer.echo(f"{path.resolve()} was not in the portfolio.")
