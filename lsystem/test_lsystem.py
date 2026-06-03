"""Tests for the L-system engine. Run: python -m pytest lsystem/ -q

These lean on ground truth rather than on the implementation itself: famous
L-systems have known, checkable properties — Lindenmayer's algae grows by the
Fibonacci numbers, the Koch production multiplies the F-count by exactly five
each pass, a closed curve returns the turtle to where it began, and a single
forward step traces a segment whose bounding box we can name in advance.
"""

import math

import pytest

from .cli import main
from .grammar import LSystem
from .presets import PRESETS, get, make
from .render import to_path_string, to_svg
from .turtle import bounding_box, interpret


# --------------------------------------------------------------------------
# Grammar: deterministic rewriting
# --------------------------------------------------------------------------

def test_algae_lengths_are_fibonacci():
    # Lindenmayer's algae: A->AB, B->A. Generation lengths are the Fibonacci
    # numbers 1, 2, 3, 5, 8, 13, 21, ...
    algae = LSystem("A", {"A": "AB", "B": "A"})
    lengths = [len(algae.expand(n)) for n in range(8)]
    assert lengths == [1, 2, 3, 5, 8, 13, 21, 34]


def test_algae_exact_strings():
    algae = LSystem("A", {"A": "AB", "B": "A"})
    assert algae.expand(0) == "A"
    assert algae.expand(1) == "AB"
    assert algae.expand(2) == "ABA"
    assert algae.expand(3) == "ABAAB"
    assert algae.expand(4) == "ABAABABA"


def test_koch_production_exact_and_f_count():
    # Each F becomes F+F-F-F+F: five Fs per F, so the F-count is 5**n.
    koch = LSystem("F", {"F": "F+F-F-F+F"})
    assert koch.expand(0) == "F"
    assert koch.expand(1) == "F+F-F-F+F"
    assert koch.expand(2) == "F+F-F-F+F+F+F-F-F+F-F+F-F-F+F-F+F-F-F+F+F+F-F-F+F"
    for n in range(5):
        assert koch.expand(n).count("F") == 5 ** n


def test_constants_rewrite_to_themselves():
    # '+' and '-' have no rule, so they pass through unchanged.
    sys = LSystem("F+F", {"F": "FF"})
    assert sys.expand(1) == "FF+FF"


def test_expand_zero_is_axiom():
    assert LSystem("XYZ", {"X": "AAA"}).expand(0) == "XYZ"


def test_expand_rejects_negative():
    with pytest.raises(ValueError):
        LSystem("F", {"F": "FF"}).expand(-1)


def test_bad_rule_keys_and_values_rejected():
    with pytest.raises(ValueError):
        LSystem("F", {"FF": "F"})          # multi-char key
    with pytest.raises(ValueError):
        LSystem("F", {"F": []})            # empty stochastic options
    with pytest.raises(ValueError):
        LSystem("F", {"F": [("FF", -1.0)]})  # negative weight


# --------------------------------------------------------------------------
# Grammar: stochastic rules and determinism
# --------------------------------------------------------------------------

def test_stochastic_same_seed_is_identical():
    sys = LSystem("F", {"F": [("F+F", 1.0), ("F-F", 1.0), ("FF", 1.0)]})
    assert sys.is_stochastic
    a = sys.expand(6, seed=42)
    b = sys.expand(6, seed=42)
    assert a == b


def test_stochastic_different_seeds_usually_differ():
    sys = LSystem("F", {"F": [("F+F", 1.0), ("F-F", 1.0), ("FF", 1.0)]})
    outputs = {sys.expand(6, seed=s) for s in range(8)}
    # With this many independent draws the seeds should rarely all coincide.
    assert len(outputs) > 1


def test_deterministic_system_ignores_seed():
    sys = LSystem("F", {"F": "F+F"})
    assert not sys.is_stochastic
    assert sys.expand(4, seed=1) == sys.expand(4, seed=999)


def test_single_weight_stochastic_is_effectively_deterministic():
    sys = LSystem("F", {"F": [("FXF", 1.0)]})
    assert sys.expand(2, seed=0) == "FXFXFXF"


# --------------------------------------------------------------------------
# Turtle geometry
# --------------------------------------------------------------------------

def test_single_segment_bounding_box():
    # axiom F, step 10, angle 90 -> one segment along +x of length 10.
    segs = interpret("F", step=10, angle=90)
    assert len(segs) == 1
    assert bounding_box(segs) == (0.0, 0.0, 10.0, 0.0)
    (x0, y0), (x1, y1) = segs[0]
    assert (x0, y0) == (0.0, 0.0)
    assert math.isclose(x1, 10.0) and math.isclose(y1, 0.0, abs_tol=1e-9)


def test_right_angle_turn_box():
    # F+F at angle 90: forward, turn left, forward up. Box is 10x10.
    segs = interpret("F+F", step=10, angle=90)
    assert len(segs) == 2
    min_x, min_y, max_x, max_y = bounding_box(segs)
    assert math.isclose(min_x, 0.0)
    assert math.isclose(min_y, 0.0)
    assert math.isclose(max_x, 10.0)
    assert math.isclose(max_y, 10.0)


def test_f_lowercase_moves_without_drawing():
    # 'f' advances the turtle but draws nothing, so only the second F is a line.
    segs = interpret("fF", step=10, angle=90)
    assert len(segs) == 1
    (x0, y0), (x1, y1) = segs[0]
    assert math.isclose(x0, 10.0)        # started after the pen-up jump
    assert math.isclose(x1, 20.0)


def test_branch_stack_returns_to_pushed_state():
    # F[+F]F: the bracketed branch is drawn, then we pop back and continue
    # straight, so the final segment starts where the first ended.
    segs = interpret("F[+F]F", step=10, angle=90)
    assert len(segs) == 3
    first_end = segs[0][1]
    last_start = segs[2][0]
    assert math.isclose(last_start[0], first_end[0], abs_tol=1e-9)
    assert math.isclose(last_start[1], first_end[1], abs_tol=1e-9)


def test_unbalanced_pop_raises():
    with pytest.raises(ValueError):
        interpret("F]")


def test_square_closes_back_to_start():
    # Four forward+left turns at 90 degrees trace a closed square.
    segs = interpret("F+F+F+F", step=10, angle=90)
    end = segs[-1][1]
    assert math.isclose(end[0], 0.0, abs_tol=1e-9)
    assert math.isclose(end[1], 0.0, abs_tol=1e-9)


def test_snowflake_is_approximately_closed():
    # The Koch snowflake is a closed curve: the turtle returns near its start.
    preset = get("snowflake")
    expanded = preset.system().expand(3)
    segs = interpret(expanded, step=preset.step, angle=preset.angle)
    start = segs[0][0]
    end = segs[-1][1]
    assert math.isclose(start[0], end[0], abs_tol=1e-6)
    assert math.isclose(start[1], end[1], abs_tol=1e-6)


def test_segment_count_matches_drawing_symbol_count():
    # The number of segments equals the count of drawing symbols (F/G), with
    # lowercase f and the steering letters drawing nothing.
    preset = get("dragon")
    expanded = preset.system().expand(6)
    drawing = sum(expanded.count(c) for c in "FG")
    segs = interpret(expanded, step=preset.step, angle=preset.angle)
    assert len(segs) == drawing


def test_empty_bounding_box():
    assert bounding_box([]) == (0.0, 0.0, 0.0, 0.0)


# --------------------------------------------------------------------------
# Rendering
# --------------------------------------------------------------------------

def test_svg_basic_structure():
    svg = to_svg(interpret("F+F", step=10, angle=90))
    assert svg.startswith("<svg")
    assert svg.rstrip().endswith("</svg>")
    assert "<path" in svg
    assert "viewBox=" in svg


def test_svg_viewbox_fits_geometry_with_margin():
    # A single 10-long segment with a 5px margin -> width 20 (10 + 2*5),
    # height 10 (a flat segment, 0 tall, + 2*5).
    svg = to_svg(interpret("F", step=10, angle=90), margin=5.0)
    assert 'viewBox="0 0 20 10"' in svg
    assert 'width="20"' in svg and 'height="10"' in svg


def test_svg_empty_segments():
    svg = to_svg([])
    assert svg.startswith("<svg")
    assert "width=\"0\"" in svg


def test_path_string_joins_connected_segments():
    # Connected segments share endpoints, so we emit one M and trailing Ls.
    path = to_path_string([((0, 0), (10, 0)), ((10, 0), (10, 10))])
    assert path.count("M") == 1
    assert path.count("L") == 2


def test_path_string_breaks_on_gap():
    # A discontinuity starts a fresh subpath with a new M.
    path = to_path_string([((0, 0), (10, 0)), ((50, 50), (60, 50))])
    assert path.count("M") == 2


def test_gradient_svg_has_linear_gradient():
    svg = to_svg(interpret("F+F+F+F", step=10, angle=90), gradient=True)
    assert "linearGradient" in svg
    assert "url(#g)" in svg


# --------------------------------------------------------------------------
# Presets
# --------------------------------------------------------------------------

def test_required_presets_present():
    for name in ("koch", "snowflake", "sierpinski", "dragon",
                 "hilbert", "levy", "plant"):
        assert name in PRESETS


def test_every_preset_expands_and_draws():
    for name, preset in PRESETS.items():
        # Keep iterations modest so the test stays fast.
        n = min(preset.iterations, 4)
        expanded = preset.system().expand(n, seed=0)
        segs = interpret(expanded, step=preset.step, angle=preset.angle,
                         heading=preset.heading)
        # Every preset draws at least one segment by a few iterations
        # (algae has angle 0 and only steering letters, so allow zero there).
        if name != "algae":
            assert segs, name


def test_make_returns_lsystem():
    sys = make("dragon")
    assert isinstance(sys, LSystem)


def test_get_unknown_preset_lists_choices():
    with pytest.raises(ValueError) as exc:
        get("nope")
    assert "unknown preset" in str(exc.value)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def test_cli_writes_preset_svg(tmp_path, capsys):
    out = tmp_path / "koch.svg"
    rc = main(["--preset", "koch", "--iterations", "3", "-o", str(out)])
    assert rc == 0
    text = out.read_text()
    assert text.startswith("<svg") and "<path" in text


def test_cli_custom_system(tmp_path):
    out = tmp_path / "c.svg"
    rc = main(["--axiom", "F", "--rule", "F=F+F-F-F+F",
               "--angle", "90", "--iterations", "3", "-o", str(out)])
    assert rc == 0
    assert out.read_text().startswith("<svg")


def test_cli_list(capsys):
    rc = main(["--list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "plant" in out and "dragon" in out


def test_cli_stochastic_seed_reproducible(tmp_path):
    a = tmp_path / "a.svg"
    b = tmp_path / "b.svg"
    main(["--preset", "weed", "--iterations", "4", "--seed", "7", "-o", str(a)])
    main(["--preset", "weed", "--iterations", "4", "--seed", "7", "-o", str(b)])
    assert a.read_text() == b.read_text()


def test_cli_bad_rule_returns_2(capsys):
    rc = main(["--axiom", "F", "--rule", "no-equals"])
    assert rc == 2
    err = capsys.readouterr().err
    assert err.startswith("lsystem:")


def test_cli_preset_and_axiom_conflict(capsys):
    rc = main(["--preset", "koch", "--axiom", "F"])
    assert rc == 2
    assert capsys.readouterr().err.startswith("lsystem:")


def test_cli_nothing_to_draw(capsys):
    rc = main([])
    assert rc == 2
    assert capsys.readouterr().err.startswith("lsystem:")


def test_cli_unknown_preset_returns_2(capsys):
    rc = main(["--preset", "bogus"])
    assert rc == 2
    assert capsys.readouterr().err.startswith("lsystem:")
