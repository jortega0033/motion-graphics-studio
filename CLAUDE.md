# Motion Graphics Studio: instructions for coding agents

A local, offline editor for title cards and simple motion graphics. Python standard library, SQLite and native browser JavaScript. Milestone M1 (durable scene) is the baseline; animation, history and export are planned in epic #1.

## Hard constraints

- **No dependencies.** No `pip` or `npm` packages, no build step, no bundler. Runtime is Python 3.12+ standard library and plain ES modules. Test tooling follows the same rule: Python `unittest`, Node's built-in test runner if Node tests are added, the installed Chrome and FFmpeg.
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

There is no linter, formatter, type checker or CI workflow in this repository. Do not claim one ran.

## Sources of truth

| Question | Read |
| --- | --- |
| What the product must do, acceptance checks A1 to A12, fixtures MG-F1 and MG-F2 | [docs/PRD.md](docs/PRD.md) |
| What is built today, demo flow, limitations | [README.md](README.md) |
| How the code is actually structured, what is implemented, planned or unverified, and where the PRD and code disagree | [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) |
| What to build next and in which order | GitHub epic #1 and its child issues |
| Agent roles and the triage loop | [.claude/agency-agents/README.md](.claude/agency-agents/README.md), [LOOP.md](LOOP.md) |

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

- `main` is the default branch. It is not protected and there is no CI, so the checks above are the only gate: run them yourself.
- One branch per issue, named `feat/<issue>-<slug>`, `fix/<issue>-<slug>` or `docs/<slug>`. Open a pull request against `main` that references the issue. Do not commit to `main` directly.
- Commit subjects follow the existing style: `feat: ...`, `fix: ...`, `docs: ...`, `test: ...`, `chore: ...`.
- Do not push, merge, close issues or delete branches unless the owner asked for it in the current session.
- Never commit `data/`, `*.sqlite*`, exported media, `test-results/` or anything under `.prep/` (all ignored).

## Evidence before calling a ticket done

1. The full command and its last lines: `python -m unittest discover -s tests -v`, with the test count. It must pass from a clean checkout with no third-party packages.
2. New behaviour has a test that fails without the change. Name the test.
3. Each acceptance ID the ticket names (A1 to A12) has a recorded check: the command or browser steps, the fixture, and the observed values. Say "not run" where that is the truth.
4. For browser work: Chrome version, the steps, and proof that no request left the machine (network panel or a blocked control request).
5. For export work: the FFmpeg version, the stream report (streams, size, fps, frame count, duration) and the sampled pixel values.
6. The service you started is stopped and `git status` shows no stray data files.
7. `README.md` and the "Delivery status" table in `docs/PRD.md` are updated when the baseline changes, and `docs/ARCHITECTURE.md` when a boundary or invariant changes.

## Agents and the loop

- Project agent roles live in `.claude/agents/`. Reviewer roles are read-only (`Read, Grep, Glob`). Their generic advice never overrides this file: for example, a role that suggests `npx` tools or a framework does not lift the no-dependency rule.
- The Loop Engineering setup is L1, report-only and manual. See `LOOP.md`. No scheduler, no automated fixes, no auto-merge.
