# Releasing

When this collection gets a new version, which number it gets, and how a
release is made: the tag, the push and the GitHub release. Users install
from Git and pin a tag, so the tag is the release.

---

## Contents

- [What a tag means](#what-a-tag-means)
- [Which version](#which-version)
- [How to release](#how-to-release)
- [GitHub releases](#github-releases)

---

## What a tag means

A tag `vX.Y.Z` is a promise: this commit passed the release tests, and it
can be pinned.

- **A pushed tag is never moved or deleted.** Whoever pinned it must keep
  getting exactly that code. A broken release is fixed by a new tag, never
  by moving the old one. Before the push, a tag may still be moved.
- **Not every commit on `main` is tagged.** `main` is what comes next.
  Changes collect under `[Unreleased]` in CHANGES.md until a release is due.

## Which version

Semver, below 1.0.0 until the extension points are stable.

| Change | Version | Examples |
|---|---|---|
| A bug fix, with no change to variables or to behaviour a user would notice | **patch**, 0.1.**1** | a task that fails on a fresh VM; a wrong default path |
| A new feature or variable, a behaviour change, or anything that breaks an existing setup (below 1.0, breaking changes are minor too) | **minor**, 0.**2**.0 | a new extension point; a renamed variable; a new Claude Code version, which rebuilds the image and changes what runs |
| Docs only | **none**: they wait on `main` for the next release | a new explanation; a fixed typo |
| Docs that fix something misleading about installing or about security | **patch** | a wrong install line; a wrong claim about what the sandbox protects |
| Extension points stable, and compatibility promised from then on | **1.0.0** | |

When `[Unreleased]` holds changes of several kinds, the highest one decides.

A release is due when `[Unreleased]` holds a fix or a change a user would
want, not when a certain amount has collected. Fixes for something broken
or insecure are released at once.

## How to release

1. The changes are in CHANGES.md under `[Unreleased]`.
2. The release tests from [docs/release-tests.md](../docs/release-tests.md)
   that the change needs have run, and are recorded there: the full run
   for code changes, the upgrade test from the previous tag where a role
   changed, and the known-unknowns session where Claude Code, the managed
   settings or the launcher changed.
3. `galaxy.yml` has the new version, and so has the pinned install example
   in the README.
4. CHANGES.md: `[Unreleased]` becomes `## [x.y.z] - <date> — <name>`, under
   a fresh empty `[Unreleased]`.
5. One commit on `main`, subject `Release vX.Y.Z — <name>`, and an annotated
   tag `vX.Y.Z` with the message `vX.Y.Z — <name>`. Without a name, the
   bare version in all three places.
6. `main` and the tag pushed.
7. The GitHub release created from the tag the same day (below).

## GitHub releases

- **One GitHub release per tag, always.** The Releases page is where people
  look first, and watching a repository for releases notifies only on
  releases, not on tags.
- **Title** `vX.Y.Z — <name>`, the same as the tag message.
- **Notes**, short: what changed for a user, anything that needs action
  (for example "rename `x` to `y` in your group_vars"), the install line
  pinned to the tag, and a link to CHANGES.md at the tag. Links point at
  `blob/vX.Y.Z/…`; relative links do not resolve in release notes.
- **0.x releases are not marked as pre-release.** Semver below 1.0 already
  says the interface may change, and on GitHub a pre-release is never the
  latest. Pre-release is for a real release candidate only, such as
  `v0.2.0-rc.1`, tested by others before the release.
- **"Set as the latest release"** for every regular release.
- **No build artefacts attached.** The collection is installed from Git; a
  `tar.gz` would be a second way in that nobody uses.
