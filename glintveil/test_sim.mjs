// test_sim.mjs — a self-contained Node smoke test for the glintveil field.
//
// No test framework, no dependencies: just node:assert and the pure sim module.
// It asserts the reaction–diffusion invariants, exits non-zero on the first
// failure, and prints a tidy pass summary. Run from the repo root with:
//
//   node glintveil/test_sim.mjs

import assert from 'node:assert/strict';
import { Field, PRESETS } from './sim.js';

let passed = 0;
function test(name, fn) {
  fn();
  passed++;
  console.log(`  ok  ${name}`);
}

// ---- silence is a fixed point ------------------------------------------
test('the uniform field (u=1, v=0) is exactly stationary', () => {
  const f = new Field(48, 32, 1);
  for (let i = 0; i < 50; i++) f.step();
  const s = f.stats();
  assert.equal(s.vMax, 0, 'no v appears from nothing');
  assert.equal(s.uMin, 1, 'u stays pinned at 1');
});

// ---- determinism: same seed + same pokes => identical fields ------------
test('two Fields with the same seed and pokes evolve identically', () => {
  const build = () => {
    const f = new Field(64, 48, 424242);
    f.seedNoise(8);
    f.poke(30, 20, 5);
    return f;
  };
  const a = build();
  const b = build();
  for (let i = 0; i < 400; i++) { a.step(); b.step(); }
  assert.deepEqual(Array.from(a.u), Array.from(b.u), 'u grids match after N steps');
  assert.deepEqual(Array.from(a.v), Array.from(b.v), 'v grids match after N steps');
});

// ---- a poke grows into something bigger than itself ---------------------
test('one poke spreads structure far beyond its own footprint', () => {
  const f = new Field(96, 96, 7);
  f.poke(48, 48, 4);
  const before = f.stats().active;
  for (let i = 0; i < 3000; i++) f.step();
  const after = f.stats().active;
  assert.ok(after > before * 3,
    `pattern grew (${before} active cells -> ${after})`);
  // ...and it reached well outside the poke's bounding box.
  let farthest = 0;
  for (let y = 0; y < f.height; y++) {
    for (let x = 0; x < f.width; x++) {
      if (f.v[y * f.width + x] > 0.1) {
        const d = Math.max(Math.abs(x - 48), Math.abs(y - 48));
        if (d > farthest) farthest = d;
      }
    }
  }
  assert.ok(farthest > 12, `structure reached ${farthest} cells from the poke`);
});

// ---- the lattice is a torus ----------------------------------------------
test('patterns cross the boundary: the field has no edge', () => {
  const f = new Field(64, 64, 3);
  const colCells = (x, eps) => {
    let n = 0;
    for (let y = 0; y < f.height; y++) {
      if (f.v[y * f.width + x] > eps) n++;
    }
    return n;
  };
  // A poke hugging the left edge (x 0..4) — the far column starts silent,
  // so anything that shows up there later had to *travel*.
  f.poke(2, 32, 2);
  assert.equal(colCells(f.width - 1, 0), 0, 'far column starts silent');
  for (let i = 0; i < 1200; i++) f.step();
  // The pattern's front could not have crawled 59 columns rightward in this
  // time (see the growth test); reaching the far column means it stepped
  // across the wrap from column 0 — the seam diffuses like anywhere else.
  assert.ok(colCells(f.width - 1, 0.05) > 0, 'v crossed the wrap onto the far column');
  // Wildly out-of-range pokes wrap too, instead of throwing or vanishing —
  // checked on a fresh, silent field so the landing actually proves it.
  const g = new Field(32, 32, 4);
  g.poke(-1000, 99999, 2);
  assert.ok(g.stats().vMax > 0, 'off-grid poke landed somewhere on the torus');
});

// ---- the field never blows up --------------------------------------------
test('u and v stay finite and inside [0,1] under every preset', () => {
  for (const [key, p] of Object.entries(PRESETS)) {
    const f = new Field(48, 48, 11);
    f.feed = p.feed;
    f.kill = p.kill;
    f.seedNoise(6);
    for (let i = 0; i < 500; i++) f.step();
    const s = f.stats();
    assert.ok(Number.isFinite(s.vMean), `${key}: field is finite`);
    assert.ok(s.uMin >= 0 && s.uMax <= 1, `${key}: u within [0,1]`);
    assert.ok(s.vMin >= 0 && s.vMax <= 1, `${key}: v within [0,1]`);
  }
});

// ---- clear and erase return to the quiet fixed point ---------------------
test('clear() and erase() restore the stationary state', () => {
  const f = new Field(40, 40, 5);
  f.seedNoise(10);
  for (let i = 0; i < 200; i++) f.step();
  f.clear();
  let s = f.stats();
  assert.equal(s.vMax, 0, 'clear() removed every trace of v');
  assert.equal(s.uMin, 1, 'clear() restored u everywhere');
  f.poke(20, 20, 5);
  f.erase(20, 20, 8); // erase with a wider brush than the poke
  s = f.stats();
  assert.equal(s.vMax, 0, 'erase() wiped the poked disc');
});

// ---- the terminal view holds its shape ------------------------------------
test('ascii() renders the requested frame from the charset', () => {
  const f = new Field(64, 48, 9);
  f.seedNoise(8);
  for (let i = 0; i < 300; i++) f.step();
  const frame = f.ascii(40, 20);
  const lines = frame.split('\n');
  assert.equal(lines.length, 20, '20 rows');
  assert.ok(lines.every((l) => l.length === 40), 'every row is 40 chars');
  const charset = ' .:-=+*#%@';
  assert.ok([...frame.replace(/\n/g, '')].every((ch) => charset.includes(ch)),
    'only charset characters appear');
  assert.ok([...frame].some((ch) => ch !== ' ' && ch !== '\n'),
    'the pattern actually shows up');
});

console.log(`\nAll ${passed} glintveil checks passed.`);
