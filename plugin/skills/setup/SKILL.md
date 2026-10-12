---
name: setup
description: 'Install, verify or troubleshoot what the fde-workflow plugin needs: the `fde-workflow` CLI (PyPI package `fde-workflow-cli`). Use it when the user wants to set up the fde-workflow plugin, asks whether it is ready, or shares an error such as "command not found".'
allowed-tools:
  - Bash(fde-workflow --version)
  - Bash(fde-workflow doctor)
---

# Set up fde-workflow

## The `fde-workflow` CLI

`fde-workflow` (PyPI package `fde-workflow-cli`, Python 3.13+) is ready when it
is installed and `fde-workflow doctor` ends with `Ready.`

1. Run `fde-workflow --version`.
   - **Command not found:** check `command -v uv` and `command -v pipx`. Propose
     `uv tool install fde-workflow-cli` (or `pipx install fde-workflow-cli`; if the
     default Python is older than 3.13, `pipx install --python python3.13 fde-workflow-cli`)
     and run it only after the user agrees. Without uv or pipx, point to
     https://docs.astral.sh/uv/getting-started/installation/. Before installing, check that
     https://pypi.org/project/fde-workflow-cli/ links to https://github.com/mjfura/fde-workflow;
     if it does not exist or points elsewhere, stop and tell the user instead of installing.
   - **Installed:** to upgrade, propose `uv tool upgrade fde-workflow-cli` (or
     `pipx upgrade fde-workflow-cli`), with the same consent rule.
2. Run `fde-workflow doctor` (exit 0 = ready, 1 = at least one ✗) and follow the hint
   printed next to each ✗.
3. Repeat `fde-workflow doctor` until it ends with `Ready.`

