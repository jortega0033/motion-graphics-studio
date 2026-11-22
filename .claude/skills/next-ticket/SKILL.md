---
name: next-ticket
description: Take the next ready ticket of epic #1 up to a ready pull request. Started only by the owner; starting it is the go signal for one ticket.
argument-hint: "[issue number]"
disable-model-invocation: true
---

# Next ticket

The owner starts this with `/next-ticket` or `/next-ticket <issue number>`. Starting it is the owner's go signal for this run and counts as the owner asking to push the ticket branch and open the pull request. It runs one ticket, never merges and never starts another run by itself. `CLAUDE.md` wins where this file differs.

## Steps

1. **Refresh the queue.** `gh issue list --state open --limit 100`, and `gh api repos/jortega0033/motion-graphics-studio/issues/<n>/sub_issues` for epic #1 and for every ticket that has sub-issues. A ticket labelled `status:blocked` whose blocking tickets are all closed becomes `status:ready` (`gh issue edit <n> --remove-label status:blocked --add-label status:ready`). A parent ticket (labelled `tracking`, or with sub-issues) whose sub-issues are all closed is closed with a comment naming them. Epic #1 is not closed here; the owner closes it after the release gate #7.
2. **Pick one leaf ticket.** Only leaf tickets are work: never pick epic #1, a ticket labelled `tracking`, or a ticket with open sub-issues. With an issue number, use it after checking it is open and not `needs-decision`; if it is a `tracking` parent or has open sub-issues, refuse it and list those sub-issues. Without a number, take the first `status:ready` leaf that is not `status:in-progress` and not `needs-decision`, in the epic's order: the parents in the table "Tickets in dependency order", then the sub-issues inside each parent in their sub-issue order. If none qualifies, say why and stop.
3. **Claim it.** Label it `status:in-progress`. Stop if it already has that label.
4. **Branch in a fresh worktree.** From an up-to-date `main`: `git worktree add ../motion-graphics-studio-<issue> -b <branch> origin/main`, with the branch named `feat/<issue>-<slug>`, `fix/<issue>-<slug>` or `docs/<slug>` as the Git workflow in `CLAUDE.md` says. Work only in that worktree.
5. **Run the playbook.** Follow `.claude/skills/implement-ticket/SKILL.md` from step 1 to its hand-off: local checks, then both gates on the current diff, before any pull request exists. Before calling Code Reviewer and Reality Checker (they have no shell), write the review diff and evidence into the worktree's `.claude/state/review/` (`git diff --stat origin/main...HEAD`, `git diff origin/main...HEAD`, the recorded check outputs; the folder is git-ignored) and name those files in each request. Do the acceptance steps that need a person as far as you can (a scripted or headless run, with the evidence) and list the rest under "Owner checks" in the pull request; Reality Checker accepts that only for steps the ticket marks as manual.
6. **Open the draft.** Once the local checks and both gates passed, push the branch (`git push -u origin <branch>`, never `main`) and open a draft pull request (`gh pr create --draft ...`) against `main` with `.github/pull_request_template.md` filled in, `Closes #<issue>`, and a `CHANGELOG.md` line. If this is the last open sub-issue of a parent, the description also says `Closes #<parent>`, so the owner's merge closes both. Never open or ready a pull request with a gate not run. The review gate hook blocks `gh pr create` and `gh pr ready` until the gate roles have run after the last code edit.
7. **Wait for CI without polling.** Bind the pull request to the session when the app offers it (the desktop app's pull request tools), then end the turn with the line "Draft pull request #N is waiting for CI". Do not loop, sleep or watch. When the session is woken (a CI event from the app, or the owner says "continue"), read `gh pr checks <n>` once: green, then step 8; red, then fix, re-run the local checks and both gates, push, and end the turn again with the same line; still running, end the turn again with the same line.
8. **Mark ready and report.** With CI green, shown by recorded `gh pr checks` output, run `gh pr ready <n>` and comment on the issue with the pull request link, the CI run link, the evidence and the roles' verdicts. Keep `status:in-progress` until the owner merges.

## Stop and report instead of continuing when

- an owner decision named in the ticket is open and the ticket states no default (label `needs-decision` and say so on the issue);
- CI is red and the cause is not in your diff;
- a gate cannot pass without widening the ticket's scope.

## Never

- Merge, close issues, release, tag or push to `main`; only the owner merges and releases.
- Start a second ticket or schedule another run.
- Change `.github/`, `.claude/`, `LOOP.md`, `CLAUDE.md` or `AGENTS.md` unless the ticket is about them.
