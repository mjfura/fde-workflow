---
name: report
description: 'Prepare the reports of an FDE customer project from its .fde/ direction: the status update for the sponsor (KPIs against baseline and target, paths, drift, decisions) and the closing value report. Use it when the user asks for a status update, weekly or monthly report, sponsor or customer update, progress summary, or the closing, final or value report of the project.'
allowed-tools:
  - Bash(fde-workflow status)
  - Bash(fde-workflow validate)
  - Bash(fde-workflow kpi due)
---

# Reports

Read `../fde-workflow/references/framework.md` (relative to this skill's directory) first.

## Steps

1. Run `fde-workflow kpi due`. If any KPI is due, offer to measure it first with the `kpi`
   skill: a report with stale numbers misleads the sponsor.
2. Generate the data: `fde-workflow report status` (the decisions since the previous status
   report; `--since YYYY-MM-DD` to choose) or `fde-workflow report close` for the closing report.
   It prints the path of the new file in `.fde/reports/`.
3. Read the file and add a `## Summary` section right after the title block, in the language the
   report is for:
   - **Status:** where the project stands against the North Star; what moved, with numbers
     against the baseline and the target; what is next; decisions needed from the sponsor.
   - **Close:** the outcome against the North Star and every KPI's target, which paths were
     validated or discarded and what they taught, and what the customer's team owns now.
   Keep it to a few short paragraphs.
4. Show the user the summary and the file path; they decide how to share it.

## Rules

- Every number comes from the report's data sections; never add numbers the CLI did not produce.
- Name the external factors and late baselines that qualify a number, and never claim the work
  caused a change the data cannot attribute to it.
- Edit only the `## Summary` section; the data sections are the record.
