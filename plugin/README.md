# fde-workflow plugin for Claude Code

Direction framework for FDE customer projects: a North Star, KPIs with baselines, paths, stages
and decisions, on top of any execution methodology (superpowers, spec-kit or none).

## Install

In a Claude Code session:

```
/plugin marketplace add mjfura/fde-workflow
/plugin install fde-workflow@fde-workflow
```

Then ask Claude to set it up, or run `/fde-workflow:setup`.

## Skills

| Skill | Use it for |
|---|---|
| `fde-workflow:fde-workflow` | Where the project stands and the next action; stage gates |
| `fde-workflow:adopt` | Set up the framework in a new or existing repository |
| `fde-workflow:discovery` | Define or confirm the North Star, non-goals, sponsor and KPIs |
| `fde-workflow:kpi` | Define KPIs with measurement recipes; measure baselines and progress |
| `fde-workflow:path` | Check new work against the paths; open, link, validate or discard paths |
| `fde-workflow:setup` | Install and check what the plugin needs: the `fde-workflow` CLI |

Claude picks them automatically; you can also call them as slash commands.

## Hooks

`SessionStart` adds the repository's direction (North Star, stage, KPIs, live paths, pending
issues) to every session in a repository with `.fde/`. It does nothing elsewhere, or when the CLI
is not installed.

## Development

See the [repository README](../README.md) and the
[design](../docs/superpowers/specs/2026-10-12-fde-direction-framework-design.md).
