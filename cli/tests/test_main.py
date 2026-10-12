from importlib.metadata import version

import pytest
from typer.testing import CliRunner

from fde_workflow_cli import doctor
from fde_workflow_cli.doctor import CheckResult
from fde_workflow_cli.main import app

runner = CliRunner()


def test_version_prints_the_command_and_package_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert result.output == f"fde-workflow {version('fde-workflow-cli')}\n"


def test_doctor_is_ready_when_every_check_passes(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(doctor, "CHECKS", [lambda: CheckResult(ok=True, message="all good")])
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 0
    assert result.output == "✓ all good\nReady.\n"


def test_doctor_fails_when_a_check_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        doctor,
        "CHECKS",
        [
            lambda: CheckResult(ok=True, message="fine"),
            lambda: CheckResult(ok=False, message="broken: fix it"),
        ],
    )
    result = runner.invoke(app, ["doctor"])
    assert result.exit_code == 1
    assert result.output == "✓ fine\n✗ broken: fix it\nNot ready: 1 problem(s).\n"
