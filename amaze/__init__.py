"""amaze — a tiny dependency-free maze generator and solver."""

from .maze import (
    Maze,
    GENERATORS,
    SOLVERS,
    generate_backtracker,
    generate_prim,
    solve_bfs,
    solve_astar,
    braid,
    dead_ends,
)
from .render import render

__all__ = [
    "Maze",
    "GENERATORS",
    "SOLVERS",
    "generate_backtracker",
    "generate_prim",
    "solve_bfs",
    "solve_astar",
    "braid",
    "dead_ends",
    "render",
]
