---
max_turns: 20
allowed_tools: [Read, Glob, Grep, Bash, Skill, AskUserQuestion]
append_system_prompt: "Eval environment: the fde-workflow CLI is installed at ./bin/fde-workflow (relative to the working directory). Run `./bin/fde-workflow` instead of `fde-workflow`."
env:
  EVAL_SCENARIO: brownfield
---

I want to start using the FDE framework in this existing project.
