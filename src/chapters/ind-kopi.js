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
.kopi{position:fixed;inset:0;z-index:36;display:flex;align-items:flex-end;justify-content:center;padding:0 12px calc(12px + var(--safe-b));pointer-events:none}
.kopi-panel{pointer-events:auto;width:min(760px,100%);background:rgba(24,19,13,.92);border:1px solid rgba(255,248,234,.22);border-radius:18px;padding:14px 16px 16px;color:#fff8ea;box-shadow:0 14px 40px rgba(0,0,0,.5);font-family:Inter,system-ui,sans-serif}
.kopi-top{display:flex;gap:12px;align-items:stretch;margin-bottom:10px}
.kopi-ticket{flex:1;background:#f3e9d6;color:#2a1d08;border-radius:10px;padding:8px 12px;font:600 14px/1.3 Inter,system-ui,sans-serif;position:relative}
.kopi-ticket b{display:block;font:700 22px/1.2 Gelasio,Georgia,serif;margin-top:2px}
.kopi-ticket small{color:#6a5840;font-weight:600}
.kopi-now{min-width:190px;text-align:center;border:1px dashed rgba(232,182,76,.6);border-radius:10px;padding:8px 10px}
.kopi-now small{display:block;color:rgba(255,248,234,.65);font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase}
.kopi-now b{display:block;font:700 22px/1.25 Gelasio,Georgia,serif;color:#f4cf7a}
.kopi-row{display:grid;grid-template-columns:62px 1fr;align-items:center;gap:8px;margin:6px 0}
.kopi-row>span{font-size:12px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,248,234,.7)}
.kopi-opts{display:flex;flex-wrap:wrap;gap:6px}
.kopi-opt{border:1px solid rgba(255,248,234,.3);background:rgba(255,248,234,.06);color:#fff8ea;border-radius:999px;padding:7px 12px;font:600 14px Inter,system-ui,sans-serif;display:flex;gap:6px;align-items:baseline;transition:background .15s,border-color .15s,transform .1s}
.kopi-opt em{font-style:normal;font-size:11px;color:rgba(255,248,234,.65);font-weight:600}
.kopi-opt.on{background:linear-gradient(180deg,#f4cf7a,#e8b64c);color:#2a1d08;border-color:transparent}
.kopi-opt.on em{color:#5a4210}
.kopi-opt.hint{box-shadow:0 0 0 3px rgba(120,200,255,.8)}
.kopi-opt:active{transform:scale(.96)}
.kopi-foot{display:flex;justify-content:space-between;align-items:center;margin-top:10px;gap:10px}
.kopi-foot p{margin:0;font-size:12px;color:rgba(255,248,234,.7)}
@media (max-height:480px){.kopi-panel{padding:10px 12px}.kopi-row{margin:3px 0}.kopi-opt{padding:5px 10px;font-size:13px}.kopi-ticket b,.kopi-now b{font-size:18px}}
`;

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
    <div class="kopi-top">
      <div class="kopi-ticket"><small>${ticket.who} ordered</small><b>${ticket.words}</b></div>
      <div class="kopi-now"><small>You're making</small><b class="kopi-name"></b></div>
    </div>
    <div class="kopi-rows"></div>
    <div class="kopi-foot"><p>Kopi & teh come with sweet condensed milk unless you choose otherwise.</p><button class="btn primary small kopi-go">Pour!</button></div>
  </div>`;
  const rows = root.querySelector('.kopi-rows');
  const nameEl = root.querySelector('.kopi-name');
  const buttons = [];
  for (const [key, opts] of Object.entries(OPTIONS)) {
    const row = document.createElement('div');
    row.className = 'kopi-row';
    row.innerHTML = `<span>${ROW_LABEL[key]}</span><div class="kopi-opts"></div>`;
    const wrap = row.querySelector('.kopi-opts');
    for (const [val, label, gloss] of opts) {
      const b = document.createElement('button');
      b.className = 'kopi-opt';
      b.innerHTML = `${label}<em>${gloss}</em>`;
      b.onclick = () => { state[key] = val; onTap?.(); refresh(); };
      b._key = key; b._val = val;
      wrap.appendChild(b);
      buttons.push(b);
    }
    rows.appendChild(row);
  }
  const refresh = () => {
    for (const b of buttons) {
      b.classList.toggle('on', state[b._key] === b._val);
      b.classList.toggle('hint', hint && target && target[b._key] === b._val && state[b._key] !== b._val);
    }
    nameEl.textContent = drinkName(state);
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
