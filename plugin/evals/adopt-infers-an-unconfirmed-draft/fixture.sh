#!/usr/bin/env bash
# Workspace for the plugin evals. run.sh puts the fake fde-workflow first on PATH; the
# eval sandbox only reads and executes files inside the workspace, so the stub is copied into ./bin.
set -eu
stub=$(command -v fde-workflow)
grep -q "Fake fde-workflow CLI" "$stub" || { echo "refusing: $stub is not the fake fde-workflow" >&2; exit 1; }
mkdir -p bin
cp "$stub" bin/fde-workflow && chmod 755 bin/fde-workflow
mkdir -p docs/superpowers/specs docs/superpowers/plans
cat > README.md <<'MD'
# acme-support-ai
AI assistance for ACME's support agents: ticket triage and answer suggestions.
MD
printf '# Auto-triage design\nClassify incoming tickets so they reach the right queue at once.\n' > docs/superpowers/specs/2026-08-18-auto-triage-design.md
printf '# Auto-triage plan\n- [x] Classifier\n- [x] Routing\n' > docs/superpowers/plans/2026-08-20-auto-triage.md
printf '# Answer suggestions design\nSuggest replies to agents from past resolved tickets.\n' > docs/superpowers/specs/2026-09-10-answer-suggestions-design.md
