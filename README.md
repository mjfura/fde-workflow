# fde-workflow

Marketplace with a plugin for working with FDE frameworks, best practices and workflow conventions for FDE roles.

This repository is a Claude Code plugin marketplace with one plugin, `fde-workflow`, in
[`plugin/`](plugin/), and the Python packages it uses, published to PyPI.

## Install

In a Claude Code session:

```
/plugin marketplace add mjfura/fde-workflow
/plugin install fde-workflow@fde-workflow
```

Then ask Claude to set it up, or run `/fde-workflow:setup`.

## Layout

| Path | What it is |
|---|---|
| `.claude-plugin/marketplace.json` | The marketplace; it lists the plugin in `plugin/` |
| `plugin/` | The Claude Code plugin: manifest and skills, evals |
| `cli/` | The `fde-workflow` CLI, published to PyPI as `fde-workflow-cli` |
| `docs/releasing.md` | How to publish a release |

## Development

Requirements: Python 3.13, [Poetry](https://python-poetry.org/) 2, [uv](https://docs.astral.sh/uv/)
and Claude Code.

```sh
git config core.hooksPath .githooks   # once per clone: git-workflow hooks
make install                          # development environment of every package
make check                            # what CI checks on a pull request
```

To try the plugin from this checkout, run `make plugin-check` first: it also checks the PyPI
names of the packages the plugin installs.

```sh
make plugin-check
claude --plugin-dir ./plugin
```

The plugin installs `fde-workflow-cli` from PyPI by name; the check
accepts a name that is not on PyPI yet or whose latest release this repository published (PyPI's
verified Trusted Publishing provenance). If a name is
taken by someone else, the check fails: rename the package first (see
[`docs/releasing.md`](docs/releasing.md)), or the plugin would run their code.

`plugin/evals/run.sh` runs Claude against a fake CLI to check the skills. It uses model calls on
your account: run it when the skills change, never in CI.

## One-time GitHub setup

Right after Backstage creates the repository:

1. Protect `main` with the git-workflow skill:
   `~/.claude/skills/git-workflow/scripts/github-setup.sh --check plugin --check cli`
2. Create the `pypi` environment and the PyPI trusted publishers described in
   [`docs/releasing.md`](docs/releasing.md).
3. Push the `v0.1.0` tag (the repository is already at 0.1.0) to publish the first release: until
   then anyone can register the PyPI names and the plugin would run their code (see
   [`docs/releasing.md`](docs/releasing.md)).

Releases: [`docs/releasing.md`](docs/releasing.md).
