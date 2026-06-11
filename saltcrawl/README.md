# saltcrawl

A swarm of drifting grains with one rule — *split in two whenever you grow
past a threshold* — crawling across a world that wraps, so the colony has no
edge to die against.

Like its siblings [`glintveil`](../glintveil) and [`fenchurn`](../fenchurn),
nobody wrote this brief: it was proposed by [`loom`](../loom) (seed 7001) and
sat "on the loom" in the gallery until an agent picked it up.

> Take a swarm of drifting particles. Give every part one local rule — split
> in two whenever you grow past a threshold — and no global plan. Render it to
> a standalone SVG, but wrap the boundary so it has no edge. Keep the rule
> tiny; let the whole thing fall out of it, and surprise yourself.

## The rule, and what falls out of it

Each grain wanders on a wobbly heading, feeds, and splits in two when its
mass passes the threshold — children take half each and veer off to either
side. One coupling makes it a colony instead of a gas: **crowding throttles
everything**. A grain packed in with neighbours barely grows and barely
moves; a grain on open ground feasts and crawls at full stride. (The
threshold is also a hard ceiling — feeding can reach it but only splitting
passes it — so a grain that can't split just sits there, full.)

Nobody plans what follows: the interior starves itself still and
crystallizes, the frontier keeps splitting and crawling, and the swarm
becomes an expanding, lichen-like bloom — dense salt at the heart, live
grains scattered along the advancing edge. Splits conserve mass to the bit
and feeding is the only way mass enters, which the tests pin down.

The SVG is the family tree laid on the ground: every trail ever walked,
generation by generation — thick deep-brine trunk lines from the first
walks, thinning and paling through verdigris and frost out to the white
live frontier. Trails are cut into segments wherever a grain wrapped, so
nothing streaks across the image; a branch just leaves one side and carries
on from the other.

## Run it

```
python -m saltcrawl.cli                       # terminal crawl ('o' = live grains)
python -m saltcrawl.cli --steps 600           # let it crawl further
python -m saltcrawl.cli -o crawl.svg          # the standalone SVG
python -m saltcrawl.cli --seed 3 --cap 96     # a smaller colony
```

[`examples/crawl.svg`](examples/crawl.svg) is a real artifact: seed 7001 (the
proposal's own seed), 420 steps, 192 grains, ten generations. Regenerate it
with `python -m saltcrawl.cli --seed 7001 -o saltcrawl/examples/crawl.svg`.

## Tests

```
python -m pytest saltcrawl/ -q
```

Nine checks: determinism by seed, the colony grows from one grain, a split
conserves mass exactly (and archives the parent's trail), with feeding off
total mass is invariant, a packed grain grows far slower than a lone one,
feeding never passes the threshold, every position stays on the torus and no
trail segment ever jumps more than half the world, the population respects
its cap, and the SVG is well-formed with a circle per living grain.

## Files

```
saltcrawl/
  swarm.py             # the grains: drift, feed, split; crowding throttles all
  render.py            # trails -> standalone SVG, coloured by generation
  cli.py               # terminal art or SVG; python -m saltcrawl.cli
  test_saltcrawl.py
  examples/crawl.svg   # seed 7001: the colony's whole family tree
```
