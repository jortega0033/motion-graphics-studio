# Agency Agents roles in this repository

The role definitions in `.claude/agents/` (except `loop-verifier.md`, which comes from Loop Engineering) are copied from **Agency Agents**. `loop-verifier` is limited to `Read, Grep, Glob` like the reviewers below, is unused at L1 and cannot run tests; see `LOOP.md`.

- Upstream: https://github.com/msitarzewski/agency-agents
- Pinned revision: `8ae6164602c95ca78828b148b9052460ee426885` (main, committed 2026-11-09)
- License: MIT, Copyright (c) 2025 AgentLand Contributors. The full text is in [LICENSE](LICENSE) in this directory (upstream blob `523078c01624b9b1b1c551e75054b9d3a9f953ab`).
- Fetched with `gh api -H "Accept: application/vnd.github.raw" "repos/msitarzewski/agency-agents/contents/<path>?ref=<pin>"`.

## Installed roles

| Project file (`.claude/agents/`) | Agent `name` | Upstream path | Upstream blob | Change | Tools |
| --- | --- | --- | --- | --- | --- |
| `engineering-software-architect.md` | Software Architect | `engineering/engineering-software-architect.md` | `1a69148c99b2c170e36e035a0c7a341e98e634e9` | added one `tools` line | Read, Grep, Glob |
| `engineering-code-reviewer.md` | Code Reviewer | `engineering/engineering-code-reviewer.md` | `fb93291f4b94a8d5687aa1cc0d05741c3352dd22` | added one `tools` line | Read, Grep, Glob |
| `engineering-codebase-onboarding-engineer.md` | Codebase Onboarding Engineer | `engineering/engineering-codebase-onboarding-engineer.md` | `cc36ec153ebe38ebf51515d8591a44e1213e5aa1` | added one `tools` line | Read, Grep, Glob |
| `testing-reality-checker.md` | Reality Checker | `testing/testing-reality-checker.md` | `e534cfbd20d3115d5265387f19db7d3b25649421` | added one `tools` line | Read, Grep, Glob |
| `testing-accessibility-auditor.md` | Accessibility Auditor | `testing/testing-accessibility-auditor.md` | `350dc3d468b96015a6b3cdefbb06f4a33f673cb1` | added one `tools` line | Read, Grep, Glob |
| `engineering-backend-architect.md` | Backend Architect | `engineering/engineering-backend-architect.md` | `e9272ed505b03f8487fc78715d69847b9a7c0d06` | none (byte-identical) | inherits the session's tools |
| `engineering-frontend-developer.md` | Frontend Developer | `engineering/engineering-frontend-developer.md` | `7fc1a355bf6cc53b5f2b8b58db52ae2860fc0616` | none (byte-identical) | inherits the session's tools |
| `testing-test-automation-engineer.md` | Test Automation Engineer | `testing/testing-test-automation-engineer.md` | `59650291b60ed280f8f5d5da69f15fec2aea3dca` | none (byte-identical) | inherits the session's tools |

The only edit to an upstream file is the line `tools: Read, Grep, Glob` in the frontmatter of the five reviewer roles. Upstream definitions carry no `tools` field, which would give a role every tool of the session.

To check a file against upstream: `git hash-object .claude/agents/<file>` equals the upstream blob for the three unmodified roles; for the five reviewers, delete the `tools` line first.

## Why these roles

| Role | Use in this repository |
| --- | --- |
| Codebase Onboarding Engineer | Read-only orientation and code-path tracing before a ticket starts. |
| Software Architect | Read-only review of design choices: export job model, lock and process supervision, HTTP protocol changes, module splits in `static/js`. |
| Code Reviewer | Read-only review of a diff for correctness, security and maintainability. |
| Reality Checker | Read-only gate before a ticket or the release check (#7) is called done: demands the recorded evidence listed in `CLAUDE.md`. |
| Accessibility Auditor | Read-only review for acceptance check A12 (keyboard access, visible focus, status without colour, 800 × 600). |
| Backend Architect | Implementation help for the Python service, SQLite schema and the export pipeline. |
| Frontend Developer | Implementation help for the native-module browser app: sampler, timeline, history and export screens. |
| Test Automation Engineer | Implementation help for the browser acceptance harness and deterministic fixtures. |

Roles left out on purpose: anything tied to a framework, cloud platform, mobile, streaming delivery (HLS, DASH, CDN) or marketing, because none applies to a local standard-library application.

## Rules that outrank the role text

The upstream prompts are generic. In this repository `CLAUDE.md` wins wherever they differ. In particular:

- No `pip` or `npm` packages and no frameworks, even where a role's examples use React, Playwright, Cypress, axe, Lighthouse, PostgreSQL or cloud services. The accessibility and test roles must work with the installed Chrome, Node's built-in modules and Python `unittest`.
- Loopback only, offline, fictional data only.
- Roles do not push, merge, publish or change GitHub issues unless the owner asked for it in the session.

## Name collisions with user-level agents

The owner's user-level directory `~/.claude/agents/` already contains the same eight roles under the same `name` values. Claude Code gives a project-level agent precedence over a user-level agent with the same name, so inside this repository the project copies are used. The practical difference is the reviewers: here they are limited to `Read, Grep, Glob`.

Two consequences:

- A Claude Code session that was already running before these files existed keeps the definitions it loaded at start. Start a new session from the repository root to get the project copies.
- To see what is loaded, run from the repository root: `claude -p "List the project-level agents available to you and the tools each one has. Do not use any tools."`

## Updating

Pick a new upstream revision, fetch the same paths, re-apply the `tools` line to the five reviewers, update the pin and blob hashes in this file, and repeat the load check.

## Local change: automatic delegation (2026-11-22)

Two local changes were made to every Agency Agents role in `.claude/agents/` (not to `loop-verifier`):

1. One sentence beginning "Use proactively" was appended to the `description:` line. Claude Code uses that field to decide when to delegate, so the roles now run during ticket work without being named.
2. A section headed `## In this repository` was inserted directly after the closing `---` of the frontmatter, before the upstream text. It is project-specific text written for this repository, not upstream text: the project and its constraints, the files and tickets the role covers, the commands from `CLAUDE.md` (or, for a read-only role, the output the caller must supply), a checklist of this project's invariants, the parts of the generic text that do not apply here, and what the role hands back. It ends with the sentence "This section and CLAUDE.md override the generic text below wherever they differ."

Nothing else in the role files changed: the rest of the frontmatter and the upstream text below the inserted section are as fetched.

This supersedes any statement above that a role file is unmodified, byte-identical or that the `tools:` line is the only local change. To compare a role with the pinned upstream file, remove the "Use proactively" sentence, the whole "In this repository" section (the heading through the override sentence, and the blank line after it) and the `tools:` line where one was added. `git hash-object` equals the upstream blob only after that.

When updating to a new upstream revision, re-apply both changes and re-check every "In this repository" section against `CLAUDE.md` and `docs/ARCHITECTURE.md`.

The steps at which each role runs are in `.claude/skills/implement-ticket/SKILL.md` and in "Agents and the loop" in `CLAUDE.md`.

Verification, 2026-11-22: from the repository root, `claude -p "List every project subagent defined in .claude/agents with its exact name and tools, say for each whether its instructions begin with a section titled In this repository, and say whether a skill named implement-ticket is available. Plain list, no commentary." --model haiku` (Claude Code 2.1.323) exited 0. It listed all eight Agency Agents roles under their exact names, each reported as beginning with "In this repository"; the five reviewers with `Read, Grep, Glob` and Backend Architect, Frontend Developer and Test Automation Engineer with no `tools` line (inheriting the session's tools); `loop-verifier` with `Read, Grep, Glob` and no such section; and the skill `implement-ticket` as available. The check was run once, on the working tree that this change commits. It shows that the files are found and parsed; it does not exercise automatic delegation on a real ticket.

## Local change: SDLC kit (2026-11-22)

This pass added, without changing any role body or upstream text beyond the lines below:

- One checklist line naming `docs/ui-quality.md` in the "In this repository" section of Frontend Developer, Code Reviewer and Accessibility Auditor. UI Designer and UX Architect are not installed here, so they got none.
- The review gate hook `.claude/hooks/role_gate.py` (gate roles Code Reviewer and Reality Checker, both installed), `.claude/settings.json`, `.github/workflows/ci.yml`, the pull request template, CODEOWNERS, issue template, Dependabot config, `SECURITY.md`, `CHANGELOG.md` and `docs/RELEASING.md`.
- The `/next-ticket` driver skill, the `ui-ux-pro-max` and `unslop` skills (each with its own `PROVENANCE.md`), `docs/ui-quality.md` and `docs/owner-decisions.md`.
- Updated `implement-ticket` playbook, `CLAUDE.md` "Delivery workflow" and a note in `LOOP.md`.
- Follow-up review fixes: the "In this repository" sections of Reality Checker, Code Reviewer and Test Automation Engineer now state that CI exists (`.github/workflows/ci.yml`, unittest on Linux and Windows) instead of saying there is none; Reality Checker's checklist now asks for recorded `gh pr checks` output.
