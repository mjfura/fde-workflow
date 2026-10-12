# fde-workflow-cli

Command line tool of the `fde-workflow` Claude Code plugin: it reads and writes a repository's
FDE direction in `.fde/` and enforces the framework's rules.

```sh
uv tool install fde-workflow-cli    # or: pipx install fde-workflow-cli
fde-workflow --version
fde-workflow doctor                 # checks that everything is ready
```

| Command | Purpose |
|---|---|
| `init`, `detect` | Set up `.fde/`; inspect a repository's methodology and artifacts |
| `status`, `context`, `validate` | Summaries for people and for Claude; rule checks |
| `northstar set\|confirm` | The North Star |
| `kpi add\|update\|measure` | KPIs, their recipes and measurements |
| `path add\|update\|move\|link\|confirm` | Paths and their links to execution work |
| `stage set\|confirm\|criteria\|decide` | The project stage and its gates |
| `decision add` | Other direction decisions |
| `hook session-start` | Entry point of the plugin's SessionStart hook |

Run `fde-workflow <command> --help` for the options. Requires Python 3.13 or newer. Source and
plugin: https://github.com/mjfura/fde-workflow
