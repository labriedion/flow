// main.js — wires the UI to the FlowField engine and runs the render loop.
import { FlowField } from './flowfield.js';
import { PALETTES } from './palettes.js';

const canvas = document.getElementById('stage');
const field = new FlowField(canvas);

// ---- Slider bindings ----------------------------------------------------
// Each entry maps a slider id to how its value should be applied and shown.
const sliders = [
  { id: 'count', apply: (v) => field.setCount(v), fmt: (v) => v | 0 },
  { id: 'speed', key: 'speed', fmt: (v) => v.toFixed(1) },
  { id: 'noiseScale', key: 'noiseScale', fmt: (v) => v.toFixed(4) },
  { id: 'curl', key: 'curl', fmt: (v) => v.toFixed(1) },
  { id: 'timeWarp', key: 'timeWarp', fmt: (v) => v.toFixed(4) },
  { id: 'fade', key: 'fade', fmt: (v) => v.toFixed(3), invertLabel: true },
  { id: 'lineWidth', key: 'lineWidth', fmt: (v) => v.toFixed(1) },
];

function syncSlider(s) {
  const el = document.getElementById(s.id);
  const val = parseFloat(el.value);
  document.getElementById(s.id + 'Val').textContent = s.fmt(val);
  if (s.apply) s.apply(val);
  else field.params[s.key] = val;
}

for (const s of sliders) {
  const el = document.getElementById(s.id);
  // Initialize slider position from the engine's defaults.
  const initial = s.id === 'count' ? field.params.count : field.params[s.key];
  el.value = initial;
  syncSlider(s);
  el.addEventListener('input', () => syncSlider(s));
}

// ---- Palette swatches ---------------------------------------------------
const palWrap = document.getElementById('palettes');
PALETTES.forEach((p, i) => {
  const sw = document.createElement('div');
  sw.className = 'swatch' + (i === 0 ? ' active' : '');
  sw.title = p.name;
  sw.style.background = `linear-gradient(135deg, ${p.stops.join(',')})`;
  sw.addEventListener('click', () => selectPalette(i));
  palWrap.appendChild(sw);
});

function selectPalette(i) {
  field.setPalette(i);
  [...palWrap.children].forEach((c, idx) =>
    c.classList.toggle('active', idx === i)
  );
}

// ---- Buttons ------------------------------------------------------------
const pauseBtn = document.getElementById('pause');
pauseBtn.addEventListener('click', () => {
  pauseBtn.textContent = field.toggle() ? 'Pause' : 'Play';
});
document.getElementById('clear').addEventListener('click', () => field.hardClear());
document.getElementById('reseed').addEventListener('click', () => field.reseed());
document.getElementById('save').addEventListener('click', savePNG);
document.getElementById('random').addEventListener('click', surprise);

function savePNG() {
  const a = document.createElement('a');
  a.href = field.snapshot();
  a.download = `flowfield-${Date.now()}.png`;
  a.click();
}

// Randomize the whole scene to a pleasing-but-unexpected configuration.
function surprise() {
  const rnd = (min, max) => min + Math.random() * (max - min);
  const set = (id, v) => {
    const el = document.getElementById(id);
    el.value = v;
    el.dispatchEvent(new Event('input'));
  };
  set('count', Math.round(rnd(800, 3500)));
  set('speed', rnd(0.8, 3));
  set('noiseScale', rnd(0.0008, 0.004));
  set('curl', rnd(1, 5));
  set('timeWarp', rnd(0.0003, 0.0025));
  set('fade', rnd(0.02, 0.12));
  set('lineWidth', rnd(0.6, 2));
  selectPalette((Math.random() * PALETTES.length) | 0);
  field.reseed();
}

// ---- Pointer interaction ------------------------------------------------
function pointerPos(e) {
  const rect = canvas.getBoundingClientRect();
  field.pointer.x = (e.clientX - rect.left) * field.dpr;
  field.pointer.y = (e.clientY - rect.top) * field.dpr;
}

canvas.addEventListener('mousedown', (e) => {
  pointerPos(e);
  field.pointer.active = true;
  field.pointer.mode = e.button === 2 ? 2 : 1; // right = repel
});
canvas.addEventListener('mousemove', (e) => {
  if (field.pointer.active) pointerPos(e);
});
window.addEventListener('mouseup', () => {
  field.pointer.active = false;
  field.pointer.mode = 0;
});
canvas.addEventListener('contextmenu', (e) => e.preventDefault());

// Touch support.
canvas.addEventListener('touchstart', (e) => {
  field.pointer.active = true;
  field.pointer.mode = 1;
  pointerPos(e.touches[0]);
}, { passive: true });
canvas.addEventListener('touchmove', (e) => pointerPos(e.touches[0]), { passive: true });
window.addEventListener('touchend', () => { field.pointer.active = false; });

// ---- Keyboard shortcuts -------------------------------------------------
const panel = document.getElementById('panel');
const togglePanel = document.getElementById('togglePanel');
togglePanel.addEventListener('click', () => panel.classList.remove('hidden'));

window.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT') return;
  switch (e.key.toLowerCase()) {
    case ' ': e.preventDefault(); pauseBtn.click(); break;
    case 'c': field.hardClear(); break;
    case 'r': field.reseed(); break;
    case 's': savePNG(); break;
    case 'h': panel.classList.toggle('hidden'); break;
  }
});

// ---- Resize + render loop ----------------------------------------------
let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => field.resize(), 150);
});

function loop() {
  field.frame();
  requestAnimationFrame(loop);
}
loop();
