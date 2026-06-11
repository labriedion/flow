// fractal.js — an escape-time renderer for the Mandelbrot and Julia sets.
//
// The heavy work is a per-pixel iteration loop writing straight into an
// ImageData buffer. Smooth (continuous) coloring removes the harsh iteration
// "bands" by blending the final iteration count with how far past the escape
// radius the orbit landed.

// Build a 1024-entry RGB palette from three phase-shifted cosines. Different
// phase/frequency triples give very different moods; `buildPalette` bakes one
// into a flat Uint8 array for fast lookup.
const PALETTE_PRESETS = {
  Inferno:   { freq: [1.0, 1.0, 1.0], phase: [0.0, 0.15, 0.30], bias: [0.5, 0.35, 0.2] },
  Ocean:     { freq: [0.8, 0.9, 1.1], phase: [0.6, 0.5, 0.2], bias: [0.2, 0.4, 0.6] },
  Acid:      { freq: [1.2, 1.0, 0.7], phase: [0.1, 0.45, 0.8], bias: [0.4, 0.6, 0.3] },
  Twilight:  { freq: [0.9, 0.7, 1.0], phase: [0.3, 0.6, 0.9], bias: [0.5, 0.3, 0.6] },
  Grayscale: { freq: [1.0, 1.0, 1.0], phase: [0.0, 0.0, 0.0], bias: [0.5, 0.5, 0.5] },
};

const PALETTE_SIZE = 1024;
const TAU = Math.PI * 2;

function buildPalette(preset) {
  const { freq, phase, bias } = preset;
  const amp = 0.5;
  const out = new Uint8ClampedArray(PALETTE_SIZE * 3);
  for (let i = 0; i < PALETTE_SIZE; i++) {
    const t = i / PALETTE_SIZE;
    out[i * 3 + 0] = 255 * (bias[0] + amp * Math.cos(TAU * (freq[0] * t + phase[0])));
    out[i * 3 + 1] = 255 * (bias[1] + amp * Math.cos(TAU * (freq[1] * t + phase[1])));
    out[i * 3 + 2] = 255 * (bias[2] + amp * Math.cos(TAU * (freq[2] * t + phase[2])));
  }
  return out;
}

class Fractal {
  constructor() {
    // The complex plane window: a center point and a vertical half-height
    // ("scale"). Horizontal extent is derived from the canvas aspect ratio.
    this.view = { cx: -0.5, cy: 0, scale: 1.4 };
    this.maxIter = 250;
    this.mode = 'mandelbrot';       // or 'julia'
    this.juliaC = { x: -0.8, y: 0.156 };
    this.colorShift = 0;            // animatable palette offset
    this.colorDensity = 12;         // how fast colors cycle across iterations
    this.setPalette('Inferno');
  }

  setPalette(name) {
    this.paletteName = name;
    this.palette = buildPalette(PALETTE_PRESETS[name]);
  }

  // Convert a screen pixel to its complex-plane coordinate for a given buffer.
  pixelToComplex(px, py, w, h) {
    const aspect = w / h;
    const reSpan = this.view.scale * aspect;
    const re = this.view.cx + (px / w - 0.5) * 2 * reSpan;
    const im = this.view.cy + (py / h - 0.5) * 2 * this.view.scale;
    return { re, im };
  }

  // Render into an ImageData of size w x h. Returns the ImageData.
  render(imageData, w, h) {
    const data = imageData.data;
    const pal = this.palette;
    const maxIter = this.maxIter;
    const isJulia = this.mode === 'julia';
    const cRe0 = this.juliaC.x;
    const cIm0 = this.juliaC.y;
    const aspect = w / h;
    const reSpan = this.view.scale * aspect;
    const imSpan = this.view.scale;
    const cx = this.view.cx;
    const cy = this.view.cy;
    const shift = this.colorShift;
    const density = this.colorDensity;
    const escape = 4 << 4; // generous escape radius for smoother coloring
    const logEscape = Math.log(Math.log(Math.sqrt(escape)));
    const log2 = Math.log(2);

    let p = 0;
    for (let py = 0; py < h; py++) {
      const im0 = cy + (py / h - 0.5) * 2 * imSpan;
      for (let px = 0; px < w; px++) {
        const re0 = cx + (px / w - 0.5) * 2 * reSpan;

        // For the Mandelbrot set, c is the pixel and z starts at 0.
        // For Julia, c is fixed and z starts at the pixel.
        let zr, zi, cRe, cIm;
        if (isJulia) {
          zr = re0; zi = im0; cRe = cRe0; cIm = cIm0;
        } else {
          zr = 0; zi = 0; cRe = re0; cIm = im0;
        }

        let n = 0;
        let zr2 = zr * zr;
        let zi2 = zi * zi;
        while (zr2 + zi2 <= escape && n < maxIter) {
          zi = 2 * zr * zi + cIm;
          zr = zr2 - zi2 + cRe;
          zr2 = zr * zr;
          zi2 = zi * zi;
          n++;
        }

        if (n >= maxIter) {
          // Interior points: solid black.
          data[p] = 0; data[p + 1] = 0; data[p + 2] = 0; data[p + 3] = 255;
        } else {
          // Smooth iteration count for band-free gradients.
          const mag = Math.sqrt(zr2 + zi2);
          const mu = n + 1 - (Math.log(Math.log(mag)) - logEscape) / log2;
          let idx = ((mu * density + shift) % PALETTE_SIZE);
          if (idx < 0) idx += PALETTE_SIZE;
          const i3 = (idx | 0) * 3;
          data[p] = pal[i3];
          data[p + 1] = pal[i3 + 1];
          data[p + 2] = pal[i3 + 2];
          data[p + 3] = 255;
        }
        p += 4;
      }
    }
    return imageData;
  }

  // Zoom toward a complex point by a multiplicative factor (<1 zooms in).
  zoomAt(re, im, factor) {
    this.view.cx = re + (this.view.cx - re) * factor;
    this.view.cy = im + (this.view.cy - im) * factor;
    this.view.scale *= factor;
  }

  reset() {
    if (this.mode === 'julia') {
      this.view = { cx: 0, cy: 0, scale: 1.6 };
    } else {
      this.view = { cx: -0.5, cy: 0, scale: 1.4 };
    }
  }
}
