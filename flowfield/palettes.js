// palettes.js — curated color ramps for the flow field.
// Each palette is a name plus a background color and an array of stop colors
// sampled along the particle's "age" / angle to produce smooth gradients.

const PALETTES = [
  {
    name: 'Aurora',
    bg: '#05070d',
    stops: ['#003973', '#0a85ed', '#21d4fd', '#43e97b', '#b8ff9f'],
  },
  {
    name: 'Ember',
    bg: '#0b0503',
    stops: ['#3a0ca3', '#7209b7', '#f72585', '#ff7b00', '#ffd60a'],
  },
  {
    name: 'Lagoon',
    bg: '#02080a',
    stops: ['#012a36', '#017a8a', '#02c39a', '#b5e48c', '#f1faee'],
  },
  {
    name: 'Sakura',
    bg: '#0c0408',
    stops: ['#6d23b6', '#c33764', '#ff5d8f', '#ffa8c5', '#ffe5ec'],
  },
  {
    name: 'Mono',
    bg: '#000000',
    stops: ['#1a1a1a', '#555555', '#999999', '#cccccc', '#ffffff'],
  },
  {
    name: 'Citrus',
    bg: '#0a0a02',
    stops: ['#386641', '#6a994e', '#a7c957', '#f2e8cf', '#ffba08'],
  },
  {
    name: 'Nebula',
    bg: '#050208',
    stops: ['#10002b', '#5a189a', '#9d4edd', '#e0aaff', '#fff0ff'],
  },
  {
    name: 'Ink',
    bg: '#f4f1ea',
    stops: ['#22223b', '#4a4e69', '#9a8c98', '#c9ada7', '#6b705c'],
  },
];

// Parse "#rrggbb" into [r, g, b].
function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

// Pre-compute a 256-entry lookup table of "rgb(...)" strings for a palette so
// per-particle coloring is a single array index instead of repeated math.
function buildRamp(palette, alpha = 1) {
  const stops = palette.stops.map(hexToRgb);
  const ramp = new Array(256);
  const segments = stops.length - 1;
  for (let i = 0; i < 256; i++) {
    const f = (i / 255) * segments;
    const idx = Math.min(Math.floor(f), segments - 1);
    const local = f - idx;
    const a = stops[idx];
    const b = stops[idx + 1];
    const r = Math.round(a[0] + (b[0] - a[0]) * local);
    const g = Math.round(a[1] + (b[1] - a[1]) * local);
    const bl = Math.round(a[2] + (b[2] - a[2]) * local);
    ramp[i] = `rgba(${r},${g},${bl},${alpha})`;
  }
  return ramp;
}
