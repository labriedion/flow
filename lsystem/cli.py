"""Command-line interface for L-systems: expand, then draw to SVG.

Examples:
    python -m lsystem.cli --preset plant --iterations 5 -o plant.svg
    python -m lsystem.cli --preset dragon -o dragon.svg
    python -m lsystem.cli --list                      # show the built-in presets
    python -m lsystem.cli --preset weed --seed 7 -o weed.svg   # stochastic
    # a custom system from the command line (repeat --rule for more symbols):
    python -m lsystem.cli --axiom F --rule "F=F+F-F-F+F" --angle 90 \\
        --iterations 4 -o koch.svg

Either pick a `--preset` or define your own with `--axiom` plus one or more
`--rule SYM=PRODUCTION`. `--list` prints every preset with its angle and a
suggested iteration count. Without `-o`, the SVG is written to stdout.
"""

from __future__ import annotations

import argparse
import sys

from .grammar import LSystem
from .presets import PRESETS, Preset, get
from .render import to_svg
from .turtle import interpret


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="lsystem",
        description="Expand an L-system and draw it as turtle-graphics SVG.",
    )
    p.add_argument("--preset", metavar="NAME",
                   help="use a built-in system (see --list)")
    p.add_argument("--list", action="store_true",
                   help="list the built-in presets and exit")
    p.add_argument("--axiom", metavar="STR",
                   help="starting string for a custom system")
    p.add_argument("--rule", action="append", default=[], metavar="SYM=PROD",
                   help="a production rule, e.g. F=F+F-F-F+F (repeatable)")
    p.add_argument("--angle", type=float, default=None,
                   help="turn angle in degrees (default: preset's, or 90)")
    p.add_argument("--step", type=float, default=None,
                   help="forward step length (default: preset's, or 10)")
    p.add_argument("--iterations", "-n", type=int, default=None,
                   help="number of rewrite passes (default: preset's, or 4)")
    p.add_argument("--heading", type=float, default=None,
                   help="initial heading in degrees, 0 = +x (default: preset's)")
    p.add_argument("--seed", type=int, default=None,
                   help="RNG seed for stochastic systems (reproducible)")
    p.add_argument("--gradient", action="store_true",
                   help="colour the stroke along a gradient (shows draw order)")
    p.add_argument("--stroke", default="#111111",
                   help="stroke colour (default: #111111)")
    p.add_argument("--stroke-width", type=float, default=1.0,
                   help="stroke width in px (default: 1)")
    p.add_argument("--margin", type=float, default=10.0,
                   help="SVG margin around the figure in px (default: 10)")
    p.add_argument("-o", "--out", metavar="PATH",
                   help="write the SVG here (default: stdout)")
    return p


def _format_list() -> str:
    """A human-readable table of the built-in presets."""
    lines = ["Built-in presets:"]
    width = max(len(name) for name in PRESETS)
    for name in sorted(PRESETS):
        preset = PRESETS[name]
        hint = f"angle {preset.angle:g}, ~{preset.iterations} iters"
        tag = " [stochastic]" if preset.system().is_stochastic else ""
        lines.append(f"  {name:<{width}}  {hint:<24}  {preset.description}{tag}")
    return "\n".join(lines)


def _parse_rule(spec: str) -> tuple[str, str]:
    """Split a `SYM=PRODUCTION` rule string into its two halves."""
    if "=" not in spec:
        raise ValueError(f"rule must look like SYM=PRODUCTION, got {spec!r}")
    symbol, _, production = spec.partition("=")
    if len(symbol) != 1:
        raise ValueError(f"rule symbol must be a single character, got {symbol!r}")
    return symbol, production


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.list:
        print(_format_list())
        return 0

    # Decide where the system, angle, step, etc. come from: a preset or custom.
    try:
        if args.preset is not None:
            if args.axiom is not None or args.rule:
                raise ValueError("use either --preset or --axiom/--rule, not both")
            preset: Preset = get(args.preset)
            system = preset.system()
            angle = preset.angle if args.angle is None else args.angle
            step = preset.step if args.step is None else args.step
            iterations = preset.iterations if args.iterations is None else args.iterations
            heading = preset.heading if args.heading is None else args.heading
        elif args.axiom is not None:
            rules: dict[str, str] = {}
            for spec in args.rule:
                symbol, production = _parse_rule(spec)
                rules[symbol] = production
            system = LSystem(args.axiom, rules)
            angle = 90.0 if args.angle is None else args.angle
            step = 10.0 if args.step is None else args.step
            iterations = 4 if args.iterations is None else args.iterations
            heading = 0.0 if args.heading is None else args.heading
        else:
            raise ValueError("nothing to draw: pass --preset NAME or --axiom STR")

        if iterations < 0:
            raise ValueError("iterations must be non-negative")
    except ValueError as exc:
        print(f"lsystem: {exc}", file=sys.stderr)
        return 2

    expanded = system.expand(iterations, seed=args.seed)
    segments = interpret(expanded, step=step, angle=angle, heading=heading)
    svg = to_svg(
        segments,
        margin=args.margin,
        stroke=args.stroke,
        stroke_width=args.stroke_width,
        gradient=args.gradient,
    )

    if args.out:
        try:
            with open(args.out, "w", encoding="utf-8") as f:
                f.write(svg)
        except OSError as exc:
            print(f"lsystem: could not write {args.out}: {exc}", file=sys.stderr)
            return 1
        label = args.preset or "custom"
        print(f"wrote {args.out} ({len(segments)} segments, {label}, {iterations} iters)")
        return 0

    print(svg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
