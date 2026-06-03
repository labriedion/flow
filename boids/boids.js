// boids.js — a flocking simulation after Craig Reynolds' 1986 "Boids".
//
// Each boid steers by three local rules, looking only at the neighbours inside
// its perception radius:
//   separation — steer away from neighbours that are too close
//   alignment  — steer towards the average heading of neighbours
//   cohesion   — steer towards the average position of neighbours
// No boid knows about the flock as a whole; the swirling, splitting, merging
// flock is entirely emergent. A uniform spatial-hash grid keeps neighbour
// lookups near O(n), so this stays smooth with thousands of boids.

import { PALETTES } from './palettes.js';

const TAU = Math.PI * 2;

export class Flock {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d', { alpha: false });
    this.dpr = Math.min(window.devicePixelRatio || 1, 2);

    // Tunable parameters (all live-editable from the UI).
    this.params = {
      count: 600,
      perception: 64,     // neighbour radius for alignment/cohesion (px)
      separation: 26,     // personal-space radius (px)
      sepWeight: 1.6,
      alignWeight: 1.0,
      cohWeight: 0.9,
      maxSpeed: 3.4,
      maxForce: 0.07,     // steering force cap (acceleration per frame)
      trail: 0.18,        // background fade per frame; higher = shorter trails
      size: 1.0,          // boid triangle scale
      showVision: false,
    };

    this.pointer = { x: 0, y: 0, active: false, mode: 0 }; // 1 attract, 2 repel
    this.running = true;
    this.paletteIndex = 0;
    this.palette = PALETTES[0];

    this.boids = [];
    this.grid = new Map();   // spatial hash: cell key -> array of boid indices
    this.cellSize = this.params.perception;

    this.resize();
    this.reseed();
  }

  // ---- Sizing -----------------------------------------------------------
  resize() {
    const { canvas } = this;
    const w = canvas.clientWidth || window.innerWidth;
    const h = canvas.clientHeight || window.innerHeight;
    canvas.width = Math.floor(w * this.dpr);
    canvas.height = Math.floor(h * this.dpr);
    this.w = canvas.width;
    this.h = canvas.height;
    this.hardClear();
  }

  get scaledSpeed() { return this.params.maxSpeed * this.dpr; }

  // ---- Population -------------------------------------------------------
  reseed() {
    this.boids = [];
    for (let i = 0; i < this.params.count; i++) this.boids.push(this._spawn());
    this.hardClear();
  }

  _spawn() {
    const angle = Math.random() * TAU;
    const speed = this.scaledSpeed * (0.5 + Math.random() * 0.5);
    return {
      x: Math.random() * this.w,
      y: Math.random() * this.h,
      vx: Math.cos(angle) * speed,
      vy: Math.sin(angle) * speed,
    };
  }

  setCount(n) {
    n = Math.max(1, Math.round(n));
    this.params.count = n;
    const b = this.boids;
    if (n < b.length) b.length = n;
    else while (b.length < n) b.push(this._spawn());
  }

  setPalette(i) {
    this.paletteIndex = i % PALETTES.length;
    this.palette = PALETTES[this.paletteIndex];
  }

  toggle() {
    this.running = !this.running;
    return this.running;
  }

  // ---- Spatial hash -----------------------------------------------------
  _key(cx, cy) { return cx * 73856093 ^ cy * 19349663; }

  _buildGrid() {
    // Cell size tracks the largest interaction radius so each boid only needs to
    // scan its own cell and the eight around it.
    this.cellSize = Math.max(8, this.params.perception) * this.dpr;
    const grid = this.grid;
    grid.clear();
    const inv = 1 / this.cellSize;
    for (let i = 0; i < this.boids.length; i++) {
      const b = this.boids[i];
      const cx = Math.floor(b.x * inv);
      const cy = Math.floor(b.y * inv);
      const key = this._key(cx, cy);
      let bucket = grid.get(key);
      if (!bucket) grid.set(key, (bucket = []));
      bucket.push(i);
    }
  }

  // ---- Simulation step --------------------------------------------------
  _step() {
    this._buildGrid();
    const b = this.boids;
    const p = this.params;
    const inv = 1 / this.cellSize;
    const perc = p.perception * this.dpr;
    const sep = p.separation * this.dpr;
    const perc2 = perc * perc;
    const sep2 = sep * sep;
    const maxSpeed = this.scaledSpeed;
    const maxForce = p.maxForce * this.dpr;

    for (let i = 0; i < b.length; i++) {
      const me = b[i];
      const cx = Math.floor(me.x * inv);
      const cy = Math.floor(me.y * inv);

      let alignX = 0, alignY = 0, alignN = 0;
      let cohX = 0, cohY = 0, cohN = 0;
      let sepX = 0, sepY = 0;

      for (let gx = cx - 1; gx <= cx + 1; gx++) {
        for (let gy = cy - 1; gy <= cy + 1; gy++) {
          const bucket = this.grid.get(this._key(gx, gy));
          if (!bucket) continue;
          for (let k = 0; k < bucket.length; k++) {
            const j = bucket[k];
            if (j === i) continue;
            const other = b[j];
            const dx = other.x - me.x;
            const dy = other.y - me.y;
            const d2 = dx * dx + dy * dy;
            if (d2 > perc2 || d2 === 0) continue;
            alignX += other.vx; alignY += other.vy; alignN++;
            cohX += other.x; cohY += other.y; cohN++;
            if (d2 < sep2) {
              // Push away, weighted by closeness (1/distance).
              const d = Math.sqrt(d2);
              sepX -= dx / d / d;
              sepY -= dy / d / d;
            }
          }
        }
      }

      let ax = 0, ay = 0;
      if (alignN > 0) {
        const s = steer(alignX / alignN, alignY / alignN, me, maxSpeed, maxForce);
        ax += s.x * p.alignWeight; ay += s.y * p.alignWeight;
      }
      if (cohN > 0) {
        const s = steer(cohX / cohN - me.x, cohY / cohN - me.y, me, maxSpeed, maxForce);
        ax += s.x * p.cohWeight; ay += s.y * p.cohWeight;
      }
      if (sepX !== 0 || sepY !== 0) {
        const s = steer(sepX, sepY, me, maxSpeed, maxForce);
        ax += s.x * p.sepWeight; ay += s.y * p.sepWeight;
      }

      // Pointer attraction / repulsion.
      if (this.pointer.active) {
        const dx = this.pointer.x - me.x;
        const dy = this.pointer.y - me.y;
        const d2 = dx * dx + dy * dy;
        const R = 220 * this.dpr;
        if (d2 < R * R && d2 > 0) {
          const sign = this.pointer.mode === 2 ? -1 : 1;
          const s = steer(dx * sign, dy * sign, me, maxSpeed, maxForce);
          ax += s.x * 1.5; ay += s.y * 1.5;
        }
      }

      me.vx += ax; me.vy += ay;

      // Clamp to the max speed, keeping a small minimum so nobody stalls.
      const sp = Math.hypot(me.vx, me.vy);
      if (sp > maxSpeed) { me.vx = (me.vx / sp) * maxSpeed; me.vy = (me.vy / sp) * maxSpeed; }
      else if (sp < maxSpeed * 0.25 && sp > 0) {
        const t = (maxSpeed * 0.25) / sp;
        me.vx *= t; me.vy *= t;
      }
    }

    // Integrate positions and wrap around the edges (a toroidal world).
    for (let i = 0; i < b.length; i++) {
      const me = b[i];
      me.x += me.vx; me.y += me.vy;
      if (me.x < 0) me.x += this.w; else if (me.x >= this.w) me.x -= this.w;
      if (me.y < 0) me.y += this.h; else if (me.y >= this.h) me.y -= this.h;
    }
  }

  // ---- Rendering --------------------------------------------------------
  _draw() {
    const ctx = this.ctx;
    // Fade the previous frame towards the background colour to leave trails.
    ctx.fillStyle = `rgba(${this.palette.bg.join(',')},${this.params.trail})`;
    ctx.fillRect(0, 0, this.w, this.h);

    const b = this.boids;
    const maxSpeed = this.scaledSpeed;
    const scale = this.params.size * this.dpr;
    const stops = this.palette.stops;

    if (this.params.showVision) {
      ctx.strokeStyle = `rgba(${this.palette.accent.join(',')},0.05)`;
      ctx.lineWidth = this.dpr;
      const perc = this.params.perception * this.dpr;
      ctx.beginPath();
      for (let i = 0; i < b.length; i += 7) {
        ctx.moveTo(b[i].x + perc, b[i].y);
        ctx.arc(b[i].x, b[i].y, perc, 0, TAU);
      }
      ctx.stroke();
    }

    for (let i = 0; i < b.length; i++) {
      const me = b[i];
      const sp = Math.hypot(me.vx, me.vy) || 1e-6;
      const angle = Math.atan2(me.vy, me.vx);
      // Colour by speed: blend across the palette's gradient stops.
      const t = Math.min(1, sp / maxSpeed);
      ctx.fillStyle = sampleGradient(stops, t);

      const len = (4 + 3 * t) * scale;   // faster boids draw a touch longer
      const wid = 2.1 * scale;
      const cos = me.vx / sp, sin = me.vy / sp;
      // A triangle: nose ahead, two tails behind.
      const nx = me.x + cos * len, ny = me.y + sin * len;
      ctx.beginPath();
      ctx.moveTo(nx, ny);
      ctx.lineTo(me.x - cos * len * 0.5 - sin * wid, me.y - sin * len * 0.5 + cos * wid);
      ctx.lineTo(me.x - cos * len * 0.5 + sin * wid, me.y - sin * len * 0.5 - cos * wid);
      ctx.closePath();
      ctx.fill();
    }
  }

  hardClear() {
    const ctx = this.ctx;
    ctx.fillStyle = `rgb(${this.palette.bg.join(',')})`;
    ctx.fillRect(0, 0, this.w, this.h);
  }

  // One animation frame.
  frame() {
    if (this.running) this._step();
    this._draw();
  }

  // A PNG data URL of the current canvas, for "Save".
  snapshot() {
    return this.canvas.toDataURL('image/png');
  }
}

// Steer from a desired direction towards it, capped by maxForce. Returns the
// steering vector (desired velocity at full speed, minus current velocity).
function steer(dirX, dirY, boid, maxSpeed, maxForce) {
  const len = Math.hypot(dirX, dirY);
  if (len === 0) return { x: 0, y: 0 };
  const dvx = (dirX / len) * maxSpeed - boid.vx;
  const dvy = (dirY / len) * maxSpeed - boid.vy;
  const fl = Math.hypot(dvx, dvy);
  if (fl > maxForce) return { x: (dvx / fl) * maxForce, y: (dvy / fl) * maxForce };
  return { x: dvx, y: dvy };
}

// Sample a CSS colour at position t in [0,1] across an array of "r,g,b" stops.
function sampleGradient(stops, t) {
  const n = stops.length - 1;
  const f = Math.max(0, Math.min(0.9999, t)) * n;
  const i = Math.floor(f);
  const frac = f - i;
  const a = stops[i], c = stops[i + 1] || stops[i];
  const r = Math.round(a[0] + (c[0] - a[0]) * frac);
  const g = Math.round(a[1] + (c[1] - a[1]) * frac);
  const b = Math.round(a[2] + (c[2] - a[2]) * frac);
  return `rgb(${r},${g},${b})`;
}
