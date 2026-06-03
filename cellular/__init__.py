"""cellular — elementary (Wolfram) cellular automata, drawn in the terminal."""

from .automaton import Automaton, random_row, rule_table, single_cell
from .render import to_half_blocks, to_svg, to_text

__all__ = [
    "Automaton",
    "rule_table",
    "single_cell",
    "random_row",
    "to_text",
    "to_half_blocks",
    "to_svg",
]
