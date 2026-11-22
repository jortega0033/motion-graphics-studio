---
name: next-ticket
description: Take the next ready ticket of epic #1 up to a ready pull request. Started only by the owner; starting it is the go signal for one ticket.
argument-hint: "[issue number]"
disable-model-invocation: true
---

# Next ticket

The owner starts this with `/next-ticket` or `/next-ticket <issue number>`. Starting it is the owner's go signal for this run and counts as the owner asking to push the ticket branch and open the pull request. It runs one ticket, never merges and never starts another run by itself. `CLAUDE.md` wins where this file differs.

## Steps

1. **Refresh the queue.** `gh issue list --state open --limit 100` and `gh issue view` for epic #1 and its children. A ticket labelled `status:blocked` whose blocking tickets are all closed becomes `status:ready` (`gh issue edit <n> --remove-label status:blocked --add-label status:ready`).
2. **Pick one ticket.** With an issue number, use it, after checking it is open and not `needs-decision`. Without one, take the first `status:ready` child in the epic's table "Tickets in dependency order" that is not `status:in-progress` and not `needs-decision`. If none qualifies, say why and stop.
3. **Claim it.** Label it `status:in-progress`. Stop if it already has that label.
4. **Branch in a fresh worktree.** From an up-to-date `main`: `git worktree add ../motion-graphics-studio-<issue> -b <branch> origin/main`, with the branch named `feat/<issue>-<slug>`, `fix/<issue>-<slug>` or `docs/<slug>` as the Git workflow in `CLAUDE.md` says. Work only in that worktree.
5. **Run the playbook.** Follow `.claude/skills/implement-ticket/SKILL.md` from step 1 to its hand-off, including both gates on the current diff.
6. **Open the pull request.** Push the branch (`git push -u origin <branch>`, never `main`) and open a pull request against `main` with `.github/pull_request_template.md` filled in, `Closes #<issue>`, and a `CHANGELOG.md` line. Mark it ready only after both gates passed on the current diff and CI is green (`gh pr checks`). Never leave a gate open. The review gate hook blocks `gh pr create` and `gh pr ready` until the gate roles have run after the last code edit.
7. **Report.** Comment on the issue with the pull request link, the evidence and the roles' verdicts. Keep `status:in-progress` until the owner merges.

## Stop and report instead of continuing when

- an owner decision named in the ticket is open and the ticket states no default (label `needs-decision` and say so on the issue);
- CI is red and the cause is not in your diff;
- a gate cannot pass without widening the ticket's scope.

## Never

- Merge, close issues, release, tag or push to `main`; only the owner merges and releases.
- Start a second ticket or schedule another run.
- Change `.github/`, `.claude/`, `LOOP.md`, `CLAUDE.md` or `AGENTS.md` unless the ticket is about them.
