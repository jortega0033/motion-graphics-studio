## Ticket

Closes #

## What changed

## Evidence

Each command and its result (for example `python -m unittest discover -s tests -v`, with the test count). Say "not run" where that is the truth.

## Agent roles run

| Role | What it was asked | Verdict |
| --- | --- | --- |

## Risks and rollback

## Checklist

- [ ] Both gates ran on the current diff (Code Reviewer, then Reality Checker)
- [ ] CI is green
- [ ] `CHANGELOG.md` has a line for this change
- [ ] UI changes were checked against `docs/ui-quality.md`; copy went through `unslop`
- [ ] No dependency, external origin, inline script/style or `innerHTML` was added
