// render_ascii.mjs — a headless run of the glintveil field, printed as text.
//
// This is the artifact loom weighs for the surprise proxy: the rule lives in
// sim.js, and this is what fell out of it — one poke of chemical, seed 7002
// (the seed of the loom proposal itself), left alone for six thousand steps
// under the coral regime. No randomness beyond the seeded sprinkle; the same
// command always prints the same veil. Regenerate it from the repo root with:
//
//   node glintveil/examples/render_ascii.mjs > glintveil/examples/sample_output.txt

import { Field, PRESETS } from '../sim.js';

const W = 144, H = 96, SEED = 7002, STEPS = 6000;
const preset = PRESETS.coral;

const f = new Field(W, H, SEED);
f.feed = preset.feed;
f.kill = preset.kill;
f.seedNoise(10);
for (let i = 0; i < STEPS; i++) f.step();

const s = f.stats();
const lines = [
  '# glintveil — headless snapshot',
  `# field ${W}x${H} (torus), seed ${SEED}, preset coral (feed ${preset.feed}, kill ${preset.kill}), after ${STEPS} steps`,
  "# ten seeded pokes of chemical v, then nothing but the one local rule:",
  '#   react and diffuse with the chemical beside you',
  "# shading is v concentration, ' ' (none) through '@' (peak)",
  '',
  f.ascii(144, 72),
  '',
  `# v: mean ${s.vMean.toFixed(4)}, peak ${s.vMax.toFixed(3)} · active cells (v>0.1): ${s.active} of ${W * H}`,
];
console.log(lines.join('\n'));
