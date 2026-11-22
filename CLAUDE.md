# Motion Graphics Studio: instructions for coding agents

A local, offline editor for title cards and simple motion graphics. Python standard library, SQLite and native browser JavaScript. Milestone M1 (durable scene) is the baseline; animation, history and export are planned in epic #1.

## Hard constraints

- **No dependencies.** No `pip` or `npm` packages, no build step, no bundler. Runtime is Python 3.12+ standard library and plain ES modules. Test tooling follows the same rule: Python `unittest`, Node's built-in test runner if Node tests are added, the installed Chrome and FFmpeg. Give the Node runner a quoted file pattern, `node --test "tests/js/*.test.mjs"`: with a directory argument (`node --test tests/js`) Node v22.23.4 reports `MODULE_NOT_FOUND`, and a pattern that matches nothing exits 0 with zero tests.
- **Offline and loopback only.** The service binds `127.0.0.1`. Nothing may load from another origin; `tests/test_static.py` fails on external URLs in the static bundle.
- **CSP-safe browser code.** No inline `<script>`, `<style>` or `style=` attributes, and no `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write` or `eval`. The same test file enforces this.
- **Fictional data only** in fixtures, templates, tests and documentation.
- Write everything in English.

## Commands

Verified on Windows 11 with Python 3.13.14 at commit `3ec6efb`. On Linux use `python3` if `python` is missing. There is no install step.

| Purpose | Command | Expected at the baseline |
| --- | --- | --- |
| Unit and HTTP tests | `python -m unittest discover -s tests -v` | `Ran 70 tests`, `OK`, about 21 s |
| One test module | `python -m unittest discover -s tests -p "test_scene.py" -v` | `OK` |
| Run the service | `python -m motion_studio --data-dir ./data --port 8765` | prints `Motion Studio listening on http://127.0.0.1:8765/` |
| Run on a free port | `python -m motion_studio --data-dir <temp dir> --port 0` | prints the chosen port |
| Health check | `curl http://127.0.0.1:<port>/api/v1/health` | `{"status":"ok","service":"motion_studio","schema_version":1}` |

Tests start a real loopback server on an ephemeral port with a disposable data directory, so they need no running service. Run the suite once and serially. Stop any service you start (Ctrl+C) and never point a test at `./data`.

There is no linter, formatter or type checker. CI (`.github/workflows/ci.yml`) runs the test command on Linux and Windows; do not claim a check ran unless you saw its output.

## Sources of truth

| Question | Read |
| --- | --- |
| What the product must do, acceptance checks A1 to A12, fixtures MG-F1 and MG-F2 | [docs/PRD.md](docs/PRD.md) |
| What is built today, demo flow, limitations | [README.md](README.md) |
| How the code is actually structured, what is implemented, planned or unverified, and where the PRD and code disagree | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| UI rules and past owner decisions | [docs/ui-quality.md](docs/ui-quality.md), [docs/owner-decisions.md](docs/owner-decisions.md) |
| What to build next and in which order | GitHub epic #1 and its child issues |
| Delivery workflow, agent roles, the ticket playbook and the triage loop | "Agents and the loop" below, [.claude/skills/implement-ticket/SKILL.md](.claude/skills/implement-ticket/SKILL.md), [LOOP.md](LOOP.md) |

When the PRD and the code disagree, the code and the PRD's "Delivery status" section describe the baseline; the rest of the PRD describes the target. Record any new disagreement in `docs/ARCHITECTURE.md` instead of silently picking one.

## Architecture boundaries

Details and line references are in [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md). The rules an implementer must keep:

- `motion_studio/scene.py` is pure: no I/O, no imports from the rest of the package. It owns the scene schema, `validate_scene` and `canonical_json`.
- `motion_studio/store.py` is the only module that touches SQLite. One connection, one `RLock`, writes inside `BEGIN IMMEDIATE`. It raises `StoreError(status, code, message, details)`.
- `motion_studio/server.py` owns HTTP: routing, the Host, Origin, session-token and content-type gates, body limits, security headers and the JSON error envelope. Handlers call the store; they hold no state of their own.
- `motion_studio/static/js/`: `api.js` (fetch and token), `scene.js` (pure scene helpers), `renderer.js` (pure Canvas2D drawing), `main.js` (UI state and DOM). Keep sampling and rendering pure so that preview and export share them.
- Invariants: revisions are immutable (database triggers); head check, insert and head update are one transaction; a retried request ID returns the first result and a reused ID with different input is a conflict; preset and dimensions never change after revision 1; every error is `{"error":{"code","message","details"}}` with a stable `code`.
- A schema change needs a `PRAGMA user_version` bump and a migration that leaves a failed database untouched.

## Git workflow

- `main` is the default branch. Branch protection (pull request required, CI jobs required) is set on GitHub after this tooling is merged; run the checks above yourself before you push.
- One branch per issue, named `feat/<issue>-<slug>`, `fix/<issue>-<slug>` or `docs/<slug>`. Open a pull request against `main` that references the issue. Do not commit to `main` directly.
- Commit subjects follow the existing style: `feat: ...`, `fix: ...`, `docs: ...`, `test: ...`, `chore: ...`.
- Do not push, close issues or delete branches unless the owner asked for it in the current session; a `/next-ticket` run counts as that request for its ticket branch and pull request. Never merge: only the owner merges and releases.
- Never commit `data/`, `*.sqlite*`, `test-results/` or anything under `.prep/` (all ignored by `.gitignore`), and never commit exported media or staged frames. Media is not ignored by a pattern of its own: nothing covers `*.webm` or `*.png`, so it is ignored only inside `data/`. Keep every data directory you create in the checkout under `./data/` (for example `--data-dir ./data/demo`), or use a temporary directory outside the checkout.

## Evidence before calling a ticket done

1. The full command and its last lines: `python -m unittest discover -s tests -v`, with the test count. It must pass from a clean checkout with no third-party packages.
2. New behaviour has a test that fails without the change. Name the test.
3. Each acceptance ID the ticket names (A1 to A12) has a recorded check: the command or browser steps, the fixture, and the observed values. Say "not run" where that is the truth.
4. For browser work: Chrome version, the steps, and proof that no request left the machine (network panel or a blocked control request).
5. For export work: the FFmpeg version, the stream report (streams, size, fps, frame count, duration) and the sampled pixel values.
6. The service you started is stopped and `git status` shows no stray data files.
   Order: local checks (items 1 to 6) first, then Code Reviewer and Reality Checker on the full diff and that recorded output, then a draft pull request (`gh pr create --draft`). CI runs on the draft. Mark it ready (`gh pr ready`) only when CI is green, shown by `gh pr checks` output you recorded; if CI fails, fix, re-run the local checks and both gates, and push. Reality Checker does not judge a CI result; the driver checks it before `gh pr ready`.
7. `README.md` and the "Delivery status" table in `docs/PRD.md` are updated when the baseline changes, and `docs/ARCHITECTURE.md` when a boundary or invariant changes.

## Agents and the loop

**Roles.** Eight project subagents (Agency Agents roles) live in `.claude/agents/`, next to the loop's `loop-verifier`. Each role file starts with an "In this repository" section tailored to this project: its files, commands, invariants, the generic advice that does not apply here, and what it must hand back. That section and this file override the generic upstream text below it; a role that suggests `npx` tools or a framework does not lift the no-dependency rule. Provenance and local changes are in [.claude/agency-agents/README.md](.claude/agency-agents/README.md).

**Ticket work.** When asked to implement, continue or finish a GitHub issue, follow the playbook [`.claude/skills/implement-ticket/SKILL.md`](.claude/skills/implement-ticket/SKILL.md). Claude Code loads it on its own for ticket work; `/implement-ticket <issue number>` starts it by hand. Delegate to the roles without waiting to be asked; the "Use proactively ..." sentence that ends each role's `description` is what triggers it.

| When | Role | Trigger |
| --- | --- | --- |
| Before coding | Codebase Onboarding Engineer | The ticket is in an unfamiliar area |
| Before coding | Software Architect | A module boundary, data model, storage schema, public API (here the HTTP contract) or dependency is added or changed |
| While coding | Backend Architect | Server-side code changes (`motion_studio/*.py`): HTTP routes, validation, persistence or data migrations |
| While coding | Frontend Developer | Browser-side code changes (`motion_studio/static/`): pages, client state, styling or keyboard interaction |
| While coding | Test Automation Engineer | Tests, fixtures or a browser test harness are added or changed (`tests/`), or acceptance criteria need new automated checks |
| After coding | Accessibility Auditor | User-facing UI, keyboard handling, focus order or markup changed |
| Review gate, every ticket | Code Reviewer | Always, on the full diff |
| Acceptance gate, every ticket | Reality Checker | Always, last, against the acceptance criteria and the recorded evidence |

- Both gates run on every ticket, whatever its size. No change is exempt.
- The session or role that wrote a change does not count as its reviewer.
- The five reviewers (the two before coding, the auditor and both gates) and `loop-verifier` are read-only (`Read, Grep, Glob`) and cannot run commands: give them the diff, the acceptance criteria and the recorded command output.
- List the roles that ran and their verdicts in the pull request description under "Agent roles run".

**Loop.** The Loop Engineering setup is L1, report-only and manual. See `LOOP.md`. No scheduler, no automated fixes, no auto-merge.

## Delivery workflow

- **Start and driver.** The owner starts ticket work with `/next-ticket` ([.claude/skills/next-ticket/SKILL.md](.claude/skills/next-ticket/SKILL.md)); that is the go signal for one ticket. It runs the playbook [.claude/skills/implement-ticket/SKILL.md](.claude/skills/implement-ticket/SKILL.md). Ticket labels: `status:ready`, `status:blocked`, `status:in-progress`, `needs-decision`.
- **Review gate hook.** `.claude/hooks/role_gate.py` blocks `gh pr create` and `gh pr ready` until Code Reviewer and Reality Checker ran after the last code edit. Start Claude Code with `ROLE_GATE=off` in the environment to switch it off for that session.
- **Permissions.** [.claude/settings.json](.claude/settings.json): documented commands are allowed; force pushes, pushes to `main`, `gh pr merge`, releases and reads of `.env` are denied; edits to CI, agent configuration and Loop files ask first.
- **CI.** [.github/workflows/ci.yml](.github/workflows/ci.yml) runs on the draft pull request and must be green before it is marked ready; the gates run before the draft is opened and do not depend on it.
- **Pull request and changelog.** Use [.github/pull_request_template.md](.github/pull_request_template.md); add one line per ticket to [CHANGELOG.md](CHANGELOG.md). Security reports: [SECURITY.md](SECURITY.md).
- **UI and copy.** [docs/ui-quality.md](docs/ui-quality.md) is binding; use the `ui-ux-pro-max` and `unslop` skills as the playbook says.
- **Merging and releasing** belong to the owner alone ([docs/RELEASING.md](docs/RELEASING.md)). Recorded owner decisions: [docs/owner-decisions.md](docs/owner-decisions.md).
