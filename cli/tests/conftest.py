import datetime as dt
from pathlib import Path

import pytest

from fde_workflow_cli import clock
from tests.helpers import TODAY, ok


@pytest.fixture(autouse=True)
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> dt.date:
    monkeypatch.setattr(clock, "today", lambda: TODAY)
    return TODAY


@pytest.fixture
def repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """An empty repository as the current directory."""
    monkeypatch.chdir(tmp_path)
    return tmp_path


@pytest.fixture
def fde(repo: Path) -> Path:
    """A repository with a fresh .fde/."""
    ok("init", "--preset", "none", "--name", "acme-support")
    return repo
