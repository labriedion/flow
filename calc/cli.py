"""Command-line interface for the calculator: one-shot or interactive REPL.

Examples:
    python -m calc.cli "2 + 3 * 4"
    python -m calc.cli "sqrt(2)^2"
    python -m calc.cli            # start the REPL
"""

from __future__ import annotations

import argparse
import sys

from .calculator import Calculator, CalcError, format_result, CONSTANTS, FUNCTIONS


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="calc",
        description="Evaluate arithmetic expressions.",
    )
    p.add_argument("expr", nargs="*", help="expression to evaluate; omit for a REPL")
    return p


def run_repl(calc: Calculator) -> int:
    print("calc — arithmetic REPL. Type an expression, ':help', or ':quit'.")
    while True:
        try:
            line = input("» ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if not line:
            continue
        if line in (":quit", ":q", "quit", "exit"):
            return 0
        if line in (":help", ":h"):
            _print_help()
            continue
        if line in (":vars",):
            if calc.vars:
                for k, v in calc.vars.items():
                    print(f"  {k} = {format_result(v)}")
            else:
                print("  (no variables defined)")
            continue
        try:
            result = calc.evaluate(line)
            print(format_result(result))
        except CalcError as exc:
            print(f"error: {exc}", file=sys.stderr)
    return 0


def _print_help() -> None:
    print("operators : + - * / % ^   (parentheses, unary minus)")
    print("constants : " + ", ".join(sorted(CONSTANTS)))
    print("functions : " + ", ".join(sorted(FUNCTIONS)))
    print("assign    : x = 3 * 4    (then use x in later expressions)")
    print("commands  : :vars  :help  :quit")


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Only -h/--help are real options. Everything else is part of the
    # expression — handled manually so a leading minus (e.g. "-2^2") isn't
    # mistaken for a flag by argparse.
    if argv and argv[0] in ("-h", "--help"):
        build_parser().parse_args(argv)
        return 0

    calc = Calculator()
    if argv:
        expr = " ".join(argv)
        try:
            print(format_result(calc.evaluate(expr)))
        except CalcError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        return 0
    return run_repl(calc)


if __name__ == "__main__":
    raise SystemExit(main())
