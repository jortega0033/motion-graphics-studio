# Design tokens

The visual system is the Pipenzo "Flow look": black page, Flow-style alpha layers, one accent (Pipenzo yellow `#FECE02`), red only for danger. Dark is the primary design; the light block is the matching light theme, chosen by the operating system colour scheme (`prefers-color-scheme`).

## Source and resync

- Source: `jortega0033/clip-to-reel-studio`, `extension/sidepanel/tokens.css` at commit `a13378ce73e5b27213c9a200fc960ec93afef054` (2026-11-21).
- Copy: `motion_studio/static/tokens.css`, served at `/static/tokens.css` and linked before `app.css` in `index.html`.
- Resync: copy the file over, nothing else. Never edit the copy.

## Token names by role

- Surfaces: `--bg`, `--bg-raised`, `--surface`, `--bg-sunken`
- Text: `--fg`, `--muted`, `--faint`, `--on-primary`, `--on-ink`, `--on-media`
- Lines: `--border`, `--hairline`, `--control-border`, `--input-border`
- Accent: `--primary`, `--primary-press`, `--primary-edge`, `--focus`
- Status: `--danger`, `--danger-bg`, `--success`, `--ok`, `--warn-fg`, `--info`
- Alpha layers: `--glass*`, `--scrim`, `--state-hover`, `--state-selected`, `--btn-secondary*`
- Shadows, type, space, radius, motion: `--shadow-*`, `--font`, `--mono`, `--space-*`, `--radius-*`, `--dur-*`, `--ease-*`

Yellow only on the primary action and the current selection marker. Text never sits on a bare alpha layer.

## Rule

New UI uses these tokens; no new colour literals. Colour that is user data (a layer fill, the scene background) stays a value in the scene.

## Light and dark

`tokens.css` declares the light values in `:root` and the dark values in a `prefers-color-scheme: dark` block. There is no manual toggle.
