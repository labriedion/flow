"""Command-line interface for the maze engine.

Examples:
    python -m amaze.cli --width 30 --height 15
    python -m amaze.cli -W 40 -H 20 --algo prim --solver astar --seed 7
    python -m amaze.cli -W 20 -H 12 --start 0,0 --goal 19,0 --braid 0.3
    python -m amaze.cli --no-solve --no-color
"""

from __future__ import annotations

import argparse
import sys

from .maze import GENERATORS, SOLVERS, braid, dead_ends
from .render import render, to_svg


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
    p.add_argument(
        "--braid", type=float, default=0.0, metavar="FRACTION",
        help="remove this fraction (0-1) of dead ends, adding loops",
    )
    p.add_argument(
        "--start", type=_coord, default=None, metavar="X,Y",
        help="start cell for the solution (default: 0,0)",
    )
    p.add_argument(
        "--goal", type=_coord, default=None, metavar="X,Y",
        help="goal cell for the solution (default: bottom-right)",
    )
    p.add_argument("--no-solve", action="store_true", help="do not overlay a solution")
    p.add_argument("--no-color", action="store_true", help="disable ANSI colors")
    p.add_argument(
        "--svg", action="store_true",
        help="emit an SVG image (to stdout) instead of terminal art",
    )
    return p


def _coord(text: str) -> tuple[int, int]:
    """Parse an "x,y" coordinate argument."""
    try:
        x, y = (int(part) for part in text.split(","))
    except ValueError:
        raise argparse.ArgumentTypeError(f"expected X,Y but got {text!r}")
    return (x, y)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.width < 1 or args.height < 1:
        print("width and height must be >= 1", file=sys.stderr)
        return 2

    start = args.start if args.start is not None else (0, 0)
    goal = args.goal if args.goal is not None else (args.width - 1, args.height - 1)
    for label, (cx, cy) in (("start", start), ("goal", goal)):
        if not (0 <= cx < args.width and 0 <= cy < args.height):
            print(f"{label} {cx},{cy} is out of bounds", file=sys.stderr)
            return 2

    maze = GENERATORS[args.algo](args.width, args.height, args.seed)
    if args.braid > 0:
        # Offset the seed so the braid pass isn't correlated with generation.
        braid(maze, args.braid, None if args.seed is None else args.seed + 1)

    path = None
    if not args.no_solve:
        path = SOLVERS[args.solver](maze, start, goal)

    if args.svg:
        print(to_svg(maze, path))
        return 0

    print(render(maze, path, color=not args.no_color))

    de = len(dead_ends(maze))
    bits = [
        f"{args.algo} maze",
        f"{args.width}×{args.height}",
        f"{de} dead ends",
    ]
    if args.braid > 0:
        bits.append("braided (has loops)")
    if path is not None:
        bits.append(f"{args.solver} path: {len(path)} cells")
    print("\n" + " · ".join(bits))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
