// sim.js — a falling-sand / cellular-physics playground, as a pure script.
//
// This is `cellular` grown a second dimension and given a handful of materials
// that fall, flow, burn and smoulder. The whole world is one flat `Uint8Array`
// of material ids, one byte per cell, plus a parallel `Uint8Array` of "life"
// timers that fire and smoke count down. There are no rules about the world as a
// whole — every cell only ever looks at its immediate neighbours, and the messy,
// piling, sloshing behaviour you see is entirely emergent from those local moves.
//
// NOTHING in here touches the DOM or a canvas, on purpose: the simulation is a
// plain object you can spin up under Node and unit-test (see test_sim.mjs). The
// renderer lives in sand.js and only ever reads the grid.

// ---- Materials ----------------------------------------------------------
// Ids are small integers so the grid can be a Uint8Array. Each material carries
// a display colour (the renderer's only interest) and a couple of physics tags:
//   density  — heavier things sink through lighter ones (SAND through WATER).
//   solid    — counts as a fixed obstacle for falling things.
// EMPTY is id 0 so a freshly-zeroed grid is already empty.
const MATERIALS = {
  EMPTY: { id: 0, name: 'Empty', color: [7, 9, 16], density: 0, solid: false },
  SAND:  { id: 1, name: 'Sand',  color: [222, 184, 110], density: 3, solid: true },
  WATER: { id: 2, name: 'Water', color: [64, 130, 210], density: 1, solid: false },
  WALL:  { id: 3, name: 'Wall',  color: [120, 128, 145], density: 9, solid: true },
  WOOD:  { id: 4, name: 'Wood',  color: [134, 92, 54],  density: 9, solid: true },
  FIRE:  { id: 5, name: 'Fire',  color: [240, 120, 36], density: 0, solid: false },
  SMOKE: { id: 6, name: 'Smoke', color: [70, 72, 82],   density: 0, solid: false },
};

// Reverse lookup id -> material, handy for the renderer and for debugging.
const BY_ID = (() => {
  const arr = [];
  for (const m of Object.values(MATERIALS)) arr[m.id] = m;
  return arr;
})();

// Bare ids, the form the engine actually shuffles around.
const EMPTY = MATERIALS.EMPTY.id;
const SAND  = MATERIALS.SAND.id;
const WATER = MATERIALS.WATER.id;
const WALL  = MATERIALS.WALL.id;
const WOOD  = MATERIALS.WOOD.id;
const FIRE  = MATERIALS.FIRE.id;
const SMOKE = MATERIALS.SMOKE.id;

// How long (in ticks) a freshly-lit fire or puff of smoke lasts before it dies.
const FIRE_LIFE = 70;
const SMOKE_LIFE = 90;

// A tiny seedable PRNG (mulberry32). The whole point of seeding it is that two
// Sandboxes given the same seed and the same painting evolve bit-for-bit
// identically — which is exactly what the determinism test leans on.
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

class Sandbox {
  constructor(width = 200, height = 150, seed = 1) {
    this.width = width | 0;
    this.height = height | 0;
    this.seed = seed >>> 0;
    this.rng = mulberry32(this.seed);

    const n = this.width * this.height;
    this.cells = new Uint8Array(n);   // material id per cell
    this.life = new Uint8Array(n);    // countdown timer for FIRE / SMOKE
    // A scratch flag so a cell that already moved this tick isn't moved twice as
    // the scan sweeps over its new home. Cleared at the top of every step().
    this.moved = new Uint8Array(n);
    this.tick = 0;
  }

  // ---- Grid access ------------------------------------------------------
  inBounds(x, y) {
    return x >= 0 && x < this.width && y >= 0 && y < this.height;
  }

  idx(x, y) { return y * this.width + x; }

  get(x, y) {
    if (!this.inBounds(x, y)) return WALL; // the world is walled-in; off-grid reads
    return this.cells[y * this.width + x]; // as WALL so nothing falls out the edges
  }

  set(x, y, material) {
    if (!this.inBounds(x, y)) return; // never write out of bounds
    const i = y * this.width + x;
    this.cells[i] = material;
    // Fire and smoke get a (slightly jittered) lifetime; everything else is 0.
    if (material === FIRE) this.life[i] = FIRE_LIFE + ((this.rng() * 20) | 0);
    else if (material === SMOKE) this.life[i] = SMOKE_LIFE + ((this.rng() * 30) | 0);
    else this.life[i] = 0;
  }

  // Paint a filled disc of `material` centred on (cx, cy). Used by the mouse.
  paint(cx, cy, radius, material) {
    const r2 = radius * radius;
    const r = Math.ceil(radius);
    for (let dy = -r; dy <= r; dy++) {
      for (let dx = -r; dx <= r; dx++) {
        if (dx * dx + dy * dy > r2) continue;
        this.set(cx + dx, cy + dy, material);
      }
    }
  }

  clear() {
    this.cells.fill(EMPTY);
    this.life.fill(0);
    this.moved.fill(0);
    this.tick = 0;
  }

  // Reset to empty and re-seed the RNG, so a reset world is reproducible.
  reset(seed = this.seed) {
    this.seed = seed >>> 0;
    this.rng = mulberry32(this.seed);
    this.clear();
  }

  // Drop a "starter" scene: a floor, a couple of walls, a hopper of sand and a
  // pool of water. Deterministic given the seed.
  seedScene() {
    this.clear();
    const W = this.width, H = this.height;
    // A solid floor and side walls.
    for (let x = 0; x < W; x++) this.set(x, H - 1, WALL);
    for (let y = 0; y < H; y++) { this.set(0, y, WALL); this.set(W - 1, y, WALL); }
    // A wooden shelf to burn.
    const shelfY = (H * 0.55) | 0;
    for (let x = (W * 0.1) | 0; x < (W * 0.45) | 0; x++) this.set(x, shelfY, WOOD);
    // A block of sand up top, ready to pour.
    this.paint((W * 0.28) | 0, (H * 0.18) | 0, Math.max(4, (W * 0.06) | 0), SAND);
    // A reservoir of water to slosh.
    for (let y = (H * 0.2) | 0; y < (H * 0.32) | 0; y++)
      for (let x = (W * 0.62) | 0; x < (W * 0.85) | 0; x++) this.set(x, y, WATER);
  }

  // ---- Physics ----------------------------------------------------------
  // Swap two cells (material + life), and flag both as having moved this tick.
  _swap(i, j) {
    const c = this.cells; const l = this.life;
    const tc = c[i]; c[i] = c[j]; c[j] = tc;
    const tl = l[i]; l[i] = l[j]; l[j] = tl;
    this.moved[i] = 1; this.moved[j] = 1;
  }

  // True if a falling material at `from` may displace whatever is at (x,y):
  // empty cells always, and lighter non-solid fluids if `from` is denser.
  _canDisplace(fromMat, x, y) {
    if (!this.inBounds(x, y)) return false;
    const j = y * this.width + x;
    if (this.moved[j]) return false;
    const target = this.cells[j];
    if (target === EMPTY) return true;
    const tm = BY_ID[target];
    // Sink through lighter fluids (e.g. SAND through WATER), never through solids.
    return !tm.solid && BY_ID[fromMat].density > tm.density;
  }

  // One physics tick. We sweep bottom-up so a grain that falls doesn't get
  // re-considered on the same row it landed in, and we flip the left/right scan
  // direction each row+tick so neither side of a pile is systematically
  // favoured (the classic source of falling-sand "lean").
  step() {
    const W = this.width, H = this.height;
    this.moved.fill(0);

    for (let y = H - 1; y >= 0; y--) {
      // Alternate horizontal scan direction to remove directional bias.
      const flip = ((y + this.tick) & 1) === 0;
      for (let xi = 0; xi < W; xi++) {
        const x = flip ? xi : W - 1 - xi;
        const i = y * W + x;
        if (this.moved[i]) continue;
        const mat = this.cells[i];
        switch (mat) {
          case SAND:  this._stepSand(x, y, i); break;
          case WATER: this._stepWater(x, y, i); break;
          case FIRE:  this._stepFire(x, y, i); break;
          case SMOKE: this._stepSmoke(x, y, i); break;
          // EMPTY, WALL, WOOD do nothing on their own.
        }
      }
    }
    this.tick++;
  }

  // SAND: fall straight down; else slide diagonally down; sinks through water.
  _stepSand(x, y, i) {
    if (this._canDisplace(SAND, x, y + 1)) { this._swap(i, this.idx(x, y + 1)); return; }
    // Pick a diagonal first, flipping by RNG so neither side is preferred.
    const left = this.rng() < 0.5;
    const d1 = left ? -1 : 1, d2 = -d1;
    if (this._canDisplace(SAND, x + d1, y + 1)) { this._swap(i, this.idx(x + d1, y + 1)); return; }
    if (this._canDisplace(SAND, x + d2, y + 1)) { this._swap(i, this.idx(x + d2, y + 1)); return; }
  }

  // WATER: fall; else slide diagonally down; else flow sideways to level out.
  _stepWater(x, y, i) {
    if (this._canDisplace(WATER, x, y + 1)) { this._swap(i, this.idx(x, y + 1)); return; }
    const left = this.rng() < 0.5;
    const d1 = left ? -1 : 1, d2 = -d1;
    if (this._canDisplace(WATER, x + d1, y + 1)) { this._swap(i, this.idx(x + d1, y + 1)); return; }
    if (this._canDisplace(WATER, x + d2, y + 1)) { this._swap(i, this.idx(x + d2, y + 1)); return; }
    // Sideways spread (only into empty cells) so a column flattens out.
    if (this._isEmptyCell(x + d1, y)) { this._swap(i, this.idx(x + d1, y)); return; }
    if (this._isEmptyCell(x + d2, y)) { this._swap(i, this.idx(x + d2, y)); return; }
  }

  _isEmptyCell(x, y) {
    if (!this.inBounds(x, y)) return false;
    const j = y * this.width + x;
    return this.cells[j] === EMPTY && !this.moved[j];
  }

  // FIRE: ignite neighbouring WOOD, prefer to rise, and burn down to SMOKE/EMPTY.
  _stepFire(x, y, i) {
    // Spread to neighbouring wood (all eight directions, probabilistically so a
    // log doesn't flash over in one tick). We also note whether we're touching
    // any fuel: a flame sitting against wood stays put to keep burning it rather
    // than drifting off into the air, so a struck log reliably catches.
    let touchingWood = false;
    for (let dy = -1; dy <= 1; dy++) {
      for (let dx = -1; dx <= 1; dx++) {
        if (dx === 0 && dy === 0) continue;
        if (this.get(x + dx, y + dy) !== WOOD) continue;
        touchingWood = true;
        if (this.rng() < 0.28) {
          this.set(x + dx, y + dy, FIRE);
          this.moved[this.idx(x + dx, y + dy)] = 1;
        }
      }
    }
    // Age the flame.
    if (this.life[i] > 0) this.life[i]--;
    if (this.life[i] === 0) {
      // Burn out: usually leave a puff of smoke, sometimes just vanish.
      this.set(x, y, this.rng() < 0.7 ? SMOKE : EMPTY);
      this.moved[i] = 1;
      return;
    }
    // Flames lick upward when there's room — but only once they've no fuel left
    // to cling to, so fire spreads through wood before floating away as smoke.
    if (!touchingWood && this._isEmptyCell(x, y - 1) && this.rng() < 0.5) {
      this._swap(i, this.idx(x, y - 1));
    }
  }

  // SMOKE: rise, drift sideways, and thin out to nothing over time.
  _stepSmoke(x, y, i) {
    if (this.life[i] > 0) this.life[i]--;
    if (this.life[i] === 0) { this.set(x, y, EMPTY); this.moved[i] = 1; return; }
    // Rise if there's space above.
    if (this._isEmptyCell(x, y - 1)) { this._swap(i, this.idx(x, y - 1)); return; }
    // Otherwise drift diagonally up, or sideways — whichever is open.
    const left = this.rng() < 0.5;
    const d = left ? -1 : 1;
    if (this._isEmptyCell(x + d, y - 1)) { this._swap(i, this.idx(x + d, y - 1)); return; }
    if (this._isEmptyCell(x + d, y)) { this._swap(i, this.idx(x + d, y)); return; }
  }

  // ---- Diagnostics (used by tests) --------------------------------------
  // Count cells matching a material id across the whole grid.
  count(material) {
    let n = 0;
    const c = this.cells;
    for (let k = 0; k < c.length; k++) if (c[k] === material) n++;
    return n;
  }
}

// Node (the tests and the headless artifact) loads this very file through
// require(); the browser just reads the declarations off the shared script
// scope. Deliberately no module syntax — module scripts refuse to load from
// file://, and double-click-to-run is house law.
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    MATERIALS, BY_ID, EMPTY, SAND, WATER, WALL, WOOD, FIRE, SMOKE, Sandbox,
  };
}
