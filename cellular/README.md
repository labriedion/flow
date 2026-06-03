# cellular

Elementary **cellular automata** — Wolfram's one-dimensional rules — drawn in
your terminal or exported as SVG. Pure Python standard library, with a test
suite that checks the engine against the *closed-form* description of several
famous rules.

A row of cells, each on or off. To make the next row, look at every cell with
its two neighbours — three bits, eight possible neighbourhoods — and decide the
new state from a lookup table. That table is just a number from 0 to 255: the
**rule**. From those eight bits of "program", startlingly rich behaviour falls
out.

```
Rule 90, from a single lit cell — a Sierpinski triangle:

                               █
                              █ █
                             █   █
                            █ █ █ █
                           █       █
                          █ █     █ █
                         █   █   █   █
                        █ █ █ █ █ █ █ █
                       █               █
                              ...
```

Rule 30 is chaotic enough that Mathematica used it as a random-number generator.
Rule 90 draws the Sierpinski gasket. Rule 110 is Turing-complete. Same engine,
different byte.

See [`examples/`](examples) for a wide [Rule 30 SVG](examples/rule30.svg), a
[Rule 90 Sierpinski SVG](examples/rule90-sierpinski.svg), and a
[text sample](examples/sample_output.txt).

## Run it

```bash
python -m cellular.cli --rule 30                  # chaos, in the terminal
python -m cellular.cli --rule 90                  # the Sierpinski triangle
python -m cellular.cli --rule 110 --width 120 --height 80
python -m cellular.cli --rule 30 --random --seed 7   # random starting row
python -m cellular.cli --rule 90 --svg out.svg    # write an SVG instead
```

By default it starts from a single lit cell in the middle and prints the
evolution using compact half-block characters (two rows per line, so the picture
keeps its true proportions). `--plain` switches to one full-block row per line.

| flag | meaning |
| --- | --- |
| `--rule N` | Wolfram rule number, 0–255 (default 30) |
| `--width` / `--height` | cells per row / generations to evolve |
| `--boundary` | `wrap` (a ring), `zero` (void), or `one` off the edges |
| `--random` `--density` `--seed` | start from a reproducible random row |
| `--plain` | one row per line, full blocks |
| `--svg PATH` `--cell` `--grid` | export an SVG at a given cell size |

## How it works

```
cellular/
  automaton.py   # rule tables, a step/evolve engine, and starting rows
  render.py      # terminal text, half-block packing, and SVG export
  cli.py         # the command-line front end
```

The core is tiny. `rule_table(n)` expands the rule number into its eight outputs;
`Automaton.step` reads each cell's neighbourhood as a 3-bit index into that
table; `evolve` stacks the rows. The SVG exporter coalesces runs of lit cells
into a single path so even a big grid stays compact.

## Use it as a library

```python
from cellular import Automaton, single_cell, to_svg

rows = Automaton(90, boundary="zero").evolve(single_cell(64), 32)
open("sierpinski.svg", "w").write(to_svg(rows, cell=6))
```

## Test it

```bash
python -m pytest cellular/ -q
```

The interesting tests don't compare the engine to itself — they compare it to
mathematics. Several rules have exact descriptions (`Rule 90 = left XOR right`,
`Rule 30 = left XOR (centre OR right)`), and Rule 90 grown from a single seed is
*Pascal's triangle mod 2*, so the suite asserts the lit cells match binomial
coefficients `C(t, k) mod 2` exactly. The rest pins down boundary handling
(wrap/zero/one), reproducible random starts, and the renderers.
