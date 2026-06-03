"""Rendering for a collapsed Wave Function Collapse grid.

The solver hands back a grid of tile *indices*; here we turn that into pixels by
**stamping** each tile's little pixel pattern into place, then drawing the
resulting pixel field either as terminal text (compact half-blocks, two pixel
rows per line) or as a standalone SVG you can drop into a README or a browser.

A "pixel field" is just a list of equal-length strings — the patterns laid out
edge to edge, with no gaps between tiles, so adjacent pipe arms or coastlines
join up seamlessly.

    from wavefn.render import stamp, to_half_blocks, to_svg
    field = stamp(grid, tiles)        # list[str]
    print(to_half_blocks(field))      # terminal art

Only the standard library is used.
"""

from __future__ import annotations

from .tilesets import Tile


def stamp(grid: list[list[int]], tiles: list[Tile]) -> list[str]:
    """Lay every tile's pixel pattern into one big pixel field.

    `grid[y][x]` is a tile index; each tile contributes a block of pixels of its
    own size. All tiles in a set share a size, so the field comes out as a clean
    rectangle of ``height*tile_h`` rows by ``width*tile_w`` columns.
    """
    if not grid or not grid[0]:
        return []
    tw, th = tiles[grid[0][0]].size
    field: list[str] = []
    for row in grid:
        # Each grid row expands to `th` pixel rows.
        block = ["" for _ in range(th)]
        for idx in row:
            pat = tiles[idx].pattern
            for r in range(th):
                block[r] += pat[r]
        field.extend(block)
    return field


def to_text(field: list[str]) -> str:
    """The pixel field as-is, one line per pixel row (full size)."""
    return "\n".join(field)


# How two vertically-stacked pixels look, keyed by whether each is "lit".
# A pixel counts as lit when it is not a space.
_HALF = {(False, False): " ", (True, False): "▀",
         (False, True): "▄", (True, True): "█"}


def to_half_blocks(field: list[str], lit: str | None = None) -> str:
    """Pack two pixel rows into each text line with Unicode half-blocks.

    A pixel is "lit" when its character is in `lit` (default: anything that is
    not a space). This halves the height and keeps the true aspect ratio, which
    looks far better in a terminal than one row per line.
    """
    if not field:
        return ""
    width = len(field[0])

    def is_lit(ch: str) -> bool:
        return ch != " " if lit is None else ch in lit

    lines = []
    blank = " " * width
    for top_i in range(0, len(field), 2):
        top = field[top_i]
        bottom = field[top_i + 1] if top_i + 1 < len(field) else blank
        lines.append(
            "".join(_HALF[(is_lit(top[x]), is_lit(bottom[x]))] for x in range(width))
        )
    return "\n".join(lines)


def to_svg(
    field: list[str],
    cell: int = 8,
    palette: dict[str, str] | None = None,
    background: str = "#ffffff",
    default: str = "#111111",
) -> str:
    """Render the pixel field as a standalone SVG string.

    `cell` is the size of one pixel in SVG units. `palette` maps pattern
    characters to fill colours; spaces draw the `background`, and any character
    without a palette entry falls back to `default`. Pixels that share a colour
    along a row are coalesced into one path per colour, so even a large grid
    stays compact — the same trick the cellular renderer uses.
    """
    if not field or not field[0]:
        return '<svg xmlns="http://www.w3.org/2000/svg" width="0" height="0"/>'
    palette = palette or {}
    height = len(field)
    width = len(field[0])
    w_px = width * cell
    h_px = height * cell

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w_px}" height="{h_px}" '
        f'viewBox="0 0 {w_px} {h_px}" shape-rendering="crispEdges">',
        f'<rect width="{w_px}" height="{h_px}" fill="{background}"/>',
    ]

    def colour(ch: str) -> str | None:
        if ch == " ":
            return None  # background, drawn already
        return palette.get(ch, default)

    # Collect coalesced horizontal segments per colour.
    by_colour: dict[str, list[str]] = {}
    for y, line in enumerate(field):
        x = 0
        while x < width:
            col = colour(line[x])
            if col is None:
                x += 1
                continue
            start = x
            while x < width and colour(line[x]) == col:
                x += 1
            run = x - start
            by_colour.setdefault(col, []).append(
                f"M{start * cell} {y * cell}h{run * cell}v{cell}h{-run * cell}z"
            )

    for col, segs in sorted(by_colour.items()):
        parts.append(f'<path fill="{col}" d="{"".join(segs)}"/>')

    parts.append("</svg>")
    return "".join(parts)
