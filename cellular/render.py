"""Rendering for cellular automata: terminal text and standalone SVG.

A run is a list of rows (each a list of 0/1). These helpers turn that grid into
something you can look at — block characters for the terminal, or a crisp SVG you
can drop into a README or open in a browser.
"""

from __future__ import annotations


def to_text(rows: list[list[int]], on: str = "█", off: str = " ") -> str:
    """One terminal line per row: `on` for a lit cell, `off` for a dead one."""
    return "\n".join("".join(on if c else off for c in row) for row in rows)


# The four ways two vertically-stacked cells can look, indexed by (top, bottom).
_HALF = {(0, 0): " ", (1, 0): "▀", (0, 1): "▄", (1, 1): "█"}


def to_half_blocks(rows: list[list[int]]) -> str:
    """Pack two rows into each line of text using Unicode half-block characters.

    Each output character shows two stacked cells (▀ top, ▄ bottom, █ both, space
    neither), so the picture comes out at its true aspect ratio and half the
    height — much nicer in a terminal than one row per line.
    """
    if not rows:
        return ""
    width = len(rows[0])
    lines = []
    for top_i in range(0, len(rows), 2):
        top = rows[top_i]
        bottom = rows[top_i + 1] if top_i + 1 < len(rows) else [0] * width
        lines.append("".join(_HALF[(top[x], bottom[x])] for x in range(width)))
    return "\n".join(lines)


def to_svg(
    rows: list[list[int]],
    cell: int = 4,
    on: str = "#111111",
    off: str = "#ffffff",
    grid: bool = False,
) -> str:
    """Render the grid as a standalone SVG string.

    `cell` is the size of one cell in pixels. Lit cells are drawn as `on`-colored
    rectangles over an `off`-colored background; `grid` adds faint cell lines.
    Only lit cells become rectangles, so the output stays compact.
    """
    if not rows:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0"/>'
    height = len(rows)
    width = len(rows[0])
    w_px = width * cell
    h_px = height * cell

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w_px}" height="{h_px}" '
        f'viewBox="0 0 {w_px} {h_px}" shape-rendering="crispEdges">',
        f'<rect width="{w_px}" height="{h_px}" fill="{off}"/>',
    ]
    # Emit lit cells as a single path of small rectangles — far smaller than one
    # <rect> element per cell.
    segments = []
    for y, row in enumerate(rows):
        x = 0
        while x < width:
            if row[x]:
                start = x
                while x < width and row[x]:
                    x += 1
                segments.append(
                    f"M{start * cell} {y * cell}h{(x - start) * cell}v{cell}"
                    f"h{-(x - start) * cell}z"
                )
            else:
                x += 1
    if segments:
        parts.append(f'<path fill="{on}" d="{"".join(segments)}"/>')

    if grid:
        lines = []
        for gx in range(width + 1):
            lines.append(f"M{gx * cell} 0v{h_px}")
        for gy in range(height + 1):
            lines.append(f"M0 {gy * cell}h{w_px}")
        parts.append(
            f'<path stroke="#cccccc" stroke-width="0.5" d="{"".join(lines)}"/>'
        )

    parts.append("</svg>")
    return "".join(parts)
