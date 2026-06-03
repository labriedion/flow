"""Regenerate the gallery and the README table from the mission registry.

The top-level index.html stops being hand-maintained and becomes a build
artifact of the loop: cards are generated from the registry, each section is
sorted by the surprise proxy (so the page literally arranges itself by how much
each mission amplified its rule), and proposed-but-unbuilt missions show up as
"on the loom". The crafted chrome — hero, palette, the live flow-field behind
it — is reproduced verbatim.
"""

import os

from . import registry, surprise

ROOT = registry.ROOT

SCORE_TIP = (
    "output compresses to this many times the size of the rule that made it "
    "— a proxy for emergence, not a judgment of taste"
)

# ---------------------------------------------------------------------------
# The crafted chrome, reproduced verbatim (plus a .score badge and .loom list).
# Kept as plain strings — never .format()'d — so the CSS/JS braces are safe.
# ---------------------------------------------------------------------------

TOP = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>flow — build whatever it wants</title>
  <meta name="description" content="A collection of small programs Claude Code built when the only brief was: build whatever you want. It keeps reaching for emergence." />
  <style>
    :root {
      --bg: #05070d;
      --panel-bg: rgba(16, 18, 27, 0.72);
      --panel-border: rgba(255, 255, 255, 0.08);
      --accent: #21d4fd;
      --accent-2: #b388ff;
      --text: #e7ecf3;
      --muted: #8b93a7;
      --faint: #545c70;
      font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
    }
    * { box-sizing: border-box; }
    html, body {
      margin: 0;
      min-height: 100%;
      background: var(--bg);
      color: var(--text);
      -webkit-font-smoothing: antialiased;
    }
    /* live flow-field hero, fixed behind everything */
    #field {
      position: fixed;
      inset: 0;
      width: 100vw;
      height: 100vh;
      display: block;
      z-index: 0;
      pointer-events: none;
    }
    /* a vignette so text stays readable over the drift */
    #veil {
      position: fixed;
      inset: 0;
      z-index: 1;
      pointer-events: none;
      background:
        radial-gradient(120% 80% at 50% 0%, rgba(5,7,13,0.35), rgba(5,7,13,0.78) 60%, rgba(5,7,13,0.93) 100%);
    }
    main {
      position: relative;
      z-index: 2;
      max-width: 920px;
      margin: 0 auto;
      padding: 0 22px 90px;
    }

    /* ---- hero / manifesto ---- */
    header.hero {
      padding: 16vh 0 7vh;
    }
    .kicker {
      font-size: 11px;
      letter-spacing: 0.34em;
      text-transform: uppercase;
      color: var(--accent);
      margin: 0 0 18px;
    }
    h1.title {
      font-size: clamp(54px, 13vw, 132px);
      line-height: 0.9;
      letter-spacing: 0.02em;
      margin: 0;
      font-weight: 700;
      background: linear-gradient(120deg, var(--text) 30%, var(--accent) 70%, var(--accent-2));
      -webkit-background-clip: text;
      background-clip: text;
      color: transparent;
    }
    .lede {
      font-size: clamp(15px, 2.1vw, 19px);
      line-height: 1.6;
      max-width: 30em;
      margin: 26px 0 0;
      color: var(--text);
    }
    .lede .em { color: var(--accent); }
    .note {
      font-size: 13.5px;
      line-height: 1.7;
      max-width: 33em;
      margin: 22px 0 0;
      color: var(--muted);
    }
    .note strong { color: var(--text); font-weight: 600; }

    /* ---- section label ---- */
    .section-label {
      display: flex;
      align-items: baseline;
      gap: 12px;
      margin: 54px 0 18px;
      letter-spacing: 0.18em;
      text-transform: uppercase;
      font-size: 11px;
      color: var(--muted);
    }
    .section-label::before {
      content: "";
      width: 22px;
      height: 1px;
      background: var(--accent);
      align-self: center;
    }
    .section-label .how {
      margin-left: auto;
      letter-spacing: 0.06em;
      text-transform: none;
      color: var(--faint);
    }

    /* ---- grid of projects ---- */
    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(248px, 1fr));
      gap: 14px;
    }
    a.card {
      display: flex;
      flex-direction: column;
      text-decoration: none;
      color: inherit;
      background: var(--panel-bg);
      border: 1px solid var(--panel-border);
      border-radius: 14px;
      padding: 16px 16px 14px;
      backdrop-filter: blur(13px) saturate(140%);
      -webkit-backdrop-filter: blur(13px) saturate(140%);
      transition: transform 0.16s ease, border-color 0.16s ease, box-shadow 0.16s ease;
      position: relative;
      overflow: hidden;
    }
    a.card::after {
      content: "";
      position: absolute;
      inset: 0;
      background: radial-gradient(80% 60% at 0% 0%, rgba(33,212,253,0.10), transparent 70%);
      opacity: 0;
      transition: opacity 0.18s ease;
      pointer-events: none;
    }
    a.card:hover {
      transform: translateY(-3px);
      border-color: rgba(33,212,253,0.4);
      box-shadow: 0 16px 40px rgba(0,0,0,0.5);
    }
    a.card:hover::after { opacity: 1; }
    .card .top {
      display: flex;
      align-items: center;
      gap: 9px;
      margin-bottom: 9px;
    }
    .card h2 {
      font-size: 15px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      margin: 0;
      color: var(--text);
    }
    .card .arrow {
      margin-left: auto;
      color: var(--accent);
      font-size: 13px;
      opacity: 0.6;
      transition: transform 0.16s ease, opacity 0.16s ease;
    }
    a.card:hover .arrow { opacity: 1; transform: translate(2px, -2px); }
    .card .blurb {
      font-size: 12.5px;
      line-height: 1.55;
      color: var(--text);
      opacity: 0.9;
      margin: 0 0 12px;
      flex: 1;
    }
    .card .rule {
      font-size: 11px;
      line-height: 1.5;
      color: var(--accent);
      opacity: 0.85;
      margin: 0 0 12px;
      font-style: italic;
    }
    .card .foot {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-wrap: wrap;
      border-top: 1px solid rgba(255,255,255,0.06);
      padding-top: 10px;
    }
    .tag {
      font-size: 10px;
      letter-spacing: 0.05em;
      color: var(--muted);
      background: rgba(255,255,255,0.05);
      border-radius: 6px;
      padding: 3px 7px;
    }
    .run {
      font-size: 10.5px;
      color: var(--muted);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 55%;
    }
    .run b { color: var(--accent); font-weight: 600; }
    .score {
      font-size: 10px;
      letter-spacing: 0.04em;
      margin-left: auto;
      color: var(--accent);
      background: rgba(33, 212, 253, 0.1);
      border: 1px solid rgba(33, 212, 253, 0.25);
      border-radius: 6px;
      padding: 3px 7px;
      white-space: nowrap;
      cursor: help;
    }

    /* ---- on the loom: proposed-but-unbuilt missions ---- */
    .loom-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(248px, 1fr)); gap: 14px; }
    .loom-item {
      background: rgba(16, 18, 27, 0.5);
      border: 1px dashed rgba(255, 255, 255, 0.14);
      border-radius: 14px;
      padding: 15px 16px;
    }
    .loom-item .name {
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--accent-2);
      margin: 0 0 7px;
    }
    .loom-item .brief {
      font-size: 11.5px;
      line-height: 1.55;
      color: var(--muted);
      margin: 0;
    }

    footer {
      margin-top: 64px;
      padding-top: 22px;
      border-top: 1px solid var(--panel-border);
      font-size: 12px;
      line-height: 1.7;
      color: var(--muted);
    }
    footer a { color: var(--accent); text-decoration: none; }
    footer a:hover { text-decoration: underline; }

    @media (max-width: 540px) {
      header.hero { padding: 11vh 0 5vh; }
      .run { max-width: 100%; }
    }
    @media (prefers-reduced-motion: reduce) {
      a.card { transition: none; }
    }
  </style>
</head>
<body>
  <canvas id="field"></canvas>
  <div id="veil"></div>

  <main>
    <header class="hero">
      <p class="kicker">a collection · build whatever it wants</p>
      <h1 class="title">flow</h1>
      <p class="lede">
        I send Claude Code off on missions to build <span class="em">whatever it
        wants</span> — and see what it comes back with.
      </p>
      <p class="note">
        What it keeps coming back with is <strong>emergence</strong>. Given a blank
        brief, again and again it reaches for the same idea: a handful of simple,
        local rules — followed faithfully by thousands of tiny parts that have no
        plan — blooming into something nobody choreographed. A flock. A dune. A
        coastline. The drift behind this page is one of them, running live.
      </p>
    </header>
"""

# %%SECTIONS%% gets spliced in here

BOTTOM = """
    <footer>
      %%COUNT%% small things, each built on a mission with no spec but its own
      taste — now sorted by how much each amplified its rule (a proxy for
      emergence, generated by <a href="./loom/README.md">loom</a>, not a judgment
      of taste). Source &amp; how-to-run for every one lives in the
      <a href="./README.md">README</a>. The throughline — simple rules, no
      conductor, surprising whole — wasn't planned. It just kept falling out.
    </footer>
  </main>

  <script>
    // A live flow field — the emblem of this whole collection, drifting behind it.
    // Particles read a smooth, slowly-evolving vector field and trail light.
    // Pure vanilla, no deps, kind to reduced-motion and hidden tabs.
    (function () {
      const canvas = document.getElementById("field");
      const ctx = canvas.getContext("2d", { alpha: false });
      const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

      let W = 0, H = 0, dpr = 1;
      let particles = [];
      let t = 0;
      let raf = null;

      const TAU = Math.PI * 2;

      function resize() {
        dpr = Math.min(window.devicePixelRatio || 1, 2);
        W = window.innerWidth;
        H = window.innerHeight;
        canvas.width = Math.floor(W * dpr);
        canvas.height = Math.floor(H * dpr);
        canvas.style.width = W + "px";
        canvas.style.height = H + "px";
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
        ctx.fillStyle = "#05070d";
        ctx.fillRect(0, 0, W, H);
        seed();
        if (reduced) settle();   // reduced-motion: hold one static frame
      }

      function seed() {
        // density scales with screen area, capped for weaker machines
        const target = Math.min(620, Math.round((W * H) / 2600));
        particles = new Array(target).fill(0).map(spawn);
      }

      function spawn() {
        return {
          x: Math.random() * W,
          y: Math.random() * H,
          // each particle keeps a hue between cyan and violet
          h: 188 + Math.random() * 82,
          life: 60 + Math.random() * 180,
        };
      }

      // Smooth pseudo-noise field from summed sinusoids — cheap, organic, curl-like.
      function angleAt(x, y, time) {
        const a =
          Math.sin(x * 0.0016 + time) +
          Math.sin(y * 0.0021 - time * 0.8) +
          Math.sin((x + y) * 0.0012 + time * 0.6) +
          Math.sin((x - y) * 0.0009 - time * 0.4);
        return a * 0.9 * TAU;
      }

      // advance + draw one frame's worth of the field, no scheduling
      function draw() {
        t += 0.0016;
        // fade the previous frame slightly to leave trails
        ctx.fillStyle = "rgba(5, 7, 13, 0.055)";
        ctx.fillRect(0, 0, W, H);
        ctx.globalCompositeOperation = "lighter";
        ctx.lineWidth = 1;

        for (const p of particles) {
          const ang = angleAt(p.x, p.y, t);
          const nx = p.x + Math.cos(ang) * 1.1;
          const ny = p.y + Math.sin(ang) * 1.1;

          ctx.strokeStyle = "hsla(" + p.h + ", 90%, 64%, 0.16)";
          ctx.beginPath();
          ctx.moveTo(p.x, p.y);
          ctx.lineTo(nx, ny);
          ctx.stroke();

          p.x = nx;
          p.y = ny;
          p.life -= 1;

          // respawn when it expires or drifts off-screen, so the field stays alive
          if (
            p.life <= 0 ||
            p.x < -4 || p.x > W + 4 ||
            p.y < -4 || p.y > H + 4
          ) {
            Object.assign(p, spawn());
          }
        }
        ctx.globalCompositeOperation = "source-over";
      }

      function step() {
        draw();
        raf = requestAnimationFrame(step);
      }

      // a single calm, static frame — no motion for those who asked for none
      function settle() {
        for (let i = 0; i < 240; i++) draw();
      }

      function start() {
        if (reduced) return;            // honour prefers-reduced-motion
        if (raf == null) raf = requestAnimationFrame(step);
      }
      function stop() {
        if (raf != null) { cancelAnimationFrame(raf); raf = null; }
      }

      window.addEventListener("resize", resize, { passive: true });
      document.addEventListener("visibilitychange", () => {
        if (document.hidden) stop(); else start();
      });

      resize();
      if (!reduced) start();
    })();
  </script>
</body>
</html>
"""

SECTION_LABELS = {
    "browser": ("Open in a browser", "just click — no server, no build"),
    "terminal": ("Run in a terminal", "pure Python stdlib · tests with pytest"),
}


def _esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _card(m, amp):
    arrow = "↗" if m["medium"] == "browser" else "→"
    rows = [
        f'      <a class="card" href="{m["href"]}">',
        f'        <div class="top"><h2>{_esc(m["title"])}</h2><span class="arrow">{arrow}</span></div>',
        f'        <p class="blurb">{_esc(m["blurb"])}</p>',
    ]
    if m.get("rule"):
        rows.append(f'        <p class="rule">rule → {_esc(m["rule"])}</p>')
    foot = [f'<span class="tag">{_esc(m["tag"])}</span>']
    if m.get("run"):
        rest = m["run"].replace("python -m ", "")
        foot.append(f'<span class="run"><b>python -m</b> {_esc(rest)}</span>')
    label = "✦ " + surprise.fmt_amplification(amp)
    foot.append(f'<span class="score" title="{SCORE_TIP}">{label}</span>')
    rows.append('        <div class="foot">' + "".join(foot) + "</div>")
    rows.append("      </a>")
    return "\n".join(rows)


def _section(medium, missions, amps):
    group = [m for m in missions if m["medium"] == medium]
    # the page sorts itself by how much each mission amplified its rule
    group.sort(key=lambda m: amps.get(m["id"], 0), reverse=True)
    if not group:
        return ""
    title, how = SECTION_LABELS[medium]
    out = [
        '    <div class="section-label">',
        f"      {title}",
        f'      <span class="how">{how}</span>',
        "    </div>",
        '    <section class="grid">',
        "",
    ]
    for m in group:
        out.append(_card(m, amps.get(m["id"], 0)))
        out.append("")
    out.append("    </section>")
    return "\n".join(out)


def _loom_section(missions):
    proposed = registry.proposed(missions)
    if not proposed:
        return ""
    out = [
        "",
        '    <div class="section-label">',
        "      On the loom",
        '      <span class="how">proposed by loom · nobody has built these yet</span>',
        "    </div>",
        '    <section class="loom-list">',
        "",
    ]
    for m in proposed:
        out.append('      <div class="loom-item">')
        out.append(f'        <p class="name">{_esc(m["title"])}</p>')
        out.append(f'        <p class="brief">{_esc(m["prompt"])}</p>')
        out.append("      </div>")
        out.append("")
    out.append("    </section>")
    return "\n".join(out)


def build_index(missions):
    """Return the full index.html as a string."""
    built = registry.built(missions)
    amps = {s["id"]: s["amplification"] for s in surprise.score_all(missions)}
    sections = [
        _section("browser", built, amps),
        _section("terminal", built, amps),
        _loom_section(missions),
    ]
    body = "\n\n".join(s for s in sections if s)
    bottom = BOTTOM.replace("%%COUNT%%", str(len(built)))
    return TOP + "\n" + body + "\n" + bottom


def build_readme_table(missions):
    """Reproduce the README project table from the registry, in registry order."""
    lines = ["| Project | What it is | Built with |", "| --- | --- | --- |"]
    for m in registry.built(missions):
        lines.append(f'| [**{m["id"]}**](./{m["id"]}) | {m["summary"]} | {m["built_with"]} |')
    return "\n".join(lines)


TABLE_START = "<!-- loom:table:start -->"
TABLE_END = "<!-- loom:table:end -->"


def write_index(missions, path=None):
    path = path or os.path.join(ROOT, "index.html")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(build_index(missions))
    return path


def update_readme(missions, path=None):
    path = path or os.path.join(ROOT, "README.md")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if TABLE_START not in text or TABLE_END not in text:
        raise RuntimeError(
            f"README is missing the {TABLE_START} / {TABLE_END} markers; "
            "add them around the project table so loom can regenerate it."
        )
    head, rest = text.split(TABLE_START, 1)
    _, tail = rest.split(TABLE_END, 1)
    table = build_readme_table(missions)
    new = f"{head}{TABLE_START}\n{table}\n{TABLE_END}{tail}"
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new)
    return path
