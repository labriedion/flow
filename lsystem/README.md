# lsystem

**L-systems** (Lindenmayer systems) — rewrite a tiny string by parallel
production rules, then read the result as turtle graphics and draw it to SVG.
Pure Python standard library, with a test suite that checks the engine against
the *known* behaviour of famous systems rather than against itself.

Start with an **axiom** (a short string) and a set of **rules** saying how to
replace each symbol. On every iteration, every symbol is rewritten at once. A
seed blossoms into a long string; feed that string to a turtle — `F` draws
forward, `+`/`-` turn, `[`/`]` save and restore position — and out come Koch
curves, dragon curves, space-filling Hilbert curves, and convincing plants.

```
axiom  F
rule   F -> F+F-F-F+F        angle 90

  F           ->        F+F-F-F+F          ->     ... and so on, a square Koch curve
  one segment           a square bump on every segment
```

The classic is Lindenmayer's algae, `A->AB`, `B->A`: each generation's length
is a Fibonacci number (1, 2, 3, 5, 8, 13, ...). Some systems are **stochastic** —
a symbol maps to several productions with weights, one chosen at random — so a
`--seed` makes a different plant each time, reproducibly.

See [`examples/`](examples) for a [Koch snowflake](examples/koch_snowflake.svg),
the [Heighway dragon](examples/dragon.svg), a [Hilbert curve](examples/hilbert.svg),
the [Sierpinski gasket](examples/sierpinski.svg), a fractal [plant](examples/plant.svg),
and a stochastic [weed](examples/weed.svg).

## Run it

```bash
python -m lsystem.cli --preset plant --iterations 5 -o plant.svg
python -m lsystem.cli --preset dragon --gradient -o dragon.svg
python -m lsystem.cli --list                       # every built-in preset
# a custom system (repeat --rule for more symbols):
python -m lsystem.cli --axiom F --rule "F=F+F-F-F+F" --angle 90 \
    --iterations 4 -o koch.svg
python -m lsystem.cli --preset weed --seed 7 -o weed.svg   # stochastic
```

Pick a `--preset` or define your own with `--axiom` plus one or more
`--rule SYM=PRODUCTION`. Without `-o`, the SVG goes to stdout.

| flag | meaning |
| --- | --- |
| `--preset NAME` | use a built-in system (see `--list`) |
| `--axiom STR` `--rule SYM=PROD` | define a custom system (`--rule` repeatable) |
| `--angle` / `--step` | turn angle in degrees / forward distance |
| `--iterations` / `-n` | number of rewrite passes |
| `--heading` | initial direction (0 = +x, 90 = up) |
| `--seed` | RNG seed for stochastic presets (reproducible) |
| `--gradient` | colour the stroke along the draw order |
| `--stroke` `--stroke-width` `--margin` | style the line and canvas |
| `-o PATH` | write the SVG here (default: stdout) |

## Built-in presets

`algae` (Fibonacci), `koch`, `snowflake`, `sierpinski`, `dragon`, `hilbert`,
`levy`, `plant`, `bush`, and the stochastic `weed`.

## How it works

```
lsystem/
  grammar.py    # LSystem: axiom + rules, expand(n) by parallel rewriting
  turtle.py     # read a symbol string as turtle moves -> line segments + bbox
  render.py     # fit a viewBox to the segments and emit one compact SVG path
  presets.py    # the canonical built-in systems
  cli.py        # the command-line front end
```

`LSystem.expand(n)` rewrites the axiom `n` times. `interpret()` walks the
expanded string with a turtle, pushing and popping position/heading on `[` and
`]` to make branches, and returns a list of `((x0, y0), (x1, y1))` segments.
`to_svg()` fits the viewBox to their bounding box (plus a margin), flips y so
the picture is upright, and coalesces connected segments into a single `<path>`
so even a 4096-segment dragon stays compact.

## Use it as a library

```python
from lsystem import LSystem, interpret, to_svg, make

# a custom Koch curve
koch = LSystem("F", {"F": "F+F-F-F+F"})
segments = interpret(koch.expand(4), step=10, angle=90)
open("koch.svg", "w").write(to_svg(segments))

# or a built-in preset
dragon = make("dragon")
open("dragon.svg", "w").write(to_svg(interpret(dragon.expand(12), angle=90)))
```

## Test it

```bash
python -m pytest lsystem/ -q
```

The interesting tests don't compare the engine to itself — they compare it to
mathematics. Lindenmayer's algae must grow by the *Fibonacci* numbers; the Koch
production multiplies the F-count by exactly five each pass (so the F-count is
`5**n`); a closed curve like the snowflake must return the turtle to where it
began; a single step of length 10 must produce a bounding box you can name in
advance; and a stochastic system must give *identical* output for the same seed.
The rest pins down the turtle's branching stack, the SVG viewBox fit, and the CLI.
