# amaze

A tiny, dependency-free maze **generator** and **solver** for your terminal.
Pure Python standard library, with a real test suite.

```
amaze/
  maze.py        # grid model, generation algorithms, pathfinding solvers
  render.py      # Unicode box-drawing renderer with a colored solution overlay
  cli.py         # argparse command-line interface
  test_maze.py   # pytest suite (structural + correctness guarantees)
```

## Run it

```bash
python -m amaze.cli --width 30 --height 15
python -m amaze.cli -W 40 -H 20 --algo prim --solver astar --seed 7
python -m amaze.cli --no-solve --no-color        # just the maze, plain text
```

| Flag | Default | Meaning |
| --- | --- | --- |
| `-W/--width`, `-H/--height` | 25 × 12 | maze size in cells |
| `--algo` | `backtracker` | `backtracker` (winding) or `prim` (bushy) |
| `--solver` | `bfs` | `bfs` or `astar` — both find the optimal path |
| `--seed` | random | fix for reproducible mazes |
| `--no-solve` | off | skip the solution overlay |
| `--no-color` | off | disable ANSI colors |

## Use it as a library

```python
from amaze import generate_backtracker, solve_astar, render

maze = generate_backtracker(20, 10, seed=42)
path = solve_astar(maze)
print(render(maze, path))
```

## Test it

```bash
python -m pytest amaze/ -q
```

The suite checks that generated mazes are **perfect** (every cell reachable,
no loops), that passages are symmetric, that generation is reproducible under
a seed, and that BFS and A* agree on the (unique) optimal path length.
