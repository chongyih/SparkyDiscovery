import * as THREE from 'three';

// Kopi orders (Chapter 2's core mechanic). Kopitiam lingo mixes Hokkien, Malay and English:
//   kopi / teh; milk: condensed (default) | O (none) | C (evaporated); sugar: normal | kosong | siew dai | ga dai; peng = iced.
// The player builds a drink in a few taps at Boon's counter, then carries the cup to the customer.

export const OPTIONS = {
  drink: [['kopi', 'Kopi', 'coffee'], ['teh', 'Teh', 'tea']],
  milk: [['condensed', '(normal)', 'condensed milk'], ['O', '-O', 'no milk'], ['C', '-C', 'evaporated milk']],
  sugar: [['normal', '(normal)', 'sweet'], ['kosong', 'kosong', 'no sugar'], ['siew dai', 'siew dai', 'less sweet'], ['ga dai', 'ga dai', 'more sweet']],
  ice: [[false, 'hot', 'hot'], [true, 'peng', 'iced']],
};
const ROW_LABEL = { drink: 'Drink', milk: 'Milk', sugar: 'Sugar', ice: 'Ice' };
// Little visual for each choice (colour swatch / sugar cubes / steam or ice).
const SWATCH = {
  drink: { kopi: '#4a2a17', teh: '#a4562a' },
  milk: { condensed: '#f1e2bf', O: null, C: '#fbf6ea' },
  sugar: { kosong: 0, 'siew dai': 1, normal: 2, 'ga dai': 3 },
};

/** Kopitiam name of a drink: e.g. { kopi, O, kosong } → "Kopi-O kosong". */
export function drinkName(d) {
  let s = d.drink === 'teh' ? 'Teh' : 'Kopi';
  if (d.milk === 'O') s += '-O';
  if (d.milk === 'C') s += '-C';
  if (d.sugar !== 'normal') s += ` ${d.sugar}`;
  if (d.ice) s += ' peng';
  return s;
}

export function sameDrink(a, b) {
  return a.drink === b.drink && a.milk === b.milk && a.sugar === b.sugar && !!a.ice === !!b.ice;
}

const CSS = `
body.kopi-open #objective,body.kopi-open #prompt,body.kopi-open #compass,body.kopi-open #toast{visibility:hidden}
.kopi{position:fixed;inset:0;z-index:36;display:flex;align-items:flex-end;justify-content:center;padding:0 12px calc(12px + var(--safe-b));pointer-events:none;animation:kopiIn .22s ease-out}
@keyframes kopiIn{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:none}}
.kopi-panel{pointer-events:auto;width:min(860px,100%);display:grid;grid-template-columns:230px 1fr;gap:14px;background:linear-gradient(180deg,rgba(38,30,21,.96),rgba(24,19,13,.96));border:1px solid rgba(232,182,76,.35);border-radius:20px;padding:14px;color:#fff8ea;box-shadow:0 18px 50px rgba(0,0,0,.55);font-family:Inter,system-ui,sans-serif}
.kopi-left{display:flex;flex-direction:column;gap:10px;align-items:stretch}
.kopi-chit{position:relative;background:#f6ecd4;color:#2a1d08;border-radius:4px 4px 10px 10px;padding:10px 12px 12px;transform:rotate(-1.2deg);box-shadow:0 4px 10px rgba(0,0,0,.35);background-image:repeating-linear-gradient(180deg,transparent 0 21px,rgba(60,90,140,.13) 21px 22px)}
.kopi-chit:before{content:'';position:absolute;left:50%;top:-6px;width:34px;height:12px;margin-left:-17px;background:rgba(232,182,76,.75);border-radius:2px}
.kopi-chit small{display:block;font:700 10px/1.2 Inter,sans-serif;letter-spacing:.1em;text-transform:uppercase;color:#7a6446}
.kopi-chit b{display:block;font:700 21px/1.15 Gelasio,Georgia,serif;margin-top:4px}
.kopi-cup{position:relative;flex:1;min-height:120px;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;border-radius:14px;background:radial-gradient(ellipse at 50% 85%,rgba(232,182,76,.18),transparent 70%)}
.kopi-cup svg{width:160px;height:auto;overflow:visible}
.kopi-cup svg *{transition:fill .25s,opacity .25s,transform .25s}
.kopi-name{font:700 19px/1.2 Gelasio,Georgia,serif;color:#f4cf7a;text-align:center;margin-top:4px;min-height:23px;white-space:nowrap;max-width:100%;overflow:hidden}
.kopi-right{display:flex;flex-direction:column;gap:11px;min-width:0}
.kopi-row{display:grid;grid-template-columns:78px 1fr;align-items:center;gap:8px}
.kopi-row>span{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,248,234,.62)}
.kopi-opts{display:flex;flex-wrap:wrap;gap:9px}
.kopi-opt{position:relative;border:1px solid rgba(255,248,234,.22);background:rgba(255,248,234,.05);color:#fff8ea;border-radius:12px;padding:6px 11px 6px 8px;font:700 14px Inter,system-ui,sans-serif;display:flex;gap:8px;align-items:center;text-align:left;transition:background .15s,border-color .15s,transform .1s,box-shadow .15s;cursor:pointer}
.kopi-opt:hover{background:rgba(255,248,234,.1)}
.kopi-opt .ic{flex:none;width:22px;height:22px;display:grid;place-items:center}
.kopi-opt .tx{display:flex;flex-direction:column;line-height:1.1}
.kopi-opt em{font-style:normal;font-size:11px;color:rgba(255,248,234,.6);font-weight:600}
.kopi-opt.on{background:linear-gradient(180deg,#f7d98c,#e8b64c);color:#2a1d08;border-color:transparent;box-shadow:0 3px 10px rgba(232,182,76,.35)}
.kopi-opt.on em{color:#5a4210}
.kopi-opt.hint{box-shadow:0 0 0 3px rgba(120,200,255,.85)}
.kopi-opt.hint:after{content:'';position:absolute;right:-4px;top:-4px;width:10px;height:10px;border-radius:50%;background:#78c8ff}
.kopi-opt:active{transform:scale(.96)}
.kopi-opt:focus-visible{outline:2px solid #fff;outline-offset:2px}
.kopi-sw{width:18px;height:18px;border-radius:50%;border:2px solid rgba(255,255,255,.55)}
.kopi-sw.none{background:transparent;position:relative}
.kopi-sw.none:after{content:'';position:absolute;left:50%;top:-2px;bottom:-2px;width:2px;margin-left:-1px;background:rgba(255,255,255,.7);transform:rotate(45deg)}
.kopi-opt.on .kopi-sw{border-color:rgba(42,29,8,.5)}
.kopi-opt.on .kopi-sw.none:after{background:rgba(42,29,8,.6)}
.kopi-cubes{display:flex;gap:2px;align-items:center;min-width:22px;justify-content:center}
.kopi-cubes i{width:6px;height:6px;border-radius:1.5px;background:currentColor;opacity:.85}
.kopi-cubes .z{font:700 12px Inter;opacity:.7}
.kopi-foot{display:flex;justify-content:space-between;align-items:center;margin-top:auto;gap:10px;padding-top:4px}
.kopi-foot p{margin:0;font-size:12px;color:rgba(255,248,234,.62);line-height:1.35}
.kopi-go{min-width:120px;font-size:16px !important}
@media (max-width:760px),(max-height:540px){
.kopi{padding:0 8px calc(8px + var(--safe-b))}
.kopi-panel{grid-template-columns:164px 1fr;gap:12px;padding:10px 12px;border-radius:16px}
.kopi-chit{padding:7px 9px 8px}.kopi-chit b{font-size:15px}.kopi-chit small{font-size:9px}
.kopi-cup{min-height:0}.kopi-cup svg{width:112px}.kopi-name{font-size:15px;min-height:19px}
.kopi-right{gap:6px}.kopi-row{grid-template-columns:1fr;gap:3px}.kopi-row>span{font-size:9px;letter-spacing:.1em}
.kopi-opts{gap:7px;flex-wrap:nowrap}.kopi-opt{padding:4px 8px 4px 5px;font-size:12px;border-radius:10px;gap:5px;white-space:nowrap}.kopi-opt .ic{height:18px}
.kopi-sw{width:15px;height:15px}.kopi-opt em{display:none}.kopi-foot p{display:none}.kopi-go{min-width:0;padding:7px 18px !important;font-size:15px !important}}
@media (max-width:480px) and (orientation:portrait){.kopi-panel{grid-template-columns:1fr}.kopi-left{flex-direction:row}.kopi-chit{flex:1}.kopi-cup{flex:0 0 110px}}
`;

/** Sugar cubes beside the saucer (a little stack), or a dashed outline for kosong. */
function sugarSVG(n) {
  const cube = (x, y) => `<g transform="translate(${x} ${y})" stroke="#7d6a48" stroke-width="1.2" stroke-linejoin="round">
    <path d="M0 5 L7 1 L15 5 L8 9 Z" fill="#ffffff"/><path d="M0 5 L8 9 L8 19 L0 15 Z" fill="#efe6d2"/><path d="M8 9 L15 5 L15 15 L8 19 Z" fill="#d7c9aa"/></g>`;
  if (!n) return '<g transform="translate(126 110)" fill="none" stroke="rgba(255,248,234,.45)" stroke-width="1.4" stroke-dasharray="3 2"><path d="M0 5 L7 1 L15 5 L15 15 L8 19 L0 15 Z"/></g>';
  const spots = [[124, 111], [139, 111], [131, 97]].slice(0, n);
  return spots.map(([x, y]) => cube(x, y)).join('');
}

/** The drink as it is being made: an opaque kopitiam cup showing the surface colour, or (iced) a
 *  glass where the condensed milk has settled at the bottom. Sugar cubes sit beside it. */
function cupSVG(d) {
  const mixed = LIQUID[`${d.drink}|${d.milk}`] || '#8a5a3a';
  const sugar = sugarSVG(SWATCH.sugar[d.sugar] ?? 2);
  if (d.ice) {
    const dark = d.drink === 'teh' ? '#9a4a1c' : '#3e2213';
    const top = d.milk === 'condensed' ? dark : mixed;
    const grad = d.milk === 'condensed'
      ? `<stop offset="0" stop-color="${top}"/><stop offset=".62" stop-color="${top}"/><stop offset=".74" stop-color="#d9c29a"/><stop offset="1" stop-color="#f3e6c6"/>`
      : `<stop offset="0" stop-color="${top}"/><stop offset="1" stop-color="${top}"/>`;
    return `<svg viewBox="0 0 160 140" aria-hidden="true"><defs><clipPath id="kc"><path d="M34 32 L86 32 L81 122 Q60 128 39 122 Z"/></clipPath>
      <linearGradient id="kg" x1="0" y1="0" x2="0" y2="1">${grad}</linearGradient></defs>
      <ellipse cx="60" cy="128" rx="34" ry="5" fill="rgba(0,0,0,.25)"/>
      <rect x="20" y="44" width="80" height="90" fill="url(#kg)" clip-path="url(#kc)"/>
      ${d.milk === 'C' ? '<path d="M40 50 q12 -5 20 2 q10 7 22 -1" fill="none" stroke="rgba(255,250,240,.55)" stroke-width="3" clip-path="url(#kc)"/>' : ''}
      <g fill="rgba(245,252,255,.7)" stroke="rgba(255,255,255,.95)" stroke-width="1.2"><rect x="42" y="38" width="16" height="16" rx="3" transform="rotate(-12 50 46)"/><rect x="60" y="44" width="16" height="16" rx="3" transform="rotate(18 68 52)"/><rect x="50" y="58" width="15" height="15" rx="3" transform="rotate(6 57 65)"/></g>
      <path d="M34 32 L86 32 L81 122 Q60 128 39 122 Z" fill="rgba(220,240,245,.12)" stroke="rgba(235,248,252,.85)" stroke-width="3"/>
      <path d="M40 40 L44 116" stroke="rgba(255,255,255,.35)" stroke-width="3" stroke-linecap="round"/>
      ${sugar}</svg>`;
  }
  const swirl = d.milk === 'condensed' ? '<path d="M44 60 q10 -4 18 0 q9 4 16 -1" fill="none" stroke="rgba(245,225,185,.55)" stroke-width="2.5"/>'
    : d.milk === 'C' ? '<path d="M44 60 q10 -4 18 0 q9 4 16 -1" fill="none" stroke="rgba(255,250,240,.7)" stroke-width="2.5"/>' : '';
  return `<svg viewBox="0 0 160 140" aria-hidden="true">
    <g stroke="rgba(255,248,234,.5)" stroke-width="2.5" fill="none" stroke-linecap="round"><path d="M48 44 q-6 -9 0 -18 q6 -9 0 -18"/><path d="M62 44 q-6 -9 0 -18 q6 -9 0 -18"/><path d="M76 44 q-6 -9 0 -18 q6 -9 0 -18"/></g>
    <ellipse cx="60" cy="124" rx="52" ry="11" fill="rgba(0,0,0,.22)"/>
    <ellipse cx="60" cy="120" rx="50" ry="10" fill="#e9e3d6"/><ellipse cx="60" cy="117" rx="40" ry="6" fill="#f6f2e8"/>
    <path d="M94 70 q20 2 16 20 q-4 14 -22 10" fill="none" stroke="#f3efe6" stroke-width="7"/>
    <path d="M24 57 L96 57 L89 108 Q60 122 31 108 Z" fill="#f6f2e8" stroke="#d8d0bf" stroke-width="1.5"/>
    <path d="M30 70 L36 104" stroke="rgba(255,255,255,.8)" stroke-width="4" stroke-linecap="round"/>
    <path d="M25 64 L95 64" stroke="#3f7a5a" stroke-width="3"/>
    <ellipse cx="60" cy="58" rx="35" ry="6" fill="#f6f2e8" stroke="#d8d0bf" stroke-width="1.5"/>
    <ellipse cx="60" cy="58.5" rx="31" ry="4.6" fill="${mixed}"/>${swirl}
    ${sugar}</svg>`;
}

function ensureCSS() {
  if (document.getElementById('kopi-css')) return;
  const st = document.createElement('style');
  st.id = 'kopi-css';
  st.textContent = CSS;
  document.head.appendChild(st);
}

/**
 * Show the counter UI. `ticket`: { who, words } (the customer's order in their own words).
 * `hint`: highlight the right options (after a wrong drink). Resolves with the drink built.
 */
export function makeDrink({ ticket, target, hint = false, onTap }) {
  ensureCSS();
  const state = { drink: 'kopi', milk: 'condensed', sugar: 'normal', ice: false };
  const root = document.createElement('div');
  root.className = 'kopi';
  root.innerHTML = `<div class="kopi-panel" role="dialog" aria-label="Make the drink">
    <div class="kopi-left">
      <div class="kopi-chit"><small>Order · ${ticket.who}</small><b>${ticket.words}</b></div>
      <div class="kopi-cup"><div class="kopi-svg"></div><div class="kopi-name" aria-live="polite"></div></div>
    </div>
    <div class="kopi-right">
      <div class="kopi-rows"></div>
      <div class="kopi-foot"><p>Kopi and teh come with sweet condensed milk unless you choose otherwise.</p><button class="btn primary kopi-go">Pour ☕</button></div>
    </div>
  </div>`;
  const rows = root.querySelector('.kopi-rows');
  const nameEl = root.querySelector('.kopi-name');
  const svgEl = root.querySelector('.kopi-svg');
  const buttons = [];
  const icon = (key, val) => {
    if (key === 'drink' || key === 'milk') {
      const c = SWATCH[key][val];
      return c ? `<span class="kopi-sw" style="background:${c}"></span>` : '<span class="kopi-sw none"></span>';
    }
    if (key === 'sugar') {
      const n = SWATCH.sugar[val];
      return `<span class="kopi-cubes">${n ? '<i></i>'.repeat(n) : '<span class="z">0</span>'}</span>`;
    }
    return val ? '❄️' : '♨️';
  };
  for (const [key, opts] of Object.entries(OPTIONS)) {
    const row = document.createElement('div');
    row.className = 'kopi-row';
    row.innerHTML = `<span>${ROW_LABEL[key]}</span><div class="kopi-opts" role="radiogroup" aria-label="${ROW_LABEL[key]}"></div>`;
    const wrap = row.querySelector('.kopi-opts');
    for (const [val, label, gloss] of opts) {
      const b = document.createElement('button');
      b.className = 'kopi-opt';
      b.setAttribute('role', 'radio');
      b.innerHTML = `<span class="ic">${icon(key, val)}</span><span class="tx">${label}<em>${gloss}</em></span>`;
      b.onclick = () => { state[key] = val; onTap?.(); refresh(); };
      b._key = key; b._val = val;
      wrap.appendChild(b);
      buttons.push(b);
    }
    rows.appendChild(row);
  }
  const refresh = () => {
    for (const b of buttons) {
      const on = state[b._key] === b._val;
      b.classList.toggle('on', on);
      b.setAttribute('aria-checked', on ? 'true' : 'false');
      b.classList.toggle('hint', hint && target && target[b._key] === b._val && !on);
    }
    nameEl.textContent = drinkName(state);
    // keep the name on one line: shrink it for the longest combinations (e.g. "Kopi-C siew dai peng")
    nameEl.style.fontSize = '';
    for (let fs = parseFloat(getComputedStyle(nameEl).fontSize); nameEl.scrollWidth > nameEl.clientWidth && fs > 11; fs -= 1) nameEl.style.fontSize = `${fs - 1}px`;
    svgEl.innerHTML = cupSVG(state);
  };
  refresh();
  document.body.appendChild(root);
  document.body.classList.add('kopi-open');
  return new Promise((resolve) => {
    const go = root.querySelector('.kopi-go');
    const done = () => { removeEventListener('keydown', key); root.remove(); document.body.classList.remove('kopi-open'); resolve({ ...state }); };
    go.onclick = done;
    const key = (e) => { if (e.code === 'Enter') { e.preventDefault(); done(); } };
    addEventListener('keydown', key);
    setTimeout(() => go.focus(), 50);
  });
}

// ------------------------------------------------------------------ the cup
const LIQUID = {
  'kopi|condensed': '#8a5a3a', 'kopi|O': '#2a160c', 'kopi|C': '#9c6c4a',
  'teh|condensed': '#c08a55', 'teh|O': '#7e3c16', 'teh|C': '#c9955f',
};

/** A kopitiam cup and saucer (or a tall glass for iced drinks), ~real size (Sparky is 1 m tall). */
export function cupMesh(d) {
  const g = new THREE.Group();
  const liquid = new THREE.MeshStandardMaterial({ color: LIQUID[`${d.drink}|${d.milk}`] || '#8a5a3a', roughness: 0.25 });
  if (d.ice) {
    const glass = new THREE.Mesh(new THREE.CylinderGeometry(0.036, 0.03, 0.13, 14, 1, true),
      new THREE.MeshStandardMaterial({ color: '#dfeeee', roughness: 0.05, transparent: true, opacity: 0.35, side: THREE.DoubleSide }));
    glass.position.y = 0.065;
    const drink = new THREE.Mesh(new THREE.CylinderGeometry(0.033, 0.028, 0.11, 14), liquid);
    drink.position.y = 0.057;
    g.add(glass, drink);
    const iceMat = new THREE.MeshStandardMaterial({ color: '#f4fbff', roughness: 0.1, transparent: true, opacity: 0.8 });
    for (let i = 0; i < 3; i++) {
      const cube = new THREE.Mesh(new THREE.BoxGeometry(0.018, 0.018, 0.018), iceMat);
      cube.position.set(Math.cos(i * 2.1) * 0.012, 0.108 + i * 0.004, Math.sin(i * 2.1) * 0.012);
      cube.rotation.set(i, i * 0.7, 0);
      g.add(cube);
    }
  } else {
    const china = new THREE.MeshStandardMaterial({ color: '#f3f0e6', roughness: 0.3 });
    const rim = new THREE.MeshStandardMaterial({ color: '#3f7a5a', roughness: 0.4 });
    const saucer = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.055, 0.012, 20), china);
    saucer.position.y = 0.006;
    const cup = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.03, 0.07, 18, 1, true), china);
    cup.material.side = THREE.DoubleSide;
    cup.position.y = 0.047;
    const band = new THREE.Mesh(new THREE.CylinderGeometry(0.0405, 0.0395, 0.008, 18, 1, true), rim);
    band.position.y = 0.075;
    const base = new THREE.Mesh(new THREE.CircleGeometry(0.03, 16), china);
    base.rotation.x = -Math.PI / 2; base.position.y = 0.013;
    const drink = new THREE.Mesh(new THREE.CircleGeometry(0.037, 18), liquid);
    drink.rotation.x = -Math.PI / 2; drink.position.y = 0.072;
    const handle = new THREE.Mesh(new THREE.TorusGeometry(0.016, 0.004, 6, 12, Math.PI * 1.2), china);
    handle.position.set(0.043, 0.048, 0); handle.rotation.z = -Math.PI * 0.6;
    g.add(saucer, cup, band, base, drink, handle);
  }
  g.traverse((o) => { if (o.isMesh) o.castShadow = false; });
  g.userData.drink = d;
  return g;
}
