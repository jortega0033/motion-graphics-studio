# Offline Motion Graphics Studio

A local, offline editor for building title cards and simple motion graphics from text and shapes. Python 3.12+ standard library, SQLite, and native browser JavaScript. No npm or pip dependencies. All example content is fictional.

See [docs/PRD.md](docs/PRD.md) for the product requirements and technical specification.

## Status

Milestone M1 (durable scene) is the current baseline.

Implemented (automated tests are in `tests/`; the browser pass for A1, A2 and A5 has not been recorded yet):

- Create a Blank or Title Card project at 1280×720 (landscape) or 720×1280 (portrait).
- Add text, rectangle, and ellipse layers. Edit position, size, opacity, fill, text, font size, and alignment.
- Rename, duplicate, reorder, and delete layers with keyboard alternatives.
- Live Canvas2D preview of the static scene.
- Save numbered immutable SQLite revisions, close the service, restart, and reopen the same document.
- Idempotent saves (a retried request adds one revision) and stale-save conflicts that keep the draft.

Not yet built: keyframe editing, frame sampling, playback, revision history UI and restore, capture, WebM export, and export recovery. See the PRD milestones M2 to M4.

## Run

```
python -m motion_studio --data-dir ./data --port 8765
```

Open http://127.0.0.1:8765/ in Chrome. The service binds to 127.0.0.1 only. `--port 0` picks a free port and prints it.

## Test

```
python -m unittest discover -s tests -v
```

Tests start a real loopback server on an ephemeral port with a disposable data directory.

## Demo flow (about two minutes)

1. Start the service with an empty data directory.
2. Create **Launch card** with template Title Card and preset Landscape. The stage shows a 1280×720 scene.
3. Choose Projects to return to the list, then create **Story panel** with template Blank and preset Portrait. The stage shows a 720×1280 scene.
4. In the editor choose Add text layer and Add rectangle. Edit the text and fill in the inspector.
5. Select the rectangle, choose Move up, and watch it cover the text. Choose Move down to restore the text.
6. Choose Duplicate, then Delete. Focus lands on a remaining layer.
7. Press Ctrl+S (or choose Save). The status reads `Saved · revision 2`.
8. Stop the service with Ctrl+C, start it again with the same `--data-dir`, open the project from the list, and confirm the layers and revision number match.

## Interfaces

- `GET /api/v1/health`
- `GET /api/session`
- `GET`, `POST /api/projects`
- `GET /api/projects/{id}/revisions`, `GET /api/projects/{id}/revisions/{n}`
- `POST /api/projects/{id}/revisions`

Writes require a same-origin `Origin` header and the session token from `/api/session`. Requests with an unexpected `Host` are rejected.

## Limitations

- One author, one machine, explicit saves. The data-root advisory lock is not built, so run one service per data directory.
- Scene presets are fixed after project creation.
- Tracks are validated and preserved but cannot be edited yet.

## Baseline verification

- The unit suite passed on Windows with Python 3.13 and on Ubuntu 24.04 in WSL2 with Python 3.12 (70 tests on Ubuntu). On Linux, use `python3` in the launch and test commands if `python` is unavailable.
- Windows Chrome 157 ran the workflow with external browser requests blocked. Created a scene with shape and text layers, changed their order, then saved and reopened the scene with the same layer order after a server restart. The browser reported no uncaught page errors.
