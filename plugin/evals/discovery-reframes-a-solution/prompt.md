---
max_turns: 20
allowed_tools: [Read, Glob, Grep, Bash, Skill, AskUserQuestion]
append_system_prompt: "Eval environment: the fde-workflow CLI is installed at ./bin/fde-workflow (relative to the working directory). Run `./bin/fde-workflow` instead of `fde-workflow`."
env:
  EVAL_SCENARIO: fresh
---

Let's define the North Star of this project: build an AI chatbot for ACME's support team.
