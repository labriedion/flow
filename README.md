# flow

> Sending Claude Code on missions.

A small collection of self-contained creative coding projects — each one
dependency-free, each one a different domain. Built unprompted as an
exploration of what's fun to make.

| Project | What it is | Stack |
| --- | --- | --- |
| [**flowfield**](./flowfield) | A generative-art studio: thousands of particles drift through an evolving simplex-noise field, painting trails in light. Live controls, eight palettes, mouse forces, PNG export. | HTML5 Canvas · vanilla JS |
| [**amaze**](./amaze) | A terminal maze generator & solver. Perfect mazes via recursive backtracker or Prim's; optimal paths via BFS or A*; Unicode rendering with a colored solution overlay. 17 passing tests. | Python (stdlib only) |
| [**driftwave**](./driftwave) | A generative ambient music engine — evolving detuned pads and probabilistic plucks over a synthesized reverb, with a live visualizer. Never the same twice. | Web Audio API · vanilla JS |

## Running them

- **flowfield** / **driftwave** — open the project's `index.html` in any modern
  browser. No server, no build.
- **amaze** — `python -m amaze.cli --width 30 --height 15` (run tests with
  `python -m pytest amaze/ -q`).

Each project has its own README with full details.
