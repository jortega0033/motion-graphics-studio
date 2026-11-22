# Loop Configuration — Issue Triage

Scaffolded with `npx --yes @cobusgreyling/loop@0.2.0 init . --pattern issue-triage --tool claude` on 2026-11-22 ([Loop Engineering](https://github.com/cobusgreyling/loop-engineering), MIT), then adjusted for this repository.

## Active Loops

| Pattern | Cadence | Status | Command |
|---------|---------|--------|---------|
| Issue Triage | manual, on request | L1 report-only | `/issue-triage` in Claude Code from the repository root |

**Operating level: L1, report-only.** No scheduler, no automated source fixes, no auto-merge, no label or comment writes. `init` generated no workflow file and none exists under `.github/`. The `/loop 2h` cadence that `init` prints was not adopted.

## Next manual triage run

From the repository root, in a new Claude Code session:

```
claude --permission-mode plan
```

then type:

```
Run the loop-constraints skill, then the loop-budget skill, then /issue-triage once in report-only mode for epic #1 and its child issues. Update issue-triage-state.md and append one entry to loop-run-log.md. Change nothing else and write nothing to GitHub.
```

Leave plan mode only to let it write the two state files. Afterwards run `npx --yes @cobusgreyling/loop@0.2.0 doctor .` and commit the two files if the report is worth keeping. No triage run has been made yet.

## Human Gates

- P0 / P1 assignment — human only
- Session token, Host and Origin checks, Content Security Policy, schema migrations, the data-root lock, FFmpeg process handling — always escalate
- Any change to `motion_studio/`, `tests/` or `docs/PRD.md` — human or a normal ticket branch, never the loop
- Duplicate closure — human confirms
- Stale issue closure — human confirms
- Raising the level above L1 — the owner records the decision here first. That decision includes whether `loop-verifier` gets `Bash` to run the tests: with a shell the role is no longer read-only (a shell can write files, run git and call `gh`) and is held to checking only by its instructions

## Pairing

Standalone. No other loop pattern is configured and there is no `STATE.md` in this repository; the Top 5 stays in `issue-triage-state.md`.

## Budget

- Max sub-agent spawns per run: 0 at L1
- See `loop-budget.md`

## Files

| File | Purpose |
|------|---------|
| `LOOP.md` | this configuration |
| `loop-constraints.md` | binding rules, read first on every run |
| `loop-budget.md` | caps and the kill switch |
| `issue-triage-state.md` | the report a run rewrites |
| `loop-run-log.md` | one appended entry per run |
| `.claude/skills/issue-triage/`, `loop-constraints/`, `loop-budget/`, `loop-intake/` | the skills, as generated |
| `.claude/agents/loop-verifier.md` | checker role for L2 and above; unused at L1. `tools: Read, Grep, Glob` and a local section were added: it cannot edit files, run git or `gh`, or run the tests, so today its only possible verdict on a change is ESCALATE_HUMAN |

Removed after `init`: the `.grok/` and `.codex/` variants (this is a Claude-only setup). `AGENTS.md` was generated with `npm` commands that do not exist here and was rewritten to point at `CLAUDE.md`.

The generated constraint about `loop-ledger.json`, `loop-context --check` and the `loop-guard` skill was dropped: none of them is installed and L1 makes no fix attempts.

## Recorded health checks

Run on 2026-11-22 on the prep branch, Windows 11, Node v22.23.4, after the scaffold was committed.

`npx --yes @cobusgreyling/loop@0.2.0 doctor .` exited 0:

```
Ready:   100/100 L3
         Strong loop readiness — good candidate for L3 with explicit gates.
Sync:    n/a
Files:   state=issue-triage-state.md  LOOP.md=yes  budget=yes  run-log=yes  gate=no
Status:  HEALTHY (exit 0)
Notes:
  · Could not parse loop-sync JSON output
```

"L3" in that output is the tool's score for how complete the files are. It is not the operating level, which stays L1, and it is not evidence of a loop run: none has been made. A run of the same command before the scaffold commit existed printed `100/100 L2` with "Strong structure but no proven loop runs yet". The score rose because the tool counts any commit of the last 14 days that touches `loop-run-log.md` or a `*state.md` file as loop activity (read in the `loop-audit` source of the package), and the scaffold commit is such a commit. Expect it to fall back to L2 once that commit is older than 14 days and no run has been logged. The doctor's suggestions (a `docs/safety.md`, issue and PR templates, workflows) were not taken: the denylist and merge policy are in `loop-constraints.md`, and adding workflows is outside a report-only setup. MCP is not required for this pattern; a run reads issues with the `gh` CLI.

`npx --yes @cobusgreyling/loop@0.2.0 status .` exited 0:

```
  Pattern:  issue-triage
  Ready:    100/100  L3
  State:    issue-triage-state.md · not yet run
  Budget:   loop-budget.md  · gate=no  · constraints=yes

  Recent runs:
    (none in loop-run-log.md)

  Next: Schedule a report-only first run and append loop-run-log.md
```

The "Next: Schedule ..." hint is the tool's default text. Nothing is scheduled here; the first run is the manual command above.

## Links

- Pattern: [issue-triage](https://github.com/cobusgreyling/loop-engineering/blob/main/patterns/issue-triage.md)
- Upstream: https://github.com/cobusgreyling/loop-engineering (package `@cobusgreyling/loop` 0.2.0)
