# flow
I send Claude Code off on missions to
build whatever it wants and see what it comes back with. 

What it keeps coming back with is **emergence** — simple local rules, no
conductor, a surprising whole. There's a gallery that ties it all together
(with one of those rule-systems drifting live behind it): open
[`index.html`](./index.html) in any browser.

Here's what's in the box so far (this table is regenerated from the mission
registry by [`loom`](./loom) — see below):

<!-- loom:table:start -->
| Project | What it is | Built with |
| --- | --- | --- |
| [**flowfield**](./flowfield) | Thousands of particles drifting through an evolving noise field, leaving trails of light. You can mess with all the knobs live and save a frame. | Canvas + vanilla JS |
| [**fractal**](./fractal) | A Mandelbrot & Julia explorer you can actually fly around in — scroll to zoom, drag to pan, morph the Julia constant with your mouse. | Canvas + vanilla JS |
| [**driftwave**](./driftwave) | Generative ambient music that's never the same twice. Pads and plucks woven over a reverb, all made up on the spot in your browser. | Web Audio API |
| [**amaze**](./amaze) | Mazes in your terminal — generate them, braid in some loops, then watch BFS or A\* find the way through. Can spit out an SVG too. | Python (stdlib) |
| [**markov**](./markov) | Feed it any text and it babbles back in the same style, word-by-word or letter-by-letter. Good for fake prose and invented words. | Python (stdlib) |
| [**calc**](./calc) | A proper little expression evaluator — tokenizer, parser, the works — with functions, constants and variables. Comes with a REPL. | Python (stdlib) |
| [**reggie**](./reggie) | A regex engine built from scratch — pattern to bytecode to a virtual machine that matches in linear time and never catastrophically backtracks. Captures and all. | Python (stdlib) |
| [**cellular**](./cellular) | Wolfram's one-dimensional cellular automata. Feed it a rule number from 0–255 and watch Sierpinski triangles and pure chaos fall out. Terminal art or SVG. | Python (stdlib) |
| [**boids**](./boids) | A flock that nobody's steering — thousands of agents following three local rules, swirling into murmurations you can gather and scatter with the mouse. | Canvas + vanilla JS |
| [**wavefn**](./wavefn) | Wave Function Collapse — hand it a few tiles and the rules for which edges may touch, and it collapses a blank grid into one pattern where everything lines up. Connected pipes, little coastlines. Terminal art or SVG. | Python (stdlib) |
| [**reverb**](./reverb) | A reverb built from the bare math — comb and allpass filters wired into a Schroeder/Freeverb tail — that takes a dry WAV and gives it a room to ring in. Comes with a demo that invents its own sound to drench. | Python (stdlib) |
| [**lsystem**](./lsystem) | Lindenmayer systems — rewrite a tiny string of symbols over and over, then let a turtle walk the result. Koch snowflakes, dragon curves, Hilbert space-fillers and branching weeds fall out as SVG. | Python (stdlib) |
| [**sand**](./sand) | A falling-sand playground — paint sand, water, walls, wood and fire onto a grid and watch it tumble, pool, burn and smoke. `cellular` grown into 2D and handed a mouse. | Canvas + vanilla JS |
| [**glintveil**](./glintveil) | Gray–Scott reaction–diffusion you can poke with the mouse. Two chemicals share a lattice — one fed, one killed — and coral fronts, mazes and dividing spots bloom out of two lines of math. Six regimes plus the whole parameter plane between them. | Canvas + vanilla JS |
<!-- loom:table:end -->

**[loom](./loom)** is the odd one out: not another emergent toy but the engine
that turns the collection *into* one. It keeps the mission registry, proposes
new "simple rules → emergent behaviour" briefs, weighs how much each built thing
amplified its rule (an honest proxy for emergence), and regenerates the gallery
from that data. `python -m loom missions` to see the loop; details in
[`loom/README.md`](./loom).

## Running them

- **flowfield** / **fractal** / **driftwave** / **boids** / **sand** / **glintveil** — open
  that project's `index.html` in any modern browser. That's it, no server. (sand and
  glintveil also have headless smoke tests: `node sand/test_sim.mjs`,
  `node glintveil/test_sim.mjs`.)
- **amaze** — `python -m amaze.cli --width 30 --height 15`
  (tests: `python -m pytest amaze/ -q`)
- **markov** — `python -m markov.cli markov/corpus.txt --order 2 --length 60`
  (tests: `python -m pytest markov/ -q`)
- **calc** — `python -m calc.cli "2 + 3 * 4"`, or just `python -m calc.cli` for
  the REPL (tests: `python -m pytest calc/ -q`)
- **reggie** — `python -m reggie.cli '\d+' "order 66 ships 1024"`
  (tests: `python -m pytest reggie/ -q`)
- **cellular** — `python -m cellular.cli --rule 30`, or `--rule 90` for a
  Sierpinski triangle (tests: `python -m pytest cellular/ -q`)
- **wavefn** — `python -m wavefn.cli --tileset pipes --seed 7`, or
  `--tileset terrain` (write an SVG with `--svg out.svg`;
  tests: `python -m pytest wavefn/ -q`)
- **reverb** — `python -m reverb.cli --demo out.wav` to hear it drench a synth
  pluck, or `python -m reverb.cli in.wav out.wav --room 0.8 --wet 0.35`
  (tests: `python -m pytest reverb/ -q`)
- **lsystem** — `python -m lsystem.cli --preset snowflake --iterations 4 -o snowflake.svg`,
  or `--list` to see them all (tests: `python -m pytest lsystem/ -q`)
