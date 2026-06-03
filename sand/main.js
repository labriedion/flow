// main.js — wires the UI to the Sandbox and runs the render loop.
//
// The shape here mirrors boids/main.js: declarative palette/slider bindings, a
// requestAnimationFrame loop, Save-PNG and keyboard shortcuts. The one extra is
// on-canvas painting — left-drag lays down the selected material, right-drag
// erases — which is the whole point of a sand toy.

import { Sandbox, MATERIALS } from './sim.js';
import { Renderer } from './sand.js';

const canvas = document.getElementById('stage');

// The grid stays a fixed, modest resolution and the canvas scales it up. Bigger
// cells = chunkier physics but a smoother frame rate; this is a comfortable mix.
const CELL = 5; // approx screen pixels per simulation cell
const dpr = Math.min(window.devicePixelRatio || 1, 2);

let sim, renderer;

function buildWorld() {
  const w = canvas.clientWidth || window.innerWidth;
  const h = canvas.clientHeight || window.innerHeight;
  canvas.width = Math.floor(w * dpr);
  canvas.height = Math.floor(h * dpr);
  const cols = Math.max(40, Math.floor(w / CELL));
  const rows = Math.max(30, Math.floor(h / CELL));
  sim = new Sandbox(cols, rows, (Math.random() * 0xffffffff) >>> 0);
  sim.seedScene();
  if (renderer) renderer.rebind(sim);
  else renderer = new Renderer(canvas, sim);
}
buildWorld();

// ---- Material palette ---------------------------------------------------
// One button per paintable material, drawn as a coloured swatch + label.
const PAINTABLE = ['SAND', 'WATER', 'WALL', 'WOOD', 'FIRE', 'SMOKE', 'EMPTY'];
let current = MATERIALS.SAND.id;

const palWrap = document.getElementById('palette');
PAINTABLE.forEach((key, i) => {
  const m = MATERIALS[key];
  const btn = document.createElement('button');
  btn.className = 'mat' + (m.id === current ? ' active' : '');
  btn.dataset.id = m.id;
  btn.textContent = key === 'EMPTY' ? 'Eraser' : m.name;
  btn.style.setProperty('--swatch', `rgb(${m.color.join(',')})`);
  btn.addEventListener('click', () => selectMaterial(m.id));
  palWrap.appendChild(btn);
});

function selectMaterial(id) {
  current = id;
  [...palWrap.children].forEach((c) =>
    c.classList.toggle('active', Number(c.dataset.id) === id)
  );
}

// ---- Sliders ------------------------------------------------------------
const brush = { radius: 5 };
const speed = { steps: 1 }; // physics ticks per rendered frame

const sliders = [
  { id: 'brush', fmt: (v) => `${v | 0}`, apply: (v) => (brush.radius = v | 0) },
  { id: 'speed', fmt: (v) => `${v | 0}x`, apply: (v) => (speed.steps = v | 0) },
];
for (const s of sliders) {
  const el = document.getElementById(s.id);
  const sync = () => {
    const raw = parseFloat(el.value);
    document.getElementById(s.id + 'Val').textContent = s.fmt(raw);
    s.apply(raw);
  };
  sync();
  el.addEventListener('input', sync);
}

// ---- Buttons ------------------------------------------------------------
let running = true;
const pauseBtn = document.getElementById('pause');
pauseBtn.addEventListener('click', () => {
  running = !running;
  pauseBtn.textContent = running ? 'Pause' : 'Play';
});
document.getElementById('clear').addEventListener('click', () => sim.clear());
document.getElementById('reseed').addEventListener('click', () => sim.seedScene());
document.getElementById('save').addEventListener('click', savePNG);

function savePNG() {
  const a = document.createElement('a');
  a.href = renderer.snapshot();
  a.download = `sand-${Date.now()}.png`;
  a.click();
}

// ---- Pointer painting ---------------------------------------------------
// Left button paints the current material; right button erases. We track the
// last cell and paint along the line between samples so fast drags don't leave
// dotted gaps.
const pointer = { active: false, erase: false, lastX: null, lastY: null };

function pointerCell(e) {
  const rect = canvas.getBoundingClientRect();
  const px = (e.clientX - rect.left) * dpr;
  const py = (e.clientY - rect.top) * dpr;
  return renderer.toCell(px, py);
}

function paintAt(cx, cy) {
  const mat = pointer.erase ? MATERIALS.EMPTY.id : current;
  sim.paint(cx, cy, brush.radius, mat);
}

// Bresenham-ish line so a quick drag paints a continuous stroke.
function paintLine(x0, y0, x1, y1) {
  const dx = Math.abs(x1 - x0), dy = Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
  let err = dx - dy, x = x0, y = y0;
  for (;;) {
    paintAt(x, y);
    if (x === x1 && y === y1) break;
    const e2 = 2 * err;
    if (e2 > -dy) { err -= dy; x += sx; }
    if (e2 < dx) { err += dx; y += sy; }
  }
}

function strokeTo(e) {
  const { cx, cy } = pointerCell(e);
  if (pointer.lastX == null) paintAt(cx, cy);
  else paintLine(pointer.lastX, pointer.lastY, cx, cy);
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

// Touch: single-finger paints the current material.
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
// Number keys jump straight to a material; the rest mirror the buttons.
const KEY_TO_MAT = {
  '1': MATERIALS.SAND.id, '2': MATERIALS.WATER.id, '3': MATERIALS.WALL.id,
  '4': MATERIALS.WOOD.id, '5': MATERIALS.FIRE.id, '6': MATERIALS.SMOKE.id,
  '7': MATERIALS.EMPTY.id,
};

const panel = document.getElementById('panel');
const togglePanel = document.getElementById('togglePanel');
togglePanel.addEventListener('click', () => panel.classList.remove('hidden'));

window.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
  if (KEY_TO_MAT[e.key] != null) { selectMaterial(KEY_TO_MAT[e.key]); return; }
  switch (e.key.toLowerCase()) {
    case ' ': e.preventDefault(); pauseBtn.click(); break;
    case 'c': sim.clear(); break;
    case 'r': sim.seedScene(); break;
    case 's': savePNG(); break;
    case 'h': panel.classList.toggle('hidden'); break;
  }
});

// ---- Resize + render loop ----------------------------------------------
let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => buildWorld(), 200);
});

function loop() {
  if (running) for (let s = 0; s < speed.steps; s++) sim.step();
  renderer.draw();
  requestAnimationFrame(loop);
}
loop();
