# Flow Field Studio

A generative-art toy: thousands of particles drift across the screen, each
step choosing a heading from an evolving 3D simplex-noise field. Trails are
drawn with additive blending and a slow fade, so the structure of the noise
field paints itself in light.

**Zero dependencies, zero build step.** Just open `index.html` in a browser.

```
flowfield/
  index.html    # UI shell
  style.css     # glassy control panel
  main.js       # UI wiring + render loop
  flowfield.js  # the simulation engine
  noise.js      # seedable 2D/3D simplex noise (public-domain port)
  palettes.js   # eight curated color ramps
```

## Controls

| Control | What it does |
| --- | --- |
| Particles | how many agents drift at once |
| Speed | step length per frame |
| Noise Scale | zoom of the field — small = sweeping, large = turbulent |
| Curl | how many rotations the noise maps onto |
| Time Warp | how fast the field evolves over time |
| Trail Length | persistence of trails (low fade = long trails) |
| Line Width | stroke thickness |

**Mouse:** hold left-click to attract particles, right-click to repel.
**Keys:** `Space` pause · `C` clear · `R` reseed · `S` save PNG · `H` hide panel.

Hit **Surprise** to randomize everything into a new scene, or **Save PNG**
to keep a frame.
