---
name: fde-workflow
description: 'Entry point of the FDE direction framework for customer projects: shows where the project stands against its North Star, KPIs, paths and stage, and proposes the next action. Use it when the user asks "how are we doing?", "what is next?", "where does the project stand?", asks about the North Star, KPIs, baselines, paths, gate criteria or the project stage, wants to move the project to another stage, or wants to use the FDE framework in a repository. Also use it at the start of work in a repository with a .fde/ directory.'
allowed-tools:
  - Bash(fde-workflow status)
  - Bash(fde-workflow validate)
  - Bash(fde-workflow context)
---

# FDE direction framework

The framework is defined in `references/framework.md` (next to this file). Read it once per
session before acting on it.

## Steps

1. Run `fde-workflow status`.
   - **Command not found:** use the `setup` skill first.
   - **"No .fde/":** the framework is not set up in this repository. Offer the `adopt` skill and
     stop.
2. Run `fde-workflow validate` and propose **one** next action, the first that applies:
   1. **Errors (✗):** explain each and fix it with the CLI command it names.
   2. **No North Star, or an inferred one (N1, C1):** the `discovery` skill.
   3. **A KPI without baseline (K3) or with a changed recipe (K4):** the `kpi` skill, baseline mode.
   4. **Stage without gate criteria (S1):** agree them now (see *Stage* below).
   5. **A path in `measuring`:** the `kpi` skill to measure it, then the `path` skill to validate
      or discard it.
   6. **Inferred paths (C1):** the `path` skill to confirm or discard them.
   7. **Primary KPI not measured in this stage (S3):** the `kpi` skill.
   8. **Nothing pending:** summarise and ask what the user wants to work on next; new work goes
      through the `path` skill's alignment check.
3. Answer in a few lines: the North Star, the stage, each KPI as baseline → latest → target, live
   paths, and the recommended action with the skill or command that does it.

## Stage

- **Gate criteria** are agreed when entering a stage, with evidence that can be checked
  (e.g. "primary KPI measured over 2 weeks of real use"), and recorded with
  `fde-workflow stage criteria "<criterion>" "<criterion>"`. Changing agreed criteria needs
  `--reason` and `--approved-by`.
- **Gate decisions** are taken with the sponsor, against the criteria, with evidence:
  `fde-workflow stage decide go|recycle|hold|kill --reason "<evidence>" --approved-by "<sponsor>"`
  (`--to <stage>` skips stages on go). Never decide a gate on the user's behalf; propose it and
  run the command once they confirm the sponsor agreed.

## Rules

- Never edit `.fde/direction.yaml`, `measurements.jsonl` or `decisions.jsonl` by hand: only
  through the CLI.
- This skill and the framework do not plan or execute work. Specs, plans and tasks belong to the
  user's own methodology; hand over to it once the direction is clear.
- Talk to the user in their language; CLI ids are kebab-case.
