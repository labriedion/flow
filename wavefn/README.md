# wavefn

A tiled **Wave Function Collapse** solver — lay down a grid of little tiles so
that every edge agrees with its neighbour, then watch pipes connect and
coastlines close up. Pure Python standard library, terminal art or SVG, with a
test suite that checks the *output* against the adjacency rule rather than
against the solver's own internals.

Each tile has four **edge sockets** — labels on its north, east, south and west
edges — plus a small pixel pattern and a weight. The whole game is one rule: two
tiles may sit next to each other only when the edges they share carry the same
socket. Horizontally, the left tile's east socket must match the right tile's
west socket; vertically, the top's south must match the bottom's north. From
that single constraint, coherent pictures fall out.

```
A corner of a pipes grid — every arm meets another arm or a wall:

 █  █▀▀█  █▀▀▀▀▀█
 █  █     █     █
 █  ▀▀▀▀▀▀█     █
▄█  ▄▄▄▄▄▄▄  ▄▄▄█
 █  █     █  █
```

The solver is plain constraint propagation wearing a physics costume. Start with
every cell *undecided* — it could still be any tile. Then repeat:

1. **Observe** — find the undecided cell with the lowest entropy (the fewest,
   least-certain options, weighted by tile weight), break ties at random, and
   **collapse** it to a single tile chosen by weight.
2. **Propagate** — that choice rules out some neighbours. Walk the consequences
   outward, AC-3 / worklist style, pruning tiles that can no longer match any
   surviving neighbour, until nothing changes.

If a cell ever loses *all* its options the grid has contradicted itself; wavefn
throws it away and retries from a fresh derived seed a few times before giving
up with a clear error. A `--seed` makes any run reproducible.

See [`examples/`](examples) for a [pipes SVG](examples/pipes.svg), a
[terrain SVG](examples/terrain.svg), and a [text sample](examples/sample_output.txt).

## Run it

```bash
python -m wavefn.cli                                   # a default pipes grid
python -m wavefn.cli --tileset pipes --width 24 --height 16 --seed 7
python -m wavefn.cli --tileset terrain --seed 3        # water, coast and land
python -m wavefn.cli --list                            # show the tilesets
python -m wavefn.cli --tileset pipes --svg out.svg     # write an SVG instead
```

By default it collapses a 24×16 pipes grid and prints the result with compact
half-block characters (two pixel rows per line, so the picture keeps its true
proportions). `--plain` switches to one full-size pixel row per line.

| flag | meaning |
| --- | --- |
| `--tileset NAME` | which built-in set: `pipes` or `terrain` (default `pipes`) |
| `--width` / `--height` | grid size in tiles |
| `--seed` | seed for a reproducible run |
| `--attempts` | retries from a derived seed on contradiction (default 12) |
| `--plain` | one full-size pixel row per line |
| `--svg PATH` `--cell` | export an SVG at a given pixel size |
| `--list` | list the tilesets and exit |

## The tilesets

- **pipes** — blank, straight, corner, tee and cross, with sockets that are
  either an open pipe end or a flat wall. Open ends only ever meet open ends, so
  the grid is always a network of pipes that genuinely connect.
- **terrain** — deep water, land, and coast/cape/bay tiles whose `w` (water) and
  `l` (land) edges only touch their own kind. Water bodies stay connected and
  land never abuts water without a coastline in between.

Most tiles are one shape turned a quarter-turn, so the tilesets describe a single
"corner" or "tee" and `rotations()` spins out the rest — rotating the socket
labels and the pixel pattern together so a rotated tile stays consistent.

## How it works

```
wavefn/
  tilesets.py    # Tile, rotations, and the built-in pipes/terrain sets
  solver.py      # adjacency tables + the observe/collapse/propagate loop
  render.py      # stamp tiles into a pixel field; half-blocks and SVG export
  cli.py         # the command-line front end
```

`build_adjacency` precomputes, for every tile and side, which tiles may sit
there — a table that is symmetric by construction. The solver keeps each cell as
a *set* of still-possible tile indices, collapses the lowest-entropy cell, and
propagates with a worklist until stable. The SVG exporter coalesces runs of
same-coloured pixels into one path per colour, so even a big grid stays compact.

## Use it as a library

```python
from wavefn import Solver, get, stamp, to_svg

grid = Solver(get("pipes"), width=24, height=16, seed=7).run()
field = stamp(grid, get("pipes"))
open("pipes.svg", "w").write(to_svg(field, cell=8))
```

## Test it

```bash
python -m pytest wavefn/ -q
```

The headline test doesn't compare the solver to itself — it compares the
collapsed grid to the *ground truth* of the adjacency rule: across several seeds
and both tilesets, every pair of neighbours must agree on its shared socket. The
rest pins down that the adjacency relation is symmetric and exactly socket
equality, that propagation really removes options, that a seed reproduces a run,
and that an over-constrained set raises a clear error instead of looping forever.
