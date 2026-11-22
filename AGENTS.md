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

## Loop conventions

- The loop is L1: report-only, started by hand. No scheduler, no automated fixes, no auto-merge.
- A triage run may change only `issue-triage-state.md` and `loop-run-log.md`.
- See [LOOP.md](LOOP.md) for the command, human gates and recorded health checks, and [loop-constraints.md](loop-constraints.md) for the binding rules.
