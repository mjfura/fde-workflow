"""Readiness checks behind `fde-workflow doctor`. Add one function per check to CHECKS."""

import sys
from collections.abc import Callable
from dataclasses import dataclass


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


CHECKS: list[Callable[[], CheckResult]] = [check_python]


def run_checks() -> list[CheckResult]:
    return [check() for check in CHECKS]
