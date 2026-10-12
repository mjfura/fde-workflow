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
