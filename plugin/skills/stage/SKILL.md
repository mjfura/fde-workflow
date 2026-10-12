---
name: stage
description: 'Manage the stage of an FDE customer project (discovery, poc, mvp, early-access, production, closed) and its gates: agree gate criteria when entering a stage, evaluate them with evidence before leaving, and record go, recycle, hold or kill with the sponsor. Use it when the user says "we are moving to MVP", "are we ready for production?", "let us pause the project", "should we stop?", asks about gate criteria, or when the current stage has none.'
allowed-tools:
  - Bash(fde-workflow status)
  - Bash(fde-workflow validate)
  - Bash(fde-workflow context)
---

# Stages and gates

Read `../fde-workflow/references/framework.md` (relative to this skill's directory) first, then
run `fde-workflow status`.

Each stage answers one question: `discovery` (is there a problem worth solving that we can
measure?), `poc` (is it technically feasible with the customer's data and systems?), `mvp` (does
it bring value to real users in a controlled setting?), `early-access` (does it hold up under
limited real use?), `production` (does it deliver the value at scale, operably?).

## Entering a stage: agree the gate criteria

1. Propose criteria that answer the stage's question with evidence that can be checked, e.g.
   "primary KPI measured over 2 weeks of real use and at least 10% better than the baseline",
   "no guardrail KPI worse than its target". Avoid criteria that are only "built" or "done".
2. Agree them with the user, who agrees them with the sponsor, then record them:
   `fde-workflow stage criteria "<criterion>" "<criterion>"`.
3. Changing agreed criteria moves the goalposts: it needs
   `--reason "..." --approved-by "<sponsor>"` and is logged.

## Leaving a stage: evaluate the gate

1. Make sure the evidence is current: `fde-workflow kpi due` and the `kpi` skill for anything due.
2. Go through each criterion with the user: met or not, and the evidence (measurements, linked
   work, decisions). Say plainly when the evidence is missing.
3. Propose one decision and explain it:
   - **go**: every criterion is met (`--to <stage>` skips a stage when the evidence covers it);
   - **recycle**: not met yet, and the paths can still get there;
   - **hold**: paused, for a reason outside the evidence (budget, access, priorities);
   - **kill**: the evidence says the outcome is not reachable. Stopping early with evidence is a
     good result, not a failure.
4. Never decide on the user's behalf. Ask who on the customer side approved it, then:
   `fde-workflow stage decide go|recycle|hold|kill --reason "<the evidence>" --approved-by "<sponsor>"`.
5. After **go**, agree the next stage's criteria right away. A go from `production` closes the
   project as completed; offer the closing report (the `report` skill).

## Inferred stage

A stage set by the `adopt` skill is a hypothesis. Check it against the evidence with the user,
then `fde-workflow stage confirm --approved-by "<who>"` or correct it with
`fde-workflow stage set <stage> --reason "..."`.
