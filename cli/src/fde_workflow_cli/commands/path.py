"""`fde-workflow path`: open paths, move them through their life cycle, link execution work."""

import datetime as dt
from pathlib import Path
from typing import Annotated

import typer

from fde_workflow_cli import clock
from fde_workflow_cli.commands.common import (
    RootOption,
    find_path,
    open_store,
    parse_date,
    record,
    require,
    user_errors,
)
from fde_workflow_cli.errors import FdeError
from fde_workflow_cli.model import DecisionType, DirectionPath, PathStatus, StageName

app = typer.Typer(help="Manage paths: hypotheses that move the KPIs.", no_args_is_help=True)

TRANSITIONS: dict[PathStatus, set[PathStatus]] = {
    PathStatus.PROPOSED: {PathStatus.ACTIVE, PathStatus.DISCARDED},
    PathStatus.ACTIVE: {PathStatus.MEASURING, PathStatus.DISCARDED},
    PathStatus.MEASURING: {PathStatus.VALIDATED, PathStatus.DISCARDED, PathStatus.ACTIVE},
    PathStatus.VALIDATED: set(),
    PathStatus.DISCARDED: set(),
}
STATUSES_AT_ADD = (PathStatus.PROPOSED, PathStatus.ACTIVE, PathStatus.MEASURING)


def parse_expects(items: list[str]) -> dict[str, float]:
    expects: dict[str, float] = {}
    for item in items:
        kpi_id, separator, value = item.partition("=")
        if not separator:
            raise FdeError(f"--expects {item!r} must look like KPI_ID=VALUE.")
        try:
            expects[kpi_id.strip()] = float(value)
        except ValueError as error:
            raise FdeError(f"--expects {item!r}: {value!r} is not a number.") from error
    return expects


def normalise_ref(root: Path, ref: str) -> str:
    """URLs stay as they are; files become POSIX paths relative to the repository root."""
    if "://" in ref:
        return ref
    path = Path(ref)
    absolute = (path if path.is_absolute() else Path.cwd() / path).resolve()
    if absolute.is_relative_to(root.resolve()):
        return absolute.relative_to(root.resolve()).as_posix()
    return path.as_posix()


@app.command()
def add(
    path_id: Annotated[str, typer.Argument(help="Kebab-case id, e.g. auto-triage.")],
    hypothesis: Annotated[
        str, typer.Option(help='"If we do X, we expect KPI Y to go from A to B."')
    ],
    expects: Annotated[
        list[str], typer.Option("--expects", help="KPI_ID=VALUE expected; repeat per KPI.")
    ],
    reason: Annotated[
        str | None, typer.Option(help="Why the path opens (not needed with --inferred).")
    ] = None,
    status: Annotated[
        PathStatus, typer.Option(help="Initial status: proposed, active or measuring.")
    ] = PathStatus.PROPOSED,
    activated: Annotated[
        str | None, typer.Option(help="When work started, YYYY-MM-DD (default: today).")
    ] = None,
    maturity: Annotated[
        StageName | None, typer.Option(help="The path's own stage, when it differs.")
    ] = None,
    link: Annotated[
        list[str] | None, typer.Option("--link", help="Execution artifact; repeat it.")
    ] = None,
    inferred: Annotated[
        bool, typer.Option("--inferred", help="Inferred from existing work; needs confirmation.")
    ] = False,
    root: RootOption = None,
) -> None:
    """Open a path; records a path-open decision unless it is --inferred."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        if direction.path(path_id):
            raise FdeError(f"Path {path_id} already exists: use `fde-workflow path update`.")
        if status not in STATUSES_AT_ADD:
            raise FdeError("A path starts as proposed, active or measuring; use `path move` later.")
        if not inferred:
            reason = require(reason, "--reason", "to open a path (or use --inferred)")
        started: dt.date | None = None
        if activated:
            started = parse_date(activated, "--activated")
        elif status is not PathStatus.PROPOSED:
            started = clock.today()
        direction.paths.append(
            DirectionPath(
                id=path_id,
                hypothesis=hypothesis,
                expects=parse_expects(expects),
                status=status,
                activated=started,
                maturity=maturity,
                confirmed=not inferred,
                links=[normalise_ref(store.root, ref) for ref in link or []],
            )
        )
        store.save(direction)
        if not inferred:
            record(
                store,
                DecisionType.PATH_OPEN,
                f"Open path {path_id}: {hypothesis}",
                reason or "",
                refs=[path_id],
            )
    typer.echo(f"Added path {path_id} ({status}{', inferred' if inferred else ''}).")


@app.command()
def update(
    path_id: Annotated[str, typer.Argument()],
    hypothesis: Annotated[str | None, typer.Option()] = None,
    expects: Annotated[
        list[str] | None, typer.Option("--expects", help="Replaces every expectation.")
    ] = None,
    maturity: Annotated[StageName | None, typer.Option()] = None,
    learning: Annotated[str | None, typer.Option()] = None,
    root: RootOption = None,
) -> None:
    """Change a path's hypothesis, expectations, maturity or learning."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        path = find_path(direction, path_id)
        if hypothesis is not None:
            path.hypothesis = hypothesis
        if expects is not None:
            path.expects = parse_expects(expects)
        if maturity is not None:
            path.maturity = maturity
        if learning is not None:
            path.learning = learning
        store.save(direction)
    typer.echo(f"Updated path {path_id}.")


@app.command()
def move(
    path_id: Annotated[str, typer.Argument()],
    status: Annotated[PathStatus, typer.Argument(help="The new status.")],
    reason: Annotated[str, typer.Option(help="Why the status changes.")],
    learning: Annotated[
        str | None, typer.Option(help="What the path taught us (required to discard).")
    ] = None,
    approved_by: Annotated[str | None, typer.Option("--approved-by")] = None,
    root: RootOption = None,
) -> None:
    """Move a path: proposed → active → measuring → validated | discarded."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        path = find_path(direction, path_id)
        if status not in TRANSITIONS[path.status]:
            allowed = ", ".join(sorted(TRANSITIONS[path.status])) or "none, it is final"
            raise FdeError(
                f"Path {path_id} cannot go from {path.status} to {status} (allowed: {allowed})."
            )
        if status is PathStatus.DISCARDED and not learning:
            raise FdeError("--learning is required to discard a path: what did it teach us?")
        path.status = status
        if status is PathStatus.ACTIVE and path.activated is None:
            path.activated = clock.today()
        if learning:
            path.learning = learning
        store.save(direction)
        if status is PathStatus.VALIDATED:
            record(
                store,
                DecisionType.PATH_VALIDATE,
                f"Validate path {path_id}",
                reason,
                approved_by or "",
                [path_id],
            )
        if status is PathStatus.DISCARDED:
            record(
                store,
                DecisionType.PATH_DISCARD,
                f"Discard path {path_id}",
                reason,
                approved_by or "",
                [path_id],
            )
    typer.echo(f"Path {path_id} is now {status}.")


@app.command()
def link(
    refs: Annotated[
        list[str], typer.Argument(help="PATH_ID REF..., or REF... with --pre-framework.")
    ],
    pre_framework: Annotated[
        bool, typer.Option("--pre-framework", help="Mark artifacts as pre-framework instead.")
    ] = False,
    root: RootOption = None,
) -> None:
    """Link execution artifacts (files or URLs) to a path, or mark them pre-framework."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        known = direction.artifacts.pre_framework
        if pre_framework:
            targets = [normalise_ref(store.root, ref) for ref in refs]
            known.extend(ref for ref in dict.fromkeys(targets) if ref not in known)
            message = f"Marked {len(targets)} artifact(s) as pre-framework."
        else:
            if len(refs) < 2:
                raise FdeError("Usage: fde-workflow path link PATH_ID REF... (or --pre-framework).")
            path = find_path(direction, refs[0])
            targets = [normalise_ref(store.root, ref) for ref in refs[1:]]
            path.links.extend(ref for ref in dict.fromkeys(targets) if ref not in path.links)
            direction.artifacts.pre_framework = [ref for ref in known if ref not in targets]
            message = f"Linked {len(targets)} artifact(s) to {path.id}."
        store.save(direction)
    typer.echo(message)


@app.command()
def confirm(
    path_id: Annotated[str, typer.Argument()],
    reason: Annotated[
        str, typer.Option(help="Why it is confirmed.")
    ] = "Confirmed a path inferred from existing work.",
    root: RootOption = None,
) -> None:
    """Mark an inferred path as confirmed; records a path-open decision."""
    with user_errors():
        store = open_store(root)
        direction = store.load()
        path = find_path(direction, path_id)
        if path.confirmed:
            typer.echo(f"Path {path_id} already confirmed.")
            return
        path.confirmed = True
        store.save(direction)
        record(
            store,
            DecisionType.PATH_OPEN,
            f"Confirm path {path_id}: {path.hypothesis}",
            reason,
            refs=[path_id],
        )
    typer.echo(f"Path {path_id} confirmed.")
