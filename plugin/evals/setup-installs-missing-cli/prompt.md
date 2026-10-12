---
max_turns: 15
allowed_tools: [Read, Glob, Grep, Skill, AskUserQuestion]
append_system_prompt: "Eval environment: the fde-workflow CLI is installed at ./bin/fde-workflow (relative to the working directory). Run `./bin/fde-workflow` instead of `fde-workflow`."
env:
  EVAL_SCENARIO: missing
---

I want to use the fde-workflow plugin. Can you set it up?
