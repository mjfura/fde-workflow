import datetime as dt
from pathlib import Path

import pytest

from fde_workflow_cli import clock
from tests.helpers import add_kpi, ok


def test_report_command_writes_a_file_and_prints_its_path(fde: Path) -> None:
    add_kpi(fde)
    output = ok("report", "status").output.strip()
    assert output.endswith(".fde/reports/2026-10-12-status.md")
    assert Path(output).read_text().startswith("# Status report: acme-support")


def test_reports_never_overwrite_each_other(fde: Path) -> None:
    first = ok("report", "status").output.strip()
    second = ok("report", "status").output.strip()
    assert first != second
    assert second.endswith("2026-10-12-status-2.md")


def test_status_report_lists_decisions_since_the_previous_one(
    fde: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ok("decision", "add", "--summary", "Before", "--reason", "r")
    ok("report", "status")
    monkeypatch.setattr(clock, "today", lambda: dt.date(2026, 10, 20))
    ok("decision", "add", "--summary", "After", "--reason", "r")
    text = Path(ok("report", "status").output.strip()).read_text()
    assert "## Decisions since 2026-10-12" in text
    assert "After" in text
    closing = Path(ok("report", "close").output.strip()).read_text()
    assert "Before" in closing


def test_regenerating_a_status_report_keeps_the_period(
    fde: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    ok("report", "status")
    monkeypatch.setattr(clock, "today", lambda: dt.date(2026, 10, 20))
    ok("decision", "add", "--summary", "During the week", "--reason", "r")
    ok("report", "status")
    again = Path(ok("report", "status").output.strip()).read_text()
    assert "## Decisions since 2026-10-12" in again
    assert "During the week" in again
