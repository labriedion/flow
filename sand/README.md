# Sand — Falling-Sand Playground

An interactive **falling-sand** toy: a grid of cells, a few materials with
opinions about gravity, and a mouse. Paint sand, water, walls, wood, fire and
smoke and watch them pile, slosh, sink, burn and drift into each other. It's
[`cellular`](../cellular) grown a second dimension — same idea (every cell only
looks at its immediate neighbours), but now things fall.

Nobody is choreographing the dune that forms when sand pours onto a ledge, or
the way a column of water collapses into a flat pool, or the smoke that peels
off a burning log. It all falls out of a handful of **local** rules applied to
every cell, every tick.

**Zero dependencies, zero build step.** Just open `index.html` in a browser.

```
sand/
  index.html    # UI shell
  style.css     # glassy control panel
  main.js       # UI wiring + render loop + mouse painting
  sand.js       # the renderer (grid of ids -> scaled ImageData)
  sim.js        # the simulation engine — pure, DOM-free, unit-tested
  test_sim.mjs  # Node smoke test (node:assert, no framework)
  examples/
    render_ascii.mjs    # headless run that dumps a text snapshot
    sample_output.txt   # a real artifact from that run
```

## Materials and their rules

| Material | Glyph | Behaviour |
| --- | --- | --- |
| **Sand** | `.` | Falls straight down; if blocked, slides diagonally. Denser than water, so it **sinks through** it. |
| **Water** | `~` | Falls; if blocked below, flows sideways to find its level (pools flatten out). |
| **Wall** | `#` | Static. Indestructible bedrock — nothing moves it, nothing burns it. |
| **Wood** | `=` | Static, but **flammable**: it catches when fire touches it. |
| **Fire** | `*` | Ignites neighbouring wood, clings to fuel, rises when there's none left, and has a short life. Dies into smoke (usually) or nothing. |
| **Smoke** | `:` | Rises, drifts sideways, and thins out to empty over time. |

Density is what lets sand bury itself in water: a falling grain is allowed to
swap places with the lighter fluid beneath it, but never with a solid.

## Controls

| Control | What it does |
| --- | --- |
| Material palette | pick what the brush paints (the **Eraser** paints empty) |
| Brush Size | radius of the painted disc, in cells |
| Sim Speed | physics ticks per rendered frame (turn it up to fast-forward) |

**Mouse:** hold **left-click** to paint the selected material, **right-click**
to erase. Drags paint a continuous stroke. **Keys:** `1`–`7` pick a material
(sand, water, wall, wood, fire, smoke, eraser) · `Space` pause · `R` reseed the
starter scene · `C` clear · `S` save PNG · `H` hide the panel.

Hit **Save PNG** to keep a frame, **Reseed** to drop a fresh starter scene
(floor, walls, a wooden shelf, a hopper of sand and a tank of water), or
**Clear** for a blank world to build from scratch.

## How the update works

A naive falling-sand sweep — top-to-bottom, left-to-right — has two problems.
It lets a grain move *down* and then, because the scan keeps going and revisits
the grain's new cell, move *again* in the same tick, so things teleport several
rows per frame. And the fixed left-to-right order makes every pile lean the same
way.

So the engine sweeps **bottom-up**: a cell is only ever considered once per
tick, after everything below it has already settled. And within each row it
**flips the horizontal scan direction** (alternating by row and tick), which
cancels out the directional bias so piles slump symmetrically. A scratch `moved`
flag stops a grain that just fell from being processed twice if the scan reaches
its landing cell.

The whole world is a flat `Uint8Array` of material ids (one byte per cell), with
a parallel `Uint8Array` of life timers that fire and smoke count down. The
renderer keeps it cheap by drawing into a grid-sized `ImageData` buffer — one
pixel per cell — and letting the canvas scale that up with smoothing off, so the
per-frame cost tracks the grid (tens of thousands of cells), not the screen
(millions of pixels).

## Tests

The simulation in `sim.js` has no DOM or canvas references, so it runs straight
under Node. From the repo root:

```
node sand/test_sim.mjs
```

It asserts the core invariants with `node:assert` (no framework): a lone grain
falls exactly one cell per step; sand piles on a wall and is conserved over
hundreds of steps with nothing leaking through; a tall water column collapses
and spreads sideways; fire next to wood consumes it, produces smoke, and
eventually burns out; two sandboxes with the same seed and same painting stay
bit-for-bit identical after N steps (the RNG is a seedable mulberry32); and the
grid never changes size or writes out of bounds. It exits non-zero on the first
failure.

For a quick look without a browser:

```
node sand/examples/render_ascii.mjs
```

prints an ASCII snapshot of a headless run; [`examples/sample_output.txt`](examples/sample_output.txt)
is a committed copy of that output.
