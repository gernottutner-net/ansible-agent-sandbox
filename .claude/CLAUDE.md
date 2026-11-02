# Project conventions

## Your role
- You help to maintain and develop the public Ansible collection `tutner.agent_sandbox` (github.com/gernottutner-net/ansible-agent-sandbox): a sandbox for agentic coding on VirtualBox.
- This file is part of the public repository. Keep it free of anything private, like the rest of the repo.

## Context
- README.md
- docs/design.md
- docs/virtualbox.md
- docs/release-tests.md
- dev/releasing.md
- CHANGES.md

## Public repository
- Nothing private goes in: no private host names, inventory, IPs other than examples, private paths or private mail addresses. Commits are authored with the GitHub noreply address set in .git/config.
- VirtualBox is the only supported platform.
- Versions follow semver; stay below 1.0.0 until the extension points are stable. The version lives in galaxy.yml and in CHANGES.md; a release also gets an annotated tag `vX.Y.Z`.
- The collection is installed from the Git URL only, never published to Galaxy.
- Before a release, run the release tests in docs/release-tests.md and record the run there.
- Releases, tags and GitHub releases follow dev/releasing.md.

## Rules
- All doc files, except CHANGES.md, get a TOC.
- Never automatically commit. Every `git commit`, every push, and every write to the remote issue tracker (issue bodies, comments, labels, state) gets its own explicit ask, with the content shown first — regardless of what was approved earlier in the same task. A "do it" for a task is not a yes for the recorded actions inside it.
- Never install or pull external resources, like NPM packages, automatically.
- Before every commit check the consistency of the doc files. Also check the correctness of their TOCs.
- The doc files: directory docs/, directory dev/, README.md.
- Before every commit update CHANGES.md. Create this file, if it doesn't exist.
- Before every commit, check on the basis of dev/releasing.md, "Which version", whether `[Unreleased]` with this commit makes a release due, and which version: none, patch or minor. Say so with the commit proposal, with the reason. Never cut it on your own: see Versioning.
- CHANGES.md structure: newest first at every level. `## [Unreleased]` sits directly under the intro, above released versions, which run newest to oldest. Beneath a version heading, `### <YYYY-MM-DD>` date headings run newest to oldest. Beneath a date, `#### Added`, `#### Changed`, `#### Decisions`, `#### Notes` in that order — omit any that are empty. A new bullet is prepended to its subsection; bullets recorded in the same batch keep whatever order reads best.
- CHANGES.md bullets carry no date prefix: the `###` heading is the date. Do not write `2026-08-23 — …` inside a bullet.
- Versioning: keep new CHANGES.md entries under `## [Unreleased]` and do NOT bump the version per change. Bump only when I explicitly say to cut a release — then rename `[Unreleased]` to `## [x.y.z] - <date> — <Release name>`, leaving the date headings inside it untouched, open a fresh empty `## [Unreleased]` above it.
- Release names: the name is the one I give when asking for the release. If I don't give one, omit the ` — <Release name>` suffix and use the bare `## [x.y.z] - <date>`. Use the same name in the commit subject and in the annotated tag message, so CHANGES.md, `git log` and `git tag` agree.
- Commit releases straight to `main` by default; no release branch is needed.
- Put the AI model used in every commit message. The `Co-Authored-By: <model> <noreply@anthropic.com>` trailer counts; add a separate line only if there is no such trailer.
