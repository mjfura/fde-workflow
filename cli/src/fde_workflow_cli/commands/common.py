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
