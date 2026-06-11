"""Render a Quilt to a standalone SVG.

Each tile is a square filled from a two-stop colour ramp (deep ink to warm
amber — quilt colours). Seams that still disagree are drawn over the top as
glowing stitch lines, opacity proportional to the mismatch; as the averaging
does its work those stitches fade everywhere except around the rebel, whose
four seams never close. The scar is the signature: it marks the cell the
whole quilt is slowly becoming.
"""

# The ramp: value 0 is deep ink, value 1 is warm amber.
_INK = (12, 16, 32)
_AMBER = (232, 162, 58)
_STITCH = "#ff5c7a"


def _fill(t):
    t = max(0.0, min(1.0, t))
    r, g, b = (round(a + (b_ - a) * t) for a, b_ in zip(_INK, _AMBER))
    return f"#{r:02x}{g:02x}{b:02x}"


def render_svg(quilt, px=28, pad=10):
    """Return the quilt as a standalone SVG string."""
    w = quilt.width * px + 2 * pad
    h = quilt.height * px + 2 * pad
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}">',
        f'  <rect width="{w}" height="{h}" fill="#070910"/>',
        f'  <!-- fenchurn: {quilt.width}x{quilt.height} tiles, seed {quilt.seed}, '
        f'after {quilt.tick} steps; rebel at {quilt.rebel} -->',
    ]

    # The tiles.
    for y in range(quilt.height):
        for x in range(quilt.width):
            cx, cy = pad + x * px, pad + y * px
            out.append(
                f'  <rect x="{cx}" y="{cy}" width="{px}" height="{px}" '
                f'fill="{_fill(quilt.value(x, y))}"/>'
            )

    # The stitches: every seam still in disagreement, drawn brighter the wider
    # it gapes. Quiet seams (and there will be more of them every step) draw
    # nothing at all.
    for y in range(quilt.height):
        for x in range(quilt.width):
            if x + 1 < quilt.width:
                gap = quilt.seam_mismatch(x, y, x + 1, y)
                if gap > 0.004:
                    sx = pad + (x + 1) * px
                    out.append(_stitch(sx, pad + y * px, sx, pad + (y + 1) * px, gap))
            if y + 1 < quilt.height:
                gap = quilt.seam_mismatch(x, y, x, y + 1)
                if gap > 0.004:
                    sy = pad + (y + 1) * px
                    out.append(_stitch(pad + x * px, sy, pad + (x + 1) * px, sy, gap))

    out.append("</svg>")
    return "\n".join(out)


def _stitch(x1, y1, x2, y2, gap):
    opacity = min(1.0, 0.15 + gap * 1.6)
    return (
        f'  <line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
        f'stroke="{_STITCH}" stroke-width="2" stroke-linecap="round" '
        f'stroke-opacity="{opacity:.3f}"/>'
    )
