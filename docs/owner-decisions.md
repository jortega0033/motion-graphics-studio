# Owner decisions

Decisions the owner made for this repository on 2026-11-22, with the file that implements each. Changing any entry needs the owner. An agent that finds a decision blocking a ticket stops and says so.

1. **Instructions, tooling and playbook live on the default branch.** Date: 2026-11-22. Implemented in: `CLAUDE.md`, `.claude/`, `docs/`, `.github/` on `main`.
2. **Persona agents run automatically during ticket work and carry project-tailored instructions.** Date: 2026-11-22. Implemented in: `.claude/agents/` ("In this repository" sections), `.claude/agency-agents/README.md`, `.claude/skills/implement-ticket/SKILL.md`.
3. **Every open ticket is about app implementation; tooling is installed, not ticketed.** Date: 2026-11-22. Implemented in: this pass (`.claude/`, `.github/`, `docs/`), epic #1.
4. **Agents may take a ticket up to a ready pull request. Only the owner merges and releases.** Date: 2026-11-22. Implemented in: `CLAUDE.md` "Git workflow" and "Delivery workflow", `.claude/skills/next-ticket/SKILL.md`, `.claude/settings.json` (deny rules), `docs/RELEASING.md`.
5. **No scheduler. Ticket work starts only on the owner's go signal (`/next-ticket`), because the repository is used to train AI models.** Date: 2026-11-22. Implemented in: `.claude/skills/next-ticket/SKILL.md` (`disable-model-invocation: true`), `LOOP.md`.
6. **A review gate hook blocks opening or readying a pull request until the gate roles have run after the last code edit.** Date: 2026-11-22. Implemented in: `.claude/hooks/role_gate.py`, `.claude/settings.json` (`hooks`).
7. **Loop Engineering stays at L1, report-only and unscheduled.** Date: 2026-11-22. Implemented in: `LOOP.md`, `loop-constraints.md`.
8. **Continuous integration runs on Linux and Windows; the default branch requires a pull request and green checks.** Date: 2026-11-22. Implemented in: `.github/workflows/ci.yml`; branch protection is set on GitHub after this tooling is merged.
9. **Permission rules: documented commands are allowed; force pushes, pushes to the default branch, merges, releases and reads of secrets are denied; edits to CI, agent configuration and Loop files ask first.** Date: 2026-11-22. Implemented in: `.claude/settings.json`.
10. **Open decisions on tickets are settled with the ticket's stated default.** Date: 2026-11-22. Implemented in: the issues named below; this list is the record. All five are in epic #1, "Decisions the owner may want to confirm".
    - #6 (and every ticket, epic #1 item 1), platform: both Linux and Windows kept working; #6 implements the data-root lock for both (`fcntl.flock` and `msvcrt.locking`).
    - #9, browser automation: a small Chrome DevTools Protocol client on Node 22 built-ins; Playwright is not added.
    - #3, Copy Draft into New Project: `POST /api/projects` accepts an optional `scene`.
    - #6, size: split into 13 sub-issues, #65 to #77 (owner, 2026-11-22; it was one issue with four ordered slices). The design-note sub-issue (#65) is agreed with the owner, with the approval recorded, before any code. Each sub-issue is its own pull request.
    - #4, #5, #8, #7, Chrome playback check: #4 checks the encoder and a decoder on the server with a generated self-test clip and asks the page for `canPlayType`; real playback is observed in #8, in the A8 scenario of #5 and in #7. The page does not play the self-test clip before each export.
11. **Rust (where present) is verified in CI only.** Date: 2026-11-22. Not applicable: this repository has no Rust.
12. **The ten UI rules in `docs/ui-quality.md` are binding, and the `ui-ux-pro-max` and `unslop` skills are installed and used for UI work and for copy.** Date: 2026-11-22. Implemented in: `docs/ui-quality.md`, `.claude/skills/ui-ux-pro-max/`, `.claude/skills/unslop/`, `.claude/skills/implement-ticket/SKILL.md`.
13. **Visual system: Pipenzo Flow look tokens (`docs/design-tokens.md`). SDLC kit version: jortega0033/sdlc-kit v1.0.0.** Date: 2026-11-23. Implemented in: `motion_studio/static/tokens.css`, `motion_studio/static/app.css`, `docs/design-tokens.md`.
