"""Command-line interface for elementary cellular automata.

Examples:
    python -m cellular.cli --rule 30                 # chaos, in the terminal
    python -m cellular.cli --rule 90                 # a Sierpinski triangle
    python -m cellular.cli --rule 110 --width 120 --height 80
    python -m cellular.cli --rule 30 --random --seed 7
    python -m cellular.cli --rule 90 --svg out.svg   # write an SVG instead

By default it starts from a single lit cell in the middle of the row and prints
the evolution using compact half-block characters.
"""

from __future__ import annotations

import argparse
import sys

from .automaton import Automaton, random_row, single_cell
from .render import to_half_blocks, to_svg, to_text


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cellular",
        description="Evolve and draw an elementary (Wolfram) cellular automaton.",
    )
    p.add_argument("--rule", type=int, default=30,
                   help="Wolfram rule number 0–255 (default: 30)")
    p.add_argument("--width", type=int, default=80,
                   help="number of cells per row (default: 80)")
    p.add_argument("--height", type=int, default=40,
                   help="number of generations to evolve (default: 40)")
    p.add_argument("--boundary", choices=["wrap", "zero", "one"], default="wrap",
                   help="what lies off the ends of the row (default: wrap)")
    p.add_argument("--random", action="store_true",
                   help="start from a random row instead of a single cell")
    p.add_argument("--density", type=float, default=0.5,
                   help="fraction of lit cells for a random start (default: 0.5)")
    p.add_argument("--seed", type=int, default=None,
                   help="seed for the random start (for reproducibility)")
    p.add_argument("--plain", action="store_true",
                   help="render one row per line with full blocks (no half-blocks)")
    p.add_argument("--svg", metavar="PATH",
                   help="write the run to an SVG file instead of the terminal")
    p.add_argument("--cell", type=int, default=4,
                   help="SVG cell size in pixels (default: 4)")
    p.add_argument("--grid", action="store_true",
                   help="draw faint cell grid lines in the SVG")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.width <= 0 or args.height < 0:
        print("cellular: width must be positive and height non-negative",
              file=sys.stderr)
        return 2

    try:
        automaton = Automaton(args.rule, boundary=args.boundary)
        if args.random:
            start = random_row(args.width, seed=args.seed, density=args.density)
        else:
            start = single_cell(args.width)
    except ValueError as exc:
        print(f"cellular: {exc}", file=sys.stderr)
        return 2

    rows = automaton.evolve(start, args.height)

    if args.svg:
        svg = to_svg(rows, cell=args.cell, grid=args.grid)
        try:
            with open(args.svg, "w", encoding="utf-8") as f:
                f.write(svg)
        except OSError as exc:
            print(f"cellular: could not write {args.svg}: {exc}", file=sys.stderr)
            return 1
        print(f"wrote {args.svg} ({args.width}×{len(rows)} cells, rule {args.rule})")
        return 0

    print(to_text(rows) if args.plain else to_half_blocks(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
