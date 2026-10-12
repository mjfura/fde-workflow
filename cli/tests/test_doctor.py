from pathlib import Path

from fde_workflow_cli.doctor import check_direction, check_python, run_checks


def test_python_check_passes_on_a_supported_python() -> None:
    result = check_python()
    assert result.ok
    assert result.message.startswith("Python 3.")


def test_run_checks_runs_every_check(repo: Path) -> None:
    assert [result.ok for result in run_checks()] == [True, True]


def test_direction_check_without_fde(repo: Path) -> None:
    assert check_direction().message.startswith("No .fde/ here yet")


def test_direction_check_with_a_readable_fde(fde: Path) -> None:
    assert check_direction().ok


def test_direction_check_with_an_unsupported_schema(fde: Path) -> None:
    (fde / ".fde" / "direction.yaml").write_text("schema_version: 9\n")
    result = check_direction()
    assert not result.ok
    assert "schema_version 9" in result.message


def test_direction_check_shows_the_whole_error(fde: Path) -> None:
    path = fde / ".fde" / "direction.yaml"
    path.write_text(path.read_text().replace("name: acme-support", "nmae: acme-support"))
    result = check_direction()
    assert not result.ok
    assert "nmae" in result.message


def test_direction_check_reads_the_logs(fde: Path) -> None:
    (fde / ".fde" / "measurements.jsonl").write_text("{}\n")
    result = check_direction()
    assert not result.ok
    assert "measurements.jsonl:1" in result.message
