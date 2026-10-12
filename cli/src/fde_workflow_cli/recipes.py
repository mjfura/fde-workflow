"""Measurement recipes: where they live, their fingerprint, and running script recipes."""

import datetime as dt
import hashlib
import math
import os
import subprocess
from pathlib import Path

from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import Recipe

SCRIPT_TIMEOUT_SECONDS = 600


def recipe_path(fde_dir: Path, recipe: Recipe) -> Path:
    """Return the recipe's file, which must stay inside `.fde/`."""
    path = (fde_dir / recipe.file).resolve()
    if not path.is_relative_to(fde_dir.resolve()):
        raise FdeError(f"Recipe {recipe.file!r} must be inside .fde/ (e.g. measures/<kpi>.sql).")
    return path


def fingerprint(fde_dir: Path, recipe: Recipe) -> str | None:
    """SHA-256 of the recipe file, or None when the file does not exist."""
    path = recipe_path(fde_dir, recipe)
    if not path.is_file():
        return None
    return hashlib.sha256(path.read_bytes()).hexdigest()


def render(fde_dir: Path, recipe: Recipe, start: dt.date, end: dt.date) -> str:
    """The recipe's text with its window placeholders filled in."""
    text = recipe_path(fde_dir, recipe).read_text(encoding="utf-8")
    return text.replace("{{window_start}}", start.isoformat()).replace(
        "{{window_end}}", end.isoformat()
    )


def run_script(fde_dir: Path, recipe: Recipe, start: dt.date, end: dt.date) -> float:
    """Run a script recipe from the repository root and return the number it prints."""
    path = recipe_path(fde_dir, recipe)
    if not os.access(path, os.X_OK):
        raise FdeError(f"{path} is not executable: run `chmod +x {path}`.")
    env = {**os.environ, "FDE_WINDOW_START": start.isoformat(), "FDE_WINDOW_END": end.isoformat()}
    try:
        result = subprocess.run(  # noqa: S603 - the project's own recipe, run only with --run
            [str(path)],
            cwd=fde_dir.parent,
            env=env,
            capture_output=True,
            text=True,
            timeout=SCRIPT_TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise FdeError(
            f"Recipe {recipe.file} did not finish in {SCRIPT_TIMEOUT_SECONDS} s."
        ) from error
    if result.returncode != 0:
        raise FdeError(
            f"Recipe {recipe.file} failed with exit code {result.returncode}:\n"
            f"{result.stderr.strip()}"
        )
    output = result.stdout.strip()
    try:
        value = float(output)
    except ValueError as error:
        raise FdeError(
            f"Recipe {recipe.file} must print one number; it printed {output!r}."
        ) from error
    if not math.isfinite(value):
        raise FdeError(f"Recipe {recipe.file} must print a finite number; it printed {output!r}.")
    return value
