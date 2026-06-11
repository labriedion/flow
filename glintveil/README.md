# glintveil

A Gray–Scott reaction–diffusion field on an HTML canvas you can poke with the
mouse. Two chemicals share a lattice; every cell follows one local rule —
*react and diffuse with the chemical beside you* — and spots split like cells,
stripes weave into fingerprints, and coral fronts crawl out of nothing but
that rule repeated everywhere at once.

**This one is different from its twelve siblings in one way: nobody wrote its
brief.** `glintveil` was proposed by [`loom`](../loom) (seed 7002) as one of
the missions "on the loom", and this build closes the loop the loom README
called its horizon: the system proposed a mission, and an agent picked it up
and built it.

> Take a lattice of coupled springs. Give every part one local rule — react
> and diffuse with the chemical beside you — and no global plan. Render it to
> an HTML canvas you can poke with the mouse. Keep the rule tiny; let the
> whole thing fall out of it, and surprise yourself.

The "coupled springs" are taken literally: the diffusion term is a Hooke
coupling, every cell pulled toward the average of its eight neighbours
(a 9-point Laplacian). The reaction stacked on top is the Gray–Scott scheme:

```
u' = Du·∇²u − u·v² + f·(1 − u)        u is fed in everywhere
v' = Dv·∇²v + u·v² − (f + k)·v        v eats u and is killed off
```

That's the entire physics — two lines, two knobs. The feed rate `f` and kill
rate `k` pick which universe you're in: nudge them a few thousandths and
mitosis becomes a maze becomes standing waves. The named presets are corners
of Pearson's classification of that parameter plane, and the sliders let you
wander the regimes in between. The lattice is a torus, so patterns have no
edge to die against.

## Run it

Open [`index.html`](./index.html) in any modern browser. No server, no build.

- **left-drag** pours the patterning chemical; **right-drag** erases back to silence
- **1–6** jump between regimes (Coral, Mitosis, Maze, Solitons, Worms, Waves)
- **feed / kill sliders** leave the presets and explore the plane between them
- **Space** pause · **R** reseed · **C** clear · **S** save a PNG · **H** hide the panel

## Files

```
glintveil/
  sim.js          # the field — pure script, no DOM, seedable, Node-testable
  main.js         # renderer + UI: colour ramp, pointer poking, presets
  index.html      # the page
  style.css       # the chrome
  test_sim.mjs    # headless Node smoke test (no framework, just node:assert)
  examples/
    render_ascii.mjs    # regenerates the artifact below, deterministically
    sample_output.txt   # a real veil from seed 7002, the proposal's own seed
```

## Tests

```
node glintveil/test_sim.mjs
```

Seven checks, no dependencies: the uniform field is exactly stationary
(nothing grows from silence), same seed + same pokes ⇒ bit-identical
evolution, one poke spreads structure far beyond its own footprint, patterns
cross the wrap (the torus has no edge), every preset stays finite and inside
[0,1], clear/erase restore the quiet fixed point, and the ASCII view holds
its shape.

## Why it belongs here

It's the collection's bet in its purest chemical form: no cell knows anything
beyond its neighbours, the rule fits in two lines, and the veil that blooms
out of it — glinting, healing around your finger, never the same twice —
was choreographed by nobody.
