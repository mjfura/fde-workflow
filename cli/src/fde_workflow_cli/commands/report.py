"""`fde-workflow report`: write a status or closing report to `.fde/reports/`."""

import datetime as dt
import re
from pathlib import Path
from typing import Annotated

import typer

from fde_workflow_cli import clock, detect, report, rules
from fde_workflow_cli.commands.common import RootOption, open_store, parse_date, user_errors
from fde_workflow_cli.report import ReportKind

STATUS_FILE = re.compile(r"^(\d{4}-\d{2}-\d{2})-status(?:-\d+)?\.md$")


def previous_status_date(reports: Path, today: dt.date) -> dt.date | None:
    """Date of the latest status report before today: regenerating one keeps its period."""
    dates = [
        date
        for path in reports.glob("*.md")
        if (match := STATUS_FILE.match(path.name))
        and (date := dt.date.fromisoformat(match.group(1))) < today
    ]
    return max(dates, default=None)


def free_path(reports: Path, stem: str) -> Path:
    path, number = reports / f"{stem}.md", 2
    while path.exists():
        path, number = reports / f"{stem}-{number}.md", number + 1
    return path


def report_command(
    kind: Annotated[ReportKind, typer.Argument(help="status (for the sponsor) or close.")],
    since: Annotated[
        str | None,
        typer.Option(help="Decisions from this date (status default: the previous report)."),
    ] = None,
    root: RootOption = None,
) -> None:
    """Write a Markdown report to .fde/reports/ and print its path."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        measurements = store.measurements()
        reports = store.dir / "reports"
        reports.mkdir(exist_ok=True)
        start = parse_date(since, "--since") if since else None
        if start is None and kind is ReportKind.STATUS:
            start = previous_status_date(reports, clock.today())
        text = report.render(
            kind,
            direction,
            measurements,
            store.decisions(),
            rules.check(direction, measurements, store.dir),
            detect.drift(store.root, direction),
            start,
            rules.stale_baselines(direction, measurements, store.dir),
        )
        path = free_path(reports, f"{clock.today()}-{kind}")
        path.write_text(text, encoding="utf-8")
    typer.echo(str(path))
