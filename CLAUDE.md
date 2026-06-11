# CLAUDE.md

Instructions for agents working in this repo.

## Browser projects must be tested in a real browser

**No browser project counts as working until it has been opened in an actual
browser — the way a user opens it: `file://`, double-click, no server — and
verified end to end.** Unit tests on the engine are necessary but not
sufficient; this repo once shipped six "working" projects whose pages were
all dead on arrival because module scripts don't load from `file://`, and no
one had ever opened them.

Before calling a browser project done:

1. **Open it via `file://`** (not a dev server) in headless Chromium —
   Playwright is available (`NODE_PATH=/opt/node22/lib/node_modules
   PLAYWRIGHT_BROWSERS_PATH=/opt/pw-browsers`, launch with `--no-sandbox`).
   Load it with `require('playwright')` or `createRequire` — ESM `import`
   ignores `NODE_PATH` and will fail with `ERR_MODULE_NOT_FOUND`.
   Open the gallery (`index.html` at the root) too if cards link to it.
2. **Capture console errors and page errors.** Zero is the bar.
3. **Screenshot after a settle delay and actually look at it.** A rendered
   panel over a black canvas is a failure, not a pass.
4. **Drive one real interaction** — click a button, drag on the canvas — and
   screenshot again to confirm the sim responded.

## The `file://` rule that bit us

Browsers refuse to load `<script type="module">` from `file://` (origin
`null`, blocked by CORS). Therefore: **no ES module syntax in any file a
browser page loads.** The house pattern is classic scripts in dependency
order (`<script src="sim.js"></script><script src="main.js"></script>` at the
end of `<body>`); engines that Node also consumes (tests, headless artifact
generators) end with a guarded CommonJS shim
(`if (typeof module !== 'undefined' && module.exports) module.exports = {...}`)
and the `.mjs` consumers read them via `createRequire`. Watch for top-level
name collisions between files sharing a page — classic scripts share one
scope.

## Other house rules (short version)

- Zero dependencies: Python stdlib or vanilla JS only. Tests for everything
  (`python -m pytest -q`, plus per-project `node <project>/test_sim.mjs`).
- Everything is deterministic by seed; example artifacts must regenerate
  bit-for-bit with the documented command.
- `index.html` (the gallery) and the README project table are **generated**
  by `python -m loom gallery --write` from `loom/missions.json` — edit the
  registry or `loom/gallery.py`, never those outputs by hand.
- New projects get a registry entry in `loom/missions.json` (program files +
  artifact paths are what the surprise proxy weighs), then regenerate the
  gallery.
