---
name: kpi
description: 'Define the KPIs of a customer project and measure them with reproducible recipes: baselines (historical or late), current values, and the measurement that validates a path, always recording external factors. Use it when the user wants to define, change or measure a KPI or metric, asks for a baseline, asks "how is KPI X doing?", or when a path is ready to be measured.'
allowed-tools:
  - Bash(fde-workflow status)
  - Bash(fde-workflow context)
---

# KPIs: define and measure

Read `../fde-workflow/references/framework.md` (relative to this skill's directory) first.

## Define a KPI

1. Agree with the user, one question at a time: what it measures and its formula, the data source,
   the unit, which direction is better, a **numeric target** (for a guardrail, the worst
   acceptable value), the window (e.g. `28d`) and the kind (`primary`, `secondary`, `guardrail`).
2. Write the **recipe** in `.fde/measures/<kpi-id>.<ext>`; it fixes how the KPI is measured, so
   the baseline and later measurements are comparable:
   - `script` (e.g. `.sh`, `.py`): an executable that prints **one number** on stdout and reads
     the window from `FDE_WINDOW_START` and `FDE_WINDOW_END` (ISO dates). Make it executable.
   - `query` (e.g. `.sql`): a query with `{{window_start}}` and `{{window_end}}` placeholders, for
     a tool that has access to the data (an MCP server or a database client).
   - `manual` (`.md`): a written procedure a person follows, saying where the value comes from.
   Show the recipe to the user before saving it.
3. Record it: `fde-workflow kpi add <id> --name "..." --kind <kind> --definition "..."
   --source "..." --unit "..." --direction increase|decrease --target <n> --window <n>d
   --recipe-type <type> --recipe-file measures/<file>`.
4. Changing a target later needs a reason and the sponsor's approval:
   `fde-workflow kpi update <id> --target <n> --reason "..." --approved-by "..."`.

## Measure a KPI

1. Run `fde-workflow kpi measure <id> [--window-end YYYY-MM-DD]` without a value: it prints the
   recipe for that window, or the script it would run. It records nothing.
2. Take the measurement **by following the recipe, never another way**:
   - `script`: ask the user before running it, then
     `fde-workflow kpi measure <id> --run [--window-end ...]`.
   - `query`: run the printed query with a tool that can reach the data. If none can, ask the user
     to run it and give you the result.
   - `manual`: walk the user through the procedure and ask for the value and where it came from.
3. **Always ask about external factors**: anything outside the project that may have moved the
   value (seasonality, another initiative, an outage, a pricing change). Record "none known" only
   if the user says so.
4. Record it: `fde-workflow kpi measure <id> --value <n> --source "..." --factors "..."
   [--window-end ...]` (`--run` already records script results; add `--factors` to that call).

## Baselines

A baseline is the first measurement, recorded with `--baseline historical|late`:
- **historical**: the window ends **before the work that should move the KPI started**; use
  `--window-end` with a date before that start (ask for it, or take it from the earliest
  linked artifact). Preferred, when the data exists.
- **late**: the data from before is gone, so it is measured now. Tell the user that reports will
  say so, because it misses any impact achieved before it.
Explain the choice to the user and let them decide. When the recipe changed after the baseline
(`[K4]`), measure the baseline again with the new recipe.

## Rules

- Never invent or estimate a value. No access to the data means asking the user.
- Never edit `.fde/measurements.jsonl` by hand; only `fde-workflow kpi measure` writes it.
- Report every result against baseline and target, with its external factors.
