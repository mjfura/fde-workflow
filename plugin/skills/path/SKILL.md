---
name: path
description: 'Manage the paths of a customer project, the hypotheses that move its KPIs: check that new work (a feature, spec, plan or brainstorm in any methodology, such as superpowers or spec-kit) serves a path, open, link, measure, validate or discard paths, and confirm inferred ones. Use it when the user starts new work or a new feature, asks whether something is aligned with the North Star, says "let us open a path", "this is built", "we are dropping X", or when a spec or plan was just written.'
allowed-tools:
  - Bash(fde-workflow status)
  - Bash(fde-workflow context)
---

# Paths: hypotheses that move the KPIs

Read `../fde-workflow/references/framework.md` (relative to this skill's directory) first, then
run `fde-workflow context`.

## Alignment check for new work

When the user starts new work, before or alongside their own methodology (e.g. a superpowers
brainstorm), ask which path it serves, proposing the most likely one from `context`:
- **An existing path:** continue; link the spec, plan or PR once it exists.
- **A new path:** open it (below). It needs a KPI it should move.
- **None:** say plainly that it is outside the direction (drift) and let the user decide whether
  to do it anyway. Do not block the work.
Then hand over to the user's methodology: this skill never writes specs or plans.

## Open a path

1. Phrase it as a hypothesis with the user: *"If we do X, we expect KPI Y to go from A to B."*
   Every targeted KPI must exist (define it first with the `kpi` skill) and have a baseline before
   the work starts.
2. `fde-workflow path add <id> --hypothesis "..." --expects <kpi>=<value> --reason "..."`
   (repeat `--expects` per KPI).

## Link execution work

`fde-workflow path link <path-id> <file-or-url>...` for specs, plans, PRs and issues. Artifacts
from before the framework: `fde-workflow path link --pre-framework <file>...`.

## Life cycle

`fde-workflow path move <id> <status> --reason "..."`:
- `active` when work starts; `measuring` when it is built and in use.
- In `measuring`, measure its KPIs with the `kpi` skill. Then:
  - `validated` only when a measurement whose whole window comes after the path became active
    shows the effect (wait a full KPI window after activation);
    otherwise the CLI refuses ([P2]). Never move a path to validated because it is built,
    deployed or "looks good": measure first.
  - `discarded` when the evidence says no or priorities change, with what it taught us:
    `--learning "..."`. Discarded paths stay as learning.
- Add `--approved-by "..."` when the sponsor took the decision.

## Inferred paths

Paths from the `adopt` skill are unconfirmed hypotheses. Review each with the user: confirm it
(`fde-workflow path confirm <id>`), correct it (`fde-workflow path update <id> ...`), or discard it.

## Rules

- Expected values and hypotheses come from the user; never invent them.
- Never edit `.fde/direction.yaml` by hand.
