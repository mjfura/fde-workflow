"""`fde-workflow hook`: entry points of the plugin's hooks. A hook never fails a session."""

import json
import os
import sys
from pathlib import Path

import typer

from fde_workflow_cli import rules, summary
from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.store import Store, locate

app = typer.Typer(help="Entry points of the Claude Code plugin hooks.", no_args_is_help=True)


def session_context(payload: str) -> str | None:
    """The context for a new session, or None when the repository has no .fde/."""
    try:
        data = json.loads(payload) if payload.strip() else {}
    except json.JSONDecodeError:
        data = {}
    cwd = data.get("cwd") if isinstance(data, dict) else None
    start = Path(cwd) if isinstance(cwd, str) else Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    store = Store(locate(start))
    if not store.exists():
        return None
    try:
        direction = store.load()
        measurements = store.measurements()
    except FdeError as error:
        return (
            f"{summary.CONTEXT_HEADER}\n\n.fde/ cannot be read: {error}\n"
            "Run `fde-workflow validate`."
        )
    issues = rules.check(direction, measurements, store.dir)
    return summary.context(direction, measurements, issues, brief=True)


@app.command("session-start")
def session_start() -> None:
    """Print the direction as SessionStart context (reads the hook's JSON on stdin)."""
    try:
        text = session_context(sys.stdin.read())
    except Exception as error:  # a hook must never interrupt the session
        typer.echo(f"fde-workflow hook: {error}", err=True)
        return
    if text:
        output = {
            "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": text}
        }
        typer.echo(json.dumps(output))
