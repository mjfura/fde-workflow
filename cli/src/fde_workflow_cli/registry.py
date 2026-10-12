"""The portfolio registry: the repositories on this machine that use the framework.

It lives outside every repository, in $XDG_CONFIG_HOME/fde-workflow/projects.json, and holds
paths only. Registering must never make a command fail, so write errors are ignored.
"""

import json
import os
import tempfile
from pathlib import Path


class RegistryError(Exception):
    """The registry file exists but cannot be read; it is never overwritten then."""


def registry_file() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "fde-workflow" / "projects.json"


def registered() -> list[Path]:
    """The registered roots; raises RegistryError when the file exists but is unreadable."""
    path = registry_file()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise RegistryError(f"{path} cannot be read ({error}): fix or delete it.") from error
    projects = data.get("projects") if isinstance(data, dict) else None
    if not isinstance(projects, list):
        raise RegistryError(f"{path} cannot be read (no projects list): fix or delete it.")
    return [Path(item) for item in projects if isinstance(item, str)]


def _write(projects: list[Path]) -> None:
    path = registry_file()
    text = json.dumps({"projects": [str(project) for project in projects]}, indent=2) + "\n"
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent, suffix=".tmp", delete=False
        ) as handle:
            handle.write(text)
    except OSError:
        return
    try:
        os.replace(handle.name, path)
    except OSError:
        Path(handle.name).unlink(missing_ok=True)


def register(root: Path) -> None:
    root = root.resolve()
    try:
        projects = registered()
    except RegistryError:
        return
    if root not in projects:
        _write([*projects, root])


def forget(root: Path) -> bool:
    root = root.resolve()
    projects = registered()
    if root not in projects:
        return False
    _write([project for project in projects if project != root])
    return True
