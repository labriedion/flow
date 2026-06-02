"""Tests for the maze engine. Run with: python -m pytest amaze/

These verify the structural guarantees we care about: every cell is reachable
(perfect maze), passages are symmetric, solutions are valid and optimal, and
generation is reproducible under a fixed seed.
"""

from .maze import (
    Maze, N, S, E, W, DX, DY, OPPOSITE,
    generate_backtracker, generate_prim, GENERATORS,
    solve_bfs, solve_astar, braid, dead_ends,
)


def _count_reachable(maze: Maze, start=(0, 0)) -> int:
    seen = {start}
    stack = [start]
    while stack:
        cur = stack.pop()
        for nb in maze.neighbors(*cur):
            if nb not in seen:
                seen.add(nb)
                stack.append(nb)
    return len(seen)


def _passages_symmetric(maze: Maze) -> bool:
    for y in range(maze.height):
        for x in range(maze.width):
            for d in (N, S, E, W):
                if maze.linked(x, y, d):
                    nx, ny = x + DX[d], y + DY[d]
                    if not maze.in_bounds(nx, ny):
                        return False
                    if not maze.linked(nx, ny, OPPOSITE[d]):
                        return False
    return True


def _path_valid(maze: Maze, path) -> bool:
    """Every consecutive pair in a path must be linked by an open passage."""
    for a, b in zip(path, path[1:]):
        if b not in set(maze.neighbors(*a)):
            return False
    return True


import pytest


@pytest.mark.parametrize("gen", list(GENERATORS.values()))
@pytest.mark.parametrize("size", [(1, 1), (2, 3), (10, 10), (20, 8)])
def test_perfect_maze_every_cell_reachable(gen, size):
    w, h = size
    maze = gen(w, h, seed=123)
    assert _count_reachable(maze) == w * h


@pytest.mark.parametrize("gen", list(GENERATORS.values()))
def test_passages_symmetric(gen):
    maze = gen(15, 9, seed=7)
    assert _passages_symmetric(maze)


def test_generation_is_reproducible():
    a = generate_backtracker(12, 12, seed=99).cells
    b = generate_backtracker(12, 12, seed=99).cells
    assert a == b
    c = generate_backtracker(12, 12, seed=100).cells
    assert a != c


@pytest.mark.parametrize("gen", list(GENERATORS.values()))
def test_solvers_find_valid_paths(gen):
    maze = gen(18, 14, seed=5)
    start, goal = (0, 0), (17, 13)
    bfs = solve_bfs(maze, start, goal)
    astar = solve_astar(maze, start, goal)
    assert bfs and astar
    assert bfs[0] == start and bfs[-1] == goal
    assert _path_valid(maze, bfs)
    assert _path_valid(maze, astar)


@pytest.mark.parametrize("gen", list(GENERATORS.values()))
def test_bfs_and_astar_agree_on_optimal_length(gen):
    # In a perfect maze there is exactly one simple path between any two cells,
    # so both optimal searches must return the same length.
    maze = gen(16, 16, seed=11)
    assert len(solve_bfs(maze)) == len(solve_astar(maze))


def test_carve_out_of_bounds_raises():
    maze = Maze(3, 3)
    with pytest.raises(ValueError):
        maze.carve(0, 0, N)


def test_trivial_single_cell():
    maze = generate_prim(1, 1, seed=1)
    assert solve_bfs(maze) == [(0, 0)]


@pytest.mark.parametrize("gen", list(GENERATORS.values()))
def test_full_braid_removes_all_dead_ends(gen):
    maze = gen(16, 12, seed=3)
    assert len(dead_ends(maze)) > 0          # a fresh perfect maze has dead ends
    braid(maze, fraction=1.0, seed=3)
    assert len(dead_ends(maze)) == 0


@pytest.mark.parametrize("gen", list(GENERATORS.values()))
def test_braid_keeps_maze_connected_and_symmetric(gen):
    maze = gen(20, 14, seed=8)
    braid(maze, fraction=0.5, seed=8)
    assert _count_reachable(maze) == 20 * 14
    assert _passages_symmetric(maze)


def test_partial_braid_reduces_but_keeps_some_dead_ends():
    maze = generate_backtracker(24, 24, seed=2)
    before = len(dead_ends(maze))
    braid(maze, fraction=0.4, seed=2)
    after = len(dead_ends(maze))
    assert 0 < after < before


def test_braid_is_reproducible():
    a = generate_prim(18, 18, seed=4)
    b = generate_prim(18, 18, seed=4)
    braid(a, 0.7, seed=42)
    braid(b, 0.7, seed=42)
    assert a.cells == b.cells


def test_braided_solution_still_valid():
    maze = generate_backtracker(20, 20, seed=6)
    braid(maze, 1.0, seed=6)
    path = solve_astar(maze)
    assert path and path[0] == (0, 0) and path[-1] == (19, 19)
    assert _path_valid(maze, path)
    # With loops present, BFS and A* still agree on the *shortest* length.
    assert len(solve_bfs(maze)) == len(path)
