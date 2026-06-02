# Fractal Explorer

An interactive Mandelbrot and Julia set explorer that renders in real time —
zoom, pan, recolor, and cycle through the complex plane. Pure HTML5 Canvas, no
dependencies, no build. Just open `index.html`.

```
fractal/
  index.html   # UI shell
  style.css    # glassy control panel
  fractal.js   # the escape-time renderer + cosine palettes
  main.js      # interaction, render pipeline, UI wiring
```

## Controls

- **Scroll** to zoom toward the cursor, **drag** to pan, **double-click** to
  zoom in on a point.
- **Mandelbrot / Julia** toggle. In Julia mode, hold **Shift** and move the
  mouse to morph the Julia constant `c` live.
- **Detail** sets the iteration cap (higher = more structure in deep zooms,
  slower).
- **Color Density** and **Color Shift** remap the palette; **Cycle Colors**
  animates the shift.
- Five cosine-based palettes, **Reset View**, and **Save PNG**.

## How it renders

Each pixel runs the escape-time iteration `z → z² + c`. Points that never
escape (within the iteration cap) are the set interior, drawn black. Escaped
points are colored by a **smooth iteration count** — the integer escape step
blended with how far past the escape radius the orbit overshot — which removes
the harsh concentric banding you'd otherwise get.

For responsiveness the renderer draws into an offscreen ImageData buffer: a
low-resolution **preview** during pans/zooms, then a debounced crisp
full-resolution pass once you settle. Palettes are 1024-entry lookup tables
baked from three phase-shifted cosines, so recoloring and cycling are cheap.
