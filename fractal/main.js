// main.js — interaction, rendering pipeline, and UI for the Fractal Explorer.
//
// Rendering uses an offscreen buffer: we compute the fractal into an ImageData
// at a chosen resolution, then blit it (scaled) onto the visible canvas. During
// pans/zooms we render a low-res *preview* for responsiveness, then debounce a
// crisp full-resolution pass once interaction settles.
import { Fractal, PALETTE_PRESETS } from './fractal.js';

const canvas = document.getElementById('stage');
const ctx = canvas.getContext('2d');
const fractal = new Fractal();

const FULL_CAP = 2000;   // max width (CSS px) for the crisp pass — high enough
                         // that typical displays render 1:1 (no upscale blur)
const PREVIEW_DIV = 3;   // preview renders at 1/3 the linear resolution
const ANIM_CAP = 640;    // cap during color cycling to keep it smooth

const buffer = document.createElement('canvas');
const bctx = buffer.getContext('2d');
let imgCache = null;     // reused ImageData, reallocated only when dims change

let cssW = 0, cssH = 0;

function fitCanvas() {
  cssW = window.innerWidth;
  cssH = window.innerHeight;
  canvas.width = cssW;
  canvas.height = cssH;
  renderFull();
}

// Render at the given target width (CSS px), preserving aspect ratio, then
// stretch the buffer across the full visible canvas.
function renderAt(targetW) {
  const aspect = cssW / cssH;
  const rw = Math.max(1, Math.round(Math.min(targetW, cssW)));
  const rh = Math.max(1, Math.round(rw / aspect));
  if (buffer.width !== rw || buffer.height !== rh) {
    buffer.width = rw;
    buffer.height = rh;
    imgCache = null; // dims changed — drop the stale buffer
  }
  if (!imgCache || imgCache.width !== rw || imgCache.height !== rh) {
    imgCache = bctx.createImageData(rw, rh);
  }
  fractal.render(imgCache, rw, rh);
  bctx.putImageData(imgCache, 0, 0);

  ctx.imageSmoothingEnabled = rw < cssW; // smooth only when upscaling a preview
  ctx.drawImage(buffer, 0, 0, rw, rh, 0, 0, cssW, cssH);
}

let fullTimer = null;
function renderPreview() {
  renderAt(cssW / PREVIEW_DIV);
  updateReadout();
}
function renderFull() {
  renderAt(FULL_CAP);
  updateReadout();
}
function scheduleFull() {
  clearTimeout(fullTimer);
  fullTimer = setTimeout(renderFull, 90);
}

// ---- Readout ------------------------------------------------------------
const readout = document.getElementById('readout');
function updateReadout() {
  // Zoom is relative to the mode's default (reset) scale.
  const base = fractal.mode === 'julia' ? 1.6 : 1.4;
  const zoom = (base / fractal.view.scale);
  const zoomStr = zoom >= 1000
    ? zoom.toExponential(2)
    : zoom.toFixed(zoom < 10 ? 2 : 0);
  let html =
    `<b>mode</b> ${fractal.mode}<br />` +
    `<b>center</b> ${fractal.view.cx.toFixed(6)}, ${fractal.view.cy.toFixed(6)}<br />` +
    `<b>zoom</b> ${zoomStr}×`;
  if (fractal.mode === 'julia') {
    html += `<br /><b>c</b> ${fractal.juliaC.x.toFixed(4)}, ${fractal.juliaC.y.toFixed(4)}`;
  }
  readout.innerHTML = html;
}

// ---- Palette swatches ---------------------------------------------------
const palWrap = document.getElementById('palettes');
Object.keys(PALETTE_PRESETS).forEach((name, i) => {
  const sw = document.createElement('div');
  sw.className = 'swatch' + (name === fractal.paletteName ? ' active' : '');
  sw.title = name;
  // Preview gradient sampled from the same cosine palette.
  const p = PALETTE_PRESETS[name];
  const stops = [];
  for (let s = 0; s <= 4; s++) {
    const t = s / 4;
    const r = 255 * (p.bias[0] + 0.5 * Math.cos(2 * Math.PI * (p.freq[0] * t + p.phase[0])));
    const g = 255 * (p.bias[1] + 0.5 * Math.cos(2 * Math.PI * (p.freq[1] * t + p.phase[1])));
    const b = 255 * (p.bias[2] + 0.5 * Math.cos(2 * Math.PI * (p.freq[2] * t + p.phase[2])));
    stops.push(`rgb(${r | 0},${g | 0},${b | 0})`);
  }
  sw.style.background = `linear-gradient(90deg, ${stops.join(',')})`;
  sw.addEventListener('click', () => {
    fractal.setPalette(name);
    [...palWrap.children].forEach((c) => c.classList.toggle('active', c === sw));
    renderFull();
  });
  palWrap.appendChild(sw);
});

// ---- Sliders ------------------------------------------------------------
function bindSlider(id, get, set, fmt) {
  const el = document.getElementById(id);
  const out = document.getElementById(id + 'Val');
  el.value = get();
  out.textContent = fmt(get());
  el.addEventListener('input', () => {
    const v = parseFloat(el.value);
    set(v);
    out.textContent = fmt(v);
    renderPreview();
    scheduleFull();
  });
}
bindSlider('iter', () => fractal.maxIter, (v) => (fractal.maxIter = v), (v) => v | 0);
bindSlider('density', () => fractal.colorDensity, (v) => (fractal.colorDensity = v), (v) => v | 0);
bindSlider('shift', () => fractal.colorShift, (v) => (fractal.colorShift = v), (v) => v | 0);

// ---- Mode toggle --------------------------------------------------------
const modeMandel = document.getElementById('modeMandel');
const modeJulia = document.getElementById('modeJulia');
function setMode(mode) {
  fractal.mode = mode;
  modeMandel.classList.toggle('active', mode === 'mandelbrot');
  modeJulia.classList.toggle('active', mode === 'julia');
  fractal.reset();
  renderFull();
}
modeMandel.addEventListener('click', () => setMode('mandelbrot'));
modeJulia.addEventListener('click', () => setMode('julia'));

// ---- Buttons ------------------------------------------------------------
document.getElementById('reset').addEventListener('click', () => {
  fractal.reset();
  renderFull();
});
document.getElementById('save').addEventListener('click', () => {
  // Render a crisp frame straight onto the visible canvas before exporting.
  renderFull();
  const a = document.createElement('a');
  a.href = canvas.toDataURL('image/png');
  a.download = `fractal-${Date.now()}.png`;
  a.click();
});

// Color cycling animation.
const animateBtn = document.getElementById('animate');
let animating = false;
let rafId = null;
function animTick() {
  if (!animating) return;
  fractal.colorShift = (fractal.colorShift + 3) % 1024;
  document.getElementById('shift').value = fractal.colorShift;
  document.getElementById('shiftVal').textContent = fractal.colorShift | 0;
  renderAt(ANIM_CAP);
  rafId = requestAnimationFrame(animTick);
}
animateBtn.addEventListener('click', () => {
  animating = !animating;
  animateBtn.classList.toggle('active', animating);
  if (animating) animTick();
  else { cancelAnimationFrame(rafId); renderFull(); }
});

// ---- Pan / zoom ---------------------------------------------------------
let dragging = false;
let last = { x: 0, y: 0 };

canvas.addEventListener('mousedown', (e) => {
  dragging = true;
  last = { x: e.clientX, y: e.clientY };
  canvas.classList.add('dragging');
});

window.addEventListener('mousemove', (e) => {
  // Julia morph: hold Shift and move to set the constant from the cursor.
  // Skip when the cursor is over the control panel so hovering the UI (while
  // not dragging) doesn't morph c.
  if (fractal.mode === 'julia' && e.shiftKey && !dragging &&
      !(e.target.closest && e.target.closest('#panel'))) {
    const c = fractal.pixelToComplex(e.clientX, e.clientY, cssW, cssH);
    fractal.juliaC = { x: c.re, y: c.im };
    renderPreview();
    scheduleFull();
    return;
  }
  if (!dragging) return;
  const dx = e.clientX - last.x;
  const dy = e.clientY - last.y;
  last = { x: e.clientX, y: e.clientY };
  // Pan: shift the center by the dragged distance in complex units.
  const aspect = cssW / cssH;
  fractal.view.cx -= (dx / cssW) * 2 * fractal.view.scale * aspect;
  fractal.view.cy -= (dy / cssH) * 2 * fractal.view.scale;
  renderPreview();
});

window.addEventListener('mouseup', () => {
  if (!dragging) return;
  dragging = false;
  canvas.classList.remove('dragging');
  renderFull();
});

canvas.addEventListener('wheel', (e) => {
  e.preventDefault();
  const c = fractal.pixelToComplex(e.clientX, e.clientY, cssW, cssH);
  const factor = e.deltaY > 0 ? 1.18 : 0.85; // wheel down = zoom out
  fractal.zoomAt(c.re, c.im, factor);
  renderPreview();
  scheduleFull();
}, { passive: false });

canvas.addEventListener('dblclick', (e) => {
  const c = fractal.pixelToComplex(e.clientX, e.clientY, cssW, cssH);
  fractal.zoomAt(c.re, c.im, 0.5);
  renderFull();
});

let resizeTimer = null;
window.addEventListener('resize', () => {
  clearTimeout(resizeTimer);
  resizeTimer = setTimeout(fitCanvas, 120);
});

fitCanvas();
