import datetime as dt
import os
from pathlib import Path

import pytest

from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import Decision, DecisionType, StageName, StageState
from fde_workflow_cli.store import Store, locate
from tests.helpers import sample_direction, write_recipe


def created(repo: Path) -> Store:
    store = Store(repo)
    write_recipe(repo, "measures/resolution-time.sql")
    store.create(sample_direction())
    return store


def test_create_writes_the_layout_and_load_reads_it_back(tmp_path: Path) -> None:
    store = created(tmp_path)
    for name in ("measures", "discovery", "reports"):
        assert (tmp_path / ".fde" / name).is_dir()
    assert (tmp_path / ".fde" / "measurements.jsonl").read_text() == ""
    assert store.load() == sample_direction()


def test_create_refuses_an_existing_fde(tmp_path: Path) -> None:
    store = created(tmp_path)
    with pytest.raises(FdeError, match="already exists"):
        store.create(sample_direction())


def test_load_without_fde_says_how_to_start(tmp_path: Path) -> None:
    with pytest.raises(FdeError, match="fde-workflow init"):
        Store(tmp_path).load()


def test_load_reports_where_the_file_is_invalid(tmp_path: Path) -> None:
    store = created(tmp_path)
    text = store.direction_file.read_text().replace("kind: primary", "kind: main")
    store.direction_file.write_text(text)
    with pytest.raises(FdeError, match=r"kpis\.0\.kind"):
        store.load()


def test_save_refuses_a_change_that_breaks_a_rule_and_keeps_the_file(tmp_path: Path) -> None:
    store = created(tmp_path)
    before = store.direction_file.read_text()
    direction = store.load()
    direction.paths[0].expects = {"unknown-kpi": 1}
    with pytest.raises(FdeError, match=r"\[P1\]"):
        store.save(direction)
    assert store.direction_file.read_text() == before


def test_save_refuses_an_invalid_model(tmp_path: Path) -> None:
    store = created(tmp_path)
    direction = store.load()
    direction.stage = StageState.model_construct(
        current=StageName.CLOSED, entered=dt.date(2026, 1, 1)
    )
    with pytest.raises(FdeError, match="outcome"):
        store.save(direction)


def test_logs_are_append_only_jsonl(tmp_path: Path) -> None:
    store = created(tmp_path)
    decision = Decision(
        date=dt.date(2026, 10, 12), type=DecisionType.OTHER, summary="s", reason="r"
    )
    store.append_decision(decision)
    store.append_decision(decision)
    assert store.decisions() == [decision, decision]


def test_a_broken_log_line_is_reported_with_its_number(tmp_path: Path) -> None:
    store = created(tmp_path)
    (tmp_path / ".fde" / "decisions.jsonl").write_text('{"date": "2026-10-12"}\n')
    with pytest.raises(FdeError, match=r"decisions\.jsonl:1"):
        store.decisions()


def test_locate_finds_fde_in_a_parent_directory(tmp_path: Path) -> None:
    created(tmp_path)
    nested = tmp_path / "src" / "app"
    nested.mkdir(parents=True)
    assert locate(nested) == tmp_path.resolve()
    assert locate(tmp_path.parent) == tmp_path.parent.resolve()


def test_locate_stops_at_the_git_root(tmp_path: Path) -> None:
    created(tmp_path)
    nested_repo = tmp_path / "repo"
    (nested_repo / ".git").mkdir(parents=True)
    (nested_repo / "src").mkdir()
    assert locate(nested_repo / "src") == (nested_repo / "src").resolve()


def test_files_that_are_not_utf8_are_reported(tmp_path: Path) -> None:
    store = created(tmp_path)
    (tmp_path / ".fde" / "decisions.jsonl").write_bytes(b'{"summary": "Decisi\xf3n"}\n')
    with pytest.raises(FdeError, match="UTF-8"):
        store.decisions()
    store.direction_file.write_bytes(b"schema_version: 1\nproject: {name: Direcci\xf3n}\n")
    with pytest.raises(FdeError, match="UTF-8"):
        store.load()


def test_direction_file_has_the_same_permissions_as_the_logs(tmp_path: Path) -> None:
    created(tmp_path)
    fde = tmp_path / ".fde"
    direction_mode = (fde / "direction.yaml").stat().st_mode & 0o777
    assert direction_mode == (fde / "measurements.jsonl").stat().st_mode & 0o777


def test_a_failed_write_leaves_no_temporary_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = created(tmp_path)
    direction = store.load()

    def broken_replace(source: str, target: object) -> None:
        raise OSError(28, "No space left on device")

    monkeypatch.setattr(os, "replace", broken_replace)
    with pytest.raises(FdeError, match="No space left"):
        store.save(direction)
    assert list((tmp_path / ".fde").glob("*.tmp")) == []


def test_save_refuses_when_another_command_changed_the_file(tmp_path: Path) -> None:
    created(tmp_path)
    first, second = Store(tmp_path), Store(tmp_path)
    stale, fresh = first.load(), second.load()
    fresh.project.sponsor = "Jane"
    second.save(fresh)
    with pytest.raises(FdeError, match="changed since"):
        first.save(stale)


@pytest.mark.parametrize(
    ("text", "message"),
    [
        ("project: {name: x}\n", "has no schema_version"),
        ("schema_version: 2\n", "Upgrade"),
        ("schema_version: 0\n", "only schema_version 1"),
    ],
)
def test_schema_version_messages(tmp_path: Path, text: str, message: str) -> None:
    store = created(tmp_path)
    store.direction_file.write_text(text)
    with pytest.raises(FdeError, match=message):
        store.load()
