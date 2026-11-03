# Diagrams

How the diagrams in `docs/images/` are made and how to change them
without breaking them in some viewers. There are two, both shown in
`docs/design.md`:

- `docs/images/architecture.svg`, under "Why this stack": how a session is
  contained.
- `docs/images/claude-code-image.svg`, under "`agentbox`: image, managed
  settings and launcher": how Claude Code gets into the image and into a
  session, and how an update replaces it.

---

## Contents

- [Source and published file](#source-and-published-file)
- [Why the published file is flattened](#why-the-published-file-is-flattened)
- [The rules for a source](#the-rules-for-a-source)
- [The palette](#the-palette)
- [The layout grid](#the-layout-grid)
  - [architecture.svg](#architecturesvg)
  - [claude-code-image.svg](#claude-code-imagesvg)
- [Changing a diagram](#changing-a-diagram)
- [Checking it](#checking-it)

---

## Source and published file

Each diagram exists twice, under the same name:

| | Where | Written by |
|---|---|---|
| Source | `dev/diagrams/<name>.svg` | hand: classes and CSS custom properties, readable and easy to change |
| Published | `docs/images/<name>.svg` | `dev/flatten-svg.py`, from the source; never edited by hand |

```bash
dev/flatten-svg.py dev/diagrams/<name>.svg docs/images/<name>.svg
```

The script needs Python 3 and nothing else. No drawing tool, nothing to
install. Both files are committed together.

## Why the published file is flattened

A diagram has to render in three kinds of places:

- **GitHub and browsers**, as an `<img>`. Full CSS, including
  `prefers-color-scheme`.
- **Plain SVG viewers** built on librsvg (GNOME's image viewer, GIMP).
  They do not support CSS custom properties: a first version that
  coloured everything with `var(--…)` showed as a black rectangle.
- **ImageMagick's built-in renderer**, the weakest: no multi-class
  selectors, no `fill-opacity`, and no `<tspan>` layout.

So the script makes the published file safe for all three:

- **Colours become attributes.** Every shape and text gets its light
  `fill`, `stroke`, font and size as presentation attributes, which every
  renderer reads.
- **No transparency.** Each `fill-opacity` tint becomes a solid colour,
  the tint blended over the background.
- **CSS holds only the dark override.** The `<style>` block keeps a single
  `@media (prefers-color-scheme: dark)` block that sets only `fill` and
  `stroke`. CSS beats presentation attributes, so a font set there would
  override the monospace attributes. A viewer that ignores the CSS shows
  the light version.
- **Single quotes inside attributes**, so `'Segoe UI'` does not end the
  attribute value.

The classes stay on the elements: they are what the dark block hooks into.

## The rules for a source

- **The `<style>` block starts with the two palettes.** Its first line is
  the light palette on `svg{--bg:…;--fg:…;…}`, its second the dark one
  inside `@media (prefers-color-scheme: dark){svg{…}}`. The script reads
  them from there.
- **One selector per rule after that**, `text` or `.class`: no
  combinators, no nesting. An element with several classes gets them in
  the order of its `class` attribute, so the last one wins, as `chip` does
  in `class="frame b-vm chip"`.
- **No `<tspan>`.** ImageMagick lays it out on top of the text before it.
  A bold word in a sentence is a separate `<text>` with its own `x`.
- **Self-contained.** No `<script>`, no `<foreignObject>`, no external
  fonts or images. Fonts are system stacks: `system-ui, -apple-system,
  "Segoe UI", Roboto, sans-serif`, and `ui-monospace, SFMono-Regular,
  Menlo, Consolas, monospace` for code.
- **Nothing private**, as everywhere in the repository: addresses and
  limits are the example policy's.
- The `data-layer` and `data-part` attributes on the groups, and the
  empty `<g id="sim">`, do nothing in the file. They are hooks for an
  interactive version of the drawings, and harmless otherwise.

## The palette

The outline colour of a box is the role that builds it, which the
controller column of the first drawing explains. The tints are what the
script computes for the published file.

| Class | Meaning | Light | Light tint | Dark | Dark tint |
|---|---|---|---|---|---|
| `vm` | `virtualbox_vm` | `#2f6fae` | `#e4ebf3` | `#6aa8e0` | `#17212d` |
| `pod` | `podman` | `#13806f` | `#deebec` | `#3cc4b3` | `#14272b` |
| `egr` | `egress_proxy` | `#b8650f` | `#ede6df` | `#f0a35a` | `#2b2623` |
| `box` | `agentbox` | `#6648b8` | `#e4e3f2` | `#a990ec` | `#222435` |
| `tok` | `git_token` | `#94750a` | | `#e0c048` | `#2d2d21` |
| `mu` | not built by a role; muted text | `#5a6575` | `#e8eaee` | `#95a2b4` | `#1b2129` |
| `ok` | allowed path, allowlist | `#1f7f45` | `#dce9e5` | `#5cc77a` | `#192b27` |
| `no` | blocked | `#c23a2f` | `#efe4e6` | `#f07066` | `#271e23` |

Background and text: light `#f4f6f9` and `#18212c`, dark `#0f141b` and
`#e3e8ef`.

The class prefixes: `b-` a box (tint fill, colour stroke), `c-` coloured
text, `s-` a solid swatch, `l-` a line (`l-ok` allowed, `l-no` blocked,
dashed, `l-mu` neutral, `l-box` the image's path), `x` the red cross at a
blocked end, `chip` a small label box with a solid background.

## The layout grid

Both diagrams are 1290 px wide and share the conventions below the
first table.

### architecture.svg

`viewBox="0 0 1290 850"`. From left to right:

| Column | x | What |
|---|---|---|
| Controller | 20–225 | playbooks, roles in run order, policy, legend |
| VirtualBox host | 245–1080 | dashed outline |
| VM | 265–1050 | |
| Nested layers | 280–740 | `agent` 280, Podman 296, container 312, Claude Code 328; each step inward is 16 px |
| Egress column | 770–1030 | nftables y 300–410, Squid y 450–590, `ansible` y 640–760 |
| Internet | 1110–1270 | denied hosts y 300–450, allowlist y 480–680 |

Text inside a box starts 16 px from its left edge. Headings are 14 px,
running text 12 px, code 11 px, notes 10 to 11 px. The `stops:` line of
each layer is italic and muted.

The allowed path runs from the Claude Code box at y 470, up the gap at
x 755 into nftables at y 355, down at x 900 into Squid, and out at y 540
through the NAT chip to the allowlist.

### claude-code-image.svg

`viewBox="0 0 1290 1070"`. Four rows inside the VM, with 40 px between
them for the arrows, and the update strip below the VM:

| Row | y | Left | Right |
|---|---|---|---|
| Recipe | 130–290 | `/etc/agentbox/` x 265–505, build or not x 535–745 | |
| Build | 330–565 | `podman build` x 265–745 | Squid x 775–1030, internet x 1090–1270 |
| Storage | 605–725 | image storage x 265–745 | the role's check x 775–1030 |
| Run | 765–845 | launcher x 265–505 | session container x 535–1030 |
| Update | 918–1010 | four steps, 290 px wide, 30 px apart, x 20–1270 | |

The controller sits at x 20–225, y 130–330, and the VM at x 245–1050,
y 90–860. Each build step names the host it needs, right-aligned, in the
`egress_proxy` colour.

## Changing a diagram

- Edit the source in `dev/diagrams/`, then run `dev/flatten-svg.py` and
  commit both files.
- Copy a neighbouring element of the same kind and change its text and
  position. That keeps its classes.
- Check that the text fits: about 6.2 px per character for 12 px text and
  6.6 px for 11 px code.
- A new colour: add it to both palette lines of the source, and a row to
  the table above.
- When the design changes what a part does, the diagram changes in the
  same commit, like any other doc file.

## Checking it

```bash
xmllint --noout docs/images/<name>.svg            # well-formed XML
convert docs/images/<name>.svg /tmp/<name>.png    # ImageMagick's own renderer: the strictest
```

Then open it in a browser in both themes. In ImageMagick's render, the
arrowheads and some letter spacing are missing; that is expected. Black
or missing boxes mean the published file was edited by hand, or a rule
for the source was broken.
