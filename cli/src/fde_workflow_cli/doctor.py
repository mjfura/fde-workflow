"""Readiness checks behind `fde-workflow doctor`. Add one function per check to CHECKS."""

import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import SCHEMA_VERSION
from fde_workflow_cli.store import Store, locate


@dataclass(frozen=True)
class CheckResult:
    ok: bool
    message: str


MINIMUM_PYTHON = (3, 13)


def check_python() -> CheckResult:
    found = ".".join(str(part) for part in sys.version_info[:3])
    if sys.version_info >= MINIMUM_PYTHON:
        return CheckResult(ok=True, message=f"Python {found}")
    return CheckResult(ok=False, message=f"Python {found} is too old: install Python 3.13 or newer")


def check_direction() -> CheckResult:
    store = Store(locate(Path.cwd()))
    if not store.exists():
        return CheckResult(ok=True, message="No .fde/ here yet: the adopt skill sets one up")
    try:
        store.load()
        store.measurements()
        store.decisions()
    except FdeError as error:
        return CheckResult(ok=False, message=f".fde/ cannot be read: {error}")
    return CheckResult(ok=True, message=f".fde/ uses schema {SCHEMA_VERSION}: {store.dir}")


CHECKS: list[Callable[[], CheckResult]] = [check_python, check_direction]


def run_checks() -> list[CheckResult]:
    return [check() for check in CHECKS]
