"""Shared helpers for the tests: a fixed today, a CLI runner and a sample direction."""

import datetime as dt
import json
from pathlib import Path

from typer.testing import CliRunner, Result

from fde_workflow_cli.main import app
from fde_workflow_cli.model import Direction

TODAY = dt.date(2026, 10, 12)
QUERY = (
    "select median(minutes) from tickets\n"
    "where closed between '{{window_start}}' and '{{window_end}}'\n"
)

runner = CliRunner()


def cli(*args: str, stdin: str | None = None) -> Result:
    return runner.invoke(app, list(args), input=stdin)


def ok(*args: str, stdin: str | None = None) -> Result:
    result = cli(*args, stdin=stdin)
    assert result.exit_code == 0, result.output
    return result


def fails(*args: str) -> Result:
    result = cli(*args)
    assert result.exit_code == 1, result.output
    return result


def make_files(repo: Path, *files: str) -> None:
    for relative in files:
        path = repo / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n", encoding="utf-8")


def write_recipe(repo: Path, relative: str, text: str = QUERY, executable: bool = False) -> Path:
    path = repo / ".fde" / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if executable:
        path.chmod(0o755)
    return path


def add_kpi(
    repo: Path, kpi_id: str = "resolution-time", kind: str = "primary", target: str = "30"
) -> None:
    write_recipe(repo, f"measures/{kpi_id}.sql")
    ok(
        "kpi", "add", kpi_id,
        "--name", "Median resolution time",
        "--kind", kind,
        "--definition", "Median minutes from creation to resolution",
        "--source", "Zendesk",
        "--unit", "min",
        "--direction", "decrease",
        "--target", target,
        "--recipe-type", "query",
        "--recipe-file", f"measures/{kpi_id}.sql",
    )  # fmt: skip


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def decisions(repo: Path) -> list[dict[str, object]]:
    return read_jsonl(repo / ".fde" / "decisions.jsonl")


def measurements(repo: Path) -> list[dict[str, object]]:
    return read_jsonl(repo / ".fde" / "measurements.jsonl")


def sample_direction() -> Direction:
    return Direction.model_validate(
        {
            "project": {"name": "acme-support", "customer": "ACME", "sponsor": "Jane Doe"},
            "north_star": {
                "statement": "ACME customers resolve issues without waiting for an agent",
                "primary_kpi": "resolution-time",
            },
            "stage": {"current": "mvp", "entered": "2026-10-01", "gate_criteria": ["2 weeks"]},
            "kpis": [
                {
                    "id": "resolution-time",
                    "name": "Median resolution time",
                    "kind": "primary",
                    "definition": "Median minutes",
                    "source": "Zendesk",
                    "unit": "min",
                    "direction": "decrease",
                    "target": 30,
                    "recipe": {"type": "query", "file": "measures/resolution-time.sql"},
                }
            ],
            "paths": [
                {
                    "id": "auto-triage",
                    "hypothesis": "If tickets are classified on arrival, resolution drops 20%",
                    "expects": {"resolution-time": 36},
                    "status": "active",
                    "activated": "2026-10-03",
                }
            ],
        }
    )
