import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';

// A 1930s box camera (Brownie No. 2 / Six-20 era): pebble-grain leatherette box, aluminium front
// with an art-deco enamel faceplate, a small meniscus lens in a stepped bezel, two reflecting
// finders (front lenses + windows on the top and side), a knurled winding key, shutter lever,
// aperture/time pull tabs, a riveted leather handle and a red film-counter window on the back.
// No brand marks. Parts are merged per material, so the whole camera is ~10 draw calls.

// Seeded, so the camera wears the same scuffs every time.
function rng(seed) {
  return () => {
    seed = (seed + 0x6d2b79f5) | 0;
    let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Smooth value noise on an integer lattice (x, y in lattice units). */
function valueNoise(seed) {
  const r = rng(seed);
  const P = 64;
  const v = Float32Array.from({ length: P * P }, r);
  const at = (i, j) => v[((j % P + P) % P) * P + ((i % P + P) % P)];
  return (x, y) => {
    const i = Math.floor(x), j = Math.floor(y);
    let fx = x - i, fy = y - j;
    fx = fx * fx * (3 - 2 * fx); fy = fy * fy * (3 - 2 * fy);
    const a = at(i, j) + (at(i + 1, j) - at(i, j)) * fx;
    const b = at(i, j + 1) + (at(i + 1, j + 1) - at(i, j + 1)) * fx;
    return a + (b - a) * fy;
  };
}

const clamp01 = (x) => (x < 0 ? 0 : x > 1 ? 1 : x);

function canvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return c;
}

function tex(c, color) {
  const t = new THREE.CanvasTexture(c);
  if (color) t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  return t;
}

/**
 * Leatherette: Worley-cell pebble grain, hand-polished pebble tops, and edge wear (every face of
 * the rounded box maps to the full texture, so the texture's border is the box's edges) where the
 * black coating has rubbed through to the brown board. Returns { map, data } where data packs
 * R = height (bump), G = roughness.
 */
function leatherMaps() {
  const N = 512, cell = 6;
  const cells = Math.ceil(N / cell) + 2;
  const r = rng(1931);
  const pts = Float32Array.from({ length: cells * cells * 2 }, r);
  const mottle = valueNoise(7), scuff = valueNoise(11), fine = valueNoise(13);
  const col = canvas(N, N), dat = canvas(N, N);
  const ci = col.getContext('2d').createImageData(N, N), di = dat.getContext('2d').createImageData(N, N);
  for (let y = 0; y < N; y++) {
    for (let x = 0; x < N; x++) {
      // Worley F1/F2 → domed pebbles separated by fine creases.
      const gx = Math.floor(x / cell), gy = Math.floor(y / cell);
      let f1 = 1e9, f2 = 1e9;
      for (let j = -1; j <= 1; j++) {
        for (let i = -1; i <= 1; i++) {
          const cx = gx + i, cy = gy + j;
          const k = (((cy + 1) % cells) * cells + ((cx + 1) % cells)) * 2;
          const px = (cx + 0.15 + pts[k] * 0.7) * cell, py = (cy + 0.15 + pts[k + 1] * 0.7) * cell;
          const d = (px - x) ** 2 + (py - y) ** 2;
          if (d < f1) { f2 = f1; f1 = d; } else if (d < f2) f2 = d;
        }
      }
      const crease = clamp01((Math.sqrt(f2) - Math.sqrt(f1)) / (cell * 0.42));
      const dome = clamp01(1 - Math.sqrt(f1) / (cell * 0.9));
      let h = Math.pow(crease, 0.55) * (0.55 + 0.45 * dome);
      const u = x / N, v = y / N;
      const m = mottle(u * 9, v * 9);
      // Edge wear: rubbed through near the box edges, broken up by noise.
      const e = Math.min(u, 1 - u, v, 1 - v);
      const edge = clamp01(1 - e / 0.06);
      const wear = clamp01((edge * edge * 1.1 + (scuff(u * 18, v * 18) - 0.5) * 1.1 + fine(u * 140, v * 140) * 0.25 - 0.62) * 4);
      // Light scuffs scattered over the faces.
      const rub = clamp01((scuff(u * 22 + 5, v * 22) - 0.72) * 3) * h;
      let cr = 22, cg = 21, cb = 20;
      const shade = (0.62 + 0.55 * h) * (0.88 + 0.24 * m) + rub * 0.5;
      cr *= shade; cg *= shade; cb *= shade;
      const wr = 70 + 34 * fine(u * 90, v * 90), wg = wr * 0.72, wb = wr * 0.52;
      const o = (y * N + x) * 4;
      ci.data[o] = cr + (wr - cr) * wear;
      ci.data[o + 1] = cg + (wg - cg) * wear;
      ci.data[o + 2] = cb + (wb - cb) * wear;
      ci.data[o + 3] = 255;
      h = h * (1 - wear * 0.8) + 0.2 * wear; // worn patches are flatter
      di.data[o] = h * 255;
      di.data[o + 1] = (0.78 - 0.26 * h * (0.6 + 0.4 * m) + 0.12 * wear) * 255;
      di.data[o + 2] = 0;
      di.data[o + 3] = 255;
    }
  }
  col.getContext('2d').putImageData(ci, 0, 0);
  dat.getContext('2d').putImageData(di, 0, 0);
  return { map: tex(col, true), data: tex(dat, false) };
}

/**
 * Art-deco faceplate: black enamel panel on brushed aluminium with a sunburst around the lens,
 * a stepped finder band and a fluted foot. The same drawing is made twice: once in colour, once
 * as data (R = height, G = roughness, B = metalness), so enamel and metal shade differently.
 * `pw`/`ph` are the plate's size in model units; `lens` and `finders` are centres in plate space.
 */
function faceplateMaps(pw, ph, lens, finders) {
  const PW = 512, PH = Math.round((PW * ph) / pw);
  const s = PW / pw;
  const X = (x) => (x + pw / 2) * s, Y = (y) => (ph / 2 - y) * s;
  const draw = (g, METAL, ENAMEL) => {
    const rrect = (x0, y0, x1, y1, rad) => {
      g.beginPath();
      g.roundRect(X(x0), Y(y1), (x1 - x0) * s, (y1 - y0) * s, rad * s);
    };
    const disc = (x, y, rad) => { g.beginPath(); g.arc(X(x), Y(y), rad * s, 0, Math.PI * 2); g.fill(); };
    const hw = pw / 2, hh = ph / 2;
    g.fillStyle = METAL; g.fillRect(0, 0, PW, PH);
    // Enamel panel inside a bright border, with a pinline inset.
    const pi = 0.032;
    g.fillStyle = ENAMEL; rrect(-hw + pi, -hh + pi, hw - pi, hh - pi, 0.02); g.fill();
    g.strokeStyle = METAL; g.lineWidth = 0.007 * s;
    rrect(-hw + pi + 0.018, -hh + pi + 0.018, hw - pi - 0.018, hh - pi - 0.018, 0.012); g.stroke();
    // Sunburst from the lens, clipped to the panel.
    g.save();
    rrect(-hw + pi + 0.03, -hh + pi + 0.03, hw - pi - 0.03, hh - pi - 0.03, 0.01); g.clip();
    g.fillStyle = METAL;
    const rays = 32;
    for (let i = 0; i < rays; i++) {
      const a = (i / rays) * Math.PI * 2, w = i % 2 ? 0.011 : 0.026;
      g.beginPath();
      g.moveTo(X(lens.x + Math.cos(a - w) * 0.26), Y(lens.y + Math.sin(a - w) * 0.26));
      g.lineTo(X(lens.x + Math.cos(a - w * 0.35) * 1.3), Y(lens.y + Math.sin(a - w * 0.35) * 1.3));
      g.lineTo(X(lens.x + Math.cos(a + w * 0.35) * 1.3), Y(lens.y + Math.sin(a + w * 0.35) * 1.3));
      g.lineTo(X(lens.x + Math.cos(a + w) * 0.26), Y(lens.y + Math.sin(a + w) * 0.26));
      g.fill();
    }
    g.restore();
    // Stepped (ziggurat) finder band across the top.
    const top = hh - pi - 0.03, b = 0.33, x0 = -hw + pi + 0.03, x1 = hw - pi - 0.03;
    g.fillStyle = METAL;
    g.beginPath();
    [[x0, top], [x1, top], [x1, b], [0.13, b], [0.13, b - 0.03], [0.065, b - 0.03], [0.065, b - 0.06],
      [-0.065, b - 0.06], [-0.065, b - 0.03], [-0.13, b - 0.03], [-0.13, b], [x0, b]]
      .forEach(([x, y], i) => (i ? g.lineTo(X(x), Y(y)) : g.moveTo(X(x), Y(y))));
    g.closePath(); g.fill();
    g.fillStyle = ENAMEL;
    for (const y of [b + 0.022, top - 0.022]) g.fillRect(X(x0 + 0.012), Y(y + 0.004), (x1 - x0 - 0.024) * s, 0.008 * s);
    for (const f of finders) {
      rrect(f.x - 0.085, f.y - 0.07, f.x + 0.085, f.y + 0.07, 0.02); g.fill();
      g.fillStyle = METAL; rrect(f.x - 0.076, f.y - 0.061, f.x + 0.076, f.y + 0.061, 0.014); g.fill();
      g.fillStyle = ENAMEL; rrect(f.x - 0.068, f.y - 0.053, f.x + 0.068, f.y + 0.053, 0.01); g.fill();
    }
    // Diamond keystone in the band's centre step.
    g.beginPath();
    [[0, b + 0.07], [0.03, b + 0.02], [0, b - 0.03], [-0.03, b + 0.02]].forEach(([x, y], i) => (i ? g.lineTo(X(x), Y(y)) : g.moveTo(X(x), Y(y))));
    g.fill();
    // Rings around the lens seat.
    g.fillStyle = METAL; disc(lens.x, lens.y, 0.245);
    g.fillStyle = ENAMEL; disc(lens.x, lens.y, 0.23);
    g.fillStyle = METAL; disc(lens.x, lens.y, 0.214);
    // Fluted foot.
    const fb = -hh + pi + 0.03, ft = fb + 0.085;
    g.fillStyle = METAL; g.fillRect(X(x0), Y(ft), (x1 - x0) * s, (ft - fb) * s);
    g.fillStyle = ENAMEL;
    for (let x = x0 + 0.02; x < x1 - 0.01; x += 0.028) g.fillRect(X(x), Y(ft - 0.014), 0.009 * s, (ft - fb - 0.028) * s);
  };
  const col = canvas(PW, PH), dat = canvas(PW, PH);
  const cg = col.getContext('2d'), dg = dat.getContext('2d');
  draw(cg, '#c9c5bc', '#15130f');
  draw(dg, 'rgb(210,70,255)', 'rgb(70,105,0)');
  // Brushed grain, grime and scratches.
  const r = rng(1934), grime = valueNoise(3), fine = valueNoise(5);
  const ci = cg.getImageData(0, 0, PW, PH), di = dg.getImageData(0, 0, PW, PH);
  const rows = Float32Array.from({ length: PH }, r);
  for (let y = 0; y < PH; y++) {
    for (let x = 0; x < PW; x++) {
      const o = (y * PW + x) * 4;
      const metal = di.data[o + 2] / 255;
      const brush = rows[y] * 0.6 + fine(x * 0.02, y * 1.7) * 0.4;
      const u = x / PW, v = y / PH;
      const edge = Math.min(u, 1 - u, v, 1 - v);
      const dirt = clamp01(grime(u * 6, v * 9) * 0.7 + clamp01(1 - edge / 0.08) * 0.5 - 0.35);
      const k = (1 + metal * (brush - 0.5) * 0.16) * (1 - dirt * 0.28);
      ci.data[o] *= k; ci.data[o + 1] *= k; ci.data[o + 2] *= k * 0.98;
      di.data[o + 1] = clamp01(di.data[o + 1] / 255 + metal * (brush - 0.5) * 0.12 + dirt * 0.18) * 255;
    }
  }
  cg.putImageData(ci, 0, 0); dg.putImageData(di, 0, 0);
  // Fine scratches: bright on metal, chipped to metal on enamel.
  for (let i = 0; i < 45; i++) {
    const x = r() * PW, y = r() * PH, a = r() * Math.PI, l = 4 + r() * 22;
    cg.strokeStyle = `rgba(214,210,200,${0.05 + r() * 0.12})`;
    cg.lineWidth = 0.6;
    cg.beginPath(); cg.moveTo(x, y); cg.lineTo(x + Math.cos(a) * l, y + Math.sin(a) * l); cg.stroke();
  }
  return { map: tex(col, true), data: tex(dat, false) };
}

let maps = null;
function sharedMaps(pw, ph, lens, finders) {
  maps ??= { leather: leatherMaps(), plate: faceplateMaps(pw, ph, lens, finders) };
  return maps;
}

/** Collects transformed parts per material and merges them into one mesh each. */
class Parts {
  constructor() { this.byMat = new Map(); }

  add(geo, mat, p = [0, 0, 0], r = [0, 0, 0], s = [1, 1, 1]) {
    const m = new THREE.Matrix4().compose(new THREE.Vector3(...p), new THREE.Quaternion().setFromEuler(new THREE.Euler(...r)), new THREE.Vector3(...s));
    const g = (geo.index ? geo.toNonIndexed() : geo.clone()).applyMatrix4(m);
    for (const k of Object.keys(g.attributes)) if (!['position', 'normal', 'uv'].includes(k)) g.deleteAttribute(k);
    g.clearGroups();
    geo.dispose();
    if (!this.byMat.has(mat)) this.byMat.set(mat, []);
    this.byMat.get(mat).push(g);
  }

  into(group) {
    for (const [mat, geos] of this.byMat) {
      const mesh = new THREE.Mesh(mergeGeometries(geos), mat);
      geos.forEach((g) => g.dispose());
      group.add(mesh);
    }
    return group;
  }
}

/**
 * Metal and glass need stronger reflections than the scene's shared environment intensity gives
 * the matte sets: pick up the scene's environment map per render, scaled by `k`.
 */
export function reflective(mat, k) {
  mat.userData.envBoost = k;
  return mat;
}
export function hookEnv(root) {
  root.traverse((o) => {
    if (o.material?.userData.envBoost === undefined) return;
    o.onBeforeRender = (r, scene) => {
      const m = o.material, env = scene.environment ?? null;
      if (m.envMap !== env) { m.envMap = env; m.needsUpdate = true; }
      m.envMapIntensity = (scene.environmentIntensity ?? 1) * m.userData.envBoost; // read live: it can be animated
    };
  });
}

/** Stepped lens-bezel profile (radius, height) for a LatheGeometry, outer edge first. */
const BEZEL = [[0.2, 0], [0.202, 0.007], [0.196, 0.012], [0.15, 0.014], [0.142, 0.016], [0.128, 0.03],
  [0.116, 0.034], [0.106, 0.031], [0.1, 0.02], [0.094, 0.008], [0.09, -0.06]];

function bezel(scale) {
  return new THREE.LatheGeometry(BEZEL.map(([r, h]) => new THREE.Vector2(r * scale, h * scale)).reverse(), 40);
}

/** A shallow spherical cap (meniscus lens face) of base radius `rad`, bulging `bulge` along +Y. */
function lensCap(rad, bulge) {
  const R = (rad * rad + bulge * bulge) / (2 * bulge);
  const g = new THREE.SphereGeometry(R, 32, 6, 0, Math.PI * 2, 0, Math.asin(rad / R));
  g.translate(0, bulge - R, 0);
  return g;
}

function roundRectShape(w, h, rad) {
  const s = new THREE.Shape();
  const x = -w / 2, y = -h / 2;
  s.moveTo(x + rad, y);
  s.lineTo(x + w - rad, y); s.quadraticCurveTo(x + w, y, x + w, y + rad);
  s.lineTo(x + w, y + h - rad); s.quadraticCurveTo(x + w, y + h, x + w - rad, y + h);
  s.lineTo(x + rad, y + h); s.quadraticCurveTo(x, y + h, x, y + h - rad);
  s.lineTo(x, y + rad); s.quadraticCurveTo(x, y, x + rad, y);
  return s;
}

/** A raised finder-window frame (extruded along +Z). */
function windowFrame(w, h, border) {
  const s = roundRectShape(w + border * 2, h + border * 2, border * 1.2);
  s.holes.push(roundRectShape(w, h, border * 0.4));
  return new THREE.ExtrudeGeometry(s, { depth: 0.008, bevelEnabled: true, bevelThickness: 0.005, bevelSize: 0.004, bevelSegments: 2, curveSegments: 4 });
}

/** A knurled cylinder along +Y: alternate rim vertices pulled in to form grip ridges. */
function knurled(rad, h, ridges) {
  const g = new THREE.CylinderGeometry(rad, rad, h, ridges * 2, 1);
  const p = g.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), z = p.getZ(i), rr = Math.hypot(x, z);
    if (rr < rad * 0.5) continue;
    const a = Math.atan2(z, x), k = Math.round((a / (Math.PI * 2)) * ridges * 2);
    if (k % 2) { p.setX(i, x * 0.9); p.setZ(i, z * 0.9); }
  }
  g.computeVertexNormals();
  return g;
}

/** A 1930s-style box camera. Unit ≈ 1 = 10 cm; scale the group as needed. Faces +Z (lens). */
export function createBrownie() {
  const W = 0.86, H = 1.25, D = 1.1;
  const hw = W / 2, hh = H / 2, hd = D / 2;
  const front = hd + 0.005; // face of the aluminium front
  const pw = W - 0.07, ph = H - 0.07;
  const lensAt = { x: 0, y: -0.1 };
  const finders = [{ x: 0.2, y: 0.43 }, { x: -0.2, y: 0.43 }];
  const M = sharedMaps(pw, ph, lensAt, finders);

  const leather = new THREE.MeshStandardMaterial({ map: M.leather.map, bumpMap: M.leather.data, bumpScale: 1.2, roughnessMap: M.leather.data, roughness: 1, metalness: 0 });
  const plate = reflective(new THREE.MeshStandardMaterial({ map: M.plate.map, bumpMap: M.plate.data, bumpScale: 2, roughnessMap: M.plate.data, metalnessMap: M.plate.data, roughness: 1, metalness: 1 }), 3.5);
  const alu = reflective(new THREE.MeshStandardMaterial({ color: 0xb6b1a7, roughness: 0.42, metalness: 1 }), 3.5);
  const chrome = reflective(new THREE.MeshStandardMaterial({ color: 0xd8d4cc, roughness: 0.24, metalness: 1, side: THREE.DoubleSide }), 4);
  const black = new THREE.MeshStandardMaterial({ color: 0x080706, roughness: 0.6 });
  const enamel = reflective(new THREE.MeshStandardMaterial({ color: 0x0e0d0b, roughness: 0.3, metalness: 0 }), 2);
  const glass = reflective(new THREE.MeshPhysicalMaterial({ color: 0x020304, roughness: 0.02, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.02, ior: 1.52 }), 3.5);
  // Reflex finders show a small bright image: a faintly lit, slightly milky pane.
  const finderGlass = reflective(new THREE.MeshPhysicalMaterial({ color: 0x3a4448, emissive: 0x2a2c26, emissiveIntensity: 0.35, roughness: 0.08, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.05 }), 4);
  // Front finder panes: dark glass with the objective's glint behind.
  const finderFront = reflective(new THREE.MeshPhysicalMaterial({ color: 0x0b0e10, roughness: 0.03, metalness: 0, clearcoat: 1, clearcoatRoughness: 0.02 }), 4);
  const strap = new THREE.MeshStandardMaterial({ color: 0x2c1f16, roughness: 0.52, metalness: 0 });
  const red = reflective(new THREE.MeshPhysicalMaterial({ color: 0x6e0d06, emissive: 0x2a0402, emissiveIntensity: 0.6, roughness: 0.1, clearcoat: 1 }), 3);

  const P = new Parts();
  // Box and its aluminium front cap (wraps over the leather's front edge).
  P.add(new RoundedBoxGeometry(W, H, D - 0.06, 4, 0.04), leather, [0, 0, -0.03]);
  P.add(new RoundedBoxGeometry(W + 0.014, H + 0.014, 0.095, 3, 0.035), alu, [0, 0, front - 0.0475]);
  P.add(new THREE.PlaneGeometry(pw, ph), plate, [0, 0, front + 0.0015]);
  // Faceplate screws in the corners.
  for (const sx of [-1, 1]) for (const sy of [-1, 1]) {
    P.add(new THREE.SphereGeometry(0.011, 10, 5, 0, Math.PI * 2, 0, Math.PI / 2), chrome, [sx * (pw / 2 - 0.016), sy * (ph / 2 - 0.016), front + 0.002], [Math.PI / 2, 0, 0]);
  }

  // Taking lens: stepped bezel, black barrel, domed glass.
  const lz = front + 0.0015;
  P.add(bezel(1), chrome, [lensAt.x, lensAt.y, lz], [Math.PI / 2, 0, 0]);
  P.add(new THREE.RingGeometry(0.146, 0.186, 48), enamel, [lensAt.x, lensAt.y, lz + 0.0142]);
  // The lens sits in the well formed by the bezel's lip: a black floor just proud of the plate.
  P.add(new THREE.CircleGeometry(0.095, 32), black, [lensAt.x, lensAt.y, lz + 0.001]);
  P.add(lensCap(0.075, 0.014), glass, [lensAt.x, lensAt.y, lz + 0.002], [Math.PI / 2, 0, 0]);
  // Finder objectives: small lenses behind framed windows.
  for (const f of finders) {
    P.add(windowFrame(0.1, 0.075, 0.012), chrome, [f.x, f.y, lz - 0.004]);
    P.add(new THREE.PlaneGeometry(0.104, 0.079), finderFront, [f.x, f.y, lz + 0.003]);
  }
  // Finder windows: on top (over the right objective) and on the left side (level with the left one).
  const fw = 0.15, fh = 0.12, fz = hd - 0.17;
  P.add(windowFrame(fw, fh, 0.022), chrome, [finders[0].x, hh - 0.003, fz], [-Math.PI / 2, 0, 0]);
  P.add(new THREE.PlaneGeometry(fw + 0.004, fh + 0.004), finderGlass, [finders[0].x, hh + 0.002, fz], [-Math.PI / 2, 0, 0]);
  P.add(windowFrame(fh, fw, 0.022), chrome, [-hw + 0.003, finders[1].y, fz], [0, -Math.PI / 2, 0]);
  P.add(new THREE.PlaneGeometry(fh + 0.004, fw + 0.004), finderGlass, [-hw - 0.002, finders[1].y, fz], [0, -Math.PI / 2, 0]);

  // Aperture and time/instant pull tabs rising out of the top, just behind the front.
  for (const x of [-0.1, -0.23]) {
    P.add(new THREE.BoxGeometry(0.075, 0.012, 0.03), black, [x, hh + 0.001, hd - 0.1]);
    P.add(new RoundedBoxGeometry(0.05, 0.07, 0.012, 2, 0.005), chrome, [x, hh + 0.03, hd - 0.1]);
    P.add(new THREE.CylinderGeometry(0.02, 0.02, 0.014, 14), chrome, [x, hh + 0.068, hd - 0.1], [Math.PI / 2, 0, 0]);
  }

  // Leather carrying handle on riveted brackets, running front to back.
  const hz = 0.34;
  const curve = new THREE.CatmullRomCurve3([V(0, hh + 0.028, -hz), V(0, hh + 0.1, -hz * 0.68), V(0, hh + 0.13, 0), V(0, hh + 0.1, hz * 0.68), V(0, hh + 0.028, hz)]);
  const band = new THREE.Shape();
  band.moveTo(-0.062, -0.011); band.lineTo(0.062, -0.011); band.lineTo(0.062, 0.011); band.lineTo(-0.062, 0.011); band.closePath();
  P.add(new THREE.ExtrudeGeometry(band, { steps: 28, extrudePath: curve, bevelEnabled: false }), strap);
  for (const z of [-hz, hz]) {
    P.add(new RoundedBoxGeometry(0.165, 0.03, 0.075, 2, 0.01), chrome, [0, hh + 0.013, z]);
    for (const x of [-0.058, 0.058]) P.add(new THREE.SphereGeometry(0.013, 10, 5, 0, Math.PI * 2, 0, Math.PI / 2), chrome, [x, hh + 0.027, z]);
  }

  // Back-door spring latches on both sides and the red film-counter window.
  for (const sx of [-1, 1]) {
    P.add(new RoundedBoxGeometry(0.018, 0.2, 0.08, 2, 0.006), chrome, [sx * (hw + 0.004), 0, -hd + 0.11]);
    P.add(new RoundedBoxGeometry(0.02, 0.045, 0.03, 2, 0.006), chrome, [sx * (hw + 0.012), 0, -hd + 0.11]);
  }
  P.add(new THREE.TorusGeometry(0.05, 0.009, 8, 28), chrome, [0.16, 0.24, -hd - 0.001]);
  P.add(new THREE.CircleGeometry(0.05, 28), red, [0.16, 0.24, -hd - 0.002], [0, Math.PI, 0]);

  const g = P.into(new THREE.Group());

  // Winding key (right side, towards the back): collar, knurled knob and a folding wing key.
  const K = new Parts();
  K.add(new THREE.CylinderGeometry(0.1, 0.1, 0.018, 32), chrome, [0.009, 0, 0], [0, 0, -Math.PI / 2]);
  K.add(knurled(0.085, 0.05, 22), chrome, [0.04, 0, 0], [0, 0, -Math.PI / 2]);
  const wing = new THREE.Shape();
  wing.absellipse(0, 0, 0.1, 0.045, 0, Math.PI * 2);
  K.add(new THREE.ExtrudeGeometry(wing, { depth: 0.012, bevelEnabled: true, bevelThickness: 0.006, bevelSize: 0.006, bevelSegments: 2, curveSegments: 20 }), chrome, [0.09, 0, -0.006], [0, 0, Math.PI / 2]);
  const knob = K.into(new THREE.Group());
  knob.position.set(hw, 0.36, -0.3);

  // Shutter lever (right side, near the front) riding in a slotted plate.
  const L = new Parts();
  L.add(new RoundedBoxGeometry(0.012, 0.28, 0.06, 2, 0.005), alu, [0.006, 0, 0]);
  L.add(new THREE.BoxGeometry(0.006, 0.22, 0.014), black, [0.012, 0, 0]);
  L.add(new RoundedBoxGeometry(0.03, 0.03, 0.02, 2, 0.006), chrome, [0.025, 0.07, 0]);
  L.add(new RoundedBoxGeometry(0.018, 0.06, 0.05, 2, 0.008), chrome, [0.045, 0.09, 0], [0, 0, -0.35]);
  const lever = L.into(new THREE.Group());
  lever.position.set(hw, 0.12, hd - 0.14);

  g.add(knob, lever);
  g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  hookEnv(g);
  g.userData.lever = lever;
  g.userData.lensGlass = glass;
  g.userData.knob = knob;
  return g;
}

function V(x, y, z) { return new THREE.Vector3(x, y, z); }
