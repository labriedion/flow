# calc

A tiny, dependency-free **arithmetic expression evaluator** — a complete little
language pipeline: tokenizer → parser → evaluator. Use it one-shot, as an
interactive REPL, or as a library. Pure Python standard library, with a real
test suite.

```
calc/
  calculator.py   # tokenizer, precedence-climbing parser, evaluator
  cli.py          # one-shot evaluation + interactive REPL
  test_calc.py    # pytest suite (precedence, associativity, functions, errors)
```

## Run it

```bash
python -m calc.cli "2 + 3 * 4"      # -> 14
python -m calc.cli "2^3^2"          # -> 512   (right-associative power)
python -m calc.cli "-2^2"           # -> -4    (unary minus binds looser than ^)
python -m calc.cli "sqrt(2)^2"      # -> 2
python -m calc.cli                  # start the REPL
```

In the REPL you can define variables and reuse them:

```
» x = 6
6
» x * 7
42
» :vars
  x = 6
```

## What it supports

- **Operators** `+ - * / % ^`, parentheses, unary `+`/`-`. Precedence and
  associativity match math/Python: `^` is right-associative and binds tighter
  than a leading unary minus, so `-2^2 == -4` and `2^3^2 == 512`.
- **Constants** `pi`, `e`, `tau`.
- **Functions** `sqrt abs exp ln log10 log2 sin cos tan asin acos atan floor
  ceil round`, two-arg `log(x, base)` and `pow(x, y)`, and variadic `min`/`max`.
- **Variables** via `x = expr`, persisted across a `Calculator` session.
- **Scientific notation** (`1e-3`) and leading-dot floats (`.5`).
- Clean, user-safe errors (`CalcError`) for every failure — parse errors with a
  position, division/modulo by zero, unknown names, wrong arity, math domain
  errors.

## Use it as a library

```python
from calc import Calculator, evaluate

evaluate("2 + 3 * 4")          # 14.0

calc = Calculator()
calc.evaluate("r = 5")
calc.evaluate("pi * r ^ 2")    # 78.539...
```

## Test it

```bash
python -m pytest calc/ -q
```

The suite (50 cases) pins down the things that are easy to get subtly wrong:
operator precedence and associativity (especially right-associative `^` and how
unary minus interacts with it), function arity, variable state and session
isolation, reserved-name protection, result formatting, and that every bad
input raises a clean `CalcError` rather than a raw traceback.
