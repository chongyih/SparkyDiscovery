import * as THREE from 'three';

// Dev-only audit harness (?autoplay). Plays Chapter 1 like a player (walks with the virtual stick,
// advances dialogue, makes choices, aligns the Then & Now photo, solves the puzzle, takes photos)
// and FREEZES the game at every camera cut / glide / dialogue line / card / objective change so a
// screenshot can be taken. Drive it from the console: `await __auto.next()` → label of the next
// capture point (the game stays frozen until the next call).

export function installAutoplay(g) {
  const S = { pending: [], waiting: null, log: [], done: false, lastSpeaker: null, captures: 0, stuck: 0 };
  window.__auto = S;
  const now = () => performance.now();
  const push = (label, times) => {
    const t = now();
    for (const dt of times) {
      if (S.pending.some((p) => Math.abs(p.at - (t + dt)) < 250)) continue;
      S.pending.push({ at: t + dt, label: `${label}${times.length > 1 ? ` (+${dt}ms)` : ''}` });
    }
    S.log.push(`${((g.time) || 0).toFixed(1)}s ${label}`);
  };

  // --- instrumentation ---
  const rig = g.rig;
  const cut = rig.cut.bind(rig);
  rig.cut = (pos, look, lambda = 3, instant = false) => {
    cut(pos, look, lambda, instant);
    if (S.quietCuts) return;
    if (instant || rig.mode !== 'shot') push('cut', [120]);
    else push('glide', [150, 700, 1600]);
  };
  const say = g.ui.say.bind(g.ui);
  g.ui.say = (name, text, o) => {
    if (name !== S.lastSpeaker) push(`line ${name || 'Narrator'}: ${text.slice(0, 60)}`, [500]);
    S.lastSpeaker = name;
    S.lineAt = now();
    return say(name, text, o);
  };
  const card = g.ui.card.bind(g.ui);
  g.ui.card = (k, t, sub, secs) => { push(`card: ${k} ${t}`, [900]); return card(k, t, sub, secs); };
  const objective = g.objective.bind(g);
  g.objective = (text, target, o) => { if (text && text !== S.lastObj) { S.lastObj = text; push(`objective: ${text}`, [400, 2200]); } return objective(text, target, o); };
  const fade = g.ui.fade.bind(g.ui);
  g.ui.fade = (on, secs, color) => { if (!on) push(`fade-in ${color || ''}`, [Math.round((secs || 0.8) * 500)]); return fade(on, secs, color); };

  // --- capture scheduler: freeze at due points ---
  setInterval(() => {
    if (S.waiting || S.done) return;
    const t = now();
    const due = S.pending.filter((p) => p.at <= t).sort((a, b) => a.at - b.at)[0];
    if (!due) return;
    S.pending = S.pending.filter((p) => p !== due);
    S.waiting = due.label;
    S.captures++;
    g.frozen = true;
  }, 30);

  S.next = (timeout = 40000) => new Promise((resolve) => {
    if (S.waiting) { S.waiting = null; g.frozen = false; }
    const t0 = now();
    const poll = setInterval(() => {
      if (S.waiting || S.done || now() - t0 > timeout) {
        clearInterval(poll);
        resolve(S.done ? 'DONE' : S.waiting ? `#${S.captures} ${S.waiting} | mode=${g.mode} era=${g.chapter?.era}` : `timeout | mode=${g.mode} obj=${S.lastObj}`);
      }
    }, 40);
  });

  // --- the player ---
  const V = new THREE.Vector3();
  let lastPos = new THREE.Vector3(), stillFor = 0, acted = 0, vfSince = 0, devSince = 0, lastAdvance = 0;
  const steer = (target) => {
    const p = g.player.root.position;
    V.set(target.x - p.x, 0, target.z - p.z);
    const d = V.length();
    if (d < 0.6) { g.input.stick.x = 0; g.input.stick.y = 0; return d; }
    V.normalize();
    const yaw = rig.yaw, fx = Math.sin(yaw), fz = Math.cos(yaw);
    const my = V.x * fx + V.z * fz;           // along camera forward
    const mx = V.x * -fz + V.z * fx;           // along camera right
    const k = d > 6 ? 1 : 0.8;
    g.input.stick.x = mx * k; g.input.stick.y = my * k;
    return d;
  };
  setInterval(() => {
    if (S.waiting || S.done || g.frozen || g.paused) return;
    const c = g.chapter;
    if (!c) return;
    const t = now();
    try {
      if (g.album.isOpen) { S.done = true; push('ALBUM (end)', [0]); return; }
      const pick = document.getElementById('pick');
      if (!pick.classList.contains('hidden')) {
        if (!S.picking) {
          S.picking = true;
          const cards = pick.querySelectorAll('.pick-card');
          push('choice screen', [0]);
          setTimeout(() => cards[0].click(), 600);
          setTimeout(() => { cards[3].click(); setTimeout(() => { S.picking = false; }, 1500); }, 1100);
        }
        return;
      }
      if (document.querySelector('.puzzle')) { if (t - acted > 700) { acted = t; g.input.emit('action'); } return; }
      if (!document.getElementById('develop').classList.contains('hidden')) {
        if (!devSince) { devSince = t; push('photo develops', [1400]); }
        if (t - devSince > 2600) { devSince = 0; g.ui.confirmDevelop(); }
        return;
      }
      if (g.ui.dialogueActive) {
        if (g.ui._typing) return; // let it type (typewriter runs in real time)
        if (t - (S.lineAt || 0) > 900 && t - lastAdvance > 300) { lastAdvance = t; g.ui.advance(); }
        return;
      }
      if (g.mode === 'viewfinder') {
        if (!vfSince) vfSince = t;
        if (c.era === 'now') {
          // Turn toward the photo like a player would (the magnet finishes the job).
          const n = c.m.THEN_NOW_Camera; n.updateWorldMatrix(true, false);
          const f = V.set(0, 0, 1).transformDirection(n.matrixWorld);
          const ty = Math.atan2(f.x, f.z);
          const v = rig.vf;
          const dy = Math.atan2(Math.sin(ty - v.yaw), Math.cos(ty - v.yaw));
          g.input.look.x += -Math.sign(dy) * Math.min(18, Math.abs(dy) * 120);
          g.input.look.y += -(v.pitch - 0.04) * 60;
        } else if (t - vfSince > 1400) { vfSince = 0; g.input.emit('snap'); }
        return;
      }
      vfSince = 0;
      if (g.mode !== 'play') { g.input.stick.x = 0; g.input.stick.y = 0; return; }
      const it = g.activeInteract;
      if (it && (it.priority || 0) >= 10 && t - acted > 800) { acted = t; g.input.stick.x = 0; g.input.stick.y = 0; g.input.emit('action'); return; }
      const tgt = g.objectiveTarget;
      if (!tgt) return;
      const tp = tgt.isVector3 ? tgt : tgt.root.position;
      const d = steer(tp);
      // Stuck? (not moving while far from the target) → nudge, then teleport.
      const p = g.player.root.position;
      stillFor = p.distanceTo(lastPos) < 0.02 && d > 1.2 ? stillFor + 0.1 : 0;
      lastPos.copy(p);
      if (stillFor > 3) { S.stuck++; push(`STUCK near ${p.x.toFixed(1)},${p.z.toFixed(1)} → teleport`, [0]); p.set(tp.x + 0.8, tp.y, tp.z + (tp.z > 0 ? -0.5 : 0.5)); stillFor = 0; }
    } catch (e) { push(`BOT ERROR ${e.message}`, [0]); }
  }, 100);

  addEventListener('error', (e) => push(`ERROR ${e.message}`, [0]));
  addEventListener('unhandledrejection', (e) => push(`REJECT ${String(e.reason?.message || e.reason)}`, [0]));
  return S;
}
