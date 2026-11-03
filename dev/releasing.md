# Releasing

When this collection gets a new version, which number it gets, and how a
release is made: the tag, the push, the GitHub release and the
announcement. Users install from Git and pin a tag, so the tag is the
release.

---

## Contents

- [What a tag means](#what-a-tag-means)
- [Which version](#which-version)
- [How to release](#how-to-release)
- [GitHub releases](#github-releases)
- [Announcing](#announcing)

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
3. `galaxy.yml` has the new version, and so have the README's pinned
   install examples: the command and `requirements.yml` under "Install",
   the command under "Updating the collection".
4. CHANGES.md: `[Unreleased]` becomes `## [x.y.z] - <date> — <name>`, under
   a fresh empty `[Unreleased]`.
5. One commit on `main`, subject `Release vX.Y.Z — <name>`, and an annotated
   tag `vX.Y.Z` with the message `vX.Y.Z — <name>`. Without a name, the
   bare version in all three places.
6. `main` and the tag pushed.
7. The GitHub release created from the tag the same day (below).
8. The release announced on Mastodon and X, by hand, once the GitHub
   release is up ([Announcing](#announcing)).

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

## Announcing

- **By hand, from the template below.** At a release every few weeks a
  post takes two minutes and can say what is interesting about this one;
  an automated "vX.Y.Z released" cannot. Automation waits until there is a
  reason for it.
- **What changed first, the version second.** One or two concrete points a
  user would care about, from the release notes.
- **Link the GitHub release**, `…/releases/tag/vX.Y.Z`. Check the preview
  card the first time: if it is GitHub's generic release card instead of
  the social preview banner, link the repository and name the tag in the
  text.
- **Mastodon: hashtags.** With no algorithm, they are how a post is found.
  CamelCase, so screen readers say them right.
- **X: the link in the first reply**, not in the post, which is widely
  reported to get less reach with an outside link.
- **X: 280 characters**, a link counts as 23. The release name alone can
  take 50, so on X the points become short sentences instead of bullets.
- **X: two or three hashtags**, such as
  `#Ansible #VirtualBox #ClaudeCode`; more look like spam there. Mastodon
  gets the full set.
- **The banner as an image, with alt text**, where the link card is weak:
  `docs/images/README_banner.png`, and its alt text from the README.

```text
sacVB vX.Y.Z — <name>: <the headline change, in one line>.

- <point 1>
- <point 2>

https://github.com/gernottutner-net/ansible-agent-sandbox/releases/tag/vX.Y.Z

#Ansible #VirtualBox #Podman #ClaudeCode #AgenticCoding
```

Without a release name, `sacVB vX.Y.Z:`. On X the URL line moves to the
first reply, and the hashtags shrink to two or three.
