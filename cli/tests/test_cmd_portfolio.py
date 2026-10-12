import json
import shutil
from pathlib import Path

import pytest

from fde_workflow_cli import registry
from tests.helpers import add_kpi, ok


def test_registry_lives_under_xdg_config_home(isolated_registry: Path) -> None:
    assert registry.registry_file() == isolated_registry / "fde-workflow" / "projects.json"


def test_init_and_status_register_the_repository(repo: Path, isolated_registry: Path) -> None:
    ok("init", "--name", "acme-support")
    ok("status")
    data = json.loads(registry.registry_file().read_text())
    assert data == {"projects": [str(repo.resolve())]}


def test_portfolio_summarises_each_project(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, second = tmp_path_factory.mktemp("acme"), tmp_path_factory.mktemp("globex")
    monkeypatch.chdir(first)
    ok("init", "--name", "acme-support")
    add_kpi(first)
    ok("northstar", "set", "--statement", "x", "--primary-kpi", "resolution-time")
    monkeypatch.chdir(second)
    ok("init", "--name", "globex-claims")
    lines = ok("portfolio").output.splitlines()
    assert lines[0].startswith("acme-support · discovery · resolution-time (primary): no baseline")
    assert lines[1].startswith("globex-claims · discovery · no primary KPI")
    assert "warning(s)" in lines[1]


def test_portfolio_survives_missing_and_broken_repositories(
    tmp_path_factory: pytest.TempPathFactory, monkeypatch: pytest.MonkeyPatch
) -> None:
    gone, broken = tmp_path_factory.mktemp("gone"), tmp_path_factory.mktemp("broken")
    for directory in (gone, broken):
        monkeypatch.chdir(directory)
        ok("init")
    shutil.rmtree(gone / ".fde")
    (broken / ".fde" / "direction.yaml").write_text("schema_version: 1\nproject: 3\n")
    output = ok("portfolio").output
    assert f"{gone.resolve()} · no .fde/ any more" in output
    assert f"{broken.resolve()} · .fde/ cannot be read" in output


def test_portfolio_forget(repo: Path) -> None:
    ok("init")
    assert "No projects registered" not in ok("portfolio").output
    ok("portfolio", "forget", str(repo))
    assert "No projects registered" in ok("portfolio").output


def test_a_corrupt_registry_is_never_overwritten(repo: Path) -> None:
    path = registry.registry_file()
    path.parent.mkdir(parents=True)
    path.write_text('{"projects": ["/a", "/b"')
    ok("init")
    assert path.read_text() == '{"projects": ["/a", "/b"'
    assert "cannot be read" in ok("portfolio").output
