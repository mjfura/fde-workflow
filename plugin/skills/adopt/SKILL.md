---
name: adopt
description: 'Set up the FDE direction framework (.fde/) in a repository, new or existing: detects the execution methodology (superpowers, spec-kit, other), and for an existing project infers a draft North Star, retroactive paths from existing specs and plans, and the current stage, all marked unconfirmed until the FDE confirms them. Use it when the user wants to start using the FDE framework, fde-workflow, a North Star or KPIs in this repository, or when another skill finds no .fde/ directory.'
allowed-tools:
  - Bash(fde-workflow status)
  - Bash(fde-workflow detect)
---

# Adopt the FDE framework in a repository

Read `../fde-workflow/references/framework.md` (relative to this skill's directory) first.

## Steps

1. Run `fde-workflow detect`. If `fde_initialised` is true, the framework is already set up: hand
   over to the `fde-workflow` skill instead.
2. Decide the mode from the evidence and tell the user which one you chose and why:
   - **New project:** no artifacts, little or no history.
   - **Existing project:** specs, plans, a README with a purpose, history or deployment signals.
3. Initialise. When `detect` found a methodology, run `fde-workflow init --preset <methodology>`.
   Otherwise ask the user where the project keeps specs, plans or design documents and run
   `fde-workflow init --glob "<pattern>"` once per location (e.g. `--glob "design/**"`), or
   `fde-workflow init --preset none` if there are none.
4. **New project:** hand over to the `discovery` skill. Stop here.
5. **Existing project:** build a draft direction from the README, the artifacts listed by
   `detect` (read them) and the history:
   1. **North Star:** an outcome for someone, never a solution. Record it as a draft:
      `fde-workflow northstar set --statement "..." --beneficiary "..." --problem "..." --inferred`.
   2. **Retroactive paths:** group the existing specs and plans into hypotheses about the outcome.
      For each, use the date of its first artifact as `--activated` and a status that reflects the
      evidence (`active` while work goes on, `measuring` when it is built). Never `validated`:
      that needs a measurement. A path needs a KPI, so propose the KPIs first with the `kpi`
      skill, then: `fde-workflow path add <id> --hypothesis "..." --expects <kpi>=<value>
      --status <status> --activated <date> --link <artifact> --inferred`.
   3. **Stage:** infer it from the evidence (deployment signals, users, CI) and record it:
      `fde-workflow stage set <stage> --reason "<evidence>" --entered <date> --inferred`.
   4. **Remaining artifacts:** ask the user which ones predate the framework and mark them:
      `fde-workflow path link --pre-framework <artifact>...`.
6. Present the draft and say clearly that every item is a **hypothesis inferred by you**. Then
   hand over to the `discovery` skill to confirm or correct it with the user (and the sponsor
   where it applies). Baselines come from the `kpi` skill: `historical` when data from before the
   work exists, otherwise `late`, always declared.

## Rules

- Everything inferred is recorded with `--inferred`; only the user confirms it.
- Never invent numbers: KPI targets and expected values come from the user.
- Read existing specs and plans; never change them. The direction only links to execution work.
