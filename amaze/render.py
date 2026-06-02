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
