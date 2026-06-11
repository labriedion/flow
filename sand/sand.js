// sand.js — the renderer. Turns a Sandbox's grid of material ids into pixels.
//
// It owns nothing about the physics; it just reads `sim.cells` every frame and
// paints it. The trick to staying fast is to draw into a tiny ImageData buffer
// that is exactly one pixel per simulation cell, then let the canvas scale that
// up to the full stage with `imageSmoothingEnabled = false` for crisp cells.
// That keeps the per-frame work proportional to the grid (tens of thousands of
// cells) rather than the screen (millions of pixels).

class Renderer {
  constructor(canvas, sim) {
    this.canvas = canvas;
    this.sim = sim;
    this.ctx = canvas.getContext('2d', { alpha: false });
    this.ctx.imageSmoothingEnabled = false;

    // The off-screen buffer is grid-sized; one ImageData pixel == one cell.
    this.buffer = document.createElement('canvas');
    this.bctx = this.buffer.getContext('2d');
    this._fit();

    // A flat lookup of packed RGBA ints (0xAABBGGRR in little-endian memory)
    // keyed by material id, so the inner loop is a single array write per cell.
    this.colorLUT = this._buildLUT();
  }

  _fit() {
    this.buffer.width = this.sim.width;
    this.buffer.height = this.sim.height;
    this.image = this.bctx.createImageData(this.sim.width, this.sim.height);
    // A Uint32 view over the same bytes lets us write a whole RGBA pixel at once.
    this.pixels = new Uint32Array(this.image.data.buffer);
  }

  _buildLUT() {
    const lut = new Uint32Array(BY_ID.length);
    for (let id = 0; id < BY_ID.length; id++) {
      const m = BY_ID[id];
      if (!m) continue;
      const [r, g, b] = m.color;
      // Little-endian: byte order in memory is R, G, B, A.
      lut[id] = (255 << 24) | (b << 16) | (g << 8) | r;
    }
    return lut;
  }

  // Call if the grid is replaced or resized.
  rebind(sim) {
    this.sim = sim;
    this._fit();
  }

  draw() {
    const cells = this.sim.cells;
    const px = this.pixels;
    const lut = this.colorLUT;
    for (let i = 0; i < cells.length; i++) px[i] = lut[cells[i]];
    this.bctx.putImageData(this.image, 0, 0);

    // Blit the small buffer up to the full canvas, nearest-neighbour scaled.
    const ctx = this.ctx;
    ctx.imageSmoothingEnabled = false;
    ctx.drawImage(this.buffer, 0, 0, this.sim.width, this.sim.height,
      0, 0, this.canvas.width, this.canvas.height);
  }

  // Convert a canvas-space pixel (CSS px * dpr) to integer grid coordinates.
  toCell(px, py) {
    const cx = Math.floor((px / this.canvas.width) * this.sim.width);
    const cy = Math.floor((py / this.canvas.height) * this.sim.height);
    return { cx, cy };
  }

  // A PNG data URL of the current canvas, for "Save".
  snapshot() {
    return this.canvas.toDataURL('image/png');
  }
}
