---
name: implement-ticket
description: Playbook for implementing a GitHub issue in this repository from start to pull request, with the project subagents run at fixed steps. Use whenever asked to implement, start, continue or finish a ticket, an issue or an epic child, for example "implement #12" or "work on the next ticket".
argument-hint: "[issue number]"
---

# Implement a ticket

Use this playbook for every implementation ticket in this repository. `CLAUDE.md` holds the commands, the architecture boundaries, the Git workflow and the evidence rules; where this playbook and `CLAUDE.md` differ, `CLAUDE.md` wins.

The project subagents in `.claude/agents/` are part of the work. Delegate to them at the steps below without waiting to be asked. If a step names a role that is not installed, do that step yourself and say so in the pull request.

## Steps

1. **Read the ticket.** `gh issue view <number>` and the epic it belongs to. Work only on a leaf ticket: a ticket labelled `tracking` or with open sub-issues is a container, so work its first ready sub-issue instead (`gh api repos/jortega0033/motion-graphics-studio/issues/<n>/sub_issues`). Check that every prerequisite issue is closed and that no owner decision named in the ticket is still open. If the ticket is blocked, stop and say what blocks it.
2. **Read the rules.** `CLAUDE.md`, then the architecture notes it links to.
3. **Orient and check the approach.** Delegate as the table "Before coding" says. Settle open design questions before writing code. For a UI ticket, run the `ui-ux-pro-max` skill first (design-system search for the product type, `python .claude/skills/ui-ux-pro-max/scripts/search.py "<query>" --design-system`) and read `docs/ui-quality.md`.
4. **Branch** as the Git workflow in `CLAUDE.md` says. Never work on the default branch.
5. **Implement** inside the ticket's stated scope. Delegate the work to the implementing role that matches the files being changed (table "While coding"). Do not widen scope; note anything else you find as a follow-up.
6. **Test.** Add or change tests for every acceptance criterion and material edge case, then run the checks listed in `CLAUDE.md`. Record each command and its result.
7. **Finish the diff.** Capture the evidence `CLAUDE.md` asks for, add one line to `CHANGELOG.md` under `Unreleased`, and run the `unslop` skill over user-facing copy, documentation and the pull request text, so the gates judge the final diff.
8. **Specialist review.** Run every role in the table "After coding" whose trigger matches the change. For a UI ticket, also check each changed screen against `docs/ui-quality.md` and record the result.
9. **Review gate, always.** Run Code Reviewer on the full diff. Fix every material finding, re-run the checks, and have the reviewer look again until no material finding is left.
10. **Acceptance gate, always.** Run Reality Checker with the ticket's acceptance criteria and the recorded local evidence. It checks that the documented checks ran locally and passed and that CI is configured to run them; it does not need a CI result, because CI runs on the draft pull request after it. Do not open a pull request unless it passes.
11. **Hand off.** Only after steps 6 to 10 passed on the current diff, commit on the issue branch, push it and open a draft pull request (`gh pr create --draft ...`) against `main` with `.github/pull_request_template.md` filled in and `Closes #<issue>`. A `/next-ticket` run is the owner's request to push and open the pull request; outside that run, do it only if the owner asked in the current session. The review gate hook blocks `gh pr create` and `gh pr ready` until Code Reviewer and Reality Checker have run after the last code edit. CI then runs on the draft. If it fails, fix, re-run the local checks and both gates, and push. Do not poll: end the turn with "Draft pull request #N is waiting for CI" and read `gh pr checks` once when woken. Mark the pull request ready (`gh pr ready`) only when CI is green, shown by recorded `gh pr checks` output; you check that, not Reality Checker. The last open sub-issue of a parent also says `Closes #<parent>` in the pull request. Only the owner merges; never merge.

## Roles

### Before coding

| Role | Access | Delegate to it |
|---|---|---|
| Codebase Onboarding Engineer | read-only reviewer | At the start of a ticket in an unfamiliar area, to trace the relevant code paths before anything is changed |
| Software Architect | read-only reviewer | Before implementing a ticket that adds or changes a module boundary, data model, storage schema, public API or dependency, to check the approach against the architecture notes |

### While coding

| Role | Access | Delegate to it |
|---|---|---|
| Backend Architect | can edit | When a ticket changes server-side code, HTTP routes, validation, persistence or data migrations |
| Frontend Developer | can edit | When a ticket changes browser-side code such as pages, components, client state, styling or keyboard interaction |
| Test Automation Engineer | can edit | When a ticket adds or changes tests, fixtures or a browser test harness, or when acceptance criteria need new automated checks |

### After coding

| Role | Access | Delegate to it |
|---|---|---|
| Accessibility Auditor | read-only reviewer | After a ticket changes user-facing UI, keyboard handling, focus order or markup |

### Gates that run on every ticket

| Role | Access | Delegate to it |
|---|---|---|
| Code Reviewer | read-only reviewer | After implementing or changing code for a ticket, before the work is called done or a pull request is opened |
| Reality Checker | read-only reviewer | As the acceptance gate of every ticket, after Code Reviewer and before the draft pull request is opened, to check each acceptance criterion against evidence that was actually produced |

## Rules

- The session or role that wrote a change does not count as its reviewer.
- Read-only reviewers cannot run commands. Write the diff and the recorded command output to `.claude/state/review/` (`git diff --stat origin/main...HEAD`, `git diff origin/main...HEAD`, the check outputs), then name those files and the acceptance criteria in the request.
- Acceptance steps that need a person (for example by hand in a normal browser) are done as far as an agent can (scripted or headless, with evidence); list the rest under "Owner checks" in the pull request. Reality Checker accepts that only for steps the ticket marks as manual.
- Do not change agent configuration (`.claude/agents/`, `.claude/skills/`, `.claude/hooks/`, `.claude/settings.json`) in a ticket, by editor or by shell; `ask` rules cover editors only.
- Where a role's general advice (frameworks, dependencies, cloud services) conflicts with `CLAUDE.md`, `CLAUDE.md` wins.
- In the pull request description, add a section "Agent roles run" listing each role that ran, what it was asked and its verdict, and any step you did yourself because a role was missing.
