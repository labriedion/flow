"""Tests for the Markov text generator. Run: python -m pytest markov/

The central guarantee we verify is *soundness*: every (context -> next token)
step the generator produces must be a transition that actually appeared in the
training text. We also check determinism under a seed, both tokenization modes,
and graceful handling of degenerate input.
"""

import pytest

from .markov import MarkovChain, tokenize

CORPUS = (
    "the quick brown fox jumps over the lazy dog . "
    "the lazy dog sleeps while the quick brown fox runs ."
)

# A cyclic corpus has no dead-end states, so generation never has to restart
# from a fresh seed. That lets us assert soundness over the *entire* output
# without tripping over restart seams.
CYCLIC = "alpha beta gamma delta " * 8


def _valid_transitions(chain: MarkovChain, tokens: list[str]) -> bool:
    """Every window of `order` tokens followed by the next must be a transition
    the model learned during training."""
    k = chain.order
    for i in range(len(tokens) - k):
        state = tuple(tokens[i:i + k])
        nxt = tokens[i + k]
        if nxt not in chain.transitions.get(state, {}):
            return False
    return True


@pytest.mark.parametrize("order", [1, 2, 3])
def test_generated_text_uses_only_learned_transitions(order):
    chain = MarkovChain(order=order, mode="word").train(CYCLIC)
    out = chain.generate(length=60, seed=1).split()
    assert len(out) == 60                 # non-trivial output to check
    assert _valid_transitions(chain, out)


def test_output_is_reproducible_with_seed():
    chain = MarkovChain(order=2).train(CORPUS)
    a = chain.generate(length=50, seed=42)
    b = chain.generate(length=50, seed=42)
    assert a == b
    c = chain.generate(length=50, seed=43)
    assert a != c  # different seeds should (almost surely) differ here


def test_length_is_respected():
    chain = MarkovChain(order=1).train(CORPUS)
    out = chain.generate(length=12, seed=0).split()
    assert len(out) == 12


def test_char_mode_only_emits_training_characters():
    text = "abracadabra"
    chain = MarkovChain(order=2, mode="char").train(text)
    out = chain.generate(length=40, seed=5)
    assert set(out) <= set(text)


def test_char_mode_soundness():
    # "abc" repeated is cyclic at the character level — no dead ends.
    chain = MarkovChain(order=3, mode="char").train("abc" * 12)
    out = list(chain.generate(length=30, seed=2))
    assert len(out) == 30
    assert _valid_transitions(chain, out)


def test_empty_model_raises():
    chain = MarkovChain(order=2)
    with pytest.raises(ValueError):
        chain.generate()


def test_corpus_too_small_builds_no_transitions():
    chain = MarkovChain(order=5).train("only four words here")
    assert chain.state_count == 0


def test_invalid_construction():
    with pytest.raises(ValueError):
        MarkovChain(order=0)
    with pytest.raises(ValueError):
        MarkovChain(mode="syllable")


def test_tokenize_modes():
    assert tokenize("a b  c", "word") == ["a", "b", "c"]
    assert tokenize("ab", "char") == ["a", "b"]
    with pytest.raises(ValueError):
        tokenize("x", "bogus")


def test_weighted_choice_respects_distribution():
    # State ('a',) -> {'a': 8, 'b': 1}, so the next token should be 'a' about
    # 8/9 ≈ 89% of the time. Assert it lands within a tolerance band, which is a
    # far stronger check than "a beats b".
    chain = MarkovChain(order=1).train("a a a a a a a a b")
    n = 2000
    a = sum(chain.generate(length=2, seed=s).split()[1] == "a" for s in range(n))
    ratio = a / n
    assert 0.84 < ratio < 0.94, ratio


# ---- Restart / seam behavior (the one place soundness does not hold) --------

def test_restart_reaches_full_length_on_acyclic_corpus():
    # A linear corpus dead-ends at its final state; reaching a length longer
    # than the corpus proves the restart mechanism fired.
    chain = MarkovChain(order=2).train("a b c d e f g")
    out = chain.generate(length=40, seed=1).split()
    assert len(out) == 40


def test_restart_can_introduce_an_unlearned_seam():
    # Documents the deliberate trade-off: on an acyclic corpus the spliced
    # restart produces at least one transition the model never learned.
    chain = MarkovChain(order=2).train("a b c d e")
    out = chain.generate(length=30, seed=1).split()
    has_seam = any(
        out[i + 2] not in chain.transitions.get(tuple(out[i:i + 2]), {})
        for i in range(len(out) - 2)
    )
    assert has_seam
