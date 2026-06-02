// main.js — UI wiring and the canvas visualizer for Driftwave.
import { Driftwave, SCALES, ROOTS } from './synth.js';

const engine = new Driftwave();

// ---- Populate selects ---------------------------------------------------
const scaleSel = document.getElementById('scale');
Object.keys(SCALES).forEach((name) => {
  const o = document.createElement('option');
  o.value = name;
  o.textContent = name.replace(/_/g, ' ');
  scaleSel.appendChild(o);
});
scaleSel.value = engine.params.scaleName;

const rootSel = document.getElementById('root');
ROOTS.forEach((name, i) => {
  const o = document.createElement('option');
  o.value = i;
  o.textContent = name;
  rootSel.appendChild(o);
});
rootSel.value = engine.params.rootIndex;

// ---- Bind controls ------------------------------------------------------
function bindRange(id, key, fmt = (v) => v) {
  const el = document.getElementById(id);
  el.value = engine.params[key];
  const out = document.getElementById(id + 'Val');
  const update = () => {
    const v = parseFloat(el.value);
    engine.setParam(key, v);
    if (out) out.textContent = fmt(v);
  };
  el.addEventListener('input', update);
  update();
}

bindRange('tempo', 'tempo', (v) => `${v | 0} bpm`);
bindRange('density', 'density', (v) => `${Math.round(v * 100)}%`);
bindRange('reverb', 'reverb', (v) => `${Math.round(v * 100)}%`);
bindRange('volume', 'volume', (v) => `${Math.round(v * 100)}%`);

scaleSel.addEventListener('change', () => {
  engine.setParam('scaleName', scaleSel.value);
});
rootSel.addEventListener('change', () => {
  engine.setParam('rootIndex', parseInt(rootSel.value, 10));
});

// ---- Transport ----------------------------------------------------------
const playBtn = document.getElementById('play');
const status = document.getElementById('status');
playBtn.addEventListener('click', async () => {
  if (engine.running) {
    engine.stop();
    playBtn.textContent = '▶ Play';
    playBtn.classList.remove('playing');
    status.textContent = 'paused';
  } else {
    await engine.start();
    playBtn.textContent = '⏸ Pause';
    playBtn.classList.add('playing');
    status.textContent = 'drifting…';
  }
});

// ---- Visualizer ---------------------------------------------------------
const canvas = document.getElementById('viz');
const ctx = canvas.getContext('2d');

function fitCanvas() {
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = canvas.clientWidth * dpr;
  canvas.height = canvas.clientHeight * dpr;
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
}
window.addEventListener('resize', fitCanvas);
fitCanvas();

function draw() {
  requestAnimationFrame(draw);
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;
  ctx.clearRect(0, 0, w, h);

  const spectrum = engine.getSpectrum();
  const wave = engine.getWaveform();

  // Frequency bars (lower half mirrored), drawn faintly behind the wave.
  if (spectrum) {
    const bars = 64;
    const step = Math.floor(spectrum.length / bars);
    const bw = w / bars;
    for (let i = 0; i < bars; i++) {
      const v = spectrum[i * step] / 255;
      const bh = v * h * 0.7;
      const hue = 250 - v * 90;
      ctx.fillStyle = `hsla(${hue}, 80%, 65%, 0.18)`;
      ctx.fillRect(i * bw, h - bh, bw - 1.5, bh);
    }
  }

  // Waveform line.
  if (wave) {
    ctx.lineWidth = 2;
    const grad = ctx.createLinearGradient(0, 0, w, 0);
    grad.addColorStop(0, '#b98cff');
    grad.addColorStop(1, '#6ad7ff');
    ctx.strokeStyle = grad;
    ctx.beginPath();
    const slice = w / wave.length;
    for (let i = 0; i < wave.length; i++) {
      // Byte data is centered on 128 (silence); map it symmetrically around the
      // vertical middle so the trace is centered and leaves a little headroom.
      const y = h / 2 + ((wave[i] - 128) / 128) * (h * 0.45);
      const x = i * slice;
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.stroke();
  } else {
    // Idle: a calm flat line.
    ctx.strokeStyle = 'rgba(255,255,255,0.12)';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(0, h / 2);
    ctx.lineTo(w, h / 2);
    ctx.stroke();
  }
}
draw();
