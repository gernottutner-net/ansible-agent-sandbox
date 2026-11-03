#!/usr/bin/env python3
"""Turn a diagram source from dev/diagrams/ into the file in docs/images/.

The source is readable: shapes and text carry classes, and the colours are
CSS custom properties. Plenty of SVG viewers cannot render that (librsvg
shows black, ImageMagick ignores fill-opacity), so the published file is
flattened, as dev/diagrams.md describes:

- light colours and fonts become presentation attributes on every element;
- translucent tints become solid colours, blended over the background;
- the <style> block keeps only a dark override of fill and stroke.

The source's <style> block must start with two lines: the light palette on
`svg{--name:#rrggbb;...}`, then the dark one inside
`@media (prefers-color-scheme: dark){svg{...}}`. Every rule after them is a
single selector, `text` or `.class`.

Usage: dev/flatten-svg.py dev/diagrams/<name>.svg docs/images/<name>.svg

Python 3 standard library only.
"""

import re
import sys

# Tints are written with the opacity that reads well in a browser over
# nested boxes; solid on one background they need a little more.
LIGHT_TINT = 1.6
DARK_TINT = 1.8

ATTRIBUTES = {
    'fill', 'stroke', 'stroke-width', 'stroke-dasharray', 'stroke-linecap',
    'stroke-linejoin', 'stroke-opacity', 'font-family', 'font-size',
    'font-weight', 'font-style', 'letter-spacing', 'text-anchor',
}
ELEMENTS = r'rect|text|tspan|line|polyline|path|circle'


def blend(colour, background, alpha):
    c = [int(colour[i:i + 2], 16) for i in (1, 3, 5)]
    b = [int(background[i:i + 2], 16) for i in (1, 3, 5)]
    return '#' + ''.join(f'{round(bb * (1 - alpha) + cc * alpha):02x}' for cc, bb in zip(c, b))


def resolve(body, palette, tint):
    """Replace var(--x) by the palette's colour and fill-opacity by a solid tint."""
    body = re.sub(r'var\(--(\w+)\)', lambda m: palette[m.group(1)], body)
    body = re.sub(r'fill:(#[0-9a-f]{6});fill-opacity:([.\d]+)',
                  lambda m: 'fill:' + blend(m.group(1), palette['bg'], float(m.group(2)) * tint),
                  body)
    # Double quotes would end the attribute value.
    return body.replace('"', "'")


def declarations(body):
    return dict(kv.split(':', 1) for kv in body.split(';') if kv.strip())


def main(source, target):
    svg = open(source, encoding='utf-8').read()
    style = re.search(r'<style>\n(.*?)</style>', svg, re.S)
    lines = style.group(1).split('\n')
    light = dict(re.findall(r'--(\w+):(#[0-9a-f]{6})', lines[0]))
    dark = dict(re.findall(r'--(\w+):(#[0-9a-f]{6})', lines[1]))
    rules = re.findall(r'([.\w-]+)\{([^}]*)\}', '\n'.join(lines[2:]))

    light_rules = {sel: declarations(resolve(body, light, LIGHT_TINT)) for sel, body in rules}

    def add_attributes(m):
        tag, rest = m.group(1), m.group(2)
        found = re.search(r'class="([^"]*)"', rest)
        classes = found.group(1).split() if found else []
        if tag != 'text' and not classes:
            return m.group(0)
        props = dict(light_rules.get('text', {})) if tag == 'text' else {}
        for c in classes:
            props.update(light_rules.get('.' + c, {}))
        present = set(re.findall(r'\s([\w-]+)=', rest))
        added = ''
        for key, value in props.items():
            if key in ATTRIBUTES and key not in present:
                value = value.strip()
                if key == 'font-weight' and value == '650':
                    value = '600'
                added += f' {key}="{value}"'
        closing = '/' if rest.endswith('/') else ''
        return f'<{tag}{rest.rstrip("/")}{added}{closing}'

    head, body = svg[:style.end()], svg[style.end():]
    body = re.sub(rf'<({ELEMENTS})(\s[^>]*?)(?=>)', add_attributes, body)

    dark_css = []
    for sel, rule in rules:
        if 'var(' not in rule:
            continue
        props = [f'{k}:{v}' for k, v in declarations(resolve(rule, dark, DARK_TINT)).items()
                 if k in ('fill', 'stroke')]
        if props:
            dark_css.append(sel + '{' + ';'.join(props) + '}')
    head = head[:style.start()] + ('<style>\n@media (prefers-color-scheme: dark){\n'
                                   + '\n'.join(dark_css) + '\n}\n</style>')

    open(target, 'w', encoding='utf-8').write(head + body)


if __name__ == '__main__':
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
