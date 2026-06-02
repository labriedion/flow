"""Command-line interface for the Markov text generator.

Examples:
    python -m markov.cli corpus.txt --order 2 --length 80
    cat book.txt | python -m markov.cli --char --order 4 --length 200
    python -m markov.cli corpus.txt --seed 7        # reproducible output
"""

from __future__ import annotations

import argparse
import sys

from .markov import MarkovChain


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="markov",
        description="Generate text with a Markov chain trained on a corpus.",
    )
    p.add_argument(
        "files", nargs="*",
        help="training text files; if omitted, read from stdin",
    )
    p.add_argument("-o", "--order", type=int, default=2, help="chain order (context length)")
    p.add_argument("-n", "--length", type=int, default=100, help="number of tokens to generate")
    p.add_argument("--char", action="store_true", help="operate on characters instead of words")
    p.add_argument("--seed", type=int, default=None, help="random seed for reproducible output")
    return p


def read_input(files: list[str]) -> str:
    if not files:
        return sys.stdin.read()
    parts = []
    for path in files:
        with open(path, "r", encoding="utf-8") as fh:
            parts.append(fh.read())
    return "\n".join(parts)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    text = read_input(args.files)
    if not text.strip():
        print("no training text provided", file=sys.stderr)
        return 2

    chain = MarkovChain(order=args.order, mode="char" if args.char else "word")
    chain.train(text)
    if chain.state_count == 0:
        print(
            f"corpus too small for order {args.order} "
            f"({'characters' if args.char else 'words'})",
            file=sys.stderr,
        )
        return 1

    print(chain.generate(length=args.length, seed=args.seed))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
