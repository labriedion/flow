"""Command-line interface for the reggie regex engine.

Examples:
    python -m reggie.cli '\\d+'  "abc 123 def 456"        # highlight matches
    python -m reggie.cli -o '\\w+@\\w+'  "to bob@server"   # print matches only
    echo "the cat sat" | python -m reggie.cli 'c.t'       # read text from stdin
    python -m reggie.cli --groups '(\\w+)=(\\d+)' "x=10"   # show capture groups

By default every match in the text is highlighted in place. With several lines
of input, each line is searched independently (like grep).
"""

from __future__ import annotations

import argparse
import sys

from .regex import Regex, RegexError


# ANSI styling, used only when writing to a terminal.
_BOLD = "\033[1;31m"
_RESET = "\033[0m"


def _highlight(rx: Regex, line: str, color: bool) -> tuple[str, int]:
    """Return `line` with every non-overlapping match wrapped, plus a count."""
    out = []
    last = 0
    count = 0
    for m in rx.finditer(line):
        s, e = m.span()
        if e == s:
            continue  # don't visually mark zero-width matches
        out.append(line[last:s])
        piece = line[s:e]
        out.append(f"{_BOLD}{piece}{_RESET}" if color else f"[{piece}]")
        last = e
        count += 1
    out.append(line[last:])
    return "".join(out), count


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="reggie",
        description="Match a regular expression against text.",
    )
    p.add_argument("pattern", help="the regular expression")
    p.add_argument("text", nargs="?", help="text to search; omit to read stdin")
    p.add_argument("-o", "--only-matching", action="store_true",
                   help="print only the matched substrings, one per line")
    p.add_argument("-g", "--groups", action="store_true",
                   help="for the first match per line, print its capture groups")
    p.add_argument("-c", "--count", action="store_true",
                   help="print only a total count of matches")
    p.add_argument("--color", choices=["auto", "always", "never"], default="auto",
                   help="colorize highlighted matches (default: auto)")
    return p


def _want_color(mode: str) -> bool:
    if mode == "always":
        return True
    if mode == "never":
        return False
    return sys.stdout.isatty()


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        rx = Regex(args.pattern)
    except RegexError as exc:
        print(f"reggie: bad pattern: {exc}", file=sys.stderr)
        return 2

    if args.text is not None:
        lines = args.text.split("\n")
    else:
        lines = sys.stdin.read().split("\n")
        if lines and lines[-1] == "":
            lines.pop()  # ignore the trailing newline's empty final line

    color = _want_color(args.color)
    total = 0
    any_match = False

    for line in lines:
        matches = [m for m in rx.finditer(line) if m.end() != m.start()]
        total += len(matches)
        if matches:
            any_match = True
        if args.count:
            continue
        if args.only_matching:
            for m in matches:
                print(m.group(0))
        elif args.groups:
            for m in matches:
                groups = m.groups()
                shown = ", ".join("None" if g is None else repr(g) for g in groups)
                print(f"{m.group(0)}\t({shown})" if groups else m.group(0))
        elif matches:
            highlighted, _ = _highlight(rx, line, color)
            print(highlighted)

    if args.count:
        print(total)

    # Exit status follows grep: 0 if anything matched, 1 if not.
    return 0 if any_match else 1


if __name__ == "__main__":
    raise SystemExit(main())
