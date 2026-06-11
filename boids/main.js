// main.js — wires the UI to the Flock engine and runs the render loop.

const canvas = document.getElementById('stage');
const flock = new Flock(canvas);

// ---- Slider bindings ----------------------------------------------------
// Trail reads as "length", but the param is "fade per frame" (more fade = a
// shorter trail), so its slider is inverted around the sum of its endpoints.
const TRAIL_SUM = 0.63; // min(0.03) + max(0.6)
const sliders = [
  { id: 'count', apply: (v) => flock.setCount(v), fmt: (v) => v | 0 },
  { id: 'perception', key: 'perception', fmt: (v) => `${v | 0}px` },
  { id: 'separation', key: 'separation', fmt: (v) => `${v | 0}px` },
  { id: 'sepWeight', key: 'sepWeight', fmt: (v) => v.toFixed(2) },
  { id: 'alignWeight', key: 'alignWeight', fmt: (v) => v.toFixed(2) },
  { id: 'cohWeight', key: 'cohWeight', fmt: (v) => v.toFixed(2) },
  { id: 'maxSpeed', key: 'maxSpeed', fmt: (v) => v.toFixed(1) },
  {
    id: 'trail', key: 'trail', invert: TRAIL_SUM,
    // Slider reads as trail *length*: a high slider value means low fade (long
    // trails). Display the slider position as a percentage of its range.
    fmt: (raw) => `${Math.round((raw / 0.6) * 100)}%`,
  },
  { id: 'size', key: 'size', fmt: (v) => v.toFixed(1) },
];

function syncSlider(s) {
  const el = document.getElementById(s.id);
  const raw = parseFloat(el.value);
  document.getElementById(s.id + 'Val').textContent = s.fmt(raw);
  const applied = s.invert != null ? s.invert - raw : raw;
  if (s.apply) s.apply(applied);
  else flock.params[s.key] = applied;
}

for (const s of sliders) {
  const el = document.getElementById(s.id);
  const param = s.id === 'count' ? flock.params.count : flock.params[s.key];
  el.value = s.invert != null ? s.invert - param : param;
  syncSlider(s);
  el.addEventListener('input', () => syncSlider(s));
}

// ---- Palette swatches ---------------------------------------------------
const palWrap = document.getElementById('palettes');
PALETTES.forEach((p, i) => {
  const sw = document.createElement('div');
  sw.className = 'swatch' + (i === 0 ? ' active' : '');
  sw.title = p.name;
  const css = p.stops.map((c) => `rgb(${c.join(',')})`);
  sw.style.background = `linear-gradient(135deg, ${css.join(',')})`;
  sw.addEventListener('click', () => selectPalette(i));
  palWrap.appendChild(sw);
});

function selectPalette(i) {
  flock.setPalette(i);
  flock.hardClear();
  [...palWrap.children].forEach((c, idx) =>
    c.classList.toggle('active', idx === i)
  );
}

// ---- Buttons ------------------------------------------------------------
const pauseBtn = document.getElementById('pause');
pauseBtn.addEventListener('click', () => {
  pauseBtn.textContent = flock.toggle() ? 'Pause' : 'Play';
});
const visionBtn = document.getElementById('vision');
visionBtn.addEventListener('click', () => {
  flock.params.showVision = !flock.params.showVision;
  visionBtn.classList.toggle('on', flock.params.showVision);
});
document.getElementById('reseed').addEventListener('click', () => flock.reseed());
document.getElementById('save').addEventListener('click', savePNG);
document.getElementById('random').addEventListener('click', surprise);

function savePNG() {
  const a = document.createElement('a');
  a.href = flock.snapshot();
  a.download = `boids-${Date.now()}.png`;
  a.click();
}

// Randomize to a pleasing-but-unexpected flock.
function surprise() {
  const rnd = (min, max) => min + Math.random() * (max - min);
  const set = (id, v) => {
    const el = document.getElementById(id);
    el.value = v;
    el.dispatchEvent(new Event('input'));
  };
  set('count', Math.round(rnd(400, 1800)));
  set('perception', rnd(40, 110));
  set('separation', rnd(14, 40));
  set('sepWeight', rnd(0.9, 2.2));
  set('alignWeight', rnd(0.5, 1.8));
  set('cohWeight', rnd(0.5, 1.6));
  set('maxSpeed', rnd(2.4, 5));
  set('trail', TRAIL_SUM - rnd(0.06, 0.22)); // longish trails
  selectPalette((Math.random() * PALETTES.length) | 0);
  flock.reseed();
}

// ---- Pointer interaction ------------------------------------------------
function pointerPos(e) {
  const rect = canvas.getBoundingClientRect();
  flock.pointer.x = (e.clientX - rect.left) * flock.dpr;
  flock.pointer.y = (e.clientY - rect.top) * flock.dpr;
}

canvas.addEventListener('mousedown', (e) => {
  pointerPos(e);
  flock.pointer.active = true;
  flock.pointer.mode = e.button === 2 ? 2 : 1; // right = scatter
});
canvas.addEventListener('mousemove', (e) => {
  if (flock.pointer.active) pointerPos(e);
});
window.addEventListener('mouseup', () => {
  flock.pointer.active = false;
  flock.pointer.mode = 0;
});
canvas.addEventListener('contextmenu', (e) => e.preventDefault());

// Touch support.
canvas.addEventListener('touchstart', (e) => {
  flock.pointer.active = true;
  flock.pointer.mode = 1;
  pointerPos(e.touches[0]);
}, { passive: true });
canvas.addEventListener('touchmove', (e) => {
  if (flock.pointer.active) pointerPos(e.touches[0]);
}, { passive: true });
window.addEventListener('touchend', () => { flock.pointer.active = false; });

// ---- Keyboard shortcuts -------------------------------------------------
const panel = document.getElementById('panel');
const togglePanel = document.getElementById('togglePanel');
togglePanel.addEventListener('click', () => panel.classList.remove('hidden'));

window.addEventListener('keydown', (e) => {
  if (e.target.tagName === 'INPUT' || e.target.tagName === 'BUTTON') return;
  switch (e.key.toLowerCase()) {
    case ' ': e.preventDefault(); pauseBtn.click(); break;
    case 'v': visionBtn.click(); break;
    case 'r': flock.reseed(); break;
    case 's': savePNG(); break;
    case 'h': panel.classList.toggle('hidden'); break;
  }
});

// ---- Resize + render loop ----------------------------------------------
let resizeTimer;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(() => flock.resize(), 150);
});

function loop() {
  flock.frame();
  requestAnimationFrame(loop);
}
loop();
