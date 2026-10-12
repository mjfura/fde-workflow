# FDE Direction Framework — Remaining Scope Implementation Plan

> **For agentic workers:** executed inline (superpowers:executing-plans) by the same session that
> wrote it. Every task is test-first: write the named tests, watch them fail, implement, run
> `make check`, commit.

**Goal:** Ship the rest of the design in one release: `drift`, `report`, `kpi due` (rule K6),
`portfolio`, the PostToolUse hook, the `stage` and `report` skills and the `kpi-measurer` agent.

**Architecture:** Same as v0.1.x: the CLI owns `.fde/` and the rules; skills and the agent bring
judgement; hooks only add context. New CLI modules: `report.py` (Markdown reports) and
`registry.py` (portfolio registry outside the repository).

**Tech Stack:** Python 3.13, Typer, pydantic, PyYAML, pytest, ruff, mypy; Claude Code skills,
agents, hooks and evals.

**Spec:** `docs/superpowers/specs/2026-10-12-fde-direction-framework-design.md` (§2.2 K6, §4.2
registry, §4.3 commands, §4.5 agent, §4.6 hooks, §7 delivery).

## Global Constraints

- Same as the phase 1 plan: Python `>=3.13`, no new dependencies, ruff + mypy strict,
  `make check` before every commit, English in git, Conventional Commits, no AI attribution.
- Tests never touch the real home directory: an autouse fixture points `XDG_CONFIG_HOME` at a
  temporary directory.
- Hooks always exit 0 and stay silent without `.fde/` or the CLI.
- Evals run only with the owner's approval.

## Review Focus

1. A KPI measured exactly one window ago is due; one day less is not; closed projects have no due
   KPIs; KPIs without a baseline are K3, not K6.
2. The PostToolUse hook ignores files outside the globs, files already linked or pre-framework,
   tools other than Write, malformed input and repositories without `.fde/`.
3. Reports never overwrite an earlier report of the same day.
4. The portfolio survives a registered repository that was deleted or whose `.fde/` is broken.
5. The registry is never written by tests to the real home directory.

## Tasks

### Task 1: Rule K6 and `kpi due`
- `rules.due_kpis(direction, measurements) -> list[tuple[Kpi, Measurement]]` (uses
  `clock.today()`); `rules.check` adds warning `K6` per due KPI.
- `fde-workflow kpi due`: one line per due KPI (`id: last measured on DATE (window Nd)`), or
  `No KPI is due.`
- Tests: `test_kpi_is_due_after_a_full_window`, `test_kpi_is_not_due_within_its_window`,
  `test_closed_projects_have_no_due_kpis`, `test_kpi_without_baseline_is_not_due`,
  `test_kpi_due_lists_due_kpis`.

### Task 2: `drift`
- `detect.drift(root, direction) -> list[str]`: artifacts matching the globs, neither linked nor
  pre-framework. `fde-workflow drift` prints them or `No drift.`; exit 0.
- Tests: `test_drift_lists_unlinked_artifacts_only`, `test_drift_command`.

### Task 3: PostToolUse hook
- `hook.post_tool_use_context(payload) -> str | None`; `fde-workflow hook post-tool-use` prints
  `{"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": ...}}`.
- `plugin/hooks/hooks.json`: `PostToolUse` with matcher `Write`.
- Tests: `test_post_tool_use_asks_about_a_new_unlinked_artifact`,
  `test_post_tool_use_ignores_linked_and_unmatched_files`,
  `test_post_tool_use_is_silent_without_fde_or_with_bad_input`.

### Task 4: Reports
- `report.render(kind, direction, measurements, decisions, issues, drift, since) -> str`; sections:
  North Star and stage, KPIs (baseline with type, latest, target, change, target met, external
  factors), paths (status, expectations, links, learning), drift, decisions, notes (late
  baselines, before/after limitation).
- `fde-workflow report status|close [--since DATE]` writes `.fde/reports/<date>-<kind>.md`
  (`-2`, `-3`… when it exists) and prints the path; `status` defaults `--since` to the date of
  the latest status report.
- Tests: `test_report_lists_kpis_against_baseline_and_target`,
  `test_report_declares_late_baselines_and_the_limitation`,
  `test_status_report_lists_decisions_since_the_previous_one`,
  `test_reports_never_overwrite_each_other`.

### Task 5: Portfolio
- `registry.py`: `registry_file()`, `register(root)`, `forget(root)`, `registered()`;
  `init`, `status`, `validate`, `context` and the SessionStart hook register the repository.
- `fde-workflow portfolio` and `portfolio forget PATH`.
- Tests: `test_init_and_status_register_the_repository`, `test_portfolio_summarises_each_project`,
  `test_portfolio_survives_missing_and_broken_repositories`, `test_portfolio_forget`.

### Task 6: `kpi-measurer` agent
- `plugin/agents/kpi-measurer.md`; the `kpi` skill delegates query and manual investigations to it.

### Task 7: Skills
- New `stage` and `report` skills; `fde-workflow` hands over to them and reports due KPIs and
  drift; `path` mentions the PostToolUse prompt; `kpi` mentions due KPIs and the agent;
  `references/framework.md` adds K6.

### Task 8: Evals
- Stub: `drift`, `kpi due`, `report`, `stage decide`, `portfolio`.
- Cases: `stage-gate-needs-the-sponsor` (no `stage decide` without sponsor approval) and
  `report-uses-the-cli` (runs `fde-workflow report status`).

### Task 9: Documentation
- `plugin/README.md` (skills, agent, hooks), `cli/README.md` (commands).
