"""Tests for the maze engine. Run with: python -m pytest amaze/

These verify the structural guarantees we care about: every cell is reachable
(perfect maze), passages are symmetric, solutions are valid and optimal, and
generation is reproducible under a fixed seed.
"""

import pytest

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


def _edge_count(maze: Maze) -> int:
    """Number of open passages. Each passage sets a bit on both cells it joins,
    so the total bit count is twice the number of edges."""
    bits = sum(
        bin(maze.cells[y][x]).count("1")
        for y in range(maze.height)
        for x in range(maze.width)
    )
    return bits // 2


@pytest.mark.parametrize("gen", list(GENERATORS.values()))
@pytest.mark.parametrize("size", [(1, 1), (2, 3), (10, 10), (20, 8)])
def test_perfect_maze_is_a_spanning_tree(gen, size):
    # A perfect maze is a spanning tree: connected AND acyclic. Connectivity is
    # |reachable| == cells; the tree (no-loops) property is edges == cells - 1.
    w, h = size
    maze = gen(w, h, seed=123)
    assert _count_reachable(maze) == w * h
    assert _edge_count(maze) == w * h - 1


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


def test_solvers_honor_custom_start_and_goal():
    maze = generate_backtracker(12, 9, seed=4)
    start, goal = (3, 2), (9, 7)
    for solver in (solve_bfs, solve_astar):
        path = solver(maze, start, goal)
        assert path and path[0] == start and path[-1] == goal
        assert _path_valid(maze, path)
    # Both remain optimal for the custom endpoints.
    assert len(solve_bfs(maze, start, goal)) == len(solve_astar(maze, start, goal))


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


def test_corridor_braid_cannot_remove_endpoint_dead_ends():
    # A 1xN maze is a straight corridor; its two ends have no in-bounds wall to
    # carve through, so full braiding legitimately leaves exactly those 2 dead
    # ends. This documents the limit of the "full braid removes all" invariant.
    maze = generate_backtracker(6, 1, seed=1)
    braid(maze, fraction=1.0, seed=1)
    assert len(dead_ends(maze)) == 2
    assert _count_reachable(maze) == 6  # still fully connected


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
