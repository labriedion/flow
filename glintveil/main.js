// main.js — wires the UI to the Field and runs the render loop.
//
// The shape here mirrors sand/main.js: declarative slider bindings, a
// requestAnimationFrame loop, Save-PNG and keyboard shortcuts. The renderer
// paints the v field through a colour ramp into an offscreen ImageData at sim
// resolution, then scales it up smoothly — the veil look comes free from the
// browser's bilinear filtering.

import { Field, PRESETS, DEFAULT_PRESET } from './sim.js';

const canvas = document.getElementById('stage');
const ctx = canvas.getContext('2d');

// The field stays a fixed, modest resolution and the canvas scales it up.
// Reaction–diffusion wants finer cells than falling sand to show its weave.
const CELL = 3; // approx screen pixels per simulation cell
const dpr = Math.min(window.devicePixelRatio || 1, 2);

let sim, buffer, bufCtx, image;

function buildField() {
  const w = canvas.clientWidth || window.innerWidth;
  const h = canvas.clientHeight || window.innerHeight;
  canvas.width = Math.floor(w * dpr);
  canvas.height = Math.floor(h * dpr);
  const cols = Math.max(80, Math.floor(w / CELL));
  const rows = Math.max(60, Math.floor(h / CELL));
  const old = sim;
  sim = new Field(cols, rows, (Math.random() * 0xffffffff) >>> 0);
  if (old) { sim.feed = old.feed; sim.kill = old.kill; }
  sim.seedNoise();
  buffer = document.createElement('canvas');
  buffer.width = cols;
  buffer.height = rows;
  bufCtx = buffer.getContext('2d');
  image = bufCtx.createImageData(cols, rows);
}
buildField();

// ---- Colour ramp ----------------------------------------------------------
// v=0 is the deep background; rising v climbs through violet glints into a
// pale crest. Precomputed as a 512-entry RGB lookup so draw() stays a tight
// loop over bytes.
const STOPS = [
  [0.0, [7, 9, 16]],      // quiet field
  [0.18, [38, 27, 78]],   // first shadow of pattern
  [0.42, [108, 66, 199]], // violet body
  [0.68, [179, 136, 255]],// the accent itself
  [0.85, [142, 219, 246]],// an icy glint at the crest
  [1.0, [240, 248, 255]], // white-hot peak
];
const RAMP = new Uint8Array(512 * 3);
for (let i = 0; i < 512; i++) {
  const t = i / 511;
  let lo = STOPS[0], hi = STOPS[STOPS.length - 1];
  for (let s = 0; s < STOPS.length - 1; s++) {
    if (t >= STOPS[s][0] && t <= STOPS[s + 1][0]) { lo = STOPS[s]; hi = STOPS[s + 1]; break; }
  }
  const f = (t - lo[0]) / Math.max(1e-9, hi[0] - lo[0]);
  for (let c = 0; c < 3; c++) {
    RAMP[i * 3 + c] = Math.round(lo[1][c] + (hi[1][c] - lo[1][c]) * f);
  }
}

function draw() {
  const { v, width: w, height: h } = sim;
  const data = image.data;
  for (let i = 0, p = 0; i < v.length; i++, p += 4) {
    // v tops out near ~0.5 in practice; stretch it across the whole ramp
    let t = v[i] * 2.2;
    if (t > 1) t = 1;
    const k = (t * 511) | 0;
    data[p] = RAMP[k * 3];
    data[p + 1] = RAMP[k * 3 + 1];
    data[p + 2] = RAMP[k * 3 + 2];
    data[p + 3] = 255;
  }
  bufCtx.putImageData(image, 0, 0);
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(buffer, 0, 0, w, h, 0, 0, canvas.width, canvas.height);
}

// ---- Presets ---------------------------------------------------------------
const presetWrap = document.getElementById('presets');
const presetKeys = Object.keys(PRESETS);
let currentPreset = DEFAULT_PRESET;

presetKeys.forEach((key) => {
  const p = PRESETS[key];
  const btn = document.createElement('button');
  btn.className = 'mat' + (key === currentPreset ? ' active' : '');
  btn.dataset.key = key;
  btn.textContent = p.name;
  btn.addEventListener('click', () => selectPreset(key));
  presetWrap.appendChild(btn);
});

function selectPreset(key) {
  currentPreset = key;
  const p = PRESETS[key];
  sim.feed = p.feed;
  sim.kill = p.kill;
  feedEl.value = p.feed;
  killEl.value = p.kill;
  syncSliders();
  [...presetWrap.children].forEach((c) =>
    c.classList.toggle('active', c.dataset.key === key)
  );
}

// ---- Sliders ---------------------------------------------------------------
const brush = { radius: 5 };
const speed = { steps: 10 }; // sim ticks per rendered frame
const feedEl = document.getElementById('feed');
const killEl = document.getElementById('kill');

const sliders = [
  { id: 'feed', fmt: (v) => v.toFixed(4), apply: (v) => { sim.feed = v; markCustom(); } },
  { id: 'kill', fmt: (v) => v.toFixed(4), apply: (v) => { sim.kill = v; markCustom(); } },
  { id: 'brush', fmt: (v) => `${v | 0}`, apply: (v) => (brush.radius = v | 0) },
  { id: 'speed', fmt: (v) => `${v | 0}x`, apply: (v) => (speed.steps = v | 0) },
];

// Nudging feed/kill off a preset un-highlights it: you're exploring the
// parameter plane between the named regimes now.
function markCustom() {
  const p = PRESETS[currentPreset];
  const onPreset = p && Math.abs(sim.feed - p.feed) < 1e-9 && Math.abs(sim.kill - p.kill) < 1e-9;
  [...presetWrap.children].forEach((c) =>
    c.classList.toggle('active', onPreset && c.dataset.key === currentPreset)
  );
}

function syncSliders() {
  for (const s of sliders) {
    const el = document.getElementById(s.id);
    document.getElementById(s.id + 'Val').textContent = s.fmt(parseFloat(el.value));
  }
}
for (const s of sliders) {
  const el = document.getElementById(s.id);
  const sync = () => {
    const raw = parseFloat(el.value);
    document.getElementById(s.id + 'Val').textContent = s.fmt(raw);
    s.apply(raw);
  };
  el.addEventListener('input', sync);
}
selectPreset(currentPreset);

// ---- Buttons ----------------------------------------------------------------
let running = true;
const pauseBtn = document.getElementById('pause');
pauseBtn.addEventListener('click', () => {
  running = !running;
  pauseBtn.textContent = running ? 'Pause' : 'Play';
});
document.getElementById('clear').addEventListener('click', () => sim.clear());
document.getElementById('reseed').addEventListener('click', () => sim.seedNoise());
document.getElementById('save').addEventListener('click', savePNG);

function savePNG() {
  const a = document.createElement('a');
  a.href = canvas.toDataURL('image/png');
  a.download = `glintveil-${Date.now()}.png`;
  a.click();
}

// ---- Pointer poking -----------------------------------------------------
// Left button pours the patterning chemical; right button erases back to the
// quiet state. Samples along the drag line so fast strokes stay continuous.
const pointer = { active: false, erase: false, lastX: null, lastY: null };

function pointerCell(e) {
  const rect = canvas.getBoundingClientRect();
  const cx = Math.floor(((e.clientX - rect.left) / rect.width) * sim.width);
  const cy = Math.floor(((e.clientY - rect.top) / rect.height) * sim.height);
  return { cx, cy };
}

function pokeAt(cx, cy) {
  if (pointer.erase) sim.erase(cx, cy, brush.radius);
  else sim.poke(cx, cy, brush.radius, 0.9);
}

function pokeLine(x0, y0, x1, y1) {
  const dx = Math.abs(x1 - x0), dy = Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
  let err = dx - dy, x = x0, y = y0;
  for (;;) {
    pokeAt(x, y);
    if (x === x1 && y === y1) break;
    const e2 = 2 * err;
    if (e2 > -dy) { err -= dy; x += sx; }
    if (e2 < dx) { err += dx; y += sy; }
  }
}

function strokeTo(e) {
  const { cx, cy } = pointerCell(e);
  if (pointer.lastX == null) pokeAt(cx, cy);
  else pokeLine(pointer.lastX, pointer.lastY, cx, cy);
  pointer.lastX = cx; pointer.lastY = cy;
}

canvas.addEventListener('mousedown', (e) => {
  pointer.active = true;
  pointer.erase = e.button === 2;
  pointer.lastX = pointer.lastY = null;
  strokeTo(e);
});
canvas.addEventListener('mousemove', (e) => { if (pointer.active) strokeTo(e); });
window.addEventListener('mouseup', () => {
  pointer.active = false;
  pointer.lastX = pointer.lastY = null;
});
canvas.addEventListener('contextmenu', (e) => e.preventDefault());

// Touch: single-finger pours chemical.
canvas.addEventListener('touchstart', (e) => {
  pointer.active = true; pointer.erase = false;
  pointer.lastX = pointer.lastY = null;
  strokeTo(e.touches[0]);
}, { passive: true });
canvas.addEventListener('touchmove', (e) => {
  if (pointer.active) strokeTo(e.touches[0]);
}, { passive: true });
window.addEventListener('touchend', () => { pointer.active = false; });

// ---- Keyboard shortcuts -------------------------------------------------
const panel = document.getElementById('panel');
const togglePanel = document.getElementById('togglePanel');
togglePanel.addEventListener('click', () => panel.classList.remove('hidden'));

window.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
  const n = parseInt(e.key, 10);
  if (n >= 1 && n <= presetKeys.length) { selectPreset(presetKeys[n - 1]); return; }
  switch (e.key.toLowerCase()) {
    case ' ': e.preventDefault(); pauseBtn.click(); break;
    case 'c': sim.clear(); break;
    case 'r': sim.seedNoise(); break;
    case 's': savePNG(); break;
    case 'h': panel.classList.toggle('hidden'); break;
  }
});

// ---- Resize + render loop ----------------------------------------------
let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => buildField(), 200);
});

function loop() {
  if (running) for (let s = 0; s < speed.steps; s++) sim.step();
  draw();
  requestAnimationFrame(loop);
}
loop();
