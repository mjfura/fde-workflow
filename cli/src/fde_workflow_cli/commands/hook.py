"""`fde-workflow hook`: entry points of the plugin's hooks. A hook never fails a session."""

import json
import os
import sys
from pathlib import Path

import typer

from fde_workflow_cli import detect, registry, rules, summary
from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.store import Store, locate

app = typer.Typer(help="Entry points of the Claude Code plugin hooks.", no_args_is_help=True)


def parse(payload: str) -> dict[str, object]:
    """The hook's JSON input, or an empty mapping when it is missing or malformed."""
    try:
        data = json.loads(payload) if payload.strip() else {}
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def store_for(data: dict[str, object]) -> Store:
    cwd = data.get("cwd")
    start = Path(cwd) if isinstance(cwd, str) else Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    return Store(locate(start))


def session_context(payload: str) -> str | None:
    """The context for a new session, or None when the repository has no .fde/."""
    store = store_for(parse(payload))
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
    registry.register(store.root)
    return summary.context(direction, measurements, issues, brief=True)


def post_tool_use_context(payload: str) -> str | None:
    """A nudge when Write created an execution artifact that no path links (rule L1)."""
    data = parse(payload)
    tool_input = data.get("tool_input")
    if data.get("tool_name") != "Write" or not isinstance(tool_input, dict):
        return None
    file_path = tool_input.get("file_path")
    if not isinstance(file_path, str):
        return None
    written = Path(file_path)
    if not written.is_absolute():
        written = store_for(data).root / written
    store = Store(locate(written.parent))
    if not store.exists():
        return None
    if not written.resolve().is_relative_to(store.root.resolve()):
        return None
    relative = written.resolve().relative_to(store.root.resolve()).as_posix()
    try:
        direction = store.load()
    except FdeError:
        return None
    if relative not in detect.drift(store.root, direction):
        return None
    return (
        f"fde-workflow: {relative} is an execution artifact that no path links. Ask the user "
        "which path it serves and link it (`fde-workflow path link <path-id> "
        f"{relative}`), or say plainly that it is outside the direction (drift). The path skill "
        "covers this."
    )


@app.command("post-tool-use")
def post_tool_use() -> None:
    """Nudge about an unlinked execution artifact (reads the hook's JSON on stdin)."""
    try:
        text = post_tool_use_context(sys.stdin.read())
    except Exception as error:  # a hook must never interrupt the session
        typer.echo(f"fde-workflow hook: {error}", err=True)
        return
    if text:
        output = {"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": text}}
        typer.echo(json.dumps(output))


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
