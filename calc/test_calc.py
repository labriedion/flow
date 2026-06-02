"""Tests for the calculator. Run: python -m pytest calc/

These pin down the parts that are easy to get subtly wrong: operator precedence,
associativity (especially right-associative `^` and how unary minus interacts
with it), function arity, variable state, and clean error reporting.
"""

import math

import pytest

from .calculator import Calculator, CalcError, evaluate, format_result


@pytest.mark.parametrize("expr,expected", [
    ("1 + 2", 3),
    ("2 + 3 * 4", 14),            # precedence
    ("(2 + 3) * 4", 20),         # parentheses
    ("10 - 2 - 3", 5),           # left-assoc subtraction
    ("2 ^ 3 ^ 2", 512),          # right-assoc power: 2^(3^2)
    ("-2 ^ 2", -4),              # unary minus looser than ^
    ("2 ^ -2", 0.25),           # power with negative exponent
    ("7 % 3", 1),
    ("--3", 3),                  # double unary minus
    ("+-+-2", 2),
    ("3 * -2", -6),
    ("1 / 2", 0.5),
    ("1e3 + 1", 1001),          # scientific notation
    (".5 + .5", 1),             # leading-dot floats
])
def test_arithmetic_and_precedence(expr, expected):
    assert evaluate(expr) == pytest.approx(expected)


@pytest.mark.parametrize("expr,expected", [
    ("sqrt(16)", 4),
    ("sqrt(2) ^ 2", 2),
    ("abs(-5)", 5),
    ("max(1, 7, 3)", 7),
    ("min(4, -1, 2)", -1),
    ("pow(2, 10)", 1024),
    ("floor(3.7)", 3),
    ("ceil(3.2)", 4),
    ("log(8, 2)", 3),
])
def test_functions(expr, expected):
    assert evaluate(expr) == pytest.approx(expected)


def test_constants():
    assert evaluate("pi") == pytest.approx(math.pi)
    assert evaluate("2 * pi") == pytest.approx(2 * math.pi)
    assert evaluate("cos(0) + e") == pytest.approx(1 + math.e)


def test_variables_persist_in_a_session():
    calc = Calculator()
    assert calc.evaluate("x = 3 + 4") == 7
    assert calc.evaluate("x * 2") == 14
    assert calc.evaluate("y = x ^ 2") == 49
    assert calc.evaluate("x + y") == 56


def test_one_shot_evaluate_has_no_shared_state():
    assert evaluate("z = 5") == 5
    with pytest.raises(CalcError):
        evaluate("z")  # fresh evaluation: z is unknown


@pytest.mark.parametrize("bad", [
    "", "   ",          # empty
    "1 +",              # dangling operator
    "1 + + ",           # nothing after unary
    "(1 + 2",           # unmatched paren
    "1 + 2)",           # extra paren
    "3 4",              # two values, no operator
    "1 @ 2",            # bad char
    "2 +* 3",           # operator where a value is expected
])
def test_parse_errors(bad):
    with pytest.raises(CalcError):
        evaluate(bad)


@pytest.mark.parametrize("bad", [
    "1 / 0", "5 % 0",            # division / modulo by zero
    "unknownvar", "nope(2)",     # unknown name / function
    "sqrt(1, 2)", "max()",       # wrong arity / variadic with no args
    "sqrt(-1)",                  # math domain error surfaces as CalcError
    "(-8) ^ 0.5",               # fractional power of a negative -> complex
    "0 ^ -1",                   # zero to a negative power
])
def test_eval_errors(bad):
    with pytest.raises(CalcError):
        evaluate(bad)


def test_modulo_follows_python_sign_semantics():
    # Result takes the sign of the divisor, matching Python's % (not C fmod).
    assert evaluate("-7 % 3") == 2
    assert evaluate("7 % -3") == -2


def test_cannot_assign_to_reserved_names():
    calc = Calculator()
    with pytest.raises(CalcError):
        calc.evaluate("pi = 3")
    with pytest.raises(CalcError):
        calc.evaluate("sqrt = 1")


def test_error_messages_are_strings():
    try:
        evaluate("1/0")
    except CalcError as exc:
        assert "zero" in str(exc).lower()


@pytest.mark.parametrize("value,text", [
    (3.0, "3"),
    (-7.0, "-7"),
    (0.5, "0.5"),
    (2.5, "2.5"),
    (1000000.0, "1000000"),
])
def test_format_result(value, text):
    assert format_result(value) == text


def test_whitespace_is_ignored():
    assert evaluate("  2   *  (  3 + 4 ) ") == 14


# ---- CLI -----------------------------------------------------------------

def test_cli_one_shot(capsys):
    from .cli import main
    assert main(["2 + 3 * 4"]) == 0
    assert capsys.readouterr().out.strip() == "14"


def test_cli_leading_minus_expression(capsys):
    from .cli import main
    assert main(["-2^2"]) == 0          # must not be parsed as a flag
    assert capsys.readouterr().out.strip() == "-4"


def test_cli_reports_errors_with_nonzero_exit(capsys):
    from .cli import main
    assert main(["1 / 0"]) == 1
    assert "zero" in capsys.readouterr().err.lower()


def test_cli_complex_power_is_clean_error(capsys):
    # Regression: must surface as a CalcError message, not a raw traceback.
    from .cli import main
    assert main(["(-8)^0.5"]) == 1
    assert "complex" in capsys.readouterr().err.lower()
