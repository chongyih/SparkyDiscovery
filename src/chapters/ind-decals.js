import * as THREE from 'three';

// Chapter 2 runtime textures: everything with lettering is drawn on a canvas in the browser, so
// Chinese, Malay and Tamil are shaped by the system fonts. The level provides plain quads with
// 0..1 UVs (DECAL_* / WALL_* nodes, see tools/build_kopitiam.py).

const SERIF = 'Gelasio, Georgia, serif';
const SANS = 'Inter, "Helvetica Neue", Arial, sans-serif';
const CJK = '"Songti SC", "STSong", "Noto Serif CJK SC", "Noto Serif SC", "PingFang SC", serif';
const CJK_BOLD = '"STHeiti", "Heiti SC", "PingFang SC", "Noto Sans CJK SC", sans-serif';
const TAMIL = '"Tamil Sangam MN", "Tamil MN", "Noto Sans Tamil", "Latha", sans-serif';

function canvas(w, h) {
  const c = document.createElement('canvas');
  c.width = w; c.height = h;
  return [c, c.getContext('2d')];
}

function tex(c) {
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.anisotropy = 4;
  t.flipY = false; // the level's quads use glTF UVs (v down)
  return t;
}

/** Fill `text` centred in a box, shrinking the font until it fits the width. */
function fit(g, text, cx, cy, maxW, size, family, weight = '700', color = '#000') {
  let s = size;
  do { g.font = `${weight} ${s}px ${family}`; s -= 2; } while (g.measureText(text).width > maxW && s > 8);
  g.fillStyle = color;
  g.textAlign = 'center';
  g.textBaseline = 'middle';
  g.fillText(text, cx, cy);
}

function grain(g, w, h, amt = 18, seed = 7) {
  const img = g.getImageData(0, 0, w, h);
  const d = img.data;
  let s = seed;
  for (let i = 0; i < d.length; i += 4) {
    s = (s * 16807) % 2147483647;
    const n = ((s / 2147483647) - 0.5) * amt;
    d[i] += n; d[i + 1] += n; d[i + 2] += n;
  }
  g.putImageData(img, 0, 0);
}

export async function loadFonts() {
  try { await Promise.all(['700 40px Gelasio', '400 40px Gelasio', '600 20px Inter'].map((f) => document.fonts.load(f))); } catch { /* fall back to system fonts */ }
}

// ------------------------------------------------------------------ signboards
export function shopSign({ zh, en }) {
  const [c, g] = canvas(1024, 160);
  g.fillStyle = '#1f4a3a'; g.fillRect(0, 0, 1024, 160);
  g.strokeStyle = '#d8b25a'; g.lineWidth = 8; g.strokeRect(10, 10, 1004, 140);
  fit(g, zh, 512, 64, 900, 84, CJK, '700', '#e9c46a');
  fit(g, en, 512, 128, 860, 30, SERIF, '700', '#f3e9d6');
  grain(g, 1024, 160, 14);
  return tex(c);
}

export function neighbourSign([zh, en], i = 0) {
  const pal = [['#7a2a22', '#f1d28a'], ['#23405e', '#f3e9d6'], ['#5a4a2a', '#f3e9d6'], ['#2e5a4a', '#f1d28a']][i % 4];
  const [c, g] = canvas(512, 96);
  g.fillStyle = pal[0]; g.fillRect(0, 0, 512, 96);
  g.strokeStyle = pal[1]; g.lineWidth = 4; g.strokeRect(6, 6, 500, 84);
  fit(g, zh, 150, 50, 220, 58, CJK, '700', pal[1]);
  fit(g, en, 360, 50, 260, 34, SERIF, '700', pal[1]);
  grain(g, 512, 96, 12);
  return tex(c);
}

export function nowSign(text) {
  const [c, g] = canvas(1024, 160);
  const grd = g.createLinearGradient(0, 0, 0, 160);
  grd.addColorStop(0, '#fbfbf8'); grd.addColorStop(1, '#e9ecef');
  g.fillStyle = grd; g.fillRect(0, 0, 1024, 160);
  g.fillStyle = '#e03a3a'; g.fillRect(0, 128, 1024, 32);
  fit(g, text, 512, 66, 900, 72, SANS, '800', '#1d4f91');
  return tex(c);
}

export function fourLanguageSign(lines) {
  const [c, g] = canvas(768, 320);
  g.fillStyle = '#f3e9d6'; g.fillRect(0, 0, 768, 320);
  g.strokeStyle = '#7a2a22'; g.lineWidth = 10; g.strokeRect(8, 8, 752, 304);
  const fams = [SERIF, CJK, SERIF, TAMIL];
  lines.forEach((t, i) => fit(g, t, 384, 52 + i * 72, 700, i === 1 ? 54 : 40, fams[i], '700', i % 2 ? '#7a2a22' : '#1f3a4a'));
  grain(g, 768, 320, 10);
  return tex(c);
}

export function notice(lines) {
  const [c, g] = canvas(360, 400);
  g.fillStyle = '#efe6cf'; g.fillRect(0, 0, 360, 400);
  g.strokeStyle = '#9a2e28'; g.lineWidth = 6; g.strokeRect(10, 10, 340, 380);
  fit(g, lines[0], 180, 110, 300, 44, SANS, '800', '#9a2e28');
  fit(g, lines[1], 180, 210, 300, 44, CJK_BOLD, '700', '#222');
  fit(g, lines[2], 180, 300, 300, 34, SANS, '700', '#222');
  grain(g, 360, 400, 16);
  return tex(c);
}

// ------------------------------------------------------------------ chalk order board
export function orderBoard({ title, rows, legend }) {
  const [c, g] = canvas(1024, 280);
  g.fillStyle = '#23302a'; g.fillRect(0, 0, 1024, 280);
  // chalk dust
  for (let i = 0; i < 900; i++) { g.fillStyle = `rgba(255,255,255,${Math.random() * 0.05})`; g.fillRect(Math.random() * 1024, Math.random() * 280, 3, 2); }
  const chalk = 'rgba(245,242,230,0.92)';
  fit(g, title, 512, 34, 500, 40, CJK, '700', chalk);
  rows.forEach(([zh, en, price], i) => {
    const col = i < 3 ? 0 : 1;
    const row = i < 3 ? i : i - 3;
    const x = 40 + col * 500, y = 92 + row * 52;
    g.textAlign = 'left';
    g.font = `700 32px ${CJK}`; g.fillStyle = chalk; g.fillText(zh, x, y);
    g.font = `700 30px ${SERIF}`; g.fillText(en, x + 130, y);
    g.textAlign = 'right'; g.fillStyle = '#f1d28a'; g.fillText(price, x + 440, y);
  });
  fit(g, legend, 512, 258, 980, 22, SANS, '600', 'rgba(241,210,138,0.95)');
  return tex(c);
}

// ------------------------------------------------------------------ calendar (tear-off daily calendar)
export function calendarPage() {
  const [c, g] = canvas(320, 448);
  g.fillStyle = '#fbf7ec'; g.fillRect(0, 0, 320, 448);
  g.fillStyle = '#b3261e'; g.fillRect(0, 0, 320, 70);
  fit(g, '1965 · AUGUST · 八月', 160, 36, 290, 30, SERIF, '700', '#fff');
  fit(g, '9', 160, 210, 280, 230, SERIF, '700', '#b3261e');
  fit(g, 'MONDAY · 星期一', 160, 350, 280, 28, SERIF, '700', '#333');
  fit(g, 'Isnin', 160, 392, 280, 24, SERIF, '400', '#555');       // review (Malay)
  g.strokeStyle = '#ccc'; g.setLineDash([6, 6]); g.beginPath(); g.moveTo(0, 74); g.lineTo(320, 74); g.stroke();
  grain(g, 320, 448, 10);
  return tex(c);
}

// ------------------------------------------------------------------ portraits (painted studio photos)
export function portrait(kind) {
  const [c, g] = canvas(256, 320);
  const grd = g.createRadialGradient(128, 140, 20, 128, 160, 200);
  grd.addColorStop(0, '#d9c3a0'); grd.addColorStop(1, '#6d5436');
  g.fillStyle = grd; g.fillRect(0, 0, 256, 320);
  g.fillStyle = 'rgba(40,28,18,0.85)';
  // shoulders
  g.beginPath(); g.ellipse(128, 330, 110, 90, 0, Math.PI, 0); g.fill();
  // head
  g.fillStyle = 'rgba(70,52,36,0.9)';
  g.beginPath(); g.ellipse(128, 150, 52, 62, 0, 0, Math.PI * 2); g.fill();
  if (kind === 'ahma') {
    g.fillStyle = 'rgba(160,150,140,0.95)'; // grey hair, bun
    g.beginPath(); g.ellipse(128, 112, 56, 34, 0, Math.PI, 0); g.fill();
    g.beginPath(); g.arc(128, 84, 22, 0, Math.PI * 2); g.fill();
  } else {
    g.fillStyle = 'rgba(20,14,10,0.95)'; // short dark hair, collar
    g.beginPath(); g.ellipse(128, 110, 54, 28, 0, Math.PI, 0); g.fill();
    g.fillStyle = 'rgba(235,228,210,0.9)';
    g.beginPath(); g.moveTo(98, 236); g.lineTo(128, 262); g.lineTo(158, 236); g.lineTo(150, 226); g.lineTo(128, 246); g.lineTo(106, 226); g.fill();
  }
  // soft face light
  g.fillStyle = 'rgba(230,205,170,0.35)';
  g.beginPath(); g.ellipse(120, 158, 30, 40, 0, 0, Math.PI * 2); g.fill();
  const v = g.createRadialGradient(128, 160, 90, 128, 160, 190);
  v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(20,12,6,0.7)');
  g.fillStyle = v; g.fillRect(0, 0, 256, 320);
  grain(g, 256, 320, 24);
  return tex(c);
}

/** Fallback for Papa's frame (no family photo saved in 1942): a red 福 ("good fortune") diamond. */
export function fuDiamond() {
  const [c, g] = canvas(256, 320);
  g.fillStyle = '#efe6cf'; g.fillRect(0, 0, 256, 320);
  g.save(); g.translate(128, 160); g.rotate(Math.PI / 4);
  g.fillStyle = '#b3261e'; g.fillRect(-72, -72, 144, 144);
  g.strokeStyle = '#e9c46a'; g.lineWidth = 5; g.strokeRect(-64, -64, 128, 128);
  g.restore();
  fit(g, '福', 128, 164, 150, 110, CJK, '700', '#1a1a1a');
  grain(g, 256, 320, 14);
  return tex(c);
}

// ------------------------------------------------------------------ the wall choices
export function newspaper() {
  const [c, g] = canvas(360, 320);
  g.fillStyle = '#ece4cf'; g.fillRect(0, 0, 360, 320);
  fit(g, 'THE STRAITS TIMES', 180, 30, 330, 34, '"Old English Text MT", ' + SERIF, '700', '#111');
  g.fillStyle = '#111'; g.fillRect(14, 50, 332, 2);
  fit(g, 'TUESDAY, AUGUST 10, 1965', 180, 62, 330, 11, SERIF, '400', '#333');
  g.fillRect(14, 72, 332, 1);
  fit(g, 'SINGAPORE', 180, 108, 330, 56, SERIF, '800', '#111');
  fit(g, 'IS OUT', 180, 160, 330, 56, SERIF, '800', '#111');
  g.fillStyle = 'rgba(40,40,40,0.55)';
  for (let col = 0; col < 3; col++) for (let r = 0; r < 12; r++) g.fillRect(16 + col * 112, 196 + r * 9, 100 - (r % 5 === 4 ? 30 : 0), 4);
  grain(g, 360, 320, 20);
  return tex(c);
}

/** Singapore's state flag (1959): red over white, white crescent and five stars on the red. */
export function flag() {
  const [c, g] = canvas(540, 360);
  g.fillStyle = '#ef3340'; g.fillRect(0, 0, 540, 180);
  g.fillStyle = '#ffffff'; g.fillRect(0, 180, 540, 180);
  g.fillStyle = '#ffffff';
  g.beginPath(); g.arc(120, 90, 60, 0, Math.PI * 2); g.fill();
  g.fillStyle = '#ef3340';
  g.beginPath(); g.arc(146, 90, 60, 0, Math.PI * 2); g.fill();
  const star = (x, y, r) => {
    g.beginPath();
    for (let i = 0; i < 10; i++) {
      const a = -Math.PI / 2 + i * Math.PI / 5;
      const rr = i % 2 ? r * 0.4 : r;
      g.lineTo(x + Math.cos(a) * rr, y + Math.sin(a) * rr);
    }
    g.closePath(); g.fill();
  };
  g.fillStyle = '#ffffff';
  for (let i = 0; i < 5; i++) {
    const a = -Math.PI / 2 + i * (Math.PI * 2 / 5);
    star(172 + Math.cos(a) * 34, 90 + Math.sin(a) * 34, 13);
  }
  return tex(c);
}
