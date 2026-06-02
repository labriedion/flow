"""Command-line interface for the maze engine.

Examples:
    python -m amaze.cli --width 30 --height 15
    python -m amaze.cli -W 40 -H 20 --algo prim --solver astar --seed 7
    python -m amaze.cli --no-solve --no-color
"""

from __future__ import annotations

import argparse
import sys

from .maze import GENERATORS, SOLVERS
from .render import render


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="amaze",
        description="Generate and solve mazes in your terminal.",
    )
    p.add_argument("-W", "--width", type=int, default=25, help="maze width in cells")
    p.add_argument("-H", "--height", type=int, default=12, help="maze height in cells")
    p.add_argument(
        "--algo", choices=sorted(GENERATORS), default="backtracker",
        help="generation algorithm",
    )
    p.add_argument(
        "--solver", choices=sorted(SOLVERS), default="bfs",
        help="pathfinding algorithm for the solution overlay",
    )
    p.add_argument("--seed", type=int, default=None, help="random seed for reproducibility")
    p.add_argument("--no-solve", action="store_true", help="do not overlay a solution")
    p.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.width < 1 or args.height < 1:
        print("width and height must be >= 1", file=sys.stderr)
        return 2

    maze = GENERATORS[args.algo](args.width, args.height, args.seed)
    path = None
    if not args.no_solve:
        path = SOLVERS[args.solver](maze)

    print(render(maze, path, color=not args.no_color))

    if path is not None:
        print(f"\n{args.algo} maze · {args.solver} path · "
              f"{len(path)} cells from S to G")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
