# Releasing

One version for the whole repository. A `vX.Y.Z` tag on `main` runs
`.github/workflows/release.yml`, which publishes `fde-workflow-cli` to PyPI and creates a GitHub
Release. Plugin users receive the new plugin when the `plugin.json` version changes.

## One-time setup (owner)

1. Create a PyPI account at <https://pypi.org/account/register/> and enable 2FA.
2. For the package, *Your account → Publishing → Add a new pending publisher*
   (GitHub tab):
   - PyPI project name: `fde-workflow-cli`
   - Owner: `mjfura` · Repository: `fde-workflow`
   - Workflow name: `release.yml` · Environment name: `pypi`
3. In GitHub, *Settings → Environments → New environment*: `pypi`. Optionally add yourself as a
   required reviewer to approve each publication.

No tokens or passwords are stored anywhere: PyPI trusts the workflow through OIDC.

`make plugin-check` and `plugin.yml` run `.github/scripts/check_pypi_names.py`, which accepts a
package that is already on PyPI only when every file of its latest release has Trusted Publishing provenance from
this repository, as verified by PyPI. `release.yml` produces it automatically:
`pypa/gh-action-pypi-publish` attaches the attestations by default when it publishes through a
trusted publisher. Project URLs are not enough, since anyone who uploads a package can set them.

PyPI rejects a name that matches an existing project once `-`, `_` and `.` are removed, and
`make plugin-check` fails when a name already belongs to a project that this repository did not
publish. In either case, choose another distribution name and change it in the package's
`pyproject.toml` (`[project].name`) and in `plugin/skills/setup/SKILL.md`. Command names can stay.

**Publish the first release early.** The `setup` skill installs
packages from PyPI by name. Until the first release is published, anyone can register
`fde-workflow-cli` and the plugin would run their code. Right after creating the repository:
set up the trusted publishers and push the `v0.1.0` tag (the repository is already at 0.1.0),
which registers the name under your account.

## Each release

1. Pick the version: `~/.claude/skills/git-workflow/scripts/next-version.sh --verbose`.
2. Open a PR `chore(release): vX.Y.Z` that changes only the version in
   `plugin/.claude-plugin/plugin.json`, `cli/pyproject.toml`, in canonical form (`0.2.0rc1` for `v0.2.0-rc.1`); `make plugin-check`
   verifies them. If `plugin/` changed since the last tag, the owner may run the evals first
   and paste the summary in the PR.
3. Merge it and tag right away.
   ```bash
   git switch main && git pull --ff-only
   git tag -a vX.Y.Z -m "Release vX.Y.Z"
   git push origin vX.Y.Z
   ```
4. Watch it: `gh run watch $(gh run list --workflow release.yml --limit 1 --json databaseId --jq '.[0].databaseId')`.
5. Smoke test from a clean environment: `uvx --from fde-workflow-cli==X.Y.Z fde-workflow --version`.

If a job fails before publishing, nothing is published: fix it on `main` and tag the next version
(PyPI never accepts the same version twice). Pre-release tags (`-rc.N`) create
pre-releases that `uv tool install` and `pipx install` ignore unless asked.
