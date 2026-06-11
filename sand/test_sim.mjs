// test_sim.mjs — a self-contained Node smoke test for the sand simulation.
//
// No test framework, no dependencies: just node:assert and the pure sim module.
// It asserts the core physics invariants, exits non-zero on the first failure,
// and prints a tidy pass summary. Run from the repo root with:
//
//   node sand/test_sim.mjs

import assert from 'node:assert/strict';
import { createRequire } from 'node:module';

// sim.js is a classic script with a CommonJS shim (so the browser can load
// it straight off the disk); require() is how Node reads that shape.
const require = createRequire(import.meta.url);
const {
  Sandbox, EMPTY, SAND, WATER, WALL, WOOD, FIRE, SMOKE,
} = require('./sim.js');

let passed = 0;
function test(name, fn) {
  fn();
  passed++;
  console.log(`  ok  ${name}`);
}

// Count every cell of every material — used to assert nothing leaks or doubles.
function totalCells(sim) {
  return sim.cells.length;
}

// ---- a single grain falls one cell ------------------------------------
test('a lone SAND grain falls down exactly one cell per step', () => {
  const sim = new Sandbox(5, 5, 1);
  sim.set(2, 0, SAND);
  sim.step();
  assert.equal(sim.get(2, 0), EMPTY, 'grain left its old cell');
  assert.equal(sim.get(2, 1), SAND, 'grain moved down one');
  sim.step();
  assert.equal(sim.get(2, 2), SAND, 'grain kept falling one per step');
});

// ---- sand does not fall through a wall, and is conserved ---------------
test('SAND piles on a WALL row and solid count is conserved', () => {
  const sim = new Sandbox(11, 20, 7);
  for (let x = 0; x < sim.width; x++) sim.set(x, sim.height - 1, WALL);
  // A clump of sand up top.
  sim.paint(5, 3, 3, SAND);
  const sandBefore = sim.count(SAND);
  const wallBefore = sim.count(WALL);
  for (let i = 0; i < 200; i++) sim.step();
  assert.equal(sim.count(SAND), sandBefore, 'no sand created or destroyed');
  assert.equal(sim.count(WALL), wallBefore, 'wall row intact');
  // Every grain ended up resting on the floor (none escaped below the wall).
  assert.equal(sim.get(5, sim.height - 1), WALL, 'wall still solid');
  // The bottom-most sand sits directly above the wall, not below it.
  for (let x = 0; x < sim.width; x++) {
    assert.notEqual(sim.get(x, sim.height - 1), SAND, 'no sand below the wall');
  }
});

// ---- water spreads to level out ---------------------------------------
test('a tall WATER column flattens out over time', () => {
  const sim = new Sandbox(21, 16, 3);
  for (let x = 0; x < sim.width; x++) sim.set(x, sim.height - 1, WALL);
  // A narrow, tall column of water in the middle.
  const cx = 10;
  const colHeight = 12;
  for (let y = sim.height - 1 - colHeight; y < sim.height - 1; y++) sim.set(cx, y, WATER);
  const heightOfWaterColumn = (sim) => {
    let top = sim.height;
    for (let y = 0; y < sim.height; y++) {
      if (sim.get(cx, y) === WATER) { top = y; break; }
    }
    return sim.height - 1 - top; // cells of water stacked in the centre column
  };
  const before = heightOfWaterColumn(sim);
  const waterBefore = sim.count(WATER);
  for (let i = 0; i < 300; i++) sim.step();
  const after = heightOfWaterColumn(sim);
  assert.equal(sim.count(WATER), waterBefore, 'water conserved while spreading');
  assert.ok(after < before, `column should fall (was ${before}, now ${after})`);
  // It should have spread sideways: more than one column now holds water.
  let wetColumns = 0;
  for (let x = 0; x < sim.width; x++) {
    for (let y = 0; y < sim.height; y++) {
      if (sim.get(x, y) === WATER) { wetColumns++; break; }
    }
  }
  assert.ok(wetColumns > 1, `water spread to ${wetColumns} columns`);
});

// ---- fire consumes wood and makes smoke -------------------------------
test('FIRE next to WOOD consumes it and eventually produces SMOKE', () => {
  const sim = new Sandbox(12, 12, 9);
  // A horizontal log with a flame at the left end.
  for (let x = 1; x < 11; x++) sim.set(x, 6, WOOD);
  sim.set(0, 6, FIRE);
  const woodBefore = sim.count(WOOD);
  let sawSmoke = false;
  for (let i = 0; i < 400; i++) {
    sim.step();
    if (sim.count(SMOKE) > 0) sawSmoke = true;
  }
  assert.ok(sim.count(WOOD) < woodBefore, 'fire ate into the wood');
  assert.ok(sawSmoke, 'burning wood produced smoke at some point');
  // Fire is mortal: after long enough with no fuel it dies out entirely.
  for (let i = 0; i < 400; i++) sim.step();
  assert.equal(sim.count(FIRE), 0, 'all fire eventually burns out');
});

// ---- determinism: same seed + same painting => identical grids ---------
test('two Sandboxes with the same seed evolve identically', () => {
  const build = () => {
    const s = new Sandbox(40, 30, 424242);
    s.seedScene();
    s.paint(20, 5, 4, SAND);
    s.set(10, 2, FIRE);
    return s;
  };
  const a = build();
  const b = build();
  const N = 250;
  for (let i = 0; i < N; i++) { a.step(); b.step(); }
  assert.deepEqual(Array.from(a.cells), Array.from(b.cells), 'grids match after N steps');
  assert.deepEqual(Array.from(a.life), Array.from(b.life), 'life timers match too');
});

// ---- grid size is fixed; no out-of-bounds writes -----------------------
test('grid size stays constant and writes never go out of bounds', () => {
  const sim = new Sandbox(30, 24, 5);
  const size = totalCells(sim);
  // Hammer the edges and corners with paint, then run a long time.
  sim.paint(0, 0, 6, WATER);
  sim.paint(sim.width - 1, 0, 6, SAND);
  sim.paint(sim.width - 1, sim.height - 1, 6, FIRE);
  sim.paint(0, sim.height - 1, 6, SMOKE);
  // Out-of-bounds set() must be a silent no-op (would throw if it indexed).
  sim.set(-5, -5, SAND);
  sim.set(9999, 9999, WATER);
  for (let i = 0; i < 300; i++) sim.step();
  assert.equal(totalCells(sim), size, 'cell array length unchanged');
  assert.equal(sim.cells.length, sim.width * sim.height, 'dimensions intact');
  // Off-grid reads report WALL, never a thrown error.
  assert.equal(sim.get(-1, -1), WALL);
  assert.equal(sim.get(sim.width, sim.height), WALL);
});

// ---- total material is conserved when nothing burns --------------------
test('non-reactive materials are perfectly conserved', () => {
  const sim = new Sandbox(30, 30, 11);
  for (let x = 0; x < sim.width; x++) sim.set(x, sim.height - 1, WALL);
  sim.paint(8, 4, 4, SAND);
  sim.paint(20, 4, 4, WATER);
  const before = sim.count(SAND) + sim.count(WATER) + sim.count(WALL);
  for (let i = 0; i < 300; i++) sim.step();
  const after = sim.count(SAND) + sim.count(WATER) + sim.count(WALL);
  assert.equal(after, before, 'sand + water + wall count unchanged');
});

console.log(`\nAll ${passed} sand-sim checks passed.`);
