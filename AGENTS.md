# AGENTS.md

The full instructions for coding agents are in [CLAUDE.md](CLAUDE.md). Read it first. This file repeats only the commands and loop conventions that tools look for here.

## Test commands

```
python -m unittest discover -s tests -v
```

There is no lint, format, type-check or build command. No `npm` or `pip` packages are used or allowed (see "Hard constraints" in `CLAUDE.md`).

## Run command

```
python -m motion_studio --data-dir ./data --port 8765
```

## Ticket workflow

To implement a GitHub issue, follow the steps and gates in [.claude/skills/implement-ticket/SKILL.md](.claude/skills/implement-ticket/SKILL.md) and "Agents and the loop" in `CLAUDE.md`. The role files in `.claude/agents/` are Claude Code subagents; an agent that cannot delegate to them does each step itself, using the "In this repository" section at the top of the matching role file as its checklist, and says so in the pull request.

## Loop conventions

- The loop is L1: report-only, started by hand. No scheduler, no automated fixes, no auto-merge.
- A triage run may change only `issue-triage-state.md` and `loop-run-log.md`.
- See [LOOP.md](LOOP.md) for the command, human gates and recorded health checks, and [loop-constraints.md](loop-constraints.md) for the binding rules.
