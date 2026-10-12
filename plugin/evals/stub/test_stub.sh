#!/bin/sh
# Tests for the fake fde-workflow CLI used by the plugin evals.
# Run: sh plugin/evals/stub/test_stub.sh
set -u
STUB="$(cd "$(dirname "$0")" && pwd)/fde-workflow"
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
cd "$WORK" || exit 1
export EVAL_STUB_LOG="$WORK/calls.log"
failures=0

check() {  # check NAME EXPECTED_EXIT EXPECTED_SUBSTRING SCENARIO ARGS...
  name=$1 want_exit=$2 want_text=$3 scenario=$4
  shift 4
  out=$(EVAL_SCENARIO="$scenario" sh "$STUB" "$@" 2>&1)
  got_exit=$?
  if [ "$got_exit" -ne "$want_exit" ] || ! printf '%s' "$out" | grep -qF -- "$want_text"; then
    echo "FAIL: $name (exit $got_exit, want $want_exit; want text: $want_text)"
    printf '%s\n' "$out" | sed 's/^/    /'
    failures=$((failures + 1))
  else
    echo "ok: $name"
  fi
}

check "version" 0 "fde-workflow 0.1.0" ready --version
check "missing is command not found" 127 "command not found" missing --version
check "doctor ready" 0 "Ready." ready doctor
check "doctor not ready" 1 "Not ready: 1 problem(s)." not-ready doctor
check "unknown command" 2 "No such command" ready nope
check "no .fde before adoption" 1 "No .fde/" brownfield status
check "fresh status" 0 "No North Star yet" fresh status
check "detect lists specs" 0 "answer-suggestions-design.md" brownfield detect
check "measure shows the recipe" 0 "Take the measurement" kpi-no-baseline kpi measure resolution-time
check "measure records a value" 0 "Recorded." kpi-no-baseline kpi measure resolution-time --value 45 --source s
check "validated needs evidence" 1 "[P2]" path-measuring path move auto-triage validated --reason r
check "validate lists warnings" 0 "[K3]" kpi-no-baseline validate
check "drift" 0 "No drift." path-measuring drift
check "kpi due" 0 "No KPI is due." path-measuring kpi due
check "report writes a file" 0 ".fde/reports/2026-10-12-status.md" path-measuring report status
check "mvp gate status" 0 "Gate: Primary KPI measured" mvp-gate status
check "brownfield init creates the marker" 0 "Created .fde/" brownfield init --preset superpowers
check "brownfield after init has a direction" 0 "North Star: not defined" brownfield status
check "brownfield detect after init" 0 '"fde_initialised": true' brownfield detect
if grep -qF "fde-workflow doctor" "$EVAL_STUB_LOG"; then
  echo "ok: calls are logged"
else
  echo "FAIL: calls are logged"; failures=$((failures + 1))
fi

if [ "$failures" -eq 0 ]; then echo "all stub tests passed"; else echo "$failures failure(s)"; exit 1; fi
