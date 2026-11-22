# Releasing

Only the owner releases. Agents never tag, publish or create a release.

## What a release is here

A tagged commit on `main`. Motion Studio is a local application run from the checkout with `python -m motion_studio`; there is no package, installer or deployment to publish.

## Before tagging

1. `main` is up to date and CI is green on the commit to be tagged (Linux and Windows).
2. On a clean checkout with no third-party packages: `python -m unittest discover -s tests -v` passes. Record the test count.
3. The release integration gate (epic #1, ticket #7) has been recorded for this commit, once that ticket is done.
4. `README.md`, the "Delivery status" table in `docs/PRD.md` and `docs/ARCHITECTURE.md` describe this commit.
5. In `CHANGELOG.md`, move the `Unreleased` entries under a new version heading with the date.

## Tagging

The owner commits the changelog change through a pull request, then tags the merge commit on `main` (`vX.Y.Z`) and pushes the tag. Version numbers follow Semantic Versioning; `0.x` until the epic's finish line holds.
