# Architecture as built, and PRD reconciliation

This document describes the code at commit `3ec6efb` (the M1 baseline) and compares it with [PRD.md](PRD.md). The PRD is the target; this file is the map of what exists. Line numbers refer to that commit.

Status words used below:

- **Implemented**: in the code and covered by a check that was run on 2026-11-22 (Windows 11, Python 3.13.14, `python -m unittest discover -s tests -v`: 70 tests, OK).
- **Implemented, needs verification**: in the code, read but not exercised by an automated check (mostly browser behaviour).
- **Planned**: required by the PRD, absent from the code. Tracked by epic #1.

## Shape of the system

A single-process, three-layer application with no third-party packages.

| Layer | Files | Responsibility |
| --- | --- | --- |
| Browser app | `motion_studio/static/index.html`, `app.css`, `js/main.js`, `js/api.js`, `js/scene.js`, `js/renderer.js` | Plain ES modules, no framework, no build. `main.js` holds one state object `S` and renders the DOM imperatively. `renderer.js` is a pure `drawScene(ctx, scene)`. |
| HTTP service | `motion_studio/server.py`, `motion_studio/__main__.py` | `ThreadingHTTPServer` with one `Handler` and a hand-written router (`_route`, `server.py:81`). Speaks HTTP/1.0 (`server.py:171`). |
| Store | `motion_studio/store.py` | One SQLite connection behind an `RLock` (`store.py:117`), WAL mode, `BEGIN IMMEDIATE` for writes (`store.py:169-183`). |
| Scene model | `motion_studio/scene.py` | Pure module: schema constants, `new_scene`, `canonical_json`, `validate_scene`. |

Import direction: `scene` has no package imports; `store` imports `scene`; `server` imports both; `__main__` imports `server` and `store`. Nothing imports upward.

One coupling to know: `StoreError` (`store.py:52`) carries the HTTP status and error code, and the server turns it into the JSON error envelope (`server.py:270-271`). The server also raises `StoreError` for its own gate failures.

## Traced workflow: create, edit, save, restart, reopen

1. **Start.** `python -m motion_studio --data-dir DIR [--port N]` parses arguments (`__main__.py:21-27`), calls `create_server` (`server.py:452`), prints the listening URL and runs `serve_forever`. `MotionServer.__init__` opens the store, creates a per-process session token and binds `127.0.0.1` only (`server.py:436-440`).
2. **Load the page.** `GET /` returns `static/index.html` (`server.py:323-324`). `init` in `main.js:577-582` requests a token (`api.js:42`, `GET /api/session`) and lists projects.
3. **Create.** `onCreate` (`main.js:122-150`) posts `{request_id, name, template, preset}` to `/api/projects`. The request ID is kept for a network retry of the same input (`main.js:135`). Every write passes the gates in `_dispatch_inner` in this order: Host allowlist (`server.py:285-288`), same-origin `Origin` (`310`), session token with a constant-time compare (`312-316`), `application/json` content type (`317-320`), then a body of at most 1 MiB (`_read_body`, `353-381`). `Store.create_project` (`store.py:219-274`) inserts the project row and revision 1 in one transaction; the scene comes from `new_scene` (`scene.py:56`).
4. **Edit.** `enterEditor` (`main.js:154`) puts the scene in `S`. Layer and inspector actions mutate `S.scene` and call `changed()` (`main.js:307`), which redraws through `drawStage` (`main.js:197`) and `drawScene` (`renderer.js:3`). Nothing is sent to the server while editing.
5. **Save.** `save()` (`main.js:450-499`) serialises `{request_id, expected_head, scene}` once and resends the same bytes on a network retry. `POST /api/projects/{id}/revisions` reaches `Store.save_revision` (`store.py:336-418`). Inside one `BEGIN IMMEDIATE` transaction it: looks up a replay by request ID and hash (`362-373`); validates the scene (`375`); checks that preset and dimensions equal revision 1 (`376-389`); compares `expected_head` (`394-400`); inserts the revision and moves the head (`402-412`).
6. **Conflict.** A stale head returns 409 `stale_head` with `current_head` and `current_revision`. The UI keeps the draft and shows "Reload saved version" (`main.js:482-486`, `501-523`).
7. **Restart and reopen.** Data is in `<data-dir>/motion_studio.sqlite3`. `openProject` (`main.js:110`) reads `GET /api/projects/{id}/revisions/{head_revision}`, served by `Store.get_revision` (`store.py:288`). No project-detail route exists.

Steps 1, 3 (server side), 5, 6 (server side) and 7 are covered by `tests/test_api.py` and `tests/test_cli.py`. The browser halves of steps 2 to 7 are **implemented, needs verification**: the README records one manual Chrome pass, and no scripted browser check exists.

## Data ownership and invariants

| Invariant | Where it is enforced | Test |
| --- | --- | --- |
| Revisions are immutable | `UPDATE` and `DELETE` triggers, `store.py:43-48` | `test_revisions_are_immutable_in_the_database` |
| Head compare, insert and head update are atomic | one `_tx()` block, `store.py:354-418` | `test_concurrent_saves_from_one_head_yield_one_winner` |
| Identical retry returns the first result; same ID with other input is 409 `request_conflict` | `store.py:245-256`, `362-373` | `test_a5_replay_adds_exactly_one_revision`, `test_reused_request_id_with_different_input_conflicts` |
| Preset, width and height are fixed after revision 1 | `store.py:376-389` | `test_preset_cannot_change` |
| A project's name exists only as `scene.title`; summaries are derived from the head revision | `store.py:88-99`, `204-215` | `test_save_numbers_revisions_and_preserves_document` |
| A database with a newer `user_version` is refused and left untouched | `store.py:126-134` | `test_newer_schema_database_is_refused_and_untouched` |
| Loopback bind, Host allowlist, same-origin writes, session token | `server.py:285-320`, `440` | `HealthAndSecurityTests` |
| Static files: allowlisted extensions, no traversal | `resolve_static`, `server.py:104-130` | `test_static_index_and_traversal` |
| Fixed security headers and CSP on every response | `_send`, `server.py:203-215` | `test_exact_security_headers` (pins the exact CSP string) |
| Scene caps: 32 layers, 64 keys per property, 300 frames, 256 text characters, positions within twice the canvas | `scene.py:9-19`, `203-308` | `tests/test_scene.py` |

Order of checks inside a save matters to clients: scene validation runs before the head comparison, so an invalid draft sent from a stale tab gets 422 `invalid_scene`, not 409.

## PRD capability status

| PRD capability | Status | Evidence |
| --- | --- | --- |
| Blank and Title Card templates, landscape and portrait presets | Implemented | `scene.py:56-118`; `test_a1_create_blank_portrait_and_title_card_landscape` |
| Text, rectangle and ellipse layers; edit, duplicate, reorder, delete with keyboard alternatives | Implemented, needs verification | `main.js:324-363`, `547-558`; no automated browser check |
| Scene validation and caps | Implemented | `scene.py`; `tests/test_scene.py` |
| Immutable revisions, idempotent save, stale-head conflict | Implemented | `store.py:336-418`; `SaveTests` |
| Revision list (25 per page) and read API | Implemented | `server.py:340-350`, `store.py:288-334`; `test_revision_history_paging` |
| Session token, Host and Origin checks | Implemented | `server.py:285-320` |
| Stale-save recovery: keep draft, Reload Saved Version | Implemented, needs verification | `main.js:482-486`, `501-523` |
| Stale-save recovery: Copy Draft into New Project | Planned | no code; a new project always starts from a template, so the API has no way to create a project from a scene |
| History panel, read-only revision view, Restore as New Revision | Planned | no UI; the read APIs exist |
| Keyframe tracks in the scene | Implemented on the server only | validated (`scene.py:203-251`) and preserved on duplicate (`scene.js:86`); the UI cannot create keys and nothing samples them |
| Frame sampler (hold, linear, smoothstep) | Planned | `renderer.js:1` is a comment only |
| Timeline: frame field, step, play and pause, key insertion | Planned | no timeline markup in `index.html` |
| Editing `duration_frames` | Planned | stored and listed (`main.js:104`), no control to change it; new scenes get 150 frames (`scene.py:69`) |
| `GET /api/capabilities` | Planned | not in `_route`; the request returns 404 |
| Export jobs, frame staging, encode, cancel, media serving and removal | Planned | no export route, no FFmpeg call, no job tables |
| Data-root advisory lock and startup reconciliation | Planned | the PRD defers the lock to M4 |
| Sampler and contract tests in Node | Planned | the repository has no Node test |
| A1, A2, A5 browser pass | Needs verification | server-side parts are tested; the README records one manual Chrome run, with no stored evidence |
| A3, A4, A6 to A11 | Planned | depend on the rows above |
| A12 keyboard and 800 × 600 review | Needs verification for the M1 screens; planned for timeline, history and export | `:focus-visible` outline in `app.css:75`; never audited |

## Where the PRD and the code disagree

1. **PRD header.** The PRD is titled "Proposed v1 engineering plan", yet M1 is built. Trust its "Delivery status" table and "Decisions made for the M1 baseline" list for the present state.
2. **Routes.** The code has `GET /api/v1/health`, which the PRD's HTTP table omits. The PRD lists `GET /api/capabilities` and all `/api/exports` routes, which do not exist yet. New routes in the PRD are unversioned (`/api/...`), so the health route is the only versioned path.
3. **Project entity.** The PRD lists ID, head revision and creation time. The table also stores `create_request_id` and `create_request_hash` (`store.py:25-31`) to make creation idempotent. Compatible, and recorded in the PRD's baseline decisions.
4. **Restore.** The PRD says restore copies an older document into a new revision using the same head check. There is no restore route and none is needed: the client can post the old scene to the existing save route. This is not implemented in the UI.
5. **Copy Draft into New Project.** `POST /api/projects` accepts only `name`, `template` and `preset` (`server.py:383-401`). The PRD screen behaviour needs a way to create a project that holds an existing draft. This is an API gap that the PRD does not spell out.
6. **Key order.** The PRD describes sampling "between consecutive keys". The validator rejects duplicate frames but does not require keys to be sorted by frame (`scene.py:228-243`). A sampler must sort, or the schema must start requiring order.
7. **Platform.** The PRD targets "a local Linux machine" and "an exclusive Linux advisory lock". The baseline was developed and verified on Windows as well (README), and the code already branches on `os.name` (`server.py:434`). The lock and process supervision need an explicit decision for Windows.
8. **Python version.** PRD and README say Python 3.12. This machine runs 3.13.14; the README reports an Ubuntu 3.12 run that was not repeated here.
9. **Content Security Policy against the planned player.** The CSP is `default-src 'none'` with no `media-src` (`server.py:22-26`), so a `<video>` element pointing at `/api/exports/{id}/media` would be blocked. The export work must add `media-src 'self'` and update the test that pins the header.
10. **Body rules against the planned frame upload.** Every write must be `application/json` and at most 1 MiB (`server.py:317-320`, `19`). The PRD's `PUT /api/exports/{id}/frames/{f}` carries a PNG of up to 2.5 MiB, so that route needs its own content type and limit.

## Risks for the next implementer

- **HTTP/1.0 and threads.** Each request is a new connection (`server.py:171`). Single-range media responses (206 and 416), 150 to 300 sequential PNG uploads and a long-running encode all have to work inside this server, or the protocol version must change with care for `Content-Length` on every response.
- **One lock for everything.** All reads and writes share one connection and one `RLock`. Export job and frame records will share it; keep file I/O and the encoder outside the lock.
- **`main.js` is 584 lines with no tests.** Timeline, key editing, history and export UI will land there unless new modules are split out. `tests/test_static.py` checks markup hooks only.
- **Preview and export parity is unproven.** The renderer uses `sans-serif` and Canvas2D. The PRD requires exact pixel equality between preview and captured PNG on one Chrome host. No harness exists to measure it.
- **Tooling on this workstation (checked 2026-11-22):** `ffmpeg` on `PATH` resolves to a 6.1.1 build with `libvpx-vp9`, while `ffprobe` resolves to a different, newer build (9.0.2). The export code must resolve one executable explicitly and report its version, and must not assume the probe and the encoder come from the same build. Chrome is installed, and Node v22.23.4 imports the modules in `static/js` directly and has a built-in `WebSocket`. Whether Chrome plays the encoder's output and what the encode time is for the 150-frame fixture has not been measured.
- **`.prep/`** (ignored by Git) holds the contract used to build M1. It is historical; the issue tracker and the PRD are current.
