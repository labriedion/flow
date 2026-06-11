// render_ascii.mjs — run the headless simulation and dump a text snapshot.
//
// There's no browser in CI, so this is the artifact that proves the physics
// actually does something: build a small world, paint a few materials, run it
// for a while, and print the grid as ASCII. Run with:
//
//   node sand/examples/render_ascii.mjs
//
// or capture it to the committed sample with:
//
//   node sand/examples/render_ascii.mjs > sand/examples/sample_output.txt

import { createRequire } from 'node:module';

const require = createRequire(import.meta.url);
const { Sandbox, EMPTY, SAND, WATER, WALL, WOOD, FIRE, SMOKE } = require('../sim.js');

// One glyph per material id, chosen so the snapshot reads at a glance.
const GLYPH = {
  [EMPTY]: ' ',
  [SAND]:  '.',
  [WATER]: '~',
  [WALL]:  '#',
  [WOOD]:  '=',
  [FIRE]:  '*',
  [SMOKE]: ':',
};

function render(sim) {
  const lines = [];
  for (let y = 0; y < sim.height; y++) {
    let row = '';
    for (let x = 0; x < sim.width; x++) row += GLYPH[sim.get(x, y)] ?? '?';
    lines.push(row);
  }
  return lines.join('\n');
}

// A compact, fixed-seed scene so the committed output is reproducible.
const sim = new Sandbox(48, 24, 12345);

// Bedrock floor + side walls.
for (let x = 0; x < sim.width; x++) sim.set(x, sim.height - 1, WALL);
for (let y = 0; y < sim.height; y++) { sim.set(0, y, WALL); sim.set(sim.width - 1, y, WALL); }

// A wooden bridge with fire set at one end, a sand hopper, and a water tank.
for (let x = 6; x < 24; x++) sim.set(x, 14, WOOD);
sim.set(6, 13, FIRE); sim.set(7, 13, FIRE);
sim.paint(14, 4, 4, SAND);
for (let y = 5; y < 11; y++) for (let x = 30; x < 44; x++) sim.set(x, y, WATER);

const STEPS = 80;
for (let i = 0; i < STEPS; i++) sim.step();

const out = [];
out.push(`# sand — headless snapshot`);
out.push(`# grid ${sim.width}x${sim.height}, seed ${sim.seed}, after ${STEPS} steps`);
out.push(`# legend:  '.' sand  '~' water  '#' wall  '=' wood  '*' fire  ':' smoke`);
out.push('');
out.push(render(sim));
out.push('');
out.push(`# tallies: sand=${sim.count(SAND)} water=${sim.count(WATER)} ` +
  `wood=${sim.count(WOOD)} fire=${sim.count(FIRE)} smoke=${sim.count(SMOKE)}`);

process.stdout.write(out.join('\n') + '\n');
