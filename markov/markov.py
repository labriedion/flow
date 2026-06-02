"""A small, dependency-free Markov-chain text generator.

A Markov chain of *order* k predicts the next token from the previous k tokens.
This module builds the transition table from training text and samples new text
from it. It works on either whitespace-delimited **words** or individual
**characters**, so you can generate prose-like babble or pronounceable made-up
words from the same code.

Only the Python standard library is used.
"""

from __future__ import annotations

import random
import re
from collections import defaultdict


def tokenize(text: str, mode: str) -> list[str]:
    """Split text into tokens. Word mode keeps punctuation attached to words
    (so generated text retains commas and periods); char mode yields characters.
    """
    if mode == "char":
        return list(text)
    if mode == "word":
        # Collapse runs of whitespace; keep everything else as-is.
        return re.split(r"\s+", text.strip())
    raise ValueError(f"unknown mode: {mode!r} (use 'word' or 'char')")


class MarkovChain:
    """An order-k Markov chain over word or character tokens."""

    def __init__(self, order: int = 2, mode: str = "word"):
        if order < 1:
            raise ValueError("order must be >= 1")
        if mode not in ("word", "char"):
            raise ValueError("mode must be 'word' or 'char'")
        self.order = order
        self.mode = mode
        # state (tuple of `order` tokens) -> {next_token: count}
        self.transitions: dict[tuple[str, ...], dict[str, int]] = defaultdict(
            lambda: defaultdict(int)
        )
        # States that legitimately begin the text, used as generation seeds.
        self.starts: list[tuple[str, ...]] = []

    def train(self, text: str) -> "MarkovChain":
        """Add a body of text to the model. Can be called repeatedly."""
        tokens = tokenize(text, self.mode)
        k = self.order
        if len(tokens) <= k:
            return self  # not enough to form a single transition
        self.starts.append(tuple(tokens[:k]))
        for i in range(len(tokens) - k):
            state = tuple(tokens[i:i + k])
            nxt = tokens[i + k]
            self.transitions[state][nxt] += 1
        return self

    def _weighted_choice(self, options: dict[str, int], rng: random.Random) -> str:
        total = sum(options.values())
        r = rng.randrange(total)
        upto = 0
        for token, count in options.items():
            upto += count
            if r < upto:
                return token
        # Unreachable barring float/int corruption; satisfy type checkers.
        return next(iter(options))

    def generate(self, length: int = 100, seed: int | None = None) -> str:
        """Generate up to `length` tokens. When the chain hits a dead-end state
        (one with no recorded successors) it restarts from a random start state,
        so generation never gets stuck.
        """
        if not self.transitions:
            raise ValueError("model is empty — train it first")
        rng = random.Random(seed)
        state = list(rng.choice(self.starts))
        out = list(state)

        while len(out) < length:
            key = tuple(state)
            options = self.transitions.get(key)
            if not options:
                # Dead end: jump to a fresh starting state.
                state = list(rng.choice(self.starts))
                out.extend(state)
                continue
            nxt = self._weighted_choice(options, rng)
            out.append(nxt)
            state = out[-self.order:]

        out = out[:length]
        return ("" if self.mode == "char" else " ").join(out)

    @property
    def state_count(self) -> int:
        return len(self.transitions)
