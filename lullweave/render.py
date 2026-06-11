"""Render a Weave — glyphs for the terminal, a standalone SVG for keeps.

The glyph frame is the brief's medium: one character per node, dark through
bright by loudness, so a flash is an '@' blooming out of a field of dots and
a wave is a ridge of '+*#' rolling across the screen. The hidden shortcuts
don't show — you only see them when a far corner lights up out of nowhere.

The SVG shows what the terminal can't: the wiring. Grid wires as faint
threads, shortcuts as long pale arcs over the top, and every node a firefly —
deep slate when dark, hot moss-gold mid-flash, the loud ones wearing a soft
halo. One moment of the weave, wires and all.
"""

GLYPHS = " .:-=+*#@"

# the firefly ramp: dark slate through moss to hot gold
_DARK = (24, 30, 44)
_MID = (96, 156, 84)
_FLASH = (244, 224, 122)


def glyph_frame(weave):
    """The weave as a width x height block of glyphs, loudness as brightness."""
    loud = weave.loudnesses()
    lines = []
    for y in range(weave.height):
        row = loud[y * weave.width:(y + 1) * weave.width]
        lines.append("".join(
            GLYPHS[min(len(GLYPHS) - 1, int(t * len(GLYPHS)))] for t in row))
    return "\n".join(lines)


def _fill(t):
    t = max(0.0, min(1.0, t))
    if t < 0.5:
        a, b, u = _DARK, _MID, t * 2.0
    else:
        a, b, u = _MID, _FLASH, (t - 0.5) * 2.0
    r, g, bl = (round(p + (q - p) * u) for p, q in zip(a, b))
    return f"#{r:02x}{g:02x}{bl:02x}"


def render_svg(weave, px=18, pad=14):
    """Return the weave as a standalone SVG string: wires, arcs, fireflies."""
    w = weave.width * px + 2 * pad
    h = weave.height * px + 2 * pad
    half = px / 2

    def at(i):
        return (pad + (i % weave.width) * px + half,
                pad + (i // weave.width) * px + half)

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">',
        f'  <rect width="{w}" height="{h}" fill="#06080f"/>',
        f'  <!-- lullweave: {weave.width}x{weave.height} nodes, '
        f'seed {weave.seed}, after {weave.tick} steps; '
        f'{len(weave.shortcuts)} shortcuts -->',
    ]

    # The grid wires — only the ones that don't wrap the world, so no thread
    # streaks across the picture. (The wrap is real; drawing it wouldn't be.)
    for i in range(weave.n):
        x, y = i % weave.width, i // weave.width
        x1, y1 = at(i)
        if x + 1 < weave.width:
            x2, y2 = at(i + 1)
            out.append(f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" '
                       f'y2="{y2:.1f}" stroke="#141c2e" stroke-width="1"/>')
        if y + 1 < weave.height:
            x2, y2 = at(i + weave.width)
            out.append(f'  <line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" '
                       f'y2="{y2:.1f}" stroke="#141c2e" stroke-width="1"/>')

    # The shortcuts — the hidden wires, drawn as long pale arcs so you can see
    # what the glyphs never show you.
    for a, b in weave.shortcuts:
        x1, y1 = at(a)
        x2, y2 = at(b)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        # bow the arc perpendicular to the wire, scaled with its length
        dx, dy = x2 - x1, y2 - y1
        d = (dx * dx + dy * dy) ** 0.5 or 1.0
        bow = min(70.0, d * 0.18)
        cx, cy = mx - dy / d * bow, my + dx / d * bow
        out.append(f'  <path d="M {x1:.1f} {y1:.1f} Q {cx:.1f} {cy:.1f} '
                   f'{x2:.1f} {y2:.1f}" fill="none" stroke="#3c4f78" '
                   f'stroke-width="1" stroke-opacity="0.55"/>')

    # The fireflies. Loud ones get a halo before their body.
    loud = weave.loudnesses()
    for i in range(weave.n):
        x, y = at(i)
        t = loud[i]
        if t > 0.45:
            out.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" '
                       f'r="{half * (1.1 + 1.6 * t):.1f}" fill="{_fill(t)}" '
                       f'fill-opacity="{0.22 * t:.3f}"/>')
        out.append(f'  <circle cx="{x:.1f}" cy="{y:.1f}" '
                   f'r="{half * (0.34 + 0.5 * t):.2f}" fill="{_fill(t)}"/>')

    out.append("</svg>")
    return "\n".join(out)
