"""A small arithmetic expression evaluator: tokenizer, parser, evaluator.

Supports `+ - * / % ^`, parentheses, unary minus/plus, named constants
(`pi`, `e`, `tau`), a library of functions (`sqrt`, `sin`, `min`, ...), and
variable assignment (`x = 3 * 4`). Operator precedence and associativity match
ordinary math / Python: `^` is right-associative and binds tighter than a
leading unary minus, so `-2^2 == -4`.

Parsing is precedence climbing — compact, and easy to reason about. Only the
standard library is used.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


class CalcError(Exception):
    """Raised for any tokenizing, parsing, or evaluation error. The message is
    safe to show directly to a user."""


# --------------------------------------------------------------------------
# Tokenizer
# --------------------------------------------------------------------------

@dataclass
class Token:
    kind: str   # 'num', 'name', 'op', 'lparen', 'rparen', 'comma', 'assign'
    value: object
    pos: int


_OPS = set("+-*/%^")


def tokenize(text: str) -> list[Token]:
    tokens: list[Token] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        if c.isdigit() or (c == "." and i + 1 < n and text[i + 1].isdigit()):
            start = i
            i = _scan_number(text, i)
            try:
                value = float(text[start:i])
            except ValueError:
                raise CalcError(f"bad number {text[start:i]!r} at position {start}")
            tokens.append(Token("num", value, start))
            continue
        if c.isalpha() or c == "_":
            start = i
            while i < n and (text[i].isalnum() or text[i] == "_"):
                i += 1
            tokens.append(Token("name", text[start:i], start))
            continue
        if c in _OPS:
            tokens.append(Token("op", c, i)); i += 1; continue
        if c == "(":
            tokens.append(Token("lparen", c, i)); i += 1; continue
        if c == ")":
            tokens.append(Token("rparen", c, i)); i += 1; continue
        if c == ",":
            tokens.append(Token("comma", c, i)); i += 1; continue
        if c == "=":
            tokens.append(Token("assign", c, i)); i += 1; continue
        raise CalcError(f"unexpected character {c!r} at position {i}")
    return tokens


def _scan_number(text: str, i: int) -> int:
    """Advance past a numeric literal including an optional exponent."""
    n = len(text)
    while i < n and (text[i].isdigit() or text[i] == "."):
        i += 1
    # Optional scientific exponent, e.g. 1e-3 or 2.5E10.
    if i < n and text[i] in "eE":
        j = i + 1
        if j < n and text[j] in "+-":
            j += 1
        if j < n and text[j].isdigit():
            i = j
            while i < n and text[i].isdigit():
                i += 1
    return i


# --------------------------------------------------------------------------
# AST
# --------------------------------------------------------------------------

@dataclass
class Num:
    value: float

@dataclass
class Var:
    name: str

@dataclass
class Unary:
    op: str
    operand: object

@dataclass
class Binary:
    op: str
    left: object
    right: object

@dataclass
class Call:
    name: str
    args: list

@dataclass
class Assign:
    name: str
    expr: object


# Binary operator precedence and associativity.
_PREC = {"+": 1, "-": 1, "*": 2, "/": 2, "%": 2, "^": 3}
_RIGHT_ASSOC = {"^"}
_UNARY_PREC = 3  # so -2^2 parses as -(2^2)


# --------------------------------------------------------------------------
# Parser (precedence climbing)
# --------------------------------------------------------------------------

class Parser:
    def __init__(self, tokens: list[Token]):
        self.tokens = tokens
        self.i = 0

    def peek(self) -> Token | None:
        return self.tokens[self.i] if self.i < len(self.tokens) else None

    def next(self) -> Token:
        tok = self.tokens[self.i]
        self.i += 1
        return tok

    def parse(self):
        """Parse a full input: either `name = expr` or a bare expression."""
        if not self.tokens:
            raise CalcError("empty expression")
        # Assignment if it's `name = ...`.
        if (len(self.tokens) >= 2 and self.tokens[0].kind == "name"
                and self.tokens[1].kind == "assign"):
            name = self.next().value
            self.next()  # '='
            expr = self.parse_expr(0)
            self._expect_end()
            return Assign(name, expr)
        node = self.parse_expr(0)
        self._expect_end()
        return node

    def _expect_end(self):
        tok = self.peek()
        if tok is not None:
            raise CalcError(f"unexpected {tok.value!r} at position {tok.pos}")

    def parse_expr(self, min_prec: int):
        left = self.parse_atom()
        while True:
            tok = self.peek()
            if tok is None or tok.kind != "op" or _PREC[tok.value] < min_prec:
                break
            op = self.next().value
            prec = _PREC[op]
            next_min = prec if op in _RIGHT_ASSOC else prec + 1
            right = self.parse_expr(next_min)
            left = Binary(op, left, right)
        return left

    def parse_atom(self):
        tok = self.peek()
        if tok is None:
            raise CalcError("unexpected end of expression")

        if tok.kind == "op" and tok.value in ("+", "-"):
            self.next()
            operand = self.parse_expr(_UNARY_PREC)
            return Unary(tok.value, operand)

        if tok.kind == "num":
            self.next()
            return Num(tok.value)

        if tok.kind == "name":
            self.next()
            # Function call if followed by '('.
            if self.peek() is not None and self.peek().kind == "lparen":
                self.next()  # '('
                args = self.parse_args()
                return Call(tok.value, args)
            return Var(tok.value)

        if tok.kind == "lparen":
            self.next()
            node = self.parse_expr(0)
            close = self.peek()
            if close is None or close.kind != "rparen":
                raise CalcError("missing closing parenthesis")
            self.next()
            return node

        raise CalcError(f"unexpected {tok.value!r} at position {tok.pos}")

    def parse_args(self) -> list:
        args = []
        if self.peek() is not None and self.peek().kind == "rparen":
            self.next()
            return args
        while True:
            args.append(self.parse_expr(0))
            tok = self.peek()
            if tok is None:
                raise CalcError("missing closing parenthesis in call")
            if tok.kind == "comma":
                self.next()
                continue
            if tok.kind == "rparen":
                self.next()
                return args
            raise CalcError(f"expected ',' or ')' at position {tok.pos}")


# --------------------------------------------------------------------------
# Evaluator
# --------------------------------------------------------------------------

CONSTANTS = {"pi": math.pi, "e": math.e, "tau": math.tau}

# name -> (callable, arity or None for variadic)
FUNCTIONS = {
    "sqrt": (math.sqrt, 1), "abs": (abs, 1), "exp": (math.exp, 1),
    "ln": (math.log, 1), "log10": (math.log10, 1), "log2": (math.log2, 1),
    "sin": (math.sin, 1), "cos": (math.cos, 1), "tan": (math.tan, 1),
    "asin": (math.asin, 1), "acos": (math.acos, 1), "atan": (math.atan, 1),
    "floor": (lambda x: float(math.floor(x)), 1),
    "ceil": (lambda x: float(math.ceil(x)), 1),
    "round": (lambda x: float(round(x)), 1),
    "log": (math.log, 2),          # log(x, base)
    "pow": (math.pow, 2),
    "min": (min, None), "max": (max, None),
}


class Calculator:
    """Holds variable state across evaluations (so a REPL can remember `x`)."""

    def __init__(self):
        self.vars: dict[str, float] = {}

    def evaluate(self, text: str) -> float:
        """Parse and evaluate one line. Assignments store the value and return
        it. Raises CalcError on any problem."""
        ast = Parser(tokenize(text)).parse()
        if isinstance(ast, Assign):
            if ast.name in CONSTANTS or ast.name in FUNCTIONS:
                raise CalcError(f"cannot assign to reserved name {ast.name!r}")
            value = self._eval(ast.expr)
            self.vars[ast.name] = value
            return value
        return self._eval(ast)

    def _eval(self, node) -> float:
        if isinstance(node, Num):
            return node.value
        if isinstance(node, Var):
            if node.name in self.vars:
                return self.vars[node.name]
            if node.name in CONSTANTS:
                return CONSTANTS[node.name]
            raise CalcError(f"unknown name {node.name!r}")
        if isinstance(node, Unary):
            v = self._eval(node.operand)
            return -v if node.op == "-" else +v
        if isinstance(node, Binary):
            return self._eval_binary(node)
        if isinstance(node, Call):
            return self._eval_call(node)
        raise CalcError("invalid expression")  # pragma: no cover

    def _eval_binary(self, node: Binary) -> float:
        a = self._eval(node.left)
        b = self._eval(node.right)
        op = node.op
        if op == "+":
            return a + b
        if op == "-":
            return a - b
        if op == "*":
            return a * b
        if op == "/":
            if b == 0:
                raise CalcError("division by zero")
            return a / b
        if op == "%":
            if b == 0:
                raise CalcError("modulo by zero")
            return math.fmod(a, b)
        if op == "^":
            try:
                return float(a ** b)
            except (ValueError, OverflowError) as exc:
                raise CalcError(f"cannot evaluate power: {exc}")
        raise CalcError(f"unknown operator {op!r}")  # pragma: no cover

    def _eval_call(self, node: Call) -> float:
        entry = FUNCTIONS.get(node.name)
        if entry is None:
            raise CalcError(f"unknown function {node.name!r}")
        func, arity = entry
        args = [self._eval(a) for a in node.args]
        if arity is None:
            if not args:
                raise CalcError(f"{node.name}() needs at least one argument")
        elif len(args) != arity:
            raise CalcError(
                f"{node.name}() takes {arity} argument(s), got {len(args)}"
            )
        try:
            return float(func(*args))
        except CalcError:
            raise
        except (ValueError, ZeroDivisionError, OverflowError) as exc:
            raise CalcError(f"{node.name}(): {exc}")


def evaluate(text: str) -> float:
    """Convenience one-shot evaluation with no persistent variables."""
    return Calculator().evaluate(text)


def format_result(value: float) -> str:
    """Render a result cleanly: whole numbers without a trailing .0, otherwise
    a trimmed float."""
    if value != value or value in (float("inf"), float("-inf")):
        return str(value)
    if value == int(value) and abs(value) < 1e16:
        return str(int(value))
    return f"{value:.10g}"
