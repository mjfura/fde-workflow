import json
from pathlib import Path

from tests.helpers import ok


def test_session_start_is_silent_without_fde(tmp_path: Path) -> None:
    result = ok("hook", "session-start", stdin=json.dumps({"cwd": str(tmp_path)}))
    assert result.stdout == ""


def test_session_start_adds_the_brief_context(fde: Path) -> None:
    nested = fde / "src"
    nested.mkdir()
    result = ok("hook", "session-start", stdin=json.dumps({"cwd": str(nested)}))
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "SessionStart"
    assert output["additionalContext"].startswith("FDE direction of this repository")
    assert "Stage: discovery since 2026-10-12" in output["additionalContext"]


def test_session_start_tolerates_bad_input(fde: Path) -> None:
    result = ok("hook", "session-start", stdin="not json")
    assert "additionalContext" in result.stdout


def test_session_start_reports_an_unreadable_fde(fde: Path) -> None:
    (fde / ".fde" / "direction.yaml").write_text("schema_version: 1\nproject: 3\n")
    result = ok("hook", "session-start", stdin=json.dumps({"cwd": str(fde)}))
    assert "cannot be read" in json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]
