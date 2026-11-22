# Loop Budget — motion-graphics-studio

> Primary loop: **Issue Triage** (scaffolded by loop-init, `@cobusgreyling/loop@0.2.0`)

## Daily limits

| Loop | Max runs/day | Max tokens/day | Max sub-agent spawns/run |
|------|--------------|----------------|--------------------------|
| Issue Triage | 2 (manual starts only) | 80k | 0 (L1) |

L2 is not enabled, so the loop never spawns the verifier on its own.

## On budget exceed

1. Stop starting runs. There is no scheduler to pause: runs are manual.
2. Append event to `loop-run-log.md`
3. Tell the owner (note under "Needs human" in `issue-triage-state.md`)

## Kill switch

- Command or issue label: `loop-pause-all`
- To pause: add a line `loop-pause-all` under "Alerts This Period" below. A run that sees it exits immediately.
- Resume only after the owner removes the line.

## Alerts This Period

- (none)

## Estimate spend

```bash
npx @cobusgreyling/loop-cost --pattern issue-triage --level L1
```
