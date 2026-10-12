#!/usr/bin/env bash
# Workspace for the plugin evals. run.sh puts the fake fde-workflow first on PATH; the
# eval sandbox only reads and executes files inside the workspace, so the stub is copied into ./bin.
set -eu
stub=$(command -v fde-workflow)
grep -q "Fake fde-workflow CLI" "$stub" || { echo "refusing: $stub is not the fake fde-workflow" >&2; exit 1; }
mkdir -p bin
cp "$stub" bin/fde-workflow && chmod 755 bin/fde-workflow
