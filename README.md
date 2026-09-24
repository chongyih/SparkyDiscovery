# Sparky Discovery — One Roll of Film

A Three.js browser game: Sparky the plush bear steps through an old box camera into three days that
shaped Singapore — 1942, 1965 and 1967. Plays on desktop (keyboard/mouse or gamepad) and phones
(touch, landscape). Chapter 1 (February 1942) is playable; chapters 2–3 are planned (see
[docs/design.md](docs/design.md)).

## Run

```bash
npm install
npm run dev      # http://localhost:5173 (also on your LAN for phone testing)
npm run build    # static build in dist/ — host anywhere (itch.io, GitHub Pages, …)
```

## Controls

| Desktop | Phone |
| --- | --- |
| WASD / arrows move, Shift run, mouse look (click to lock) | Left thumb: move · drag right side: look |
| E talk / use · Space snap photo / continue | Gold button: talk / use · Run toggle |
| J album · R recentre · Esc pause · gamepad supported | Camera icon: album · double-tap: recentre |

Settings (pause menu): graphics tier (Low / Medium / High), volume, music, sound captions,
reduced camera shake & flashes, invert Y.

## Debug URL flags

- `?beat=papers|raid|shelter|blackout|rumours|epilogue` — jump to a beat after pressing Begin.
- `?stats` — FPS / draw calls / triangles overlay.
- `?test` — keep simulating in a hidden tab (automated playtests).

## Project layout

- `src/engine/` — renderer (pmndrs postprocessing, quality tiers, adaptive resolution), input
  (keyboard/mouse/touch via nipplejs/gamepad), third-person camera, characters, collision
  (three-mesh-bvh), audio (Howler), UI, photo album, effects, newspaper puzzle.
- `src/chapters/` — chapter scripts and text (`ww2-text.js` holds all Chapter 1 writing + sources).
- `public/assets/` — models (Blender-built, meshopt-compressed, desktop + `-mobile` variants),
  audio (with licences in `audio/README.md`), fonts (OFL).
- `tools/` — reproducible Blender / audio build scripts.
- `docs/research/` — historical, architectural and costume research with sources.
