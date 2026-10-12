---
name: discovery
description: 'Define or confirm the direction of a customer project with the FDE: the North Star (an outcome, never a solution), its beneficiary, problem, non-goals, sponsor and candidate KPIs, through a guided interview and a review of the repository and customer documents. Use it when starting a new customer project, when the user says "let us define the North Star", "what is this project for", "define success" or "discovery", when the North Star is missing or unconfirmed, or when the adopt skill hands over a draft.'
allowed-tools:
  - Bash(fde-workflow status)
  - Bash(fde-workflow context)
---

# Discovery: define the direction

Read `../fde-workflow/references/framework.md` (relative to this skill's directory) first, then
run `fde-workflow status` to see what already exists (a draft from the `adopt` skill, or nothing).

## Interview

Ask **one question at a time**; prefer offering options when you can infer them from the
repository or documents. Skip what the documents already answer, and say what you inferred.

1. **Problem:** what hurts today, for whom, and how do they cope now (the current process)?
2. **Beneficiary:** who gets the outcome? (end users, an internal team, the customer's customers)
3. **Outcome:** what will be different for them when this works? This becomes the North Star.
4. **Evidence:** how would we see it in data? Which systems hold that data, and can we access it?
5. **Constraints:** deadlines, data access, security, budget, systems that cannot change.
6. **Non-goals:** what is explicitly out of scope?
7. **Sponsor:** who on the customer side approves direction changes and gate decisions?

Save the notes, with the date and who was interviewed, to
`.fde/discovery/<YYYY-MM-DD>-<topic>.md`.

## North Star check

Before recording it, test the statement with the user:
- It names an **outcome for someone**, not a solution or deliverable. "Build an AI chatbot" is a
  solution; "ACME customers resolve their issues without waiting for an agent" is an outcome.
  When the user gives a solution, ask what it is for and propose an outcome version.
- *If this is achieved, would the customer call the project a success?*
- It can be measured by one primary KPI.

## Record

1. Propose KPIs from the evidence answers: exactly one primary, the secondary ones that add nuance,
   and guardrails (cost, errors, satisfaction) that must not get worse. Define each with the `kpi`
   skill; it writes the recipe and measures the baseline.
2. Record the customer and the sponsor:
   `fde-workflow project set --customer "..." --sponsor "<name, role>"`.
3. Record the North Star once the user agrees on the wording:
   `fde-workflow northstar set --statement "..." --beneficiary "..." --problem "..."
   --non-goal "..." --primary-kpi <id>`. Draft from `adopt`: update it the same way, then
   `fde-workflow northstar confirm --approved-by "<who>"` when the user confirms it.
4. Agree the gate criteria of the current stage with the `stage` skill.
5. Finish with `fde-workflow status` and a short summary.

## Rules

- Never record a North Star, KPI or target the user has not agreed to.
- A confirmed North Star only changes with a reason and the sponsor's approval
  (`--reason`, `--approved-by`).
