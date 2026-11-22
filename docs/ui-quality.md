# UI quality rules

Ten binding rules for every screen and every piece of user-facing copy in this repository. They were set by the owner on 2026-11-22 (rules 1 and 2) and approved the same day (rules 3 to 10). They exist to avoid the usual marks of AI-generated interfaces. Changing them needs the owner.

1. No thick accent border on one side of a card, callout, alert, list item or quote (for example `border-left: 4px solid <accent>`). Use spacing, type weight, an icon or a full hairline border instead.
2. No "soft tinted background with a thin border of the same hue" as the default way to mark a status, tag, callout or card. One neutral surface and one clear signal (text, icon or a solid chip) is enough.
3. No gradient text and no purple-to-blue gradient as a default accent.
4. No blur or glass panels, and no drop shadow plus large radius on every card.
5. No emoji used as icons or bullets, and no sparkle marks.
6. No pill or badge on things that are not states. No all-caps, letter-spaced micro labels as section decoration.
7. No centred hero with a slogan in an application screen. Screens open on the user's task.
8. One accent colour, used for the primary action and the current selection. Status colours only for status.
9. Dense, aligned layouts on a consistent spacing scale. No card grid where a table or a list is the right form.
10. User-facing copy is plain and specific: no filler, no exclamation marks, and the same word for the same thing everywhere.

## How they are applied

- A UI ticket starts with the `ui-ux-pro-max` skill (`.claude/skills/ui-ux-pro-max/`): search the design system for the product type before writing markup or CSS.
- A UI ticket ends with a check of every changed screen against this file. The result goes into the pull request under Evidence.
- User-facing copy, documentation and pull request text go through the `unslop` skill (`.claude/skills/unslop/`) before the pull request is opened.
- Enforcement is the review gate: Code Reviewer runs on every ticket and checks these rules; Frontend Developer and Accessibility Auditor have this file in their checklists. Rule 1 can be linted with `grep -nE "border-(left|right|inline)" motion_studio/static/app.css`; rule 2 cannot be detected reliably from CSS, so it is a review judgement.
- These rules sit under the hard constraints in `CLAUDE.md`: no external origin, no inline style, no dependency.
- Findings against the existing screens are tracked in the epic, not fixed in passing.
