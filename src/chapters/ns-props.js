import * as THREE from 'three';

// Chapter 3 small props and runtime textures: the tiffin carrier, a paper bag of oranges, the bed frame
// (fallback when the level has none), the heritage marker / community-centre sign / banner textures,
// and Farid's letter (a paper overlay the player watches fill up, and an album image of it).

const SERIF = 'Gelasio, Georgia, serif';
const HAND = '"Bradley Hand", "Segoe Print", "Comic Sans MS", cursive';
const SANS = 'Inter, "Helvetica Neue", Arial, sans-serif';
const CJK = '"Songti SC", "STSong", "Noto Serif CJK SC", "PingFang SC", serif';

function canvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return [c, c.getContext('2d')];
}

function tex(c, flipY = false) {
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  t.flipY = flipY; // level quads use glTF UVs (v down)
  return t;
}

function fit(g, text, cx, cy, maxW, size, family, weight = '700', color = '#000') {
  let s = size;
  do { g.font = `${weight} ${s}px ${family}`; s -= 2; } while (g.measureText(text).width > maxW && s > 8);
  g.fillStyle = color;
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.fillText(text, cx, cy);
}

// ------------------------------------------------------------------ meshes
const mat = (color, rough = 0.5, metal = 0) => new THREE.MeshStandardMaterial({ color, roughness: rough, metalness: metal });

/** A four-tier enamel tiffin carrier (Papa's is chipped white and blue; the fallback is aluminium). */
export function tiffinCarrier(papa = true) {
  const g = new THREE.Group();
  g.name = 'PROP_Tiffin';
  const body = papa ? mat('#e9e4d6', 0.35, 0.05) : mat('#b9bec2', 0.3, 0.8);
  const band = papa ? mat('#355c8a', 0.4) : mat('#8e959b', 0.35, 0.8);
  const r = 0.06, h = 0.045;
  for (let i = 0; i < 4; i++) {
    const tin = new THREE.Mesh(new THREE.CylinderGeometry(r, r * 0.97, h, 20), body);
    tin.position.y = h / 2 + i * (h + 0.004);
    g.add(tin);
    const rim = new THREE.Mesh(new THREE.TorusGeometry(r * 1.0, 0.004, 6, 20), band);
    rim.rotation.x = Math.PI / 2;
    rim.position.y = (i + 1) * (h + 0.004) - 0.003;
    g.add(rim);
  }
  const top = 4 * (h + 0.004);
  const lid = new THREE.Mesh(new THREE.SphereGeometry(r, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), body);
  lid.scale.y = 0.35;
  lid.position.y = top;
  g.add(lid);
  // The carrying frame: two uprights and a handle.
  const rodM = mat('#9aa0a5', 0.3, 0.9);
  for (const s of [-1, 1]) {
    const rod = new THREE.Mesh(new THREE.CylinderGeometry(0.004, 0.004, top + 0.05, 6), rodM);
    rod.position.set(s * (r + 0.006), (top + 0.05) / 2, 0);
    g.add(rod);
  }
  const handle = new THREE.Mesh(new THREE.TorusGeometry(r + 0.006, 0.005, 6, 16, Math.PI), rodM);
  handle.position.y = top + 0.05;
  g.add(handle);
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  return g;
}

/** A brown paper bag with oranges peeking out. */
export function orangeBag() {
  const g = new THREE.Group();
  g.name = 'PROP_Oranges';
  const bag = new THREE.Mesh(new THREE.BoxGeometry(0.16, 0.18, 0.1), mat('#b08a5a', 0.9));
  bag.position.y = 0.09;
  g.add(bag);
  const om = mat('#ee8a1c', 0.55);
  [[-0.04, 0.2, 0.01], [0.035, 0.195, -0.015], [0.0, 0.215, 0.02]].forEach(([x, y, z]) => {
    const o = new THREE.Mesh(new THREE.SphereGeometry(0.035, 12, 8), om);
    o.position.set(x, y, z);
    g.add(o);
  });
  return g;
}

/** Iron bed frame, ~1.9 × 0.8 m, long axis along local Z (used if the level has no PROP_Bed). */
export function bedFrame() {
  const g = new THREE.Group();
  g.name = 'PROP_Bed';
  const iron = mat('#3f4a3f', 0.55, 0.6);
  const L = 1.9, W = 0.8, H = 0.42;
  const rail = (a, b) => {
    const d = new THREE.Vector3().subVectors(b, a);
    const m = new THREE.Mesh(new THREE.CylinderGeometry(0.014, 0.014, d.length(), 6), iron);
    m.position.copy(a).addScaledVector(d, 0.5);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize());
    g.add(m);
  };
  const V = (x, y, z) => new THREE.Vector3(x, y, z);
  for (const sx of [-1, 1]) {
    rail(V(sx * W / 2, H, -L / 2), V(sx * W / 2, H, L / 2));
    for (const sz of [-1, 1]) rail(V(sx * W / 2, 0, sz * L / 2), V(sx * W / 2, sz > 0 ? 0.8 : 0.6, sz * L / 2));
  }
  for (const sz of [-1, 1]) {
    const top = sz > 0 ? 0.8 : 0.6;
    rail(V(-W / 2, H, sz * L / 2), V(W / 2, H, sz * L / 2));
    rail(V(-W / 2, top, sz * L / 2), V(W / 2, top, sz * L / 2));
    for (let i = 1; i < 4; i++) rail(V(-W / 2 + (W * i) / 4, H, sz * L / 2), V(-W / 2 + (W * i) / 4, top, sz * L / 2));
  }
  const springs = new THREE.Mesh(new THREE.PlaneGeometry(W - 0.04, L - 0.04), new THREE.MeshStandardMaterial({ color: '#6c7266', roughness: 0.7, metalness: 0.5, side: THREE.DoubleSide }));
  springs.rotation.x = -Math.PI / 2;
  springs.position.y = H;
  g.add(springs);
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  return g;
}

/**
 * An M16 rifle (stylised, ~0.99 m, muzzle along local +Y so it stands upright). Dark grey receiver and furniture,
 * carry handle, triangular handguard, straight magazine, sling. For drill only: no firing in the game.
 */
export function m16() {
  const g = new THREE.Group();
  g.name = 'PROP_M16';
  const black = mat('#2f3231', 0.5, 0.3);
  const metal = mat('#55595a', 0.35, 0.75);
  const sling = mat('#4d5a3a', 0.9);
  // Parts go in an inner group that is thickened (toy proportions: a true-scale rifle reads as a twig next to them).
  const inner = new THREE.Group();
  inner.scale.set(1.9, 1, 1.9);
  g.add(inner);
  const box = (w, h, d, m, x, y, z) => { const o = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m); o.position.set(x, y, z); inner.add(o); return o; };
  const cyl = (r0, r1, h, m, x, y, z, seg = 8) => { const o = new THREE.Mesh(new THREE.CylinderGeometry(r0, r1, h, seg), m); o.position.set(x, y, z); inner.add(o); return o; };
  box(0.036, 0.26, 0.07, black, 0, 0.13, 0.0);           // stock
  box(0.036, 0.05, 0.085, black, 0, 0.0, 0.004);          // butt plate
  box(0.034, 0.24, 0.06, metal, 0, 0.38, 0.005);          // receiver
  box(0.02, 0.16, 0.022, metal, 0, 0.42, 0.045);          // carry handle
  box(0.02, 0.03, 0.03, metal, 0, 0.35, 0.036);
  box(0.03, 0.14, 0.03, metal, 0, 0.40, -0.048);          // magazine
  box(0.028, 0.06, 0.028, black, 0, 0.27, -0.04).rotation.x = 0.35; // pistol grip
  cyl(0.024, 0.02, 0.22, black, 0, 0.61, 0.0, 3);         // handguard (triangular)
  cyl(0.007, 0.007, 0.26, metal, 0, 0.84, 0.0);           // barrel
  box(0.008, 0.06, 0.012, metal, 0, 0.72, 0.03);          // front sight
  cyl(0.009, 0.009, 0.05, metal, 0, 0.98, 0.0);           // flash hider
  // Sling from the stock to the front swivel.
  const s = new THREE.Mesh(new THREE.BoxGeometry(0.006, 0.64, 0.018), sling);
  s.position.set(0, 0.42, -0.07); s.rotation.x = 0.05; inner.add(s);
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  return g;
}

/**
 * Give a character a rifle in a drill position. Characters face +Z; their right is −X.
 *   'order': butt on the ground by the right foot, muzzle up (standing at attention).
 *   'sling': upright against the right shoulder, butt in the right hand (the chapter locks that arm still).
 * opts.scale overrides the body scale (Sparky is small and big-headed); opts.lift nudges it up/down.
 */
export function rifleOn(ch, pose = 'sling', { scale = null, lift = 0, out = 0 } = {}) {
  const k = scale ?? (ch.height || 1.7) / 1.7;
  if (!ch.rifle) {
    ch.rifle = m16();
    ch.root.add(ch.rifle);
  }
  const r = ch.rifle;
  r.visible = true;
  r.scale.setScalar(k * 0.92);
  if (pose === 'order') { r.position.set(-(0.2 + out) * k, 0.0, 0.06 * k); r.rotation.set(0, Math.PI, 0); }
  // Sling: upright against the right shoulder, butt in the right hand at the hip; the muzzle rises beside the head.
  else { r.position.set(-(0.25 + out) * k, (0.5 + lift) * k, 0.02 * k); r.rotation.set(0.04, Math.PI, -0.05); }
  ch.riflePose = pose;
  return r;
}

export function rifleOff(ch) { if (ch.rifle) ch.rifle.visible = false; }

/** A wooden rack of rifles (the issue table). Origin at the floor, rack along local X. */
export function rifleRack(n = 6) {
  const g = new THREE.Group();
  g.name = 'PROP_RifleRack';
  const wood = mat('#6b4a2e', 0.8);
  const bar = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.06, 0.18), wood);
  bar.position.y = 0.62; g.add(bar);
  const base = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.08, 0.3), wood);
  base.position.y = 0.04; g.add(base);
  for (const x of [-0.78, 0.78]) { const leg = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.66, 0.06), wood); leg.position.set(x, 0.33, 0); g.add(leg); }
  g.rifles = [];
  for (let i = 0; i < n; i++) {
    const r = m16();
    r.position.set(-0.62 + i * (1.24 / Math.max(1, n - 1)), 0.08, 0.04);
    r.rotation.set(-0.12, Math.PI / 2, 0);
    g.add(r);
    g.rifles.push(r);
  }
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  return g;
}

// ------------------------------------------------------------------ runtime textures
/** A stand-in heritage marker plate (NOT the real marker's wording). */
export function markerPlate([title, sub]) {
  const [c, g] = canvas(768, 512);
  g.fillStyle = '#2f3a36'; g.fillRect(0, 0, 768, 512);
  g.strokeStyle = '#c9b27a'; g.lineWidth = 10; g.strokeRect(22, 22, 724, 468);
  fit(g, title, 384, 190, 660, 58, SERIF, '700', '#efe4c6');
  fit(g, sub, 384, 290, 640, 34, SANS, '500', '#d9cfb2');
  g.fillStyle = '#c9b27a'; g.fillRect(284, 360, 200, 4);
  return tex(c);
}

/** The kopitiam's tear-off day calendar for a given day (Chapter 2's shows 9 August 1965). */
export function calendarPage({ head, day, weekday, malay }) {
  const [c, g] = canvas(320, 448);
  g.fillStyle = '#fbf7ec'; g.fillRect(0, 0, 320, 448);
  g.fillStyle = '#b3261e'; g.fillRect(0, 0, 320, 70);
  fit(g, head, 160, 36, 290, 30, SERIF, '700', '#fff');
  fit(g, String(day), 160, 210, 280, 230, SERIF, '700', '#b3261e');
  fit(g, weekday, 160, 350, 280, 28, SERIF, '700', '#333');
  fit(g, malay, 160, 392, 280, 24, SERIF, '400', '#555'); // review (Malay)
  g.strokeStyle = '#ccc'; g.setLineDash([6, 6]); g.beginPath(); g.moveTo(0, 74); g.lineTo(320, 74); g.stroke();
  return tex(c);
}

export function ccSign([en, zh, ms]) {
  const [c, g] = canvas(1024, 256);
  g.fillStyle = '#f1ead8'; g.fillRect(0, 0, 1024, 256);
  g.fillStyle = '#7a2a22'; g.fillRect(0, 0, 1024, 14); g.fillRect(0, 242, 1024, 14);
  fit(g, zh, 512, 78, 900, 72, CJK, '700', '#7a2a22');
  fit(g, en, 512, 158, 940, 56, SANS, '800', '#2a2a2a');
  fit(g, ms, 512, 212, 900, 34, SANS, '600', '#555');
  return tex(c);
}

/** A string of red and white pennants from `a` to `b` (world points), sagging in the middle. */
export function bunting(a, b, { n = 16, sag = 0.35 } = {}) {
  const g = new THREE.Group();
  g.name = 'PROP_Bunting';
  const tri = new THREE.Shape([new THREE.Vector2(-0.13, 0), new THREE.Vector2(0.13, 0), new THREE.Vector2(0, -0.3)]);
  const geo = new THREE.ShapeGeometry(tri);
  const mats = ['#c0392b', '#f7f2e4'].map((c) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.8, side: THREE.DoubleSide }));
  const pts = [];
  const yaw = Math.atan2(b.x - a.x, b.z - a.z) - Math.PI / 2;
  for (let i = 0; i <= n; i++) {
    const t = i / n;
    const p = a.clone().lerp(b, t);
    p.y -= sag * 4 * t * (1 - t);
    pts.push(p);
    if (i === n) break;
    const f = new THREE.Mesh(geo, mats[i % 2]);
    f.position.copy(p).lerp(a.clone().lerp(b, (i + 1) / n).add(new THREE.Vector3(0, -sag * 4 * ((i + 1) / n) * (1 - (i + 1) / n), 0)), 0.5);
    f.rotation.y = yaw;
    g.add(f);
  }
  g.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: '#e8e0cc' })));
  return g;
}

export function banner(text) {
  const [c, g] = canvas(1536, 256);
  g.fillStyle = '#f7f2e4'; g.fillRect(0, 0, 1536, 256);
  g.fillStyle = '#c0392b'; g.fillRect(0, 0, 1536, 36); g.fillRect(0, 220, 1536, 36);
  fit(g, text, 768, 128, 1440, 104, SANS, '800', '#1d2b53');
  return tex(c);
}

// ------------------------------------------------------------------ the letter
const LETTER_CSS = `
.letter{position:fixed;inset:0;z-index:34;display:flex;align-items:center;justify-content:center;pointer-events:none;padding:16px}
.letter-paper{position:relative;width:min(560px,92vw);max-height:78vh;overflow:hidden;background:#f5eedb;color:#2b2418;border-radius:4px;box-shadow:0 18px 50px rgba(0,0,0,.45);padding:26px 30px 22px;font:21px/1.45 ${HAND};transform:rotate(-1.2deg);background-image:repeating-linear-gradient(0deg,transparent 0 29px,rgba(80,110,160,.18) 29px 30px)}
.letter-paper .hd{font-size:15px;opacity:.75;margin-bottom:8px}
.letter-paper p{margin:0 0 6px}
.letter-paper .ln{opacity:0;transition:opacity .6s}
.letter-paper .ln.on{opacity:1}
.letter-paper .ps{margin-top:10px;font-size:19px}
.letter-paper .ps small{display:block;font:italic 13px ${SERIF};opacity:.7}
.letter-paper .map{display:inline-block;vertical-align:middle;margin-right:8px}
.letter-paper .paw{font-size:30px;float:right;margin-top:-6px}
.letter.dim .letter-paper{transform:rotate(-1.2deg) scale(.66) translateY(-26vh);opacity:.92}
.letter{flex-direction:column;gap:14px}
.letter.closable{pointer-events:auto;cursor:pointer;background:rgba(10,8,6,.35)}
.letter-hint{font:600 14px/1.2 Inter,system-ui,sans-serif;color:#fff8ea;background:rgba(20,16,11,.78);border:1px solid rgba(255,248,234,.3);padding:8px 16px;border-radius:999px;opacity:0;transition:opacity .3s}
.letter.closable .letter-hint{opacity:1}
.letter-paper{transition:transform .45s ease,opacity .45s}
@media (max-height:760px){.letter-paper{font-size:18px;line-height:1.35;padding:18px 24px}}
@media (max-height:480px){.letter-paper{font-size:15px;padding:12px 18px}}
`;

function ensureCSS() {
  if (document.getElementById('letter-css')) return;
  const st = document.createElement('style');
  st.id = 'letter-css';
  st.textContent = LETTER_CSS;
  document.head.appendChild(st);
}

/** Ravi's little map of the parade square, as an inline SVG. */
const MAP_SVG = '<svg class="map" width="92" height="58" viewBox="0 0 92 58" aria-label="map"><rect x="4" y="4" width="84" height="38" fill="none" stroke="#3b3b3b" stroke-width="2"/><rect x="36" y="44" width="20" height="10" fill="none" stroke="#3b3b3b" stroke-width="2"/><path d="M8 24h76" stroke="#3b3b3b" stroke-dasharray="4 3"/><path d="M62 44l8 8M70 44l-8 8" stroke="#b3261e" stroke-width="3"/></svg>';
const PAW_SVG = '<svg class="paw" width="40" height="40" viewBox="0 0 40 40" aria-label="paw print"><g fill="#3a2a1a"><ellipse cx="20" cy="26" rx="9" ry="7.5"/><circle cx="9" cy="16" r="4"/><circle cx="16" cy="10" r="4"/><circle cx="24" cy="10" r="4"/><circle cx="31" cy="16" r="4"/></g></svg>';

/** The letter on screen. `state` = { opening, body[], ps: { AhHock, Ravi, Leo }, paw }. */
export class LetterView {
  constructor(L) { this.L = L; }

  mount() {
    ensureCSS();
    this.el = document.createElement('div');
    this.el.className = 'letter';
    this.el.innerHTML = '<div class="letter-paper" role="document"></div>';
    document.body.appendChild(this.el);
    this.paper = this.el.firstElementChild;
  }

  unmount() { this.offClose?.(); this.el?.remove(); this.el = null; }

  /**
   * Leave the letter up until the player closes it (click / tap / E / Space / Enter / Esc), then unmount.
   * `game` is used to free the mouse and to listen for the interact button.
   */
  waitClose(game, hint) {
    if (!this.el) return Promise.resolve();
    game?.input.releaseLock?.();
    this.el.classList.add('closable');
    let h = this.el.querySelector('.letter-hint');
    if (!h) { h = document.createElement('div'); h.className = 'letter-hint'; this.el.appendChild(h); }
    h.textContent = hint;
    const t0 = performance.now();
    return new Promise((resolve) => {
      const done = () => {
        if (performance.now() - t0 < 350) return; // not the same press that opened it
        this.offClose?.();
        this.unmount();
        resolve();
      };
      const onKey = (e) => { if (['Space', 'Enter', 'KeyE', 'Escape'].includes(e.code)) { e.preventDefault(); done(); } };
      this.el.addEventListener('click', done);
      addEventListener('keydown', onKey);
      const offAction = game?.input.on?.('action', done);
      this.offClose = () => { removeEventListener('keydown', onKey); offAction?.(); this.offClose = null; };
    });
  }

  dim(on) { this.el?.classList.toggle('dim', !!on); }

  /** Re-render; `reveal` = how many lines to show (for Siti reading it out), or all. */
  render(state, reveal = Infinity) {
    if (!this.el) this.mount();
    const L = this.L;
    const rows = [];
    rows.push(`<div class="hd">${L.heading}</div>`);
    rows.push(`<p>${L.greeting}</p>`);
    if (state.opening) rows.push(`<p>${state.opening}</p>`);
    for (const b of state.body || []) rows.push(`<p>${b}</p>`);
    if (state.body?.length) rows.push(`<p>${L.sign}</p>`);
    if (state.ps.AhHock) rows.push(`<p class="ps">${L.ps.AhHock.text}<small>${L.ps.AhHock.gloss}</small></p>`);
    if (state.ps.Ravi) rows.push(`<p class="ps">${MAP_SVG}${L.ps.Ravi.text}</p>`);
    if (state.ps.Leo) rows.push(`<p class="ps">${L.ps.Leo.text}</p>`);
    if (state.paw) rows.push(`<p>${PAW_SVG}</p>`);
    this.count = rows.length;
    this.paper.innerHTML = rows.map((r, i) => r.replace(/^<(\w+) ?(class="([^"]*)")?/, (m, tag, _c, cls) => `<${tag} class="${cls ? `${cls} ` : ''}ln${i < reveal ? ' on' : ''}"`)).join('');
    // Keep the newest line in view (the paper is a fixed window on short screens).
    const lastOn = [...this.paper.querySelectorAll('.ln.on')].pop();
    if (lastOn) this.paper.scrollTop = Math.max(0, lastOn.offsetTop + lastOn.offsetHeight - this.paper.clientHeight + 16);
  }
}

/** The letter as an album photo (warm paper, handwriting). */
export function letterImage(L, state, size = 512) {
  const [c, g] = canvas(size, size);
  g.fillStyle = '#e9dfc6'; g.fillRect(0, 0, size, size);
  g.save();
  g.translate(size / 2, size / 2); g.rotate(-0.03); g.translate(-size / 2, -size / 2);
  g.fillStyle = '#f5eedb'; g.fillRect(40, 26, size - 80, size - 52);
  g.strokeStyle = 'rgba(80,110,160,.2)';
  for (let y = 70; y < size - 30; y += 22) { g.beginPath(); g.moveTo(52, y); g.lineTo(size - 52, y); g.stroke(); }
  g.fillStyle = '#2b2418';
  g.font = `15px ${HAND}`;
  const lines = [L.heading, '', L.greeting, state.opening || '', ...(state.body || []), L.sign];
  if (state.ps.AhHock) lines.push(L.ps.AhHock.text);
  if (state.ps.Ravi) lines.push(`[map] ${L.ps.Ravi.text}`);
  if (state.ps.Leo) lines.push(L.ps.Leo.text);
  let y = 62;
  const wrapLine = (t) => {
    const words = t.split(' ');
    let line = '';
    for (const w of words) {
      const test = line ? `${line} ${w}` : w;
      if (g.measureText(test).width > size - 120) { g.fillText(line, 60, y); y += 21; line = w; } else line = test;
    }
    g.fillText(line, 60, y); y += 21;
  };
  for (const t of lines) { if (y > size - 50) break; wrapLine(t); }
  if (state.paw) {
    g.fillStyle = '#3a2a1a';
    const px = size - 100, py = size - 80;
    g.beginPath(); g.ellipse(px, py + 8, 11, 9, 0, 0, Math.PI * 2); g.fill();
    [[-12, -4], [-5, -11], [5, -11], [12, -4]].forEach(([dx, dy]) => { g.beginPath(); g.arc(px + dx, py + dy, 4.5, 0, Math.PI * 2); g.fill(); });
  }
  g.restore();
  return c.toDataURL('image/jpeg', 0.86);
}
