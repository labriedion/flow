"""reggie — a small, dependency-free regex engine (Pike VM, linear time)."""

from .regex import (
    Match,
    Regex,
    RegexError,
    compile,
    findall,
    fullmatch,
    match,
    search,
)

__all__ = [
    "Match",
    "Regex",
    "RegexError",
    "compile",
    "findall",
    "fullmatch",
    "match",
    "search",
]
