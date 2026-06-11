// sim.js — a Gray–Scott reaction–diffusion field, as a pure script.
//
// This is the loom-proposed mission `glintveil` (seed 7002): a lattice of
// coupled springs whose one local rule is "react and diffuse with the chemical
// beside you". The spring reading is literal — the diffusion term is a Hooke
// coupling, every cell pulled toward the average of its neighbours — and the
// reaction is the two-chemical Gray–Scott scheme:
//
//   u' = Du·∇²u − u·v² + f·(1 − u)        u is fed in everywhere
//   v' = Dv·∇²v + u·v² − (f + k)·v        v eats u and is killed off
//
// No cell knows anything beyond its eight neighbours, yet spots split like
// cells, stripes weave into fingerprints and coral fronts crawl — which
// pattern falls out is decided entirely by the feed/kill pair.
//
// NOTHING in here touches the DOM or a canvas, on purpose: the field is a
// plain object you can spin up under Node and unit-test (see test_sim.mjs).
// The renderer lives in main.js and only ever reads the grids.

// ---- Presets --------------------------------------------------------------
// Named feed/kill pairs from Pearson's classification of the Gray–Scott
// parameter plane. Tiny nudges to f or k move you between regimes — the whole
// "phase diagram in two knobs" is half the show.
const PRESETS = {
  coral:    { name: 'Coral',    feed: 0.0545, kill: 0.0620 },
  mitosis:  { name: 'Mitosis',  feed: 0.0367, kill: 0.0649 },
  maze:     { name: 'Maze',     feed: 0.0290, kill: 0.0570 },
  solitons: { name: 'Solitons', feed: 0.0300, kill: 0.0620 },
  worms:    { name: 'Worms',    feed: 0.0780, kill: 0.0610 },
  waves:    { name: 'Waves',    feed: 0.0140, kill: 0.0450 },
};

const DEFAULT_PRESET = 'coral';

// Diffusion rates for the 9-point Laplacian below, the classic stable pair.
// u must out-diffuse v (the activator hoards, the substrate spreads) or no
// pattern forms at all — Turing's whole trick in one inequality.
const DU = 0.2097;
const DV = 0.105;

// A tiny seedable PRNG (mulberry32), same as sand's. Two Fields given the same
// seed and the same pokes evolve bit-for-bit identically — which is exactly
// what the determinism test leans on.
function mulberry32(seed) {
  let a = seed >>> 0;
  return function () {
    a |= 0;
    a = (a + 0x6d2b79f5) | 0;
    let t = Math.imul(a ^ (a >>> 15), 1 | a);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

class Field {
  constructor(width = 256, height = 192, seed = 1) {
    this.width = width | 0;
    this.height = height | 0;
    this.seed = seed >>> 0;
    this.rng = mulberry32(this.seed);

    const n = this.width * this.height;
    this.u = new Float32Array(n).fill(1); // the fed substrate, 1 everywhere
    this.v = new Float32Array(n);         // the patterning chemical, 0 until poked
    this.un = new Float32Array(n);        // back buffers — every cell updates
    this.vn = new Float32Array(n);        // from the same frozen frame

    const p = PRESETS[DEFAULT_PRESET];
    this.feed = p.feed;
    this.kill = p.kill;
    this.tick = 0;
  }

  // ---- Grid access --------------------------------------------------------
  // The lattice is a torus: every coordinate wraps, so there is no edge for a
  // pattern to die against and pokes anywhere (even far off-grid) are safe.
  index(x, y) {
    const w = this.width, h = this.height;
    return (((y % h) + h) % h) * w + (((x % w) + w) % w);
  }

  // ---- The one local rule -------------------------------------------------
  step() {
    const { width: w, height: h, u, v, un, vn, feed, kill } = this;
    for (let y = 0; y < h; y++) {
      const yN = (y === 0 ? h - 1 : y - 1) * w;
      const yS = (y === h - 1 ? 0 : y + 1) * w;
      const yC = y * w;
      for (let x = 0; x < w; x++) {
        const xW = x === 0 ? w - 1 : x - 1;
        const xE = x === w - 1 ? 0 : x + 1;
        const i = yC + x;

        // 9-point Laplacian: the spring coupling toward the neighbours.
        // Weights 0.2 (edge) / 0.05 (corner) sum to 1 against the centre.
        const lapU =
          0.2 * (u[yC + xW] + u[yC + xE] + u[yN + x] + u[yS + x]) +
          0.05 * (u[yN + xW] + u[yN + xE] + u[yS + xW] + u[yS + xE]) -
          u[i];
        const lapV =
          0.2 * (v[yC + xW] + v[yC + xE] + v[yN + x] + v[yS + x]) +
          0.05 * (v[yN + xW] + v[yN + xE] + v[yS + xW] + v[yS + xE]) -
          v[i];

        // The reaction: v eats u in proportion to u·v², u is fed back in,
        // v is killed off. That's the entire physics.
        const uvv = u[i] * v[i] * v[i];
        let nu = u[i] + DU * lapU - uvv + feed * (1 - u[i]);
        let nv = v[i] + DV * lapV + uvv - (feed + kill) * v[i];

        // Clamp to [0,1] so a wild feed/kill slider can't blow the field up.
        un[i] = nu < 0 ? 0 : nu > 1 ? 1 : nu;
        vn[i] = nv < 0 ? 0 : nv > 1 ? 1 : nv;
      }
    }
    // Swap buffers: the new frame becomes the one everyone reads next step.
    this.u = un; this.un = u;
    this.v = vn; this.vn = v;
    this.tick++;
  }

  // ---- Poking -------------------------------------------------------------
  // Splash the patterning chemical into a disc. This is the mouse's verb: a
  // poke is a seed, and what grows from it is the field's business.
  poke(cx, cy, radius = 4, amount = 1) {
    const r = Math.max(0, radius | 0);
    for (let dy = -r; dy <= r; dy++) {
      for (let dx = -r; dx <= r; dx++) {
        if (dx * dx + dy * dy > r * r) continue;
        const i = this.index(cx + dx, cy + dy);
        this.v[i] = Math.min(1, this.v[i] + amount);
        this.u[i] = Math.max(0, this.u[i] - amount * 0.5);
      }
    }
  }

  // Reset a disc back to the quiet fixed point (u=1, v=0) — the eraser.
  erase(cx, cy, radius = 4) {
    const r = Math.max(0, radius | 0);
    for (let dy = -r; dy <= r; dy++) {
      for (let dx = -r; dx <= r; dx++) {
        if (dx * dx + dy * dy > r * r) continue;
        const i = this.index(cx + dx, cy + dy);
        this.u[i] = 1;
        this.v[i] = 0;
      }
    }
  }

  // Back to the uniform fixed point everywhere. Nothing grows from silence:
  // u=1, v=0 is exactly stationary under the rule (the tests prove it).
  clear() {
    this.u.fill(1);
    this.v.fill(0);
    this.tick = 0;
  }

  // Sprinkle a handful of seeds from the field's own PRNG — deterministic,
  // so reseeding a seeded Field is as reproducible as everything else.
  seedNoise(spots = 12) {
    for (let s = 0; s < spots; s++) {
      const x = (this.rng() * this.width) | 0;
      const y = (this.rng() * this.height) | 0;
      this.poke(x, y, 2 + ((this.rng() * 3) | 0));
    }
  }

  // ---- Inspection (tests and the headless artifact) -----------------------
  stats() {
    let vMin = Infinity, vMax = -Infinity, uMin = Infinity, uMax = -Infinity;
    let active = 0, vSum = 0;
    for (let i = 0; i < this.v.length; i++) {
      const uv = this.u[i], vv = this.v[i];
      if (vv < vMin) vMin = vv;
      if (vv > vMax) vMax = vv;
      if (uv < uMin) uMin = uv;
      if (uv > uMax) uMax = uv;
      if (vv > 0.1) active++;
      vSum += vv;
    }
    return { uMin, uMax, vMin, vMax, active, vMean: vSum / this.v.length };
  }

  // Downsample v into a character frame — the terminal's view of the veil.
  ascii(cols = 96, rows = 48, charset = ' .:-=+*#%@') {
    const lines = [];
    for (let r = 0; r < rows; r++) {
      let line = '';
      for (let c = 0; c < cols; c++) {
        // average the v values inside this character's patch of field
        const x0 = Math.floor((c * this.width) / cols);
        const x1 = Math.max(x0 + 1, Math.floor(((c + 1) * this.width) / cols));
        const y0 = Math.floor((r * this.height) / rows);
        const y1 = Math.max(y0 + 1, Math.floor(((r + 1) * this.height) / rows));
        let sum = 0, count = 0;
        for (let y = y0; y < y1; y++) {
          for (let x = x0; x < x1; x++) { sum += this.v[y * this.width + x]; count++; }
        }
        // v rarely exceeds ~0.5; stretch so patterns use the whole ramp
        const t = Math.min(1, (sum / count) * 2.5);
        line += charset[Math.min(charset.length - 1, (t * charset.length) | 0)];
      }
      lines.push(line);
    }
    return lines.join('\n');
  }
}

// Node (the tests and the headless artifact) loads this very file through
// require(); the browser just reads the declarations off the shared script
// scope. Deliberately no module syntax — module scripts refuse to load from
// file://, and double-click-to-run is house law.
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { PRESETS, DEFAULT_PRESET, Field };
}
