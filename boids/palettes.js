// palettes.js — colour schemes for the flock.
// Each palette has a background, an accent (for vision circles), and a gradient
// of stops that boids are coloured along by their speed. Colours are authored as
// hex and parsed to [r, g, b] once at load time, which is the form the renderer
// wants (it builds `rgb(...)` / `rgba(...)` strings directly from the numbers).

function hexToRgb(hex) {
  const n = parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

const RAW = [
  {
    name: 'Starling',
    bg: '#070910',
    accent: '#7aa2ff',
    stops: ['#1b2a6b', '#3a6df0', '#7ad7ff', '#dff6ff'],
  },
  {
    name: 'Ember',
    bg: '#0c0603',
    accent: '#ffb066',
    stops: ['#5a189a', '#e01e5a', '#ff7b00', '#ffd60a'],
  },
  {
    name: 'Reef',
    bg: '#02090b',
    accent: '#5fe6c6',
    stops: ['#013a4a', '#018a8a', '#02c39a', '#d6ff8c'],
  },
  {
    name: 'Dusk',
    bg: '#0a0610',
    accent: '#c79bff',
    stops: ['#241468', '#7b2cbf', '#e056a0', '#ffd6f0'],
  },
  {
    name: 'Mono',
    bg: '#060606',
    accent: '#aaaaaa',
    stops: ['#3a3a3a', '#808080', '#c4c4c4', '#ffffff'],
  },
  {
    name: 'Ink',
    bg: '#f3efe6',
    accent: '#4a4e69',
    stops: ['#22223b', '#4a4e69', '#8a5a44', '#9a8c98'],
  },
];

// Export with bg/accent/stops parsed into numeric RGB.
export const PALETTES = RAW.map((p) => ({
  name: p.name,
  bg: hexToRgb(p.bg),
  accent: hexToRgb(p.accent),
  stops: p.stops.map(hexToRgb),
}));
