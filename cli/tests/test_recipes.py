import datetime as dt
from pathlib import Path

import pytest

from fde_workflow_cli import recipes
from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import Recipe, RecipeType
from tests.helpers import write_recipe

START, END = dt.date(2026, 9, 15), dt.date(2026, 10, 12)


def script(repo: Path, body: str) -> Recipe:
    write_recipe(repo, "measures/k.sh", f"#!/bin/sh\n{body}\n", executable=True)
    return Recipe(type=RecipeType.SCRIPT, file="measures/k.sh")


def test_fingerprint_changes_with_the_recipe(tmp_path: Path) -> None:
    recipe = Recipe(type=RecipeType.QUERY, file="measures/k.sql")
    assert recipes.fingerprint(tmp_path / ".fde", recipe) is None
    write_recipe(tmp_path, "measures/k.sql", "select 1")
    first = recipes.fingerprint(tmp_path / ".fde", recipe)
    write_recipe(tmp_path, "measures/k.sql", "select 2")
    assert first is not None
    assert recipes.fingerprint(tmp_path / ".fde", recipe) != first


def test_recipes_must_stay_inside_fde(tmp_path: Path) -> None:
    recipe = Recipe(type=RecipeType.QUERY, file="../secrets.sql")
    with pytest.raises(FdeError, match=r"inside \.fde/"):
        recipes.fingerprint(tmp_path / ".fde", recipe)


def test_render_fills_the_window(tmp_path: Path) -> None:
    write_recipe(tmp_path, "measures/k.sql", "between '{{window_start}}' and '{{window_end}}'")
    recipe = Recipe(type=RecipeType.QUERY, file="measures/k.sql")
    assert recipes.render(tmp_path / ".fde", recipe, START, END) == (
        "between '2026-09-15' and '2026-10-12'"
    )


def test_run_script_passes_the_window_and_reads_the_number(tmp_path: Path) -> None:
    recipe = script(
        tmp_path, 'test "$FDE_WINDOW_START/$FDE_WINDOW_END" = 2026-09-15/2026-10-12 && echo 42.5'
    )
    assert recipes.run_script(tmp_path / ".fde", recipe, START, END) == 42.5


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("echo boom >&2; exit 3", "exit code 3"),
        ("echo forty-two", "one number"),
        ("echo nan", "finite"),
    ],
)
def test_run_script_failures_record_nothing(tmp_path: Path, body: str, message: str) -> None:
    with pytest.raises(FdeError, match=message):
        recipes.run_script(tmp_path / ".fde", script(tmp_path, body), START, END)


def test_run_script_requires_an_executable(tmp_path: Path) -> None:
    write_recipe(tmp_path, "measures/k.sh", "#!/bin/sh\necho 1\n")
    recipe = Recipe(type=RecipeType.SCRIPT, file="measures/k.sh")
    with pytest.raises(FdeError, match="chmod"):
        recipes.run_script(tmp_path / ".fde", recipe, START, END)


def test_run_script_without_a_shebang_says_so(tmp_path: Path) -> None:
    write_recipe(tmp_path, "measures/k.sh", "echo 1\n", executable=True)
    recipe = Recipe(type=RecipeType.SCRIPT, file="measures/k.sh")
    with pytest.raises(FdeError, match="shebang"):
        recipes.run_script(tmp_path / ".fde", recipe, START, END)
