# FDE Direction Framework — Design

- **Date:** 2026-10-12
- **Status:** Approved design, pending spec review
- **Scope:** the `fde-workflow` plugin (`plugin/`) and CLI (`cli/`)

## 1. Purpose

Forward Deployed Engineers (FDEs) work inside customer projects where the hardest problems are not
technical: agreeing on what success means, keeping the work pointed at it while everything else
changes, and proving the impact at the end.

`fde-workflow` is a **direction layer** for a repository. It answers two questions, always:

1. **Why does this repository exist?** (North Star, KPIs)
2. **Is the work being done moving us towards it?** (Paths, measurements, stages)

It does **not** plan or execute work. Specs, plans, tasks and code belong to whatever execution
methodology the project uses (superpowers, spec-driven development, spec-kit, or none). The
direction layer only **links to and reads** execution artifacts; it never writes into them.

```
┌────────────── DIRECTION (fde-workflow) ───────────────┐
│ North Star  — near-immutable, changes are recorded    │
│   ├─ KPIs   — primary · secondary · guardrails        │
│   │    └─ Measurements (baseline + history)           │
│   ├─ Paths  — mutable hypotheses that target KPIs     │
│   │    └─ Links ──────────────────────────────────────┼──┐
│   ├─ Stage  — discovery → poc → mvp → … with gates    │  │
│   └─ Decisions — log of direction changes             │  │
└───────────────────────────────────────────────────────┘  │
┌──────── EXECUTION (superpowers, SDD, anything) ───────┐  │
│ specs · plans · PRs · issues  ◄───────────────────────┼──┘
└───────────────────────────────────────────────────────┘
```

### Non-goals

- Creating or managing specs, plans or tasks (execution methodologies do that).
- Technical decision records (ADRs); only direction-level decisions are logged.
- Methodology-specific adapters that parse spec or plan formats.
- Multi-project portfolio views, scheduled measurements, dashboards (deferred; see §9).

## 2. The framework

Seven components. Each has a purpose, its content, and rules. Rules marked **[V]** are enforced by
`fde-workflow validate` or by the CLI command that changes the component.

### 2.1 North Star

**Why the repository exists.** One sentence about an **outcome** for someone — never a solution.

- Content: statement, beneficiary, problem it solves, **non-goals** (what is explicitly out of
  scope), primary KPI, and the customer **sponsor** who approves direction changes.
- Test: *if this is achieved, would the customer call the project a success?*
- ✗ "Build an AI bot for support" (a solution). ✓ "ACME customers resolve their issues without
  waiting for an agent."
- Rules:
  - N1 **[V]** There is exactly one North Star and it names exactly one primary KPI.
  - N2 **[V]** Changing it requires a recorded decision with a reason and the approver.

### 2.2 KPIs

**How we know, objectively, that we are getting closer.**

- Kinds: **primary** (the North Star metric; exactly one), **secondary** (add nuance),
  **guardrail** (must not get worse: cost, error rate, satisfaction…).
- Content: id, name, definition and formula, data source, unit, direction (`increase` or
  `decrease` is better), **numeric target**, measurement window (e.g. `28d`), and a measurement
  **recipe** (§2.5). For a guardrail, the target is the worst acceptable value.
- Rules:
  - K1 **[V]** Every target is a number. "Better than the baseline" is not a target.
  - K2 **[V]** Exactly one KPI is `primary` and it is the North Star's primary KPI.
  - K3 Each KPI's baseline is measured before work that should move it starts.
  - K4 **[V]** If a KPI's recipe changes after its baseline, the baseline must be measured again with
    the new recipe; until then the comparison is flagged as invalid.
  - K5 **[V]** Changing a target requires a recorded decision with a reason and the approver.

### 2.3 Paths

**Bets to move the KPIs.** Each path is a hypothesis: *"If we do X, we expect KPI Y to go from A to
B."*

- Content: id, hypothesis, target KPIs with the expected value for each, status, optional maturity
  (a stage, §2.7, when it differs from the project's), links (§2.4), and the learning when it ends.
- Status: `proposed → active → measuring → validated | discarded`.
  - `active`: execution work is under way. `measuring`: the work is built and the effect is being
    measured. `validated`: a measurement shows the effect. `discarded`: abandoned, kept with its
    learning.
- Rules:
  - P1 **[V]** Every path targets at least one existing KPI.
  - P2 **[V]** *Built is not validated*: a path becomes `validated` only if a KPI it targets has a
    measurement taken after the path became `active`.
  - P3 **[V]** Discarding or validating a path requires a reason and records a decision; discarded
    paths are never deleted.

### 2.4 Links

**The bridge to execution.** References from a path to execution artifacts of any methodology: a
file path in the repository (spec, plan, document) or a URL (PR, issue).

- The project declares where execution artifacts live as glob patterns (`artifacts.globs`), with
  presets for known methodologies (e.g. superpowers: `docs/superpowers/specs/**`,
  `docs/superpowers/plans/**`; spec-kit: `specs/**`).
- Rules:
  - L1 An artifact matching the globs that no path links to is **drift**: either the work is outside
    the direction, or a path is missing. Drift is reported, not blocked.
  - L2 Artifacts that existed before the framework was adopted can be marked **pre-framework**; they
    are listed in reports but are not drift.

### 2.5 Measurements

**The evidence.** Each measurement records: KPI, date taken, the window it covers
(`window_start`, `window_end`), value, source, **external factors** (anything outside the project
that may have moved the value: seasonality, another initiative, an outage…), and the fingerprint
(SHA-256) of the recipe used.

- The **baseline** is the first measurement of a KPI, flagged as such, with a type:
  - `historical`: reconstructed from data that predates the work (same recipe, a past window).
    Preferred.
  - `late`: measured when the work had already started because no earlier data exists. Valid, but
    every report states it, because it does not capture impact achieved before it.
- **Recipes** live in `.fde/measures/` and make every measurement reproducible. Types:
  - `script`: an executable that prints one number on stdout and receives `FDE_WINDOW_START` and
    `FDE_WINDOW_END` (ISO dates) as environment variables.
  - `query`: a query (e.g. SQL) with `{{window_start}}` and `{{window_end}}` placeholders that the
    agent runs through whatever tool has access to the data (an MCP server, a database client).
  - `manual`: a written procedure a person follows; the measurement records where the value came
    from.
- Rules:
  - M1 The agent never improvises how to measure: it follows the KPI's recipe or, if there is none,
    writes one first and gets it approved.
  - M2 **[V]** Measurements are append-only.

### 2.6 Decisions

**The direction log.** Only direction-level decisions: North Star changes, target changes, opening,
validating or discarding a path, stage gate outcomes, scope changes.

- Content: date, type, summary, reason, approver, references.
- Rules:
  - D1 **[V]** Append-only.
  - D2 The CLI records a decision automatically whenever a command changes direction (§2.1, §2.2,
    §2.3, §2.7); `decision add` covers anything else.

### 2.7 Stage

**The project's maturity**, defined by the question each stage answers and the evidence needed to
leave it (its **gate**), following a stage-gate model.

| Stage | Question it answers | Typical gate criteria | KPIs that matter |
|---|---|---|---|
| `discovery` | Is there a problem worth solving that we can measure? | North Star agreed, KPIs defined with baselines, sponsor identified | baselines |
| `poc` | Is it technically feasible with the customer's data and systems? | Feasibility threshold met (e.g. accuracy ≥ X on real data) | technical indicators |
| `mvp` | Does it bring value to real users in a controlled setting? | Real users use it; first measurements trend towards the target | primary KPI, small scale |
| `early-access` | Does it hold up under limited real use? | Primary KPI beats baseline without breaking guardrails | KPIs and guardrails |
| `production` | Does it deliver the value at scale, operably? | Target reached, stable operation, hand-off done | all |
| `closed` | Final state, outcome `completed` or `discontinued` | Value report produced | final vs baseline |

- Gate decisions: **go** (next stage), **recycle** (repeat the stage, criteria may be revised),
  **hold** (pause), **kill** (close as `discontinued`). From `production`, **go** closes the project
  as `completed`.
- Paths may record their own maturity when it differs from the project stage (one path in
  production while another is still a POC). The project stage is what the customer sees.
- Rules:
  - S1 **[V]** Gate criteria are agreed when entering a stage, not when leaving it; the current stage
    must have criteria (warning while missing).
  - S2 **[V]** Every gate decision records the reason and the approver (the sponsor).
  - S3 **[V]** From `mvp` onwards, the primary KPI must have a measurement taken after the stage was
    entered (warning while missing).

## 3. How it is used

| Moment | What happens | Plugin pieces |
|---|---|---|
| Adoption (once per repo) | New repo: initialise and go to discovery. Existing repo: inventory artifacts, infer a draft direction, confirm it, link artifacts, resolve baselines. | `adopt` skill, `init`, `detect` |
| Discovery | Interview and context review produce the North Star, non-goals, sponsor and KPI candidates; KPIs get recipes and baselines. | `discovery`, `kpi` skills |
| Every session | Claude already knows the North Star, the stage, active paths, KPI status and pending warnings. | SessionStart hook, `context` |
| Starting new work | Before or while an execution methodology creates a spec or plan, the work is matched to a path, or flagged as drift. | `path` skill, PostToolUse hook |
| Path built | The path moves to `measuring`; its KPIs are measured with their recipes; it is validated or discarded with its learning. | `path`, `kpi` skills |
| Weekly / milestone | Status report for the sponsor: KPIs vs baseline and target, paths, drift, decisions. | `report` skill |
| Stage change | Gate criteria evaluated with evidence; go / recycle / hold / kill recorded with the sponsor. | `stage` skill |
| Close | Value report: final vs baseline for every KPI, external factors, validated and discarded paths with their learning. | `report` skill |

The entry point is the `fde-workflow` skill: "how are we doing?", "what's next?". It reads the
state and proposes the **next action** (e.g. "two KPIs have no baseline", "the current stage has no
gate criteria", "three new specs are not linked to any path").

### 3.1 Adopting the framework in an existing project

Existing projects already have specs, plans and history, and their "before" may be gone. The
`adopt` skill:

1. Runs `fde-workflow detect` to identify the execution methodology and list existing artifacts.
2. Infers a **draft** direction: a North Star from the README, specs and history; **retroactive
   paths** grouping existing specs and plans; the current stage from evidence (deployments, CI,
   usage), set with `stage set --inferred`. Everything inferred is stored with `confirmed: false`.
3. Confirms the draft with the FDE (and the sponsor where it applies) through the `discovery` skill,
   which starts from the draft instead of from scratch.
4. Links existing artifacts to their paths, marking the rest **pre-framework**.
5. Resolves baselines: `historical` when the data allows it, otherwise `late`, always declared.

## 4. Architecture

### 4.1 Principles

1. **The CLI is the only writer of `.fde/`'s structured files** (`direction.yaml`,
   `measurements.jsonl`, `decisions.jsonl`). It validates, records decisions and enforces the
   rules. Skills never edit those files directly; they only write free-form files: recipes in
   `measures/` and notes in `discovery/`.
2. **Skills bring judgement and conversation**: interviewing, inferring, proposing; they write
   through the CLI.
3. **Hooks only add context and nudges.** They never block and never fail a session: if the CLI is
   missing or `.fde/` does not exist, they exit silently.
4. **Direction links to execution, never writes into it.** Methodology independence comes from
   configurable artifact globs, not from parsing formats.

### 4.2 Data in the customer repository (`.fde/`)

| File | Content | Why |
|---|---|---|
| `direction.yaml` | Project, North Star, stage and gate criteria, KPIs, paths with links, artifact globs and pre-framework list | Current state, validated as a whole |
| `measurements.jsonl` | One measurement per line | Append-only evidence |
| `decisions.jsonl` | One decision per line | Append-only audit trail |
| `measures/<kpi-id>.<ext>` | Recipe of each KPI | Reproducibility |
| `discovery/` | Interview notes and customer context (Markdown) | Grounds the North Star |
| `reports/` | Generated reports (Markdown) | Shared with the customer |

Logs are separate JSONL files so concurrent work merges cleanly. Content (statements, notes,
reports) is written in whatever language the FDE and the customer use; keys and enum values are
fixed English identifiers.

`direction.yaml` (illustrative):

```yaml
schema_version: 1
project:
  name: acme-support
  customer: ACME
  sponsor: "Jane Doe, VP Customer Support"
north_star:
  statement: "ACME customers resolve their issues without waiting for an agent"
  beneficiary: "ACME end customers"
  problem: "Tickets wait a median of 45 minutes for a first agent response"
  non_goals:
    - "Replacing the ticketing system"
  primary_kpi: resolution-time
  confirmed: true
stage:
  current: mvp            # discovery | poc | mvp | early-access | production | closed
  entered: 2026-10-01
  outcome: null           # completed | discontinued, only when closed
  on_hold: false
  gate_criteria:
    - "Primary KPI measured over at least 2 weeks of real usage"
kpis:
  - id: resolution-time
    name: "Median resolution time"
    kind: primary         # primary | secondary | guardrail
    definition: "Median minutes from ticket creation to resolution, closed tickets only"
    source: "Zendesk, tickets table"
    unit: min
    direction: decrease   # increase | decrease
    target: 30
    window: 28d
    recipe: { type: query, file: measures/resolution-time.sql }
paths:
  - id: auto-triage
    hypothesis: "If tickets are classified on arrival, median resolution time drops 20%"
    expects: { resolution-time: 36 }
    status: active        # proposed | active | measuring | validated | discarded
    activated: 2026-10-03
    maturity: null        # optional stage when it differs from the project's
    confirmed: true
    links:
      - docs/superpowers/specs/2026-10-02-auto-triage-design.md
      - https://github.com/acme/support-ai/pull/12
    learning: null
artifacts:
  globs:
    - "docs/superpowers/specs/**"
    - "docs/superpowers/plans/**"
  pre_framework: []
```

Measurement (one JSONL line):

```json
{"kpi": "resolution-time", "taken": "2026-10-01", "window_start": "2026-08-01", "window_end": "2026-08-28", "value": 45, "baseline": "historical", "source": "Zendesk export", "external_factors": "", "recipe_sha256": "…"}
```

Decision (one JSONL line):

```json
{"date": "2026-10-03", "type": "path-open", "summary": "Open path auto-triage", "reason": "…", "approved_by": "Jane Doe", "refs": ["auto-triage"]}
```

Decision types: `north-star-change`, `target-change`, `path-open`, `path-validate`,
`path-discard`, `stage-gate`, `stage-set`, `scope-change`, `other`.

### 4.3 CLI (`fde-workflow`)

Extends the existing Typer application in `cli/src/fde_workflow_cli/`. Every command works on
`.fde/` in the current directory (or `--root`). Commands that change direction require `--reason`,
and `--approved-by` where §2 says so.

| Command | Purpose |
|---|---|
| `init [--preset auto\|superpowers\|spec-kit\|none]` | Create `.fde/` with an empty direction in stage `discovery` and the artifact globs of the preset (`auto` detects them) |
| `detect` | JSON: detected methodology, artifact inventory (path, first commit date), signals of deployment; read-only |
| `validate` | Check the schema and every **[V]** rule; errors exit 1, warnings exit 0 |
| `status` | Human-readable summary: North Star, stage, KPIs (baseline → latest → target), paths, warnings |
| `context [--brief]` | Compact summary for the SessionStart hook and for skills |
| `northstar set …` | Create or change the North Star (a change records a decision) |
| `northstar confirm` | Mark an inferred North Star as confirmed |
| `kpi add\|update <id> …` | Define or change a KPI (target change records a decision) |
| `kpi measure <id> [--baseline historical\|late] [--window-end DATE] [--value N --source TEXT] [--factors TEXT] [--run]` | Record a measurement. For `script` recipes, `--run` executes the recipe and records its output; without `--run` it prints the command it would run. For `query` and `manual` recipes, `--value` and `--source` are required |
| `path add\|update <id> …` | Define or change a path (`add` records `path-open`) |
| `path move <id> <status> --reason` | Change status, enforcing P2 and P3; moving to `active` sets `activated` |
| `path link <id> <ref>…` / `path link --pre-framework <ref>…` | Link artifacts to a path, or mark them pre-framework |
| `path confirm <id>` | Mark an inferred path as confirmed |
| `stage set <stage> --reason [--inferred]` | Set the stage directly, without a gate; used when adopting an existing project (records `stage-set`) |
| `stage criteria <criterion>…` | Set the current stage's gate criteria |
| `stage decide go\|recycle\|hold\|kill --reason --approved-by` | Record a gate decision and apply it |
| `decision add …` | Record any other direction decision |
| `drift` | List artifacts matching the globs that are neither linked nor pre-framework |
| `report status\|close` | Write a Markdown report with the data tables to `.fde/reports/` and print its path |
| `hook session-start` / `hook post-tool-use` | Hook entry points: read the hook JSON from stdin, print hook output; always exit 0 |
| `doctor` (existing) | Adds a check: when `.fde/` exists, its `schema_version` is supported |

### 4.4 Skills (`plugin/skills/`)

Skill names, descriptions and bodies are in English; the skills converse in the user's language.
Each skill uses `allowed-tools` for read-only CLI commands only, so every command that writes or
runs a recipe goes through Claude Code's permission prompt.

| Skill | Triggers | What it does |
|---|---|---|
| `fde-workflow` (replaces the template skeleton) | "How are we doing?", "what's next?", opening a project | Reads `fde-workflow status`/`validate`, proposes the next action and hands over to the right skill. Without `.fde/`, offers `adopt` |
| `setup` (existing) | Installing or checking the CLI | Unchanged, plus: when the CLI is ready and the current repo has no `.fde/`, offers `adopt` |
| `adopt` | "Use the framework here", first use in a repo | New repo: `init` with a preset, then `discovery`. Existing repo: §3.1 |
| `discovery` | New project, "let's define the North Star", or handed a draft by `adopt` | Guided interview (problem, beneficiary, current process, data, constraints, sponsor) plus review of the repository and customer documents; checks the North Star is an outcome, not a solution; writes notes to `.fde/discovery/`; proposes KPIs and hands each to `kpi` |
| `kpi` | "Define this KPI", "measure the baseline", "how is KPI X doing?" | **Define**: definition, kind, target, window, and the recipe file. **Measure**: runs the recipe with the tools available (CLI `--run` for scripts, an MCP server or client for queries) or asks a person for the value with its evidence; always asks about external factors; in baseline mode decides `historical` vs `late` |
| `path` | "Let's open a path", "this is built", "we're dropping X", starting new work | Path lifecycle; alignment check for new work ("which path does this serve?"); links artifacts; moves to `measuring` and calls `kpi`; validates only with evidence |
| `stage` | "We're moving to MVP", "are we ready for production?" | Agrees gate criteria on entry; evaluates them with evidence on exit; records the decision with the sponsor |
| `report` | "Prepare the sponsor update", "closing report" | Generates the report with the CLI and writes the narrative: KPIs vs baseline and target, external factors, late baselines, paths and learning, drift, decisions |

### 4.5 Hooks (`plugin/hooks/hooks.json`)

| Event | Matcher | Behaviour |
|---|---|---|
| `SessionStart` | — | Runs `fde-workflow hook session-start`, which adds `context --brief` as session context when `.fde/` exists |
| `PostToolUse` | `Write` | Runs `fde-workflow hook post-tool-use`; when the written file matches `artifacts.globs` and is neither linked nor pre-framework, adds context asking Claude to confirm with the user which path the artifact serves |

A small wrapper script calls the CLI only if it is on `PATH`; otherwise it exits 0 silently. The
plugin is installed for every project, so hooks stay silent in repositories without `.fde/`.
A hook on every user prompt was considered and rejected: constant alignment checks would be noise.

## 5. Error handling

- **CLI missing:** hooks stay silent; skills hand over to `setup`.
- **No `.fde/`:** hooks stay silent; `fde-workflow` and `setup` offer `adopt`; other commands fail
  with a hint to run `fde-workflow init`.
- **Invalid `.fde/`:** `validate` lists every problem with its location; write commands refuse to
  write when the result would be invalid, leaving files unchanged.
- **Unsupported `schema_version`:** commands fail with a hint to upgrade the CLI; `doctor` reports it.
- **Recipe failures:** a non-zero exit or a non-numeric output records nothing and shows the
  recipe's stderr.
- **Recipe execution:** only with `--run`, which is not in any skill's `allowed-tools`, so the user
  approves each execution.
- **Hooks:** always exit 0; internal errors are written to stderr and never interrupt the session.

## 6. Testing

- **CLI:** unit tests in `cli/tests/` for the data model, every **[V]** rule (valid and invalid
  fixtures), each command's effects on `.fde/` (including automatic decisions), recipe execution,
  `detect` on fixture repositories, and hook input/output.
- **Skills:** one eval per skill with the existing pattern in `plugin/evals/` (fake CLI, graders).
  Examples: `discovery` rejects a North Star that is a solution; `path` does not validate a path
  without a measurement; `kpi` asks about external factors and declares the baseline type; `adopt`
  on a repository with superpowers specs proposes retroactive paths marked unconfirmed; the
  PostToolUse context leads to an alignment question. Evals run only with the owner's approval.
- `make cli-check` and `make plugin-check` stay the gates before each commit.

## 7. Delivery phases

1. **Core, usable on a real project:** data model; CLI `init`, `detect`, `validate`, `status`,
   `context`, `northstar`, `kpi`, `path` (including `link`), `stage`, `decision`, `hook
   session-start`, `doctor` check; skills `fde-workflow`, `adopt`, `discovery`, `kpi`, `path`, and
   the `setup` hand-over; SessionStart hook. → **Used on a real customer project before phase 2.**
2. **Governance:** CLI `drift`, `report`, `hook post-tool-use`; skills `stage` and `report`;
   PostToolUse hook.
3. **Only if real use asks for it:** a measurement subagent, scheduled measurements, a
   multi-project view.

Each phase gets its own implementation plan.

## 8. Foundations

The framework as a whole is a synthesis for this plugin, not a published, validated method. Its
parts rest on the following sources, with different levels of evidence.

**Peer-reviewed research and research-based references**

| Framework element | Source |
|---|---|
| Numeric, specific targets (K1) | Locke, E. A., & Latham, G. P. (2002). Building a practically useful theory of goal setting and task motivation: A 35-year odyssey. *American Psychologist, 57*(9), 705–717. https://doi.org/10.1037/0003-066X.57.9.705 — and Locke, E. A., & Latham, G. P. (1990). *A theory of goal setting & task performance*. Prentice Hall. |
| Guardrail KPIs, fixed measurement method (K4) | Ordóñez, L. D., Schweitzer, M. E., Galinsky, A. D., & Bazerman, M. H. (2009). Goals gone wild: The systematic side effects of overprescribing goal setting. *Academy of Management Perspectives, 23*(1), 6–16. https://doi.org/10.5465/amp.2009.37007999 |
| Same | Goodhart, C. A. E. (1975/1976). Problems of monetary management: The U.K. experience. In *Papers in Monetary Economics* (Vol. 1). Reserve Bank of Australia. (Presented 1975, printed 1976; origin of Goodhart's law.) |
| Same | Campbell, D. T. (1979). Assessing the impact of planned social change. *Evaluation and Program Planning, 2*(1), 67–90. https://doi.org/10.1016/0149-7189(79)90048-X |
| One primary KPI plus guardrails; measurement trustworthiness | Kohavi, R., Tang, D., & Xu, Y. (2020). *Trustworthy online controlled experiments: A practical guide to A/B testing*. Cambridge University Press. https://doi.org/10.1017/9781108653985 — ch. 7 (Overall Evaluation Criterion) and ch. 21 (guardrail metrics). |
| Stages with evidence-based gates and go/kill decisions | Cooper, R. G. (1990). Stage-gate systems: A new tool for managing new products. *Business Horizons, 33*(3), 44–54. https://doi.org/10.1016/0007-6813(90)90040-I |
| Maturity levels defined by demonstrated evidence | Mankins, J. C. (1995). *Technology readiness levels: A white paper*. NASA, Office of Space Access and Technology. |

**Practitioner literature (widely adopted, not peer-reviewed)**

| Framework element | Source |
|---|---|
| Outcome-oriented goals with measurable key results | Grove, A. S. (1983). *High output management*. Random House. — Doerr, J. (2018). *Measure what matters*. Portfolio/Penguin. |
| North Star and its metric | Ellis, S., & Brown, M. (2017). *Hacking growth*. Crown Business. (Ellis is commonly credited with popularising the North Star Metric; no primary first-use source was found.) — Cutler, J., & Scherschligt, J. (2019). *The North Star playbook*. Amplitude. https://amplitude.com/books/north-star |
| Paths as hypotheses validated by evidence (P2) | Ries, E. (2011). *The lean startup*. Crown Business. — Torres, T. (2021). *Continuous discovery habits*. Product Talk LLC. |
| Diagnosis → guiding policy → coherent actions (problem → North Star → paths) | Rumelt, R. P. (2011). *Good strategy bad strategy: The difference and why it matters*. Crown Business. |

There is almost no academic literature on the FDE role itself; it is described mainly in industry
writing.

**Known limitation.** Comparing a KPI before and after the work does not prove causation: the value
may move because of factors outside the project. The framework does not require controlled
experiments, but every measurement records external factors and every report states them, together
with late baselines, so that the claimed impact stays honest.

## 9. Deferred

- Measurement subagent, scheduled measurements, multi-project view (phase 3, only if needed).
- Methodology adapters that read plan progress (rejected for now: they couple the plugin to formats
  it does not own).
