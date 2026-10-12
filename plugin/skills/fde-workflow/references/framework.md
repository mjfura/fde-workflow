# The FDE direction framework

A direction layer for a repository: **why it exists** and **whether the work moves us towards
it**. It never plans or executes work: specs, plans and tasks belong to the project's execution
methodology (superpowers, spec-kit, anything). The framework links to them and reads them.

Full design: https://github.com/mjfura/fde-workflow/blob/main/docs/superpowers/specs/2026-10-12-fde-direction-framework-design.md

## Components

| Component | What it is | Rules |
|---|---|---|
| **North Star** | One sentence about an outcome, for someone; never a solution. Plus beneficiary, problem, non-goals, primary KPI, and the customer sponsor who approves direction changes. Test: *if this is achieved, would the customer call the project a success?* | N1 one North Star naming one primary KPI. N2 changing it records a decision with reason and approver. |
| **KPIs** | `primary` (exactly one, the North Star metric), `secondary`, `guardrail` (must not get worse; its target is the worst acceptable value). Definition, source, unit, direction, numeric target, window, recipe. | K1 targets are numbers. K2 one primary. K3 baseline before the work that should move it. K4 a recipe change invalidates the baseline. K5 a target change records a decision. |
| **Paths** | Hypotheses: *if we do X, we expect KPI Y to go from A to B.* Status `proposed → active → measuring → validated \| discarded`. | P1 every path targets an existing KPI. P2 built is not validated: validation needs a measurement whose whole window comes after the path became active. P3 validating or discarding records a decision; discarded paths keep their learning. |
| **Links** | References from a path to execution artifacts: files (specs, plans) or URLs (PRs, issues). | L1 an artifact matching the artifact globs that no path links to is drift. L2 artifacts from before adoption can be marked pre-framework. |
| **Measurements** | Value, window, source, external factors, recipe fingerprint. The first one, flagged as baseline, is `historical` (reconstructed from data before the work) or `late` (measured once work had started; reports must say so). | M1 never improvise how to measure: follow the KPI's recipe (`script`, `query` or `manual`, in `.fde/measures/`). M2 append-only. |
| **Decisions** | Direction-level only: North Star, targets, paths, stage gates, scope. Not technical ADRs. | D1 append-only. D2 the CLI records them automatically. |
| **Stage** | `discovery → poc → mvp → early-access → production → closed`, each with gate criteria agreed on entry. Gate decisions: go, recycle, hold, kill. | S1 criteria agreed on entry. S2 gate decisions record reason and approver. S3 from mvp on, the primary KPI is measured in the stage. |

Items inferred from existing work (by the adopt skill) stay unconfirmed (rule C1) until the FDE,
and the sponsor where it applies, confirm them.

## Files

`.fde/direction.yaml`, `.fde/measurements.jsonl` and `.fde/decisions.jsonl` are written **only**
by the `fde-workflow` CLI, which validates every change. Skills write free-form files only:
recipes in `.fde/measures/` and notes in `.fde/discovery/`.

## Limitation

Before/after comparisons do not prove causation. Record external factors with every measurement
and state them, and any late baseline, in every report.
