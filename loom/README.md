# loom

The other twelve-and-one things in [`flow`](../) are emergent systems: simple
local rules, no conductor, a surprising whole. **loom is the move that makes the
collection itself one of them.**

The human's loop — *propose a "simple rules → emergent behaviour" mission, send
Claude Code to build it, keep the ones that genuinely surprised you, hang them
in the gallery* — was invisible and hand-run. loom makes it explicit and
partly self-running, in pure Python standard library, zero dependencies, every
result reproducible by seed (the house rules).

```
loom/
  missions.json   # the registry — the spine of flow, every brief + what came back
  registry.py     # load / save / filter missions
  primitives.py   # the vocabulary the generator composes from
  propose.py      # dream up new missions (deterministic by seed)
  surprise.py     # the emergence proxy — how much did the rule amplify?
  gallery.py      # regenerate index.html + the README table from the registry
  cli.py          # python -m loom <command>
```

## The loop

```
python -m loom missions               # the registry: what's built, what surprised it
python -m loom propose --seed 7        # dream up new missions from a seed
python -m loom propose --seed 7 --save # …and add them to the registry as "proposed"
python -m loom score                   # weigh every built mission's surprise proxy
python -m loom gallery --write         # rebuild index.html + README table from the data
```

Tests: `python -m pytest loom/ -q`.

### propose — emergence about emergence

The generator is *itself* an instance of the bet flow keeps making. A handful of
primitives — a **substrate**, one **local rule**, a **medium**, an optional
**twist** (including "seeded from another project's output") — and one combining
rule produce a mission space far larger and stranger than the parts. Same seed,
same mission, always.

### score — an honest proxy, not a verdict

Emergence has a signature you can weigh: a *small* rule producing a *richly
complex* output. We approximate both sides with compression (a practical lower
bound on Kolmogorov complexity):

- **amplification** `= compressed(output) / compressed(rule)` — how much
  incompressible structure the rule blew up into. The headline number.
- **richness** `= compressed(output) / raw(output)` — how non-trivial the
  output is on its own.

**What it cannot see**, stated plainly because the honesty is the point:

- It is a proxy for emergence, **not** beauty, taste, or whether anyone was
  actually surprised. That subjective question is genuinely unsolved.
- Amplification rewards the *amount* of structure; it can't tell structured
  emergence from pure noise. The edge-of-chaos distinction is exactly what
  byte-counting misses.
- It's blind to structural cleverness with small output — `reggie` (a regex VM)
  and `calc` (a parser) score low here even though their surprise is real. The
  proxy favours the generative-visual systems, and we report the number anyway
  rather than fudge it.

### gallery — the murmuration falls out

`index.html` is no longer hand-maintained. loom reproduces the crafted chrome
(hero, palette, the live flow field behind it) verbatim, generates a card per
built mission, **sorts each section by the surprise proxy** so the page arranges
itself by how much each amplified its rule, and lists proposed-but-unbuilt
missions as *on the loom*. The README project table regenerates the same way,
between its `loom:table` markers.

## The horizon this is reaching for

This is Phases 1–4 of closing the loop: the missions are visible, the system
proposes its own, it weighs what surprised it, and the gallery assembles itself
from that data. The last step — having an agent autonomously *build* a proposed
mission and report back — is left as a clean seam: `propose` already emits a
ready-to-send brief. Today a human carries it across (send Claude Code on the
mission); a future `loom run` could call an API to close it fully. That step is
real research and infrastructure, not a flag we pretend to have planted — the
subjective "did this delight me?" at its core is still open.
