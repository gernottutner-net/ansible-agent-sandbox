# Diagrams

How the diagrams in `docs/images/` are made and how to change them
without breaking them in some viewers. For now there is one,
`docs/images/architecture.svg`, shown in `docs/design.md` under
"Why this stack".

---

## Contents

- [Why the file looks the way it does](#why-the-file-looks-the-way-it-does)
- [The rules](#the-rules)
- [The palette](#the-palette)
- [The layout grid](#the-layout-grid)
- [Changing the diagram](#changing-the-diagram)
- [Checking it](#checking-it)

---

## Why the file looks the way it does

The SVG is written by hand: no drawing tool, no build step, nothing to
install. It has to render in three kinds of places:

- **GitHub and browsers**, as an `<img>`. Full CSS, including
  `prefers-color-scheme`.
- **Plain SVG viewers** built on librsvg (GNOME's image viewer, GIMP).
  They do not support CSS custom properties: a first version that
  coloured everything with `var(--…)` showed as a black rectangle.
- **ImageMagick's built-in renderer**, the weakest: no multi-class
  selectors and no `fill-opacity`.

So the light colours are written as attributes on every element, which
every renderer reads, and CSS is used only for the dark variant. A viewer
that ignores the CSS shows the light version.

## The rules

- **Colours are attributes.** Every shape and text carries its light
  `fill` and `stroke` as presentation attributes, also fonts and sizes
  (`font-family`, `font-size`, `font-weight`). Never `var(--…)`, and never
  a light colour that exists only in CSS.
- **No transparency.** No `fill-opacity`. Box tints are solid colours,
  precomputed by blending the role colour over the background (see
  [The palette](#the-palette)).
- **CSS holds only the dark override.** The `<style>` block contains a
  single `@media (prefers-color-scheme: dark)` block, and that block sets
  only `fill` and `stroke`. CSS beats presentation attributes, so a font
  set there would override the monospace attributes.
- **Classes stay on the elements.** `class="frame b-vm"` and the like are
  what the dark block hooks into, so keep them on new elements, next to
  the attributes.
- **Single quotes inside attributes.** `font-family="system-ui,'Segoe UI',…"`;
  double quotes break the XML.
- **Self-contained.** No `<script>`, no `<foreignObject>`, no external
  fonts or images. Fonts are system stacks: `system-ui, -apple-system,
  'Segoe UI', Roboto, sans-serif`, and `ui-monospace, SFMono-Regular,
  Menlo, Consolas, monospace` for code.
- **Nothing private**, as everywhere in the repository: addresses and
  limits are the example policy's.
- The `data-layer` attributes on the groups, and the empty `<g id="sim">`,
  do nothing in the file. They are hooks for an interactive version of
  the drawing, and harmless otherwise.

## The palette

The outline colour of a box is the role that builds it, which the
controller column of the drawing explains.

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
dashed, `l-mu` neutral), `x` the red cross at a blocked end.

A new tint is the role colour blended over the background:

```python
def blend(colour, background, alpha):
    c = [int(colour[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(background[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(bb * (1 - alpha) + cc * alpha):02x}' for cc, bb in zip(c, b))

blend('#2f6fae', '#f4f6f9', 0.08)   # light tint, alpha 0.08 to 0.13
blend('#6aa8e0', '#0f141b', 0.09)   # dark tint, alpha 0.09 to 0.14
```

## The layout grid

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

## Changing the diagram

- Copy a neighbouring element of the same kind and change its text and
  position. That keeps the classes and the attributes together.
- Check that the text fits: about 6.2 px per character for 12 px text and
  6.6 px for 11 px code.
- A new colour or role: add its light attributes to the elements, its
  `fill` and `stroke` to the dark block, and a row to the table above.
- When the design changes what a part does, the diagram changes in the
  same commit, like any other doc file.

## Checking it

```bash
xmllint --noout docs/images/architecture.svg            # well-formed XML
convert docs/images/architecture.svg /tmp/arch.png      # ImageMagick's own renderer: the strictest
```

Then open it in a browser in both themes. In ImageMagick's render, the
arrowheads and some letter spacing are missing; that is expected. Black
or missing boxes mean a rule above was broken.
