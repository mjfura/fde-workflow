"""The portfolio registry: the repositories on this machine that use the framework.

It lives outside every repository, in $XDG_CONFIG_HOME/fde-workflow/projects.json, and holds
paths only. Registering must never make a command fail, so write errors are ignored.
"""

import json
import os
from pathlib import Path


def registry_file() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "fde-workflow" / "projects.json"


def registered() -> list[Path]:
    try:
        data = json.loads(registry_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    projects = data.get("projects") if isinstance(data, dict) else None
    if not isinstance(projects, list):
        return []
    return [Path(item) for item in projects if isinstance(item, str)]


def _write(projects: list[Path]) -> None:
    path = registry_file()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps({"projects": [str(project) for project in projects]}, indent=2)
        path.write_text(text + "\n", encoding="utf-8")
    except OSError:
        return


def register(root: Path) -> None:
    root = root.resolve()
    projects = registered()
    if root not in projects:
        _write([*projects, root])


def forget(root: Path) -> bool:
    root = root.resolve()
    projects = registered()
    if root not in projects:
        return False
    _write([project for project in projects if project != root])
    return True
