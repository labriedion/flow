"""Tests for the cellular-automata engine. Run: python -m pytest cellular/

We lean on the fact that several famous rules have exact algebraic descriptions,
which lets us check the engine against ground truth rather than against itself:

  * Rule 90  is  next = left XOR right
  * Rule 30  is  next = left XOR (centre OR right)
  * Rule 90 from a single seed (with a void boundary) is Pascal's triangle mod 2
    — the Sierpinski gasket — so the lit cells must match binomial coefficients.
"""

import random

import pytest

from .automaton import Automaton, random_row, rule_table, single_cell
from .render import to_half_blocks, to_svg, to_text


# --------------------------------------------------------------------------
# Rule tables
# --------------------------------------------------------------------------

def test_rule_table_endpoints():
    assert rule_table(0) == (0,) * 8
    assert rule_table(255) == (1,) * 8


def test_rule_table_is_the_bits_of_the_number():
    # Rule 30 = 0b00011110; bit n is the output for neighbourhood n.
    assert rule_table(30) == (0, 1, 1, 1, 1, 0, 0, 0)
    # Reconstruct the rule number from its table to confirm the bit order.
    for rule in (0, 1, 30, 90, 110, 184, 255):
        table = rule_table(rule)
        assert sum(bit << n for n, bit in enumerate(table)) == rule


@pytest.mark.parametrize("bad", [-1, 256, 1000, 2.5, "30"])
def test_rule_table_rejects_bad_input(bad):
    with pytest.raises(ValueError):
        rule_table(bad)


# --------------------------------------------------------------------------
# step(): check against closed-form rules
# --------------------------------------------------------------------------

def _brute(rule_fn, row, boundary="zero"):
    """Reference next-row using a plain neighbour function, for cross-checking."""
    n = len(row)
    edge = 0 if boundary == "zero" else 1
    out = []
    for i in range(n):
        left = row[i - 1] if i > 0 else (row[-1] if boundary == "wrap" else edge)
        right = row[i + 1] if i < n - 1 else (row[0] if boundary == "wrap" else edge)
        out.append(rule_fn(left, row[i], right))
    return out


def test_rule90_is_xor_of_neighbours():
    rng = random.Random(1)
    auto = Automaton(90, boundary="zero")
    for _ in range(50):
        row = [rng.randint(0, 1) for _ in range(17)]
        assert auto.step(row) == _brute(lambda l, c, r: l ^ r, row)


def test_rule30_is_left_xor_center_or_right():
    rng = random.Random(2)
    auto = Automaton(30, boundary="zero")
    for _ in range(50):
        row = [rng.randint(0, 1) for _ in range(17)]
        assert auto.step(row) == _brute(lambda l, c, r: l ^ (c | r), row)


def test_rule90_single_seed_is_pascal_mod_2():
    # From one lit centre cell on an empty background, Rule 90 lights cell
    # (gen t, offset k from centre, same parity as t) iff C(t, (t+k)/2) is odd.
    width = 81
    gens = 30
    auto = Automaton(90, boundary="zero")
    rows = auto.evolve(single_cell(width), gens)
    centre = width // 2
    from math import comb
    for t in range(gens + 1):
        for x in range(width):
            k = x - centre
            if (t + k) % 2 != 0 or abs(k) > t:
                expected = 0
            else:
                expected = comb(t, (t + k) // 2) & 1
            assert rows[t][x] == expected, (t, x)


def test_rule0_and_rule255():
    assert Automaton(0).step([1, 0, 1, 1]) == [0, 0, 0, 0]
    assert Automaton(255).step([0, 0, 0, 0]) == [1, 1, 1, 1]


# --------------------------------------------------------------------------
# Boundaries
# --------------------------------------------------------------------------

def test_wrap_boundary_sees_the_far_edge():
    # Rule 90 (left XOR right). A single lit cell at the left edge: with wrap,
    # its left neighbour is the (dead) right edge, so the new lit cells are the
    # two cells either side, including the wrapped-around far end.
    auto = Automaton(90, boundary="wrap")
    nxt = auto.step([1, 0, 0, 0])
    assert nxt == [0, 1, 0, 1]   # neighbours of index 0 are index 1 and index 3


def test_zero_vs_one_boundary_differ_at_edges():
    z = Automaton(90, boundary="zero").step([0, 0, 0])
    o = Automaton(90, boundary="one").step([0, 0, 0])
    assert z == [0, 0, 0]
    assert o == [1, 0, 1]        # the off-edge 1s light the two edge cells


def test_bad_boundary_rejected():
    with pytest.raises(ValueError):
        Automaton(30, boundary="reflect")


# --------------------------------------------------------------------------
# evolve()
# --------------------------------------------------------------------------

def test_evolve_row_count_and_first_row():
    auto = Automaton(110)
    start = single_cell(11)
    rows = auto.evolve(start, 7)
    assert len(rows) == 8            # generations + 1
    assert rows[0] == start
    assert rows[0] is not start      # the start row is copied, not aliased
    assert all(len(r) == 11 for r in rows)


def test_evolve_zero_generations():
    rows = Automaton(30).evolve([1, 0, 1], 0)
    assert rows == [[1, 0, 1]]


def test_evolve_rejects_negative():
    with pytest.raises(ValueError):
        Automaton(30).evolve([1], -1)


# --------------------------------------------------------------------------
# Seeds
# --------------------------------------------------------------------------

def test_single_cell_lights_exactly_the_middle():
    row = single_cell(7)
    assert row == [0, 0, 0, 1, 0, 0, 0]
    assert sum(row) == 1


def test_random_row_is_reproducible_and_sized():
    a = random_row(50, seed=99)
    b = random_row(50, seed=99)
    c = random_row(50, seed=100)
    assert a == b
    assert a != c
    assert len(a) == 50 and set(a) <= {0, 1}


def test_random_density_extremes():
    assert random_row(40, seed=1, density=0.0) == [0] * 40
    assert random_row(40, seed=1, density=1.0) == [1] * 40


@pytest.mark.parametrize("bad_width", [0, -3])
def test_seeds_reject_bad_width(bad_width):
    with pytest.raises(ValueError):
        single_cell(bad_width)
    with pytest.raises(ValueError):
        random_row(bad_width)


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def test_to_text_maps_cells_to_glyphs():
    out = to_text([[1, 0], [0, 1]], on="#", off=".")
    assert out == "#.\n.#"


def test_half_blocks_pack_two_rows_per_line():
    # top row [1,0,1,0], bottom [0,0,1,1]  ->  ▀ space █ ▄
    out = to_half_blocks([[1, 0, 1, 0], [0, 0, 1, 1]])
    assert out == "▀ █▄"
    # An odd number of rows pads the missing bottom row with dead cells.
    out2 = to_half_blocks([[1, 1]])
    assert out2 == "▀▀"


def test_half_blocks_empty():
    assert to_half_blocks([]) == ""


def test_svg_dimensions_and_content():
    rows = [[1, 0], [0, 1]]
    svg = to_svg(rows, cell=10)
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert 'width="20"' in svg and 'height="20"' in svg
    assert "<path" in svg                 # lit cells were drawn
    # An all-dead grid draws a background but no cell path.
    blank = to_svg([[0, 0], [0, 0]], cell=10)
    assert "<path" not in blank


def test_svg_run_renders_consistent_size():
    rows = Automaton(90, boundary="zero").evolve(single_cell(31), 20)
    svg = to_svg(rows, cell=3)
    assert f'width="{31 * 3}"' in svg
    assert f'height="{21 * 3}"' in svg
