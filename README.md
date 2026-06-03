# flow
I send Claude Code off on missions to
build whatever it wants and see what it comes back with. 

Here's what's in the box so far:

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

## Running them

- **flowfield** / **fractal** / **driftwave** / **boids** — open that project's `index.html`
  in any modern browser. That's it, no server.
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
