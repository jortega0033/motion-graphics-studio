# Offline Motion Graphics Studio
## Product requirements and technical specification

Proposed v1 engineering plan

### Product

A creator making technical demos or short videos can build an original title card, lower third, or callout from text and shapes. They can align layers, place keyframes, scrub frame by frame, reopen a saved project, and watch a silent WebM in the workspace browser. A saved scene is the source of truth for preview and export.

The first release supports one author on a local Linux machine. All example names, text, shapes, and timelines are fictional or generated. A complete journey starts with a blank scene and ends with a verified video from a saved revision. The studio creates graphics. SceneSift handles review of existing footage and subtitles.

Start with text, rectangles, and ellipses on an opaque canvas. Use 30 fps, the 1280 × 720 and 720 × 1280 presets, and 1–300 frames. Support layer position and opacity, three easing modes, keyboard editing, a built-in title template, persistent revisions, and a local video viewer. Later releases can add image imports, audio, rotation, longer timelines, or other formats.

### Epic MG-E1 · Build and verify an offline title and lower-third workflow

From a blank composition or built-in template, author and verify an animation across preview, save and reopen, and silent WebM export. Finish when the linked checks pass against one commit in a clean workspace. Editing and persistence form the first durable milestone. Export proves that a saved scene keeps its timing and visible content through the pipeline.

### User stories

| Story | User need | Acceptance |
| --- | --- | --- |
| MG-S1 | As a creator, I can start with a blank scene or title template and edit its text, background, and layer order to fit my video. | A1, A2 |
| MG-S2 | As an animator, I can set position and opacity on exact frames, choose easing, and step through an entrance, hold, or exit. | A3, A4 |
| MG-S3 | As a returning editor, I can reopen saved work and restore an earlier version safely when another tab has edited the project. | A5, A6 |
| MG-S4 | As a creator checking delivery, I can export one saved revision and play it locally to check its content and timing. | A7, A8, A9 |
| MG-S5 | As a creator on a limited machine, I can cancel or retry a troubled export while keeping my saved design. | A10, A11 |
| MG-S6 | As a keyboard user, I can build, scrub, save, and inspect a title using named controls and clear status messages. | A2, A4, A12 |

### Screen behavior

1. **Projects.** Show saved names, dimensions, duration, and revision. Select Blank or Title Card when creating a project. Opening a project creates no revision.
2. **Editor.** The stage previews the active frame. A keyboard-accessible layer list provides Add, Duplicate, Move Up, Move Down, and Delete with predictable focus. The inspector provides position, opacity, geometry, and text. The timeline provides a frame field, play and pause, previous and next frame, and key insertion at the playhead. Coordinates remain in project pixels when the preview scales.
3. **Save and history.** Show Saved or Unsaved, current revision, and last successful save. Save commits the whole draft. Open an immutable revision in read-only view or choose Restore as New Revision. On a stale save, keep the draft visible and offer Reload Saved Version or Copy Draft into a New Project. Confirm any draft discard.
4. **Export and results.** Select a saved revision and show its number, dimensions, fps, and frame count. Distinguish capture progress from encoding. Provide Cancel during an active job and Retry for a recoverable failure. Play a completed result in the browser, and identify its source revision.

### Milestones and exit checks

| Milestone | Depends on | Observable gate |
| --- | --- | --- |
| M1 · Durable scene | — | Create a text layer and a shape, reorder them, save, restart, and reopen the same document at the right size. A1, A2, A5 |
| M2 · Frame editor | M1 | Edit keyframes and compare easing at known frames. Exercise keyboard editing, stale saves, and revision restore. A3, A4, A6, and the editor portion of A12 |
| M3 · Verified export | M2 | Capture 150 frames of a generated fixture from a pinned revision, encode on CPU, and verify the silent WebM and decoded sample frames. A7, A8, A9 |
| M4 · Recovery and release | M3 | Exercise lost responses, closed tabs, cancellation, encoder failure, and resource caps. A10, A11, A12 |

### Technical specification

#### Runtime and ownership

- **Browser.** Native JavaScript modules and Canvas2D. A pure scene sampler takes a snapshot and an integer frame. One shared renderer consumes sampled layers and a canvas of explicit size. UI code owns selection, timeline edits, draft and transport state, and progress.
- **Loopback service.** Python 3.12 standard library and SQLite. Serve the browser app, commit immutable revisions, stage captures, manage one CPU FFmpeg process, and serve completed local videos.
- **Encoder.** FFmpeg reads the app-generated numbered PNG sequence and produces a silent WebM. The guide lists FFmpeg in both environments. Check the installed CPU VP9 encoder, decoder, and Chrome playback on a tiny generated fixture before enabling export.
- **Storage.** One database and a managed job directory in an explicit local data root. Database transactions cover document and job metadata. Atomic renames and startup reconciliation cover staged media files. Hold an exclusive Linux advisory lock on the data root before reconciliation. A second service using the same root reports that it is busy. An encoding supervisor retains the lease while its worker is active and enforces its deadline, so a service restart cannot reconcile files that an older worker is still writing.

#### Domain model and revision contract

| Entity | Fields and invariants |
| --- | --- |
| Project | Generated UUID, head revision, creation timestamp. A project name lives in the scene snapshot so history retains its name. |
| Revision | Project ID, monotonic number, scene JSON, schema version, commit time, request ID, request hash. Unique project/revision and project/request. Immutable after commit. |
| Scene | Schema version 1, title, preset dimensions, integer duration, fixed fps 30, opaque RGB background, and ordered layer array. Draw bottom-to-top. |
| Layer | Stable UUID, kind text, rectangle, or ellipse, name, geometry, base x, y, opacity, fill, and optional property tracks. Text has bounded content, system sans-serif, size, explicit line breaks, and alignment. Position anchors at the layer's top left. |
| Track key | Property x, y, or opacity, integer frame in the scene, finite bounded value, and outgoing easing hold, linear, or smoothstep. One key per frame and property. |
| Export job | UUID, request ID and hash, pinned project/revision, dimensions, fps, expected frame count, next index, staged byte usage, state, capture fingerprint, creation and last activity time, and terminal reason or media availability. |
| Staged frame | Job ID, frame index, length, and SHA-256 digest. Unique job/index. Server chooses filenames from verified IDs and indices. |

Validate exact fields, finite ranges, unique IDs, schema version, order, and size caps before committing. Opacity uses [0, 1]. Geometry dimensions are positive and bounded by the preset dimensions. Bound position values to twice the relevant canvas dimension in either direction, allowing negative positions for slide-ins. Accept opaque fills as six hexadecimal RGB digits and use alpha from opacity. Text size ranges from 8 to 192 px, with explicit left, center, or right alignment. Shortening duration requires moving or removing any keys outside the new scene. An invalid save keeps the prior head and browser draft.

Each save carries an expected head revision and a generated request ID. Return the previous success for an identical request. Reject a reused ID with different input. Execute the head comparison, revision insert, and head update in one transaction. A stale head returns the current revision and leaves the draft available. Restore copies an older document into a new revision using the same head check. Failed migrations preserve the database and return an actionable diagnostic.

#### Frame sampling and preview parity

- A scene has N frames, numbered 0 through N − 1. Frame f samples time f / 30 seconds. Output duration is N / 30. A five-second scene contains frames 0–149 and samples the last pose at 149 / 30.
- An empty track uses its base value. Before the first key and after the last, hold the nearest key value. A key at the exact frame wins. Between consecutive keys a and b, compute u = (f − a.frame) / (b.frame − a.frame). Progress is 0 for hold, u for linear, and 3u² − 2u³ for smoothstep. The sampled property is a.value + (b.value − a.value) × progress.
- Paint the opaque background first, then draw layers in their array order with source-over composition. Reset canvas state per layer and per frame. Both canvases use the project dimensions, same draw options, and same resolved system font on the same Chrome host. Set the canvas bitmap size from the project and scale its preview through layout.
- Playback uses monotonic elapsed browser time to choose the frame and stops on the last frame. Scrub and step select integer frames directly. Export iterates every integer frame in a separate canvas from the pinned scene. Wait for font resolution and drive capture by completed rendering and upload acknowledgment. Record a capture fingerprint from the renderer version, browser version, preset, and a hashed generated font-sample raster. A resume requires a matching fingerprint. A different one offers a new export job from the pinned revision.
- Captured PNGs preserve the raster losslessly. The proposed delivery preset is CPU VP9 and 4:2:0 WebM. RGB conversion and chroma subsampling can change reconstructed colors even with the encoder's lossless option. Compare preview pixels with PNG pixels on the same Chrome host. Set the RGB-to-YUV conversion matrix, range, and corresponding video tags in the tested preset. Use neutral and saturated decoded samples with a documented tolerance for WebM. Video file byte hashes are an exploratory check.

#### Local HTTP and process contract

| Operation | Contract |
| --- | --- |
| `GET /api/capabilities` | Report encoder readiness, local limits, and an actionable diagnostic. |
| `GET /api/session` | Issue a process-local mutation token to the editor with a no-store response. Reload it after a service restart. |
| `GET /api/projects`, `POST /api/projects` | List summaries or create one initialized project. Generated project and request IDs make retries unambiguous. |
| `GET /api/projects/{id}/revisions`, `GET /api/projects/{id}/revisions/{n}` | List revision summaries newest first or read one immutable snapshot. Limit history pages to 25. |
| `POST /api/projects/{id}/revisions` | Commit with expected head and request ID. Return a new revision, a prior result on identical retry, or the current head on conflict. |
| `POST /api/exports` | Create or recover a job for a saved revision using a unique request ID and canonical input hash. An identical retry returns the original job. A changed payload under that key conflicts. If another job occupies the worker, return its ID with a busy result. |
| `PUT /api/exports/{id}/frames/{f}` | Accept one bounded PNG and return the next contiguous index. An identical frame retry returns success. A changed hash or skipped index returns conflict. |
| `POST /api/exports/{id}/encode` | Require all consecutive frames. Start one encoder or return the existing state on replay. |
| `GET /api/exports/{id}`, `POST /api/exports/{id}/cancel` | Read job status or request cancellation. Report the terminal result of the job. |
| `GET /api/exports/{id}/media` | Stream an available completed WebM to the local player. Support a single byte range for seeking and report unsatisfiable ranges. Distinguish deliberate removal from a missing file in job status. |
| `DELETE /api/exports/{id}/media` | Remove an output selected by the author. Record `media_removed` in job metadata, remove the local media file, and keep the revision and job history. Repeating the removal is safe. |

Bind to loopback. Validate Host on every request. Require the same-origin Origin header and a process-local mutation token on writes. Serve script and media from the local origin. Treat text as data. Build paths from generated job IDs and validated indices. Limit logs to IDs, reason codes, counts and elapsed times. Use FFmpeg with a server-owned executable, fixed argument array, no shell, and stdin disabled. Set the numbered PNG input to start at index 0 and specify `-framerate 30` before the input. Pin thread count and the validated CPU VP9 speed parameters in the preset. Read the managed frame sequence and write a managed partial WebM with audio disabled. Drain process diagnostics into a bounded tail and enforce a subprocess timeout. Return stable error codes for invalid input, conflicts, caps, and unavailable encoding.

Proposed first-release caps are 32 layers, 64 keys per property, 256 text characters per layer, 2.5 MiB per PNG, 768 MiB of frame staging across the data root, 128 MiB per output, one active job, five retained outputs per project, and 1 GiB for completed videos across the data root. A full 300-frame job fits the per-frame budget at 750 MiB. Check capacity before allocating the job. Monitor partial output size and terminate an encode that exceeds its limit. Target two encoder threads. Set a bounded deadline with a floor and a per-frame allowance derived from the first fixture measurement. Validate PNG structure and project dimensions before accepting a frame. Test caps with smaller injected limits. Record actual capture and encoding results before adopting throughput commitments.

#### Retry, cancellation, and storage recovery

- The success path is capturing → encoding → completed. Failed and cancelled are terminal. Only completed jobs with available media expose video. Complete startup reconciliation before accepting new jobs.
- Spool each frame into a bounded temporary file. Hold a short write transaction while checking job state and index, renaming the file, and recording the digest. Startup reconciliation removes unrecorded frame files and fails affected jobs if a committed frame is missing or has the wrong digest. A capturing job with a valid prefix can resume from its next index and pinned revision after comparing the capture fingerprint. Retry a pending request with the original bytes. After a reload, read the recorded next index before rendering more frames. Mark an abandoned capture expired at 24 hours of inactivity and release its staging.
- Encode to a managed partial filename. Before exposing the result, check process success, stream metadata, frame count, and media size. Rename the output locally and transition state under a job lock. Startup reconciliation removes uncommitted outputs and fails interrupted encodes with a retryable reason. For a completed job, distinguish author removal with `media_removed` from an unexpected `media_missing` result.
- Cancellation wins if recorded before the worker marks a result available. Stop the owning process and wait for exit before deleting any captured files. A late cancellation returns the completed state. Timeout and failure preserve the saved scene. An explicit Retry creates a fresh job with a new request ID and the same pinned revision.
- Release staging and partial media at every terminal outcome after closing encoder files. Startup reconciliation also completes pending cleanup, including deliberately removed outputs. Completed videos remain available until the creator chooses to remove one. At the retention cap, show how to remove an older result before starting an export.

### Synthetic fixtures and acceptance evidence

**MG-F1 · Moving lower third.** Landscape 1280 × 720, 150 frames. Background RGB (16,16,16). A 64 × 40 neutral rectangle of RGB (224,224,224) stays at y=48, with linear x-keys (0,32) and (60,272). Place the fictional title below the sample area. The background sample is (8,8). Sample the moving rectangle center at y=68. Add a static 80 × 72 patch of RGB (200,40,40) at (1000,60) and sample its interior at (1040,96).

| Frame | Expected rectangle x | Expected center sample x |
| --- | --- | --- |
| 0 | 32 | 64 |
| 15 | 92 | 124 |
| 30 | 152 | 184 |
| 45 | 212 | 244 |
| 60 | 272 | 304 |
| 149 | 272 | 304 |

**MG-F2 · Keyframe boundaries.** An opacity track from 0 to 1 over frames 0–60 using smoothstep reaches 0.15625 at 15, 0.5 at 30, and 0.84375 at 45. A hold track from −10 to 40 over frames 0–30 stays at −10 on frame 29 and becomes 40 on frame 30.

| ID | Observable acceptance |
| --- | --- |
| A1 | Cold-start with an empty temporary data root and block external network traffic. Verify the block with a control request. Create a blank portrait project and a template landscape project. Both show their expected dimensions and use only local resources. |
| A2 | Edit, duplicate, and reorder overlapping layers. Verify one interior pixel changes to the new top layer color and returns when the order is restored. Deleting the selected layer moves keyboard focus to a valid control. |
| A3 | Verify exact values in MG-F1 and MG-F2. Duplicate keys, out-of-range frames, and duration changes that would strand keys show clear validation errors with the saved revision intact. |
| A4 | In MG-F1, use only keyboard controls to select frame 0, step to 1, seek to 149, and add a key. Next at the last frame stays at 149. Pause preserves the displayed frame. |
| A5 | Save an edited scene, restart the service, and reopen. The document and revision match. Replay the same save request and verify exactly one revision was added. |
| A6 | With both tabs loaded at head 2, save in tab A and verify head 3. A save from tab B returns a conflict and keeps its draft visible. Restore revision 1 as a new revision and verify revision 3 remains inspectable. |
| A7 | Compare six sampled preview frames with the corresponding staged PNGs. Interior RGBA samples match exactly on the same Chrome host. Start an export from one revision, save a visible change in a newer revision, and verify the job still shows and renders the pinned revision. |
| A8 | Play the generated WebM in local Chrome and verify with a local media probe or decode. Expect one video stream, zero audio streams, 1280 × 720, 30 fps, and exactly 150 frames. Reported duration is five seconds within one frame of container rounding. |
| A9 | Decode the six MG-F1 samples. Check each RGB channel in small interior patches of the moving rectangle, background, and saturated marker within four units of the expected values. Re-export the same revision and repeat the count, ordering, and sampled pixel checks. |
| A10 | Drop a frame response after commit and retry the same bytes at the same index. Verify exactly one frame record. A changed retry or skipped index leaves staging unchanged. Restart during capture and verify resume at the next contiguous index with the matching fingerprint and pinned revision. A changed fingerprint starts a fresh job after user confirmation. |
| A11 | Inject a missing encoder, an encoding timeout, a staging cap breach, and cancellation during capture and encoding. Saved revisions remain intact, the player exposes only verified output, and each terminal job releases staging. A fresh retry from the same revision reaches the expected fixture frame count. Removing that result keeps its revision and sets `media_removed`. A separate missing-file test reports `media_missing`. A second server pointed at an actively held data root leaves the first job intact. |
| A12 | Complete editor and export review by keyboard with visible focus. Progress and errors convey status without color. At 800 × 600, every timeline and form control is reachable by keyboard or scrolling. |

Run frame sampling and contract tests in Node and Python. Use disposable roots for service and restart tests, and use the workspace's local Chrome for the browser path. For media checks, use the validated installed probe when available or FFmpeg decode and frame-count metadata. Browser acceptance records the environment, tool versions, fixture revision, actual stream report and frame evidence, and elapsed capture and encode times. Track failures and skips separately. Use the installed Chrome and available Playwright runner after preflight. On a workspace image without Playwright, Node 22 can use its WebSocket client with a disposable loopback-only Chrome debugging profile for test input and network evidence.

### Implementation decisions to confirm

- Confirm that the 30 fps presets and ten-second maximum cover the first use. The five-second fixture is the first performance sample.
- Confirm that system sans-serif and explicit line breaks cover the initial title style. The chosen renderer resolves fonts before capture.
- Pick a CPU VP9 configuration after checking the installed FFmpeg build and Chrome playback. Keep the fixed frame and sampled-pixel checks when tuning it.
- Prefer explicit saves, numbered revision history, and one active export as the first release defaults. Check the staging and time caps on the target CPU before committing to an encode-time claim.
- Verify availability of the installed encoder and local browser early. M1 can be checked independently of the media capability gate.

### Delivery status

| Milestone | Status |
| --- | --- |
| M1 · Durable scene (A1, A2, A5) | Implemented as a local baseline. Automated checks are in `tests/`. The browser pass for A1, A2 and A5 is a scripted or manual run still to be recorded. |
| M2 · Frame editor | Remaining. |
| M3 · Verified export | Remaining. |
| M4 · Recovery and release | Remaining. |

Decisions made for the M1 baseline:

- Scene colors are stored as lowercase `#rrggbb` strings.
- The preset (dimensions) is fixed once a project exists. Duration may change.
- Text layers carry `text`, `font_size`, and `align` with no width or height. Shapes carry `width` and `height`.
- Layer `tracks` are validated in full and preserved on save and duplicate, but the baseline cannot create keys.
- Opening a project reads the head revision through `GET /api/projects/{id}/revisions/{n}`, using `head_revision` from the project list. No separate project-detail route exists.
- Project creation is idempotent through a request ID, like saves.
- `GET /api/session` and the mutation token are included in M1 because writes need them.
- The data-root advisory lock is deferred to M4. Until then, run one service per data directory.

See the README for the working baseline, run commands and demo flow.
