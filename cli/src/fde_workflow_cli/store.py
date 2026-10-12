"""Read and write `.fde/`. direction.yaml is validated, rules included, before every write."""

import hashlib
import os
import tempfile
from pathlib import Path

import yaml
from pydantic import BaseModel, ValidationError

from fde_workflow_cli import rules
from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import SCHEMA_VERSION, Decision, Direction, Measurement

FDE_DIR = ".fde"
DIRECTION_FILE = "direction.yaml"
MEASUREMENTS_FILE = "measurements.jsonl"
DECISIONS_FILE = "decisions.jsonl"
SUBDIRECTORIES = ("measures", "discovery", "reports")


def locate(start: Path) -> Path:
    """The closest directory from `start` up to its git root that contains `.fde/`, else `start`."""
    start = start.resolve()
    for directory in (start, *start.parents):
        if (directory / FDE_DIR / DIRECTION_FILE).is_file():
            return directory
        if (directory / ".git").exists():
            break
    return start


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise FdeError(
            f"{path} is not valid UTF-8 (byte {error.start}): save it as UTF-8."
        ) from error
    except OSError as error:
        raise FdeError(f"{path} cannot be read: {error.strerror}.") from error


def describe_validation_error(source: str, error: ValidationError) -> str:
    lines = [f"{source} is not valid:"]
    for item in error.errors():
        where = ".".join(str(part) for part in item["loc"]) or "(root)"
        lines.append(f"  {where}: {item['msg']}")
    return "\n".join(lines)


class Store:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.dir = root / FDE_DIR
        self.direction_file = self.dir / DIRECTION_FILE
        self._loaded_digest: str | None = None

    def exists(self) -> bool:
        return self.direction_file.is_file()

    def create(self, direction: Direction) -> None:
        if self.exists():
            raise FdeError(f"{self.dir} already exists.")
        for name in SUBDIRECTORIES:
            (self.dir / name).mkdir(parents=True, exist_ok=True)
        for name in (MEASUREMENTS_FILE, DECISIONS_FILE):
            (self.dir / name).touch()
        self.save(direction)

    def load(self) -> Direction:
        if not self.exists():
            raise FdeError(
                f"No .fde/ in {self.root}: run `fde-workflow init` (or the adopt skill) first."
            )
        text = read_text(self.direction_file)
        self._loaded_digest = _digest(text)
        try:
            data = yaml.safe_load(text)
        except yaml.YAMLError as error:
            raise FdeError(f"{self.direction_file} is not valid YAML: {error}") from error
        if not isinstance(data, dict):
            raise FdeError(f"{self.direction_file} must contain a YAML mapping.")
        version = data.get("schema_version")
        if version is None:
            raise FdeError(
                f"{self.direction_file} has no schema_version: it is not an fde-workflow "
                "direction file, or it was damaged."
            )
        if isinstance(version, int) and version > SCHEMA_VERSION:
            raise FdeError(
                f"{self.direction_file} has schema_version {version}; this fde-workflow "
                f"supports {SCHEMA_VERSION}. Upgrade it: uv tool upgrade fde-workflow-cli."
            )
        if version != SCHEMA_VERSION:
            raise FdeError(
                f"{self.direction_file} has schema_version {version!r}; this fde-workflow "
                f"reads only schema_version {SCHEMA_VERSION}."
            )
        try:
            return Direction.model_validate(data)
        except ValidationError as error:
            raise FdeError(describe_validation_error(str(self.direction_file), error)) from error

    def save(self, direction: Direction) -> None:
        """Write direction.yaml if it is valid and breaks no rule; otherwise change nothing."""
        data = direction.model_dump(mode="json")
        try:
            checked = Direction.model_validate(data)
        except ValidationError as error:
            raise FdeError(describe_validation_error("The change", error)) from error
        errors = [
            issue
            for issue in rules.check(checked, self.measurements(), self.dir)
            if issue.level == "error"
        ]
        if errors:
            listed = "\n".join(f"  [{issue.rule}] {issue.message}" for issue in errors)
            raise FdeError(f"Not saved: the change breaks the framework's rules:\n{listed}")
        if (
            self._loaded_digest is not None
            and self.direction_file.is_file()
            and _digest(read_text(self.direction_file)) != self._loaded_digest
        ):
            raise FdeError(
                f"{self.direction_file} changed since it was read (another fde-workflow "
                "command?): run the command again."
            )
        text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=self.dir, suffix=".tmp", delete=False
        ) as handle:
            handle.write(text)
        try:
            os.chmod(handle.name, 0o666 & ~_umask())
            os.replace(handle.name, self.direction_file)
        except OSError as error:
            Path(handle.name).unlink(missing_ok=True)
            raise FdeError(f"Cannot write {self.direction_file}: {error.strerror}.") from error
        self._loaded_digest = _digest(text)

    def measurements(self) -> list[Measurement]:
        return _read_jsonl(self.dir / MEASUREMENTS_FILE, Measurement)

    def decisions(self) -> list[Decision]:
        return _read_jsonl(self.dir / DECISIONS_FILE, Decision)

    def append_measurement(self, measurement: Measurement) -> None:
        _append_jsonl(self.dir / MEASUREMENTS_FILE, measurement)

    def append_decision(self, decision: Decision) -> None:
        _append_jsonl(self.dir / DECISIONS_FILE, decision)


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _umask() -> int:
    mask = os.umask(0)
    os.umask(mask)
    return mask


def _read_jsonl[M: BaseModel](path: Path, model: type[M]) -> list[M]:
    if not path.is_file():
        return []
    records = []
    for number, line in enumerate(read_text(path).splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(model.model_validate_json(line))
        except ValidationError as error:
            raise FdeError(describe_validation_error(f"{path}:{number}", error)) from error
    return records


def _append_jsonl(path: Path, record: BaseModel) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(record.model_dump_json() + "\n")
