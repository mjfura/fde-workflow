import json
from pathlib import Path

import pytest

from tests.helpers import add_kpi, make_files, ok


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


def written(repo: Path, relative: str, tool: str = "Write") -> str:
    return json.dumps(
        {
            "cwd": str(repo),
            "hook_event_name": "PostToolUse",
            "tool_name": tool,
            "tool_input": {"file_path": str(repo / relative), "content": "x"},
        }
    )


def test_post_tool_use_asks_about_a_new_unlinked_artifact(repo: Path) -> None:
    make_files(repo, "docs/superpowers/specs/new.md")
    ok("init")
    result = ok("hook", "post-tool-use", stdin=written(repo, "docs/superpowers/specs/new.md"))
    output = json.loads(result.stdout)["hookSpecificOutput"]
    assert output["hookEventName"] == "PostToolUse"
    assert "docs/superpowers/specs/new.md" in output["additionalContext"]
    assert "fde-workflow path link" in output["additionalContext"]


def test_post_tool_use_ignores_linked_and_unmatched_files(repo: Path) -> None:
    make_files(repo, "docs/superpowers/specs/old.md", "src/app.py")
    ok("init")
    ok("path", "link", "--pre-framework", "docs/superpowers/specs/old.md")
    for relative in ("docs/superpowers/specs/old.md", "src/app.py"):
        assert ok("hook", "post-tool-use", stdin=written(repo, relative)).stdout == ""
    other_tool = written(repo, "docs/superpowers/specs/x.md", tool="Read")
    assert ok("hook", "post-tool-use", stdin=other_tool).stdout == ""


def test_post_tool_use_is_silent_without_fde_or_with_bad_input(repo: Path) -> None:
    assert ok("hook", "post-tool-use", stdin=written(repo, "specs/a.md")).stdout == ""
    ok("init")
    for payload in ("not json", "{}", json.dumps({"cwd": str(repo), "tool_name": "Write"})):
        assert ok("hook", "post-tool-use", stdin=payload).stdout == ""


def test_post_tool_use_uses_the_fde_of_the_written_file(repo: Path) -> None:
    service = repo / "service"
    make_files(service, "docs/superpowers/specs/new.md")
    ok("init", "--root", str(service))
    payload = json.dumps(
        {
            "cwd": str(repo),
            "tool_name": "Write",
            "tool_input": {"file_path": str(service / "docs/superpowers/specs/new.md")},
        }
    )
    assert "docs/superpowers/specs/new.md" in ok("hook", "post-tool-use", stdin=payload).stdout


def test_post_tool_use_ignores_path_linked_and_outside_files(
    repo: Path, tmp_path_factory: pytest.TempPathFactory
) -> None:
    make_files(repo, "docs/superpowers/specs/a.md")
    ok("init")
    add_kpi(repo)
    ok("path", "add", "p", "--hypothesis", "h", "--expects", "resolution-time=1", "--reason", "r")
    ok("path", "link", "p", "docs/superpowers/specs/a.md")
    assert (
        ok("hook", "post-tool-use", stdin=written(repo, "docs/superpowers/specs/a.md")).stdout == ""
    )
    outside = tmp_path_factory.mktemp("elsewhere") / "x.md"
    outside.write_text("x")
    payload = json.dumps(
        {"cwd": str(repo), "tool_name": "Write", "tool_input": {"file_path": str(outside)}}
    )
    assert ok("hook", "post-tool-use", stdin=payload).stdout == ""
