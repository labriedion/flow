// flowfield.js — the simulation engine.
// Particles drift across the canvas, sampling a Perlin/simplex noise field to
// pick a heading each step. The field slowly evolves through a third noise
// dimension (time), so the whole picture breathes. Trails are produced by
// fading the previous frame rather than clearing it.

import { SimplexNoise } from './noise.js';
import { PALETTES, buildRamp } from './palettes.js';

const TAU = Math.PI * 2;

export class FlowField {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d', { alpha: false });
    this.particles = [];
    this.running = true;
    this.z = 0; // time dimension into the noise field
    this.pointer = { x: 0, y: 0, active: false, mode: 0 }; // 0 none,1 attract,2 repel

    // Tunable parameters (mutated by the UI).
    this.params = {
      count: 1400,
      speed: 1.6,
      noiseScale: 0.0016,
      curl: 2.4,        // how many TAU rotations the noise maps onto
      timeWarp: 0.0009, // how fast the field evolves
      fade: 0.045,      // trail persistence (lower = longer trails)
      lineWidth: 1.1,
      paletteIndex: 0,
      pointerForce: 90,
    };

    this.setPalette(0, true);
    this.resize();
  }

  setPalette(index, skipFill = false) {
    this.params.paletteIndex = ((index % PALETTES.length) + PALETTES.length) % PALETTES.length;
    this.palette = PALETTES[this.params.paletteIndex];
    this.ramp = buildRamp(this.palette, 1);
    if (!skipFill) this.hardClear();
  }

  reseed(seed = (Math.random() * 1e9) | 0) {
    this.seed = seed;
    this.noise = new SimplexNoise(seed);
    this.z = 0;
    this.spawnAll();
    this.hardClear();
  }

  resize() {
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    this.dpr = dpr;
    const w = this.canvas.clientWidth;
    const h = this.canvas.clientHeight;
    this.canvas.width = Math.max(1, Math.floor(w * dpr));
    this.canvas.height = Math.max(1, Math.floor(h * dpr));
    this.w = this.canvas.width;
    this.h = this.canvas.height;
    if (!this.noise) this.reseed(); else { this.spawnAll(); this.hardClear(); }
  }

  hardClear() {
    if (!this.ctx) return;
    this.ctx.fillStyle = this.palette.bg;
    this.ctx.fillRect(0, 0, this.w, this.h);
  }

  spawnParticle(p) {
    p.x = Math.random() * this.w;
    p.y = Math.random() * this.h;
    p.life = 0;
    p.maxLife = 120 + Math.random() * 380;
    return p;
  }

  spawnAll() {
    const n = this.params.count;
    this.particles = [];
    for (let i = 0; i < n; i++) this.particles.push(this.spawnParticle({}));
  }

  setCount(n) {
    n = Math.max(1, n | 0);
    this.params.count = n;
    const arr = this.particles;
    if (n < arr.length) {
      arr.length = n;
    } else {
      while (arr.length < n) arr.push(this.spawnParticle({}));
    }
  }

  step() {
    const { ctx, params } = this;
    const { noiseScale, speed, curl, fade, lineWidth, pointerForce } = params;

    // Fade the previous frame toward the background color to create trails.
    ctx.globalCompositeOperation = 'source-over';
    ctx.fillStyle = this.fadeColor(fade);
    ctx.fillRect(0, 0, this.w, this.h);

    ctx.lineWidth = lineWidth * this.dpr;
    ctx.lineCap = 'round';
    ctx.globalCompositeOperation = this.palette.name === 'Ink' ? 'source-over' : 'lighter';

    const z = this.z;
    const ptr = this.pointer;
    const force = pointerForce * this.dpr;

    for (let i = 0; i < this.particles.length; i++) {
      const p = this.particles[i];
      const px = p.x, py = p.y;

      // Heading from the noise field.
      const n = this.noise.noise3D(px * noiseScale, py * noiseScale, z);
      const angle = n * TAU * curl;
      let vx = Math.cos(angle) * speed * this.dpr;
      let vy = Math.sin(angle) * speed * this.dpr;

      // Pointer interaction.
      if (ptr.active && ptr.mode) {
        const dx = ptr.x - px;
        const dy = ptr.y - py;
        const d2 = dx * dx + dy * dy;
        const radius = 220 * this.dpr;
        if (d2 < radius * radius) {
          const d = Math.sqrt(d2) || 1;
          const falloff = (1 - d / radius);
          const dir = ptr.mode === 1 ? 1 : -1;
          vx += (dx / d) * force * falloff * dir * 0.06;
          vy += (dy / d) * force * falloff * dir * 0.06;
        }
      }

      const nx = px + vx;
      const ny = py + vy;

      // Color by heading so the field's structure reads as hue.
      const ci = (((angle % TAU) + TAU) % TAU) / TAU;
      ctx.strokeStyle = this.ramp[(ci * 255) | 0];

      ctx.beginPath();
      ctx.moveTo(px, py);
      ctx.lineTo(nx, ny);
      ctx.stroke();

      p.x = nx;
      p.y = ny;
      p.life++;

      // Respawn when a particle leaves the canvas or ages out.
      if (
        nx < 0 || nx > this.w || ny < 0 || ny > this.h ||
        p.life > p.maxLife
      ) {
        this.spawnParticle(p);
      }
    }

    this.z += params.timeWarp;
  }

  // Build an rgba background color with the requested alpha for trail fading.
  fadeColor(alpha) {
    const bg = this.palette.bg;
    const n = parseInt(bg.slice(1), 16);
    const r = (n >> 16) & 255, g = (n >> 8) & 255, b = n & 255;
    return `rgba(${r},${g},${b},${alpha})`;
  }

  frame() {
    if (this.running) this.step();
  }

  toggle() { this.running = !this.running; return this.running; }

  // Export the current canvas as a PNG data URL.
  snapshot() {
    return this.canvas.toDataURL('image/png');
  }
}
