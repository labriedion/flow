# lullweave

A graph of wired-up nodes with one rule — *pull toward whoever is loudest
nearby* — that holds itself at the edge of chaos, because the second half of
the rule is a homeostat every node runs on its own neighbourhood.

Like its siblings [`glintveil`](../glintveil), [`fenchurn`](../fenchurn) and
[`saltcrawl`](../saltcrawl), nobody wrote this brief: it was proposed by
[`loom`](../loom) (seed 11001) and sat "on the loom" in the gallery until an
agent picked it up.

> Take a graph of wired-up nodes. Give every part one local rule — pull
> toward whoever is loudest nearby — and no global plan. Render it to the
> terminal, in glyphs, but tuned to sit right at the edge of chaos. Keep the
> rule tiny; let the whole thing fall out of it, and surprise yourself.

## The rule, and what falls out of it

Every node is a tiny oscillator: dark, brightening, a flash, dark again. Its
loudness is how close to the flash it is, and each step it leans its own
clock toward its neighbours' clocks — harder toward the loud ones. The
neighbours are mostly the four nodes beside it (the world wraps), plus a
sprinkle of long-range shortcuts thrown across the graph, so a flash can leap
to a far corner the glyphs gave you no warning about. Fireflies on a small
world.

The brief's twist — *tuned to sit right at the edge of chaos* — isn't a dial
anyone set. Each node keeps its own coupling gain and adjusts it by ear:
surrounded by lockstep consensus it gets bored and loosens its grip; lost in
noise it tightens. Nobody can see the whole graph, but with every node
homeostatting its own neighbourhood toward half-coherence, the weave
globally never freezes into one big flash and never boils into static —
patches of synchrony knit, fray and re-knit forever, waves of light chasing
the hidden wires. Pin every gain high and the graph locks into near-total
sync; cut the gain to zero and it's static; let the homeostat run and it
holds the middle indefinitely. The tests pin all three.

(That middle is exactly what [`loom`](../loom)'s surprise proxy admits it
cannot see — compression can't tell the edge of chaos from noise. This
mission walked straight at the proxy's documented blind spot.)

## Run it

```
python -m lullweave.cli                      # watch the weave, live glyphs
python -m lullweave.cli --steps 2000         # let it run longer
python -m lullweave.cli --once --steps 300   # one still frame, no animation
python -m lullweave.cli -o weave.svg         # standalone SVG, wires and all
python -m lullweave.cli --shortcuts 0        # cut the hidden wires; waves only crawl
```

The SVG shows what the terminal can't: grid wires as faint threads, the
shortcuts as long pale arcs, and every node a firefly — the loud ones wearing
halos. [`examples/weave.svg`](examples/weave.svg) is a real artifact: seed
11001 (the proposal's own seed) after 480 steps. Regenerate it with
`python -m lullweave.cli --seed 11001 --steps 480 -o lullweave/examples/weave.svg`.

## Tests

```
python -m pytest lullweave/ -q
```

Ten checks: determinism by seed, seeds diverge, the wiring is an honest
symmetric graph whose shortcuts are genuinely long-range, clocks stay on the
circle and loudness in bounds, gain pinned high locks into one big flash,
gain zero is static, the homeostat holds global coherence between the two
and never lets it settle, gains stay clamped however twitchy the tuner, the
glyph frame is the right shape, and the SVG is well-formed with a firefly
per node and an arc per shortcut.

## Files

```
lullweave/
  weave.py             # the graph and the rule: the pull, and the homeostat
  render.py            # glyph frames for the terminal; the SVG with the wires
  cli.py               # animate, snapshot, or SVG; python -m lullweave.cli
  test_lullweave.py
  examples/weave.svg   # seed 11001: one moment of the weave, wires and all
```
