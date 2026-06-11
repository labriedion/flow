# fenchurn

A heap of edge-matching tiles that averages itself into a quilt — except for
one cell that refuses, and thereby wins.

Like [`glintveil`](../glintveil), nobody wrote this brief: it was proposed by
[`loom`](../loom) (seed 7000) and sat "on the loom" in the gallery until an
agent picked it up.

> Take a heap of edge-matching tiles. Give every part one local rule — average
> yourself toward your neighbours — and no global plan. Render it to a
> standalone SVG, but with one cell that disobeys. Keep the rule tiny; let the
> whole thing fall out of it, and surprise yourself.

## The rule, and what falls out of it

Every tile carries four numbers, one per edge. Each step, two strictly local
moves:

- every **seam** (a pair of facing edges) pulls both edges toward their shared
  midpoint — neighbours negotiating;
- every **tile** pulls its own four edges toward their own mean — keeping
  itself in one piece.

Nothing imposes edge-matching; it *emerges*. Seams negotiate themselves shut
and the heap of clashing tiles becomes one continuous quilt. Both moves
conserve their sums, so without a rebel the quilt settles exactly on its own
average — the tests pin that invariant down to 1e-9.

Then the twist the brief demanded: **one cell disobeys**. The rebel never
averages — its edges never move. And because everyone else keeps politely
meeting it halfway, its colour leaks across every seam it touches and slowly
recolours the entire quilt. The rebel is the only door value can enter
through, which is exactly why it wins. The surprise, stated as a koan: *the
cell that refused to average ends up averaging everyone.* (Opinion-dynamics
people know this as the zealot effect; the quilt discovers it from scratch.)

The SVG draws each tile from a deep-ink-to-amber ramp and overlays every seam
that still disagrees as a glowing stitch, opacity proportional to the
mismatch. Mid-run the stitches have faded everywhere except the scar around
the rebel — the mark of the cell the whole quilt is slowly becoming.

## Run it

```
python -m fenchurn.cli                          # terminal quilt ('!' is the rebel)
python -m fenchurn.cli --steps 1200             # later: the rebel's colour spreading
python -m fenchurn.cli --no-rebel               # nobody disobeys; plain consensus
python -m fenchurn.cli -o quilt.svg             # the standalone SVG
python -m fenchurn.cli --rebel 3 3 --rebel-value 0.0   # a dark rebel, off-centre
```

[`examples/quilt.svg`](examples/quilt.svg) is a real artifact: seed 7000 (the
proposal's own seed), 36×24 tiles, 90 steps in — seams mostly healed, the scar
still glowing. Regenerate it with
`python -m fenchurn.cli --width 36 --height 24 --steps 90 --seed 7000 -o fenchurn/examples/quilt.svg`.

## Tests

```
python -m pytest fenchurn/ -q
```

Seven checks: determinism by seed, a short run melts the heap's disagreement,
the widest mid-run seam touches the rebel, the rebel never budges, the rebel
recolours every tile and every seam closes around its value, the no-rebel
quilt conserves its mean exactly and lands consensus on it, and the SVG is
well-formed with one rect per tile.

## Files

```
fenchurn/
  quilt.py           # the heap: four edges per tile, two conserving moves, one rebel
  render.py          # quilt -> standalone SVG (tiles + glowing stitches)
  cli.py             # terminal art or SVG; python -m fenchurn.cli
  test_fenchurn.py
  examples/quilt.svg # seed 7000, mid-run, scar visible
```
