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

/** Present-day neighbourhood shop sign: backlit panel, English + Chinese. */
export function nowShopSign([en, zh], i = 0) {
  const pal = [['#ffffff', '#1d4f91', '#e03a3a'], ['#fff4d6', '#9a2b1f', '#9a2b1f'], ['#f2f7f2', '#1f6a45', '#1f6a45'], ['#1c1c22', '#f0d27a', '#f0d27a']][i % 4];
  const [c, g] = canvas(1024, 160);
  g.fillStyle = pal[0]; g.fillRect(0, 0, 1024, 160);
  fit(g, zh, 250, 80, 380, 96, CJK_BOLD, '700', pal[2]);
  fit(g, en, 690, 80, 560, 64, SANS, '800', pal[1]);
  return tex(c);
}

/** The block number, painted HDB-style. */
export function blockNumber(n) {
  const [c, g] = canvas(256, 256);
  g.fillStyle = '#f4efe4'; g.fillRect(0, 0, 256, 256);
  fit(g, 'BLK', 128, 58, 200, 44, SANS, '800', '#7a3b22');
  fit(g, String(n), 128, 160, 220, 150, SANS, '800', '#7a3b22');
  return tex(c);
}

/** A heritage-trail style plaque (our own design, with verified facts). */
export function heritageMarker({ title, lines }) {
  const [c, g] = canvas(512, 336);
  g.fillStyle = '#23443a'; g.fillRect(0, 0, 512, 336);
  g.strokeStyle = '#e2c98a'; g.lineWidth = 6; g.strokeRect(12, 12, 488, 312);
  fit(g, title, 256, 62, 440, 44, SERIF, '700', '#e2c98a');
  g.font = `500 24px ${SANS}`;
  g.fillStyle = '#f3ecdc';
  g.textAlign = 'center';
  let y = 124;
  for (const line of lines) {
    const words = line.split(' ');
    let row = '';
    for (const w of words) {
      const next = row ? `${row} ${w}` : w;
      if (g.measureText(next).width > 440) { g.fillText(row, 256, y); y += 32; row = w; } else row = next;
    }
    g.fillText(row, 256, y); y += 42;
  }
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
/** A hand-tinted sepia studio portrait in an oval card mount (Ah Ma, or Papa's 1942 photo). */
export function portrait(kind) {
  const W = 512, H = 640;
  const [c, g] = canvas(W, H);
  // card mount with an oval window
  const mount = g.createLinearGradient(0, 0, 0, H);
  mount.addColorStop(0, '#e9dec6'); mount.addColorStop(1, '#d8c9a8');
  g.fillStyle = mount; g.fillRect(0, 0, W, H);
  const cx = 256, cy = 300, rx = 200, ry = 252;
  g.save();
  g.beginPath(); g.ellipse(cx, cy, rx, ry, 0, 0, Math.PI * 2); g.clip();
  const bg = g.createRadialGradient(cx - 30, cy - 60, 30, cx, cy, 300);
  bg.addColorStop(0, '#d6c19c'); bg.addColorStop(1, '#6f5838');
  g.fillStyle = bg; g.fillRect(0, 0, W, H);
  g.translate(cx, 330); g.scale(1.2, 1.2); g.translate(-cx, -330);   // a closer head-and-shoulders crop
  const ahma = kind === 'ahma';
  const skin = ahma ? '#c69e76' : '#caa47c', skinDark = ahma ? '#9c7652' : '#a07a55';
  // body
  g.fillStyle = ahma ? '#3a2b1f' : '#e8dcc2';
  g.beginPath(); g.ellipse(cx, 610, 230, 190, 0, Math.PI, 0); g.fill();
  if (ahma) {
    // samfu: mandarin collar, diagonal opening with frog buttons
    g.fillStyle = '#4a3828'; g.fillRect(cx - 46, 402, 92, 34);
    g.strokeStyle = '#a58a62'; g.lineWidth = 4;
    g.beginPath(); g.moveTo(cx - 40, 436); g.quadraticCurveTo(cx + 40, 450, cx + 92, 520); g.stroke();
    g.fillStyle = '#b89b70';
    for (const [x, y] of [[cx + 20, 452], [cx + 52, 478], [cx + 80, 506]]) { g.beginPath(); g.ellipse(x, y, 11, 5, 0.5, 0, Math.PI * 2); g.fill(); }
  } else {
    // open-collared white shirt under a dark jacket
    g.fillStyle = '#2f2419';
    g.beginPath(); g.moveTo(cx - 230, 640); g.lineTo(cx - 60, 430); g.lineTo(cx - 20, 640); g.fill();
    g.beginPath(); g.moveTo(cx + 230, 640); g.lineTo(cx + 60, 430); g.lineTo(cx + 20, 640); g.fill();
    g.fillStyle = '#f2e9d6';
    g.beginPath(); g.moveTo(cx - 52, 420); g.lineTo(cx, 470); g.lineTo(cx + 52, 420); g.lineTo(cx + 36, 404); g.lineTo(cx, 440); g.lineTo(cx - 36, 404); g.fill();
  }
  // neck + head
  g.fillStyle = skinDark; g.fillRect(cx - 34, 350, 68, 70);
  const face = g.createRadialGradient(cx - 26, 250, 20, cx, 280, 130);
  face.addColorStop(0, '#e2c49c'); face.addColorStop(0.6, skin); face.addColorStop(1, skinDark);
  g.fillStyle = face; g.beginPath(); g.ellipse(cx, 280, 96, 110, 0, 0, Math.PI * 2); g.fill();
  g.fillStyle = skinDark;
  for (const sd of [-1, 1]) { g.beginPath(); g.ellipse(cx + sd * 96, 290, 14, 22, 0, 0, Math.PI * 2); g.fill(); }
  // hair
  g.fillStyle = ahma ? '#a59c8e' : '#231a12';
  g.beginPath(); g.ellipse(cx, ahma ? 222 : 214, 100, ahma ? 66 : 62, 0, Math.PI, 0); g.fill();
  if (ahma) {
    g.beginPath(); g.arc(cx, 158, 34, 0, Math.PI * 2); g.fill();                 // bun
    g.strokeStyle = 'rgba(80,70,60,.5)'; g.lineWidth = 3;
    g.beginPath(); g.moveTo(cx, 162); g.lineTo(cx, 214); g.stroke();              // centre parting
  } else {
    g.beginPath(); g.moveTo(cx - 100, 222); g.quadraticCurveTo(cx - 40, 160, cx + 104, 212); g.lineTo(cx + 100, 236); g.quadraticCurveTo(cx, 200, cx - 100, 232); g.fill();
  }
  // face: brows, eyes, nose, mouth (the game's simple style, softened)
  g.strokeStyle = ahma ? '#6d5a48' : '#2a1f16'; g.lineWidth = 5; g.lineCap = 'round';
  for (const sd of [-1, 1]) { g.beginPath(); g.moveTo(cx + sd * 22, 250); g.quadraticCurveTo(cx + sd * 40, 242, cx + sd * 58, 250); g.stroke(); }
  g.fillStyle = '#2a1d14';
  for (const sd of [-1, 1]) { g.beginPath(); g.ellipse(cx + sd * 40, 276, 8, 10, 0, 0, Math.PI * 2); g.fill(); }
  g.strokeStyle = skinDark; g.lineWidth = 4;
  g.beginPath(); g.moveTo(cx - 4, 292); g.quadraticCurveTo(cx + 8, 312, cx - 6, 318); g.stroke();
  g.strokeStyle = '#7a4e3a'; g.lineWidth = 4;
  g.beginPath(); g.moveTo(cx - 22, 344); g.quadraticCurveTo(cx, 352, cx + 22, 344); g.stroke();
  if (ahma) {
    g.strokeStyle = 'rgba(110,80,55,.45)'; g.lineWidth = 3;
    for (const sd of [-1, 1]) { g.beginPath(); g.moveTo(cx + sd * 30, 322); g.quadraticCurveTo(cx + sd * 38, 340, cx + sd * 30, 356); g.stroke(); }
  }
  // vignette inside the oval
  const v = g.createRadialGradient(cx, cy, 120, cx, cy, 260);
  v.addColorStop(0, 'rgba(0,0,0,0)'); v.addColorStop(1, 'rgba(40,24,10,.55)');
  g.fillStyle = v; g.fillRect(0, 0, W, H);
  g.restore();
  // gilt line around the window, a studio emboss in the corner
  g.strokeStyle = '#b9975a'; g.lineWidth = 5;
  g.beginPath(); g.ellipse(cx, cy, rx + 4, ry + 4, 0, 0, Math.PI * 2); g.stroke();
  g.fillStyle = 'rgba(120,95,60,.55)'; g.font = `600 22px ${CJK}`; g.textAlign = 'right';
  g.fillText(ahma ? '南光照相' : '一九四二', W - 34, H - 30);
  grain(g, W, H, 16);
  return tex(c);
}

/** Fallback for Papa's frame (no 1942 photo saved): a red 福 on red paper, on a red-and-gold mount. */
export function fuDiamond() {
  const W = 512, H = 640;
  const [c, g] = canvas(W, H);
  g.fillStyle = '#7e1813'; g.fillRect(0, 0, W, H);
  g.strokeStyle = '#d9b25e'; g.lineWidth = 8; g.strokeRect(26, 26, W - 52, H - 52);
  g.lineWidth = 2; g.strokeRect(40, 40, W - 80, H - 80);
  g.save(); g.translate(W / 2, H / 2); g.rotate(Math.PI / 4);
  const paper = g.createLinearGradient(-150, -150, 150, 150);
  paper.addColorStop(0, '#d53a2c'); paper.addColorStop(1, '#b02419');
  g.fillStyle = paper; g.fillRect(-150, -150, 300, 300);
  g.strokeStyle = '#f0cf72'; g.lineWidth = 7; g.strokeRect(-134, -134, 268, 268);
  g.restore();
  g.save(); g.shadowColor = 'rgba(60,10,0,.6)'; g.shadowBlur = 6; g.shadowOffsetY = 3;
  fit(g, '福', W / 2, H / 2 + 8, 300, 230, CJK, '700', '#f3d47a');
  g.restore();
  grain(g, W, H, 14);
  return tex(c);
}

/** A congratulations mirror: silvered glass, gold characters (the shop's opening gift from friends). */
export function congratsMirror({ main, to, from }) {
  const W = 640, H = 410;
  const [c, g] = canvas(W, H);
  const glass = g.createLinearGradient(0, 0, W, H);
  glass.addColorStop(0, '#c9d2d5'); glass.addColorStop(0.45, '#8d9aa0'); glass.addColorStop(1, '#d6dcde');
  g.fillStyle = glass; g.fillRect(0, 0, W, H);
  g.fillStyle = 'rgba(255,255,255,.22)';
  for (const [x, w] of [[90, 60], [190, 24], [430, 70]]) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x + w, 0); g.lineTo(x + w - 160, H); g.lineTo(x - 160, H); g.fill(); }
  g.strokeStyle = 'rgba(232,194,90,.9)'; g.lineWidth = 4; g.strokeRect(18, 18, W - 36, H - 36);
  const gold = '#e3bb55';
  g.save(); g.shadowColor = 'rgba(40,25,5,.55)'; g.shadowBlur = 4; g.shadowOffsetY = 2;
  fit(g, main, W / 2, H / 2 + 6, W - 200, 118, CJK_BOLD, '700', gold);
  const column = (text, x, y0, size) => { g.font = `700 ${size}px ${CJK_BOLD}`; g.fillStyle = gold; g.textAlign = 'center'; [...text.replace(/ /g, '')].forEach((ch, i) => g.fillText(ch, x, y0 + i * (size + 4))); };
  column(to, W - 56, 64, 30);
  column(from, 56, 150, 30);
  g.restore();
  return tex(c);
}

/** A coffee supplier's 1965 calendar poster (invented firm). */
export function calendarPoster({ zh, en, year, tag }) {
  const W = 320, H = 488;
  const [c, g] = canvas(W, H);
  g.fillStyle = '#efe3c6'; g.fillRect(0, 0, W, H);
  g.fillStyle = '#a8261c'; g.fillRect(0, 0, W, 84);
  fit(g, zh, W / 2, 46, W - 40, 56, CJK_BOLD, '700', '#f8e7b8');
  // painted tin and cup
  g.fillStyle = '#2f5a45'; g.fillRect(64, 120, 96, 130);
  g.fillStyle = '#e8c25a'; g.fillRect(64, 150, 96, 34);
  g.fillStyle = '#23443a'; g.beginPath(); g.ellipse(112, 120, 48, 12, 0, 0, Math.PI * 2); g.fill();
  fit(g, 'KOPI', 112, 168, 86, 22, SANS, '800', '#2f5a45');
  g.fillStyle = '#f6f2e8'; g.beginPath(); g.moveTo(182, 196); g.lineTo(252, 196); g.lineTo(244, 246); g.quadraticCurveTo(217, 258, 190, 246); g.fill();
  g.strokeStyle = '#f6f2e8'; g.lineWidth = 8; g.beginPath(); g.arc(256, 218, 14, -1.2, 1.3); g.stroke();
  g.fillStyle = '#6b3f22'; g.beginPath(); g.ellipse(217, 198, 34, 6, 0, 0, Math.PI * 2); g.fill();
  g.fillStyle = '#e9e3d6'; g.beginPath(); g.ellipse(217, 252, 50, 9, 0, 0, Math.PI * 2); g.fill();
  fit(g, en, W / 2, 290, W - 30, 22, SERIF, '700', '#5a3d1e');
  fit(g, tag, W / 2, 318, W - 40, 16, SANS, '600', '#8a6a44');
  // the year and a 12-month grid
  fit(g, year, W / 2, 360, 160, 40, SERIF, '700', '#a8261c');
  g.fillStyle = 'rgba(90,61,30,.55)';
  for (let m = 0; m < 12; m++) {
    const x = 28 + (m % 4) * 68, y = 386 + Math.floor(m / 4) * 32;
    g.fillRect(x, y, 56, 3);
    for (let k = 0; k < 4; k++) g.fillRect(x + k * 14, y + 8, 10, 14);
  }
  grain(g, W, H, 16);
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
