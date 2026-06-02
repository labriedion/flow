"""Core maze data structure, generation algorithms, and solvers.

A maze is a grid of cells; walls live *between* cells. Each cell tracks which
of its four neighbours it has an open passage to. Generation algorithms carve
passages; solvers search the resulting passage graph.

No third-party dependencies — just the standard library.
"""

from __future__ import annotations

import heapq
import random
from collections import deque
from dataclasses import dataclass, field

# Direction bit flags stored per cell.
N, S, E, W = 1, 2, 4, 8
DX = {E: 1, W: -1, N: 0, S: 0}
DY = {N: -1, S: 1, E: 0, W: 0}
OPPOSITE = {N: S, S: N, E: W, W: E}


@dataclass
class Maze:
    width: int
    height: int
    # cells[y][x] is a bitmask of open passages (N/S/E/W).
    cells: list[list[int]] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.cells:
            self.cells = [[0] * self.width for _ in range(self.height)]

    def in_bounds(self, x: int, y: int) -> bool:
        return 0 <= x < self.width and 0 <= y < self.height

    def carve(self, x: int, y: int, direction: int) -> None:
        """Open the wall from (x, y) toward `direction`, and the matching wall
        on the neighbouring cell so passages are symmetric."""
        nx, ny = x + DX[direction], y + DY[direction]
        if not self.in_bounds(nx, ny):
            raise ValueError("cannot carve out of bounds")
        self.cells[y][x] |= direction
        self.cells[ny][nx] |= OPPOSITE[direction]

    def linked(self, x: int, y: int, direction: int) -> bool:
        """True if there is an open passage from (x, y) toward `direction`."""
        return bool(self.cells[y][x] & direction)

    def neighbors(self, x: int, y: int):
        """Yield (nx, ny) cells reachable from (x, y) through open passages."""
        for d in (N, S, E, W):
            if self.linked(x, y, d):
                yield x + DX[d], y + DY[d]


# --------------------------------------------------------------------------
# Generation
# --------------------------------------------------------------------------

def generate_backtracker(width: int, height: int, seed: int | None = None) -> Maze:
    """Recursive backtracker (randomized depth-first search).

    Produces long, winding corridors with relatively few short dead-ends.
    """
    rng = random.Random(seed)
    maze = Maze(width, height)
    visited = [[False] * width for _ in range(height)]
    stack = [(0, 0)]
    visited[0][0] = True

    while stack:
        x, y = stack[-1]
        unvisited = []
        for d in (N, S, E, W):
            nx, ny = x + DX[d], y + DY[d]
            if maze.in_bounds(nx, ny) and not visited[ny][nx]:
                unvisited.append(d)
        if unvisited:
            d = rng.choice(unvisited)
            maze.carve(x, y, d)
            nx, ny = x + DX[d], y + DY[d]
            visited[ny][nx] = True
            stack.append((nx, ny))
        else:
            stack.pop()
    return maze


def generate_prim(width: int, height: int, seed: int | None = None) -> Maze:
    """Randomized Prim's algorithm.

    Tends to produce mazes with many short branches and a more "bushy" texture
    than the backtracker.
    """
    rng = random.Random(seed)
    maze = Maze(width, height)
    in_maze = [[False] * width for _ in range(height)]

    sx, sy = rng.randrange(width), rng.randrange(height)
    in_maze[sy][sx] = True
    # Frontier of (x, y, direction-from-cell) candidate walls.
    frontier: list[tuple[int, int, int]] = []

    def add_walls(x: int, y: int) -> None:
        for d in (N, S, E, W):
            nx, ny = x + DX[d], y + DY[d]
            if maze.in_bounds(nx, ny) and not in_maze[ny][nx]:
                frontier.append((x, y, d))

    add_walls(sx, sy)
    while frontier:
        i = rng.randrange(len(frontier))
        x, y, d = frontier.pop(i)
        nx, ny = x + DX[d], y + DY[d]
        if in_maze[ny][nx]:
            continue
        maze.carve(x, y, d)
        in_maze[ny][nx] = True
        add_walls(nx, ny)
    return maze


GENERATORS = {
    "backtracker": generate_backtracker,
    "prim": generate_prim,
}


# --------------------------------------------------------------------------
# Post-processing
# --------------------------------------------------------------------------

def dead_ends(maze: Maze) -> list[tuple[int, int]]:
    """Cells with exactly one open passage — the tips of the maze's branches."""
    out = []
    for y in range(maze.height):
        for x in range(maze.width):
            if bin(maze.cells[y][x]).count("1") == 1:
                out.append((x, y))
    return out


def braid(maze: Maze, fraction: float = 1.0, seed: int | None = None) -> Maze:
    """Remove a fraction of dead ends by carving one extra passage out of each.

    Braiding turns a "perfect" maze (exactly one path between any two cells)
    into a "partial braid" with loops, so there are multiple routes to the
    goal. Because it only *adds* passages it never disconnects the maze. When
    possible it links a dead end to a neighbouring dead end, dissolving two at
    once. Mutates and returns the same maze.
    """
    rng = random.Random(seed)
    ends = dead_ends(maze)
    rng.shuffle(ends)
    target = int(round(len(ends) * max(0.0, min(1.0, fraction))))

    for (x, y) in ends[:target]:
        # Skip cells that an earlier braid already opened up.
        if bin(maze.cells[y][x]).count("1") != 1:
            continue
        # Directions we could carve into (in bounds and not already linked).
        options = []
        for d in (N, S, E, W):
            nx, ny = x + DX[d], y + DY[d]
            if maze.in_bounds(nx, ny) and not maze.linked(x, y, d):
                options.append(d)
        if not options:
            continue
        # Prefer connecting to another dead end so we resolve two at a time.
        preferred = [
            d for d in options
            if bin(maze.cells[y + DY[d]][x + DX[d]]).count("1") == 1
        ]
        d = rng.choice(preferred or options)
        maze.carve(x, y, d)
    return maze


# --------------------------------------------------------------------------
# Solving
# --------------------------------------------------------------------------

def solve_bfs(maze: Maze, start=(0, 0), goal=None) -> list[tuple[int, int]]:
    """Breadth-first search — returns the shortest path as a list of cells.

    Because every passage has unit cost, BFS already finds an optimal path.
    Returns an empty list if the goal is unreachable.
    """
    if goal is None:
        goal = (maze.width - 1, maze.height - 1)
    prev: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == goal:
            return _reconstruct(prev, goal)
        for nb in maze.neighbors(*cur):
            if nb not in prev:
                prev[nb] = cur
                q.append(nb)
    return []


def solve_astar(maze: Maze, start=(0, 0), goal=None) -> list[tuple[int, int]]:
    """A* search using Manhattan distance — same optimal length as BFS but it
    expands fewer cells, which matters on large grids."""
    if goal is None:
        goal = (maze.width - 1, maze.height - 1)

    def h(c):
        return abs(c[0] - goal[0]) + abs(c[1] - goal[1])

    prev: dict[tuple[int, int], tuple[int, int] | None] = {start: None}
    g = {start: 0}
    pq = [(h(start), 0, start)]
    while pq:
        _, cost, cur = heapq.heappop(pq)
        if cur == goal:
            return _reconstruct(prev, goal)
        if cost > g.get(cur, float("inf")):
            continue
        for nb in maze.neighbors(*cur):
            ng = cost + 1
            if ng < g.get(nb, float("inf")):
                g[nb] = ng
                prev[nb] = cur
                heapq.heappush(pq, (ng + h(nb), ng, nb))
    return []


def _reconstruct(prev, goal) -> list[tuple[int, int]]:
    path = [goal]
    while prev[path[-1]] is not None:
        path.append(prev[path[-1]])
    path.reverse()
    return path


SOLVERS = {
    "bfs": solve_bfs,
    "astar": solve_astar,
}
