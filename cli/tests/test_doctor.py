from fde_workflow_cli.doctor import check_python, run_checks


def test_python_check_passes_on_a_supported_python() -> None:
    result = check_python()
    assert result.ok
    assert result.message.startswith("Python 3.")


def test_run_checks_runs_every_check() -> None:
    assert [result.ok for result in run_checks()] == [True]
