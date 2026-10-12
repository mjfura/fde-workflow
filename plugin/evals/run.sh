#!/bin/sh
# Run the plugin eval suite against the fake fde-workflow CLI (evals/stub/): no real work
# is done. Uses model calls on your account (plan usage or API billing), capped by --max-cost-usd.
#   EVAL_MODEL     model under test (default: sonnet)
#   EVAL_MAX_COST  USD ceiling for this run (default: 5)
# Extra arguments go to `claude plugin eval` (e.g. --case 'setup-*' --runs 1 --ablation none).
set -eu
plugin_dir=$(cd "$(dirname "$0")/.." && pwd)
# The eval sandbox cannot read $HOME, so the plugin and the stub are copied outside it.
work=$(mktemp -d /tmp/fde-workflow-eval.XXXXXX)
trap 'rm -rf "$work"' EXIT
mkdir -p "$work/bin"
cp "$plugin_dir/evals/stub/fde-workflow" "$work/bin/fde-workflow"
chmod 755 "$work" "$work/bin" "$work/bin/fde-workflow"
cp -R "$plugin_dir" "$work/plugin"
rm -rf "$work/plugin/evals/results"
# Each case's fixture.sh finds the stub through PATH and copies it into the run's workspace:
# the sandbox only executes and reads files there.
status=0
(
  cd "$work/plugin"
  PATH="$work/bin:$PATH" claude plugin eval . \
    --scaffold --trust-plugin --allow-tools Bash \
    --model "${EVAL_MODEL:-sonnet}" \
    --max-cost-usd "${EVAL_MAX_COST:-5}" \
    "$@"
) || status=$?
if [ -d "$work/plugin/evals/results" ]; then
  mkdir -p "$plugin_dir/evals/results"
  cp -R "$work/plugin/evals/results/." "$plugin_dir/evals/results/"
fi
exit "$status"
