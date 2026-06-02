"""Terminal rendering for mazes using Unicode box-drawing characters.

Each cell becomes a 2x1 block of characters so corridors read clearly. An
optional solution path is overlaid with colored dots.
"""

from __future__ import annotations

from .maze import Maze, N, S, E, W

WALL = "█"
PATH_CHAR = "·"

# ANSI colors for the overlaid solution path and endpoints.
RESET = "\033[0m"
PATH_COLOR = "\033[38;5;45m"   # cyan
START_COLOR = "\033[38;5;46m"  # green
GOAL_COLOR = "\033[38;5;201m"  # magenta


def render(maze: Maze, path: list[tuple[int, int]] | None = None,
           color: bool = True) -> str:
    """Return a printable string for the maze.

    The grid is drawn at double resolution: walls occupy the cells between
    passages, so an N-wide maze renders as (2N+1) characters per row.
    """
    path_set = set(path or [])
    start = path[0] if path else None
    goal = path[-1] if path else None

    w, h = maze.width, maze.height
    # Build a character grid of size (2h+1) x (2w+1).
    rows = 2 * h + 1
    cols = 2 * w + 1
    grid = [[WALL] * cols for _ in range(rows)]

    for y in range(h):
        for x in range(w):
            cy, cx = 2 * y + 1, 2 * x + 1
            grid[cy][cx] = " "  # cell interior
            if maze.linked(x, y, E):
                grid[cy][cx + 1] = " "
            if maze.linked(x, y, S):
                grid[cy + 1][cx] = " "
            # Northern and western passages are filled in by the neighbour,
            # but the entrance cell (0,0) has no neighbour to the N/W, so its
            # surrounding walls stay intact — which is what we want.

    # Overlay the solution path.
    for (x, y) in path_set:
        cy, cx = 2 * y + 1, 2 * x + 1
        ch = PATH_CHAR
        if (x, y) == start:
            ch = "S"
        elif (x, y) == goal:
            ch = "G"
        grid[cy][cx] = ch
        # Connect consecutive path cells through their shared passage.
    if path:
        for (x0, y0), (x1, y1) in zip(path, path[1:]):
            mx, my = x0 + x1 + 1, y0 + y1 + 1  # midpoint in char coords
            grid[my][mx] = PATH_CHAR

    if not color:
        return "\n".join("".join(r) for r in grid)

    # Colorize special characters.
    out_lines = []
    for r in grid:
        line = []
        for ch in r:
            if ch == "S":
                line.append(f"{START_COLOR}{ch}{RESET}")
            elif ch == "G":
                line.append(f"{GOAL_COLOR}{ch}{RESET}")
            elif ch == PATH_CHAR:
                line.append(f"{PATH_COLOR}{ch}{RESET}")
            else:
                line.append(ch)
        out_lines.append("".join(line))
    return "\n".join(out_lines)


def to_svg(maze: Maze, path: list[tuple[int, int]] | None = None,
           cell: int = 22, margin: int = 12) -> str:
    """Render the maze as a standalone SVG string.

    Walls are drawn as a single dark stroked path; an optional solution is
    overlaid as a smooth colored polyline with start/goal markers. SVG is
    crisp at any zoom and renders inline on GitHub, which makes it a nice
    artifact for a README.
    """
    w, h = maze.width, maze.height
    width = w * cell + 2 * margin
    height = h * cell + 2 * margin

    def gx(cx):
        return margin + cx * cell

    def gy(cy):
        return margin + cy * cell

    # Build the wall geometry. For each cell, draw the walls on the sides that
    # have no open passage; the outer border falls out of the same checks.
    segs = []
    for y in range(h):
        for x in range(w):
            x0, y0 = gx(x), gy(y)
            x1, y1 = gx(x + 1), gy(y + 1)
            if not maze.linked(x, y, N):
                segs.append(f"M{x0} {y0}H{x1}")
            if not maze.linked(x, y, W):
                segs.append(f"M{x0} {y0}V{y1}")
            if x == w - 1 and not maze.linked(x, y, E):
                segs.append(f"M{x1} {y0}V{y1}")
            if y == h - 1 and not maze.linked(x, y, S):
                segs.append(f"M{x0} {y1}H{x1}")
    walls = "".join(segs)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="#0d1017"/>',
        f'<path d="{walls}" fill="none" stroke="#5b6478" '
        f'stroke-width="2" stroke-linecap="square"/>',
    ]

    if path:
        pts = " ".join(f"{gx(x) + cell / 2:.1f},{gy(y) + cell / 2:.1f}" for x, y in path)
        parts.append(
            f'<polyline points="{pts}" fill="none" stroke="#21d4fd" '
            f'stroke-width="{max(2, cell // 6)}" stroke-linejoin="round" '
            f'stroke-linecap="round" opacity="0.9"/>'
        )
        sx, sy = path[0]
        gx_, gy_ = path[-1]
        r = cell * 0.28
        parts.append(
            f'<circle cx="{gx(sx) + cell / 2:.1f}" cy="{gy(sy) + cell / 2:.1f}" '
            f'r="{r:.1f}" fill="#2ecc71"/>'
        )
        parts.append(
            f'<circle cx="{gx(gx_) + cell / 2:.1f}" cy="{gy(gy_) + cell / 2:.1f}" '
            f'r="{r:.1f}" fill="#ff4fa3"/>'
        )

    parts.append("</svg>")
    return "\n".join(parts)
