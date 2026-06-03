"""Tests for the reggie regex engine. Run: python -m pytest reggie/

Three kinds of checks:

  * unit tests pinning down each syntactic feature and its edge cases;
  * capture-group semantics, compared explicitly against Python's `re`;
  * a differential fuzz test that throws thousands of random pattern/text pairs
    at both reggie and `re` and asserts they agree on what matches and where —
    the strongest evidence that the engine is actually correct;
  * a performance guard proving the headline property: reggie does *not*
    catastrophically backtrack on patterns that bring `re` to its knees.
"""

import random
import re
import time

import pytest

import reggie
from .regex import Match, RegexError, _run


# --------------------------------------------------------------------------
# Literals, wildcards, anchors
# --------------------------------------------------------------------------

def test_plain_literal():
    assert reggie.search("cat", "the cat sat").span() == (4, 7)
    assert reggie.search("dog", "the cat sat") is None


def test_dot_matches_any_but_newline():
    assert reggie.fullmatch("a.c", "axc") is not None
    assert reggie.fullmatch("a.c", "a\nc") is None


def test_anchors():
    assert reggie.search("^cat", "cat sat") is not None
    assert reggie.search("^cat", "the cat") is None
    assert reggie.search("sat$", "the cat sat") is not None
    assert reggie.search("cat$", "cat sat") is None


def test_fullmatch_requires_whole_string():
    assert reggie.fullmatch("a+", "aaa") is not None
    assert reggie.fullmatch("a+", "aaab") is None


def test_fullmatch_explores_non_greedy_branch_to_reach_end():
    # The greedy-preferred branch `a` matches at the start, but only `ab` spans
    # the whole string — fullmatch must find it (cf. re.fullmatch).
    assert reggie.fullmatch("a|ab", "ab").span() == (0, 2)
    assert reggie.fullmatch("a|ab|abc", "abc").span() == (0, 3)
    m = reggie.fullmatch("(a|ab)(c|bcd)", "abcd")
    assert m.groups() == ("a", "bcd")


def test_match_is_anchored_at_start_only():
    assert reggie.match("a+", "aaab").span() == (0, 3)
    assert reggie.match("a+", "baaa") is None


# --------------------------------------------------------------------------
# Quantifiers (greedy + lazy)
# --------------------------------------------------------------------------

def test_star_plus_question():
    assert reggie.fullmatch("ab*c", "ac") is not None
    assert reggie.fullmatch("ab*c", "abbbc") is not None
    assert reggie.fullmatch("ab+c", "ac") is None
    assert reggie.fullmatch("ab?c", "abc") is not None
    assert reggie.fullmatch("ab?c", "abbc") is None


def test_greedy_vs_lazy():
    assert reggie.search("a.*b", "axbxb").span() == (0, 5)   # greedy: to last b
    assert reggie.search("a.*?b", "axbxb").span() == (0, 3)  # lazy: to first b


def test_bounded_repetition():
    assert reggie.fullmatch("a{3}", "aaa") is not None
    assert reggie.fullmatch("a{3}", "aa") is None
    assert reggie.search("a{2,4}", "aaaaa").span() == (0, 4)
    assert reggie.search("a{2,}", "aaaaa").span() == (0, 5)
    assert reggie.search("a{2,4}?", "aaaaa").span() == (0, 2)


def test_brace_that_is_not_a_quantifier_is_literal():
    # `{` not followed by a valid count is an ordinary character.
    assert reggie.fullmatch("a{b}", "a{b}") is not None
    assert reggie.fullmatch(r"x\{2\}", "x{2}") is not None


# --------------------------------------------------------------------------
# Alternation and grouping
# --------------------------------------------------------------------------

def test_alternation():
    assert reggie.fullmatch("cat|dog|bird", "dog") is not None
    assert reggie.fullmatch("cat|dog|bird", "fish") is None


def test_empty_alternative():
    assert reggie.fullmatch("a|", "") is not None
    assert reggie.fullmatch("(ab|)c", "c") is not None


def test_grouping_with_quantifier():
    assert reggie.fullmatch("(ab)+", "ababab") is not None
    assert reggie.fullmatch("(ab)+", "aba") is None


def test_non_capturing_group():
    m = reggie.search("(?:ab)+(c)", "ababc")
    assert m.groups() == ("c",)


# --------------------------------------------------------------------------
# Character classes
# --------------------------------------------------------------------------

def test_char_class_basics():
    assert reggie.fullmatch("[abc]+", "cabba") is not None      # all in class
    assert reggie.fullmatch("[abc]+", "cabbage") is None        # 'g','e' excluded
    assert reggie.fullmatch("[a-z]+", "hello") is not None
    assert reggie.fullmatch("[A-Za-z0-9_]+", "Hello_42") is not None


def test_negated_class():
    assert reggie.search("[^0-9]+", "abc123").span() == (0, 3)
    assert reggie.fullmatch("[^x]", "x") is None


def test_class_edge_literals():
    # Leading ']' and a trailing '-' are literals, not syntax.
    assert reggie.fullmatch("[]]", "]") is not None
    assert reggie.fullmatch("[a-]+", "a-a-") is not None


def test_shorthands():
    assert reggie.fullmatch(r"\d+", "12345") is not None
    assert reggie.fullmatch(r"\d+", "12a45") is None
    assert reggie.fullmatch(r"\w+", "ab_12") is not None
    assert reggie.search(r"\s", "a b").span() == (1, 2)
    assert reggie.fullmatch(r"\D+", "abc") is not None
    assert reggie.fullmatch(r"[\d.]+", "3.14") is not None  # shorthand in class


# --------------------------------------------------------------------------
# Escapes
# --------------------------------------------------------------------------

def test_escaped_metacharacters():
    assert reggie.fullmatch(r"a\.b", "a.b") is not None
    assert reggie.fullmatch(r"a\.b", "axb") is None
    assert reggie.fullmatch(r"\(\)", "()") is not None
    assert reggie.fullmatch(r"a\\b", "a\\b") is not None


def test_escaped_whitespace():
    assert reggie.fullmatch(r"a\tb", "a\tb") is not None
    assert reggie.fullmatch(r"a\nb", "a\nb") is not None


# --------------------------------------------------------------------------
# Capture groups (compared against re)
# --------------------------------------------------------------------------

@pytest.mark.parametrize("pat,text", [
    ("(a*)(b*)", "aaabb"),
    ("(ab|a)(b)?", "ab"),
    ("(\\d+)-(\\d+)", "12-345"),
    ("(?:x)(y)(z)", "xyz"),
    ("(a)(b)?(c)", "ac"),
    ("((a)(b))", "ab"),
    ("(foo)|(bar)", "bar"),
])
def test_capture_groups_match_re(pat, text):
    mine = reggie.search(pat, text)
    theirs = re.search(pat, text)
    assert (mine is None) == (theirs is None)
    if mine is not None:
        assert mine.span() == theirs.span()
        assert mine.groups() == theirs.groups()


def test_group_accessors():
    m = reggie.search(r"(\w+)@(\w+)", "send to bob@server now")
    assert m.group(0) == "bob@server"
    assert m.group(1) == "bob"
    assert m.group(2) == "server"
    assert m.span(1) == (8, 11)
    assert m.start(2) == 12 and m.end(2) == 18
    with pytest.raises(IndexError):
        m.group(3)


def test_nonparticipating_group_is_none():
    m = reggie.search("(a)|(b)", "b")
    assert m.group(1) is None
    assert m.group(2) == "b"
    assert m.span(1) == (-1, -1)


# --------------------------------------------------------------------------
# finditer / findall
# --------------------------------------------------------------------------

def test_findall():
    assert reggie.findall(r"\d+", "a1bb22ccc333") == ["1", "22", "333"]


def test_finditer_non_overlapping():
    spans = [m.span() for m in reggie.compile("aa").finditer("aaaa")]
    assert spans == [(0, 2), (2, 4)]


def test_finditer_zero_width_terminates():
    # An all-optional pattern matches empty everywhere but must still terminate.
    out = reggie.findall("a*", "aba")
    assert out == ["a", "", "a", ""]
    assert out == re.findall("a*", "aba")


# --------------------------------------------------------------------------
# Errors
# --------------------------------------------------------------------------

@pytest.mark.parametrize("pat", [
    "(unclosed",
    "a)",
    "[unterminated",
    "[]",            # empty class
    "*nothing",
    "a{3,2}",        # range out of order
    "[z-a]",         # bad range
    "\\",            # trailing backslash
    "(?P<name>x)",   # unsupported group syntax
])
def test_bad_patterns_raise(pat):
    with pytest.raises(RegexError):
        reggie.compile(pat)


# --------------------------------------------------------------------------
# Differential fuzzing against re
# --------------------------------------------------------------------------

def _random_pattern(rng: random.Random) -> str:
    """Build a random pattern from a subset of syntax where reggie and `re`
    are guaranteed to agree on leftmost-greedy semantics."""
    atoms = ["a", "b", "c", ".", "[ab]", "[^ab]", r"\d", r"\w",
             "(a)", "(ab)", "(a|b)", "(?:ab)"]
    quants = ["", "", "*", "+", "?", "*?", "+?", "??", "{2}", "{1,3}", "{2,}"]
    parts = []
    for _ in range(rng.randint(1, 5)):
        atom = rng.choice(atoms)
        parts.append(atom + rng.choice(quants))
    pat = "".join(parts)
    if rng.random() < 0.3:
        pat = pat + "|" + "".join(
            rng.choice(atoms) + rng.choice(quants) for _ in range(rng.randint(1, 3))
        )
    if rng.random() < 0.2:
        pat = "^" + pat
    if rng.random() < 0.2:
        pat = pat + "$"
    return pat


def _random_text(rng: random.Random) -> str:
    alphabet = "abc012 "
    return "".join(rng.choice(alphabet) for _ in range(rng.randint(0, 8)))


def test_differential_against_re():
    rng = random.Random(20240601)
    checked = 0
    for _ in range(4000):
        pat = _random_pattern(rng)
        try:
            mine = reggie.compile(pat)
            theirs = re.compile(pat)
        except (RegexError, re.error):
            continue
        text = _random_text(rng)
        # Compare an anchored match at *every* offset. This exercises the
        # matcher directly and is free of any iteration policy: `re`'s
        # `pattern.match(text, pos)` and reggie running from the same `pos` must
        # agree on whether there's a match and on its full span (group 0).
        for pos in range(len(text) + 1):
            saved = _run(mine.prog, text, pos)
            a = Match(text, saved, mine.ngroups) if saved is not None else None
            b = theirs.match(text, pos)
            assert (a is None) == (b is None), (pat, text, pos)
            if a is not None:
                assert a.span() == b.span(), (pat, text, pos, a.span(), b.span())
        # fullmatch has different winner-selection than match (the end anchor
        # can make a lower-priority branch win), so cross-check it directly.
        fa = mine.fullmatch(text)
        fb = theirs.fullmatch(text)
        assert (fa is None) == (fb is None), (pat, text, "fullmatch")
        if fa is not None:
            assert fa.span() == fb.span(), (pat, text, "fullmatch", fa.span(), fb.span())
        # Unanchored search: span and capture groups must match re exactly.
        sa = mine.search(text)
        sb = theirs.search(text)
        assert (sa is None) == (sb is None), (pat, text, "search")
        if sa is not None:
            assert sa.span() == sb.span(), (pat, text, "search", sa.span(), sb.span())
            assert sa.groups() == sb.groups(), (pat, text, "search groups")
        # The full sequence of finditer spans, *including zero-width matches*,
        # must match re's — this pins down the empty-match stepping rule.
        assert [m.span() for m in mine.finditer(text)] == \
               [m.span() for m in theirs.finditer(text)], (pat, text, "finditer")
        checked += 1
    assert checked > 2000   # make sure the generator actually exercised things


# --------------------------------------------------------------------------
# The headline property: linear time, no catastrophic backtracking
# --------------------------------------------------------------------------

def test_no_catastrophic_backtracking():
    # `(a*)*b` (or `(a+)+b`) against many 'a's and no 'b' is the classic
    # exponential blow-up for backtracking engines. The Pike VM stays linear.
    pat = reggie.compile("(a+)+b")
    text = "a" * 40        # `re` on this can take effectively forever
    start = time.perf_counter()
    assert pat.search(text) is None
    elapsed = time.perf_counter() - start
    assert elapsed < 1.0, f"matching took {elapsed:.2f}s — backtracking?"


def test_search_scales_linearly_with_text():
    # A non-matching pattern is the worst case for unanchored search: a naive
    # restart-at-every-offset search would be O(n^2). The implicit-prefix VM
    # search is a single linear pass, so doubling the text ~doubles the time.
    pat = reggie.compile("z")

    def timed(n: int) -> float:
        text = "a" * n
        start = time.perf_counter()
        pat.search(text)
        return time.perf_counter() - start

    base = timed(4000)
    for n in (8000, 16000):
        base = timed(2000)  # warm reference each step to dampen timer noise
    t1 = min(timed(4000) for _ in range(3)) + 1e-6
    t2 = min(timed(8000) for _ in range(3))
    # Linear would be ~2x; quadratic would be ~4x. Assert well under quadratic.
    assert t2 < t1 * 3.0, f"search looks super-linear: {t1:.4f}s -> {t2:.4f}s"


def test_huge_repetition_counts_are_rejected_fast():
    # Every way of asking for an enormous expansion must raise cleanly rather
    # than hang: a giant minimum, a giant maximum, and the product of nested
    # repeats (which no single per-node limit would catch).
    start = time.perf_counter()
    for pat in ("a{2000000,}", "a{0,2000000}", "a{50000,50000}{50000,50000}"):
        with pytest.raises(RegexError):
            reggie.compile(pat)
    # The point is that it doesn't *hang* (the un-capped versions ran for many
    # seconds / effectively forever); a generous budget still proves that.
    assert time.perf_counter() - start < 2.0
    # A merely large-but-reasonable pattern still compiles and works.
    assert reggie.fullmatch("a{500}", "a" * 500) is not None
