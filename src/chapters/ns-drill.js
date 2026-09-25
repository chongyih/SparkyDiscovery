import * as THREE from 'three';
import { settings, isTouch } from '../engine/settings.js';

// Foot drill (Chapter 3's core mechanic): "wait for the word".
// Every command is a drawn-out cautionary word ("Ke kanaaan…") then a sharp executive word ("PUSING!").
// You move on the executive word only. Timing is measured from the executive word (not a metronome), with a
// closing ring as the main cue; pressing during the cautionary word is "jumping the gun". No fail state.
//   Day one: Ah Hock can't follow the Malay, so he copies Sparky: right or wrong. Mistakes → "Again!".
//   Passing out: words only, no second tries; if Sparky slips, Ah Hock nudges him back into line.
// Design: docs/design.md (Chapter 3, core mechanic). Words: docs/ch3-script.md (Drill words). [SAF/native review]

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const HALF = Math.PI / 2;

/** turn: yaw change (right turn = −90°). input: which control answers it. */
export const CMD = {
  sedia: { caution: 'Seksyen…', exec: 'SEDIA!', input: 'stamp', turn: 0, mean: 'Attention!' },
  kanan: { caution: 'Ke kanan…', exec: 'PUSING!', input: 'right', turn: -HALF, mean: 'Right… turn!' },
  kiri: { caution: 'Ke kiri…', exec: 'PUSING!', input: 'left', turn: HALF, mean: 'Left… turn!' },
  belakang: { caution: 'Ke belakang…', exec: 'PUSING!', input: 'back', turn: -Math.PI, mean: 'About… turn!' },
  jalan: { caution: 'Dari kiri, cepat…', exec: 'JALAN!', input: 'up', march: true, mean: 'From the left, quick… march!' },
  berhenti: { caution: 'Seksyen…', exec: 'BERHENTI!', input: 'stamp', halt: true, mean: 'Halt!' },
  pandang: { caution: 'Pandang…', exec: 'KANAN!', input: 'look', mean: 'Eyes… right!' },
  depan: { caution: 'Pandang…', exec: 'DEPAN!', input: 'auto', mean: 'Eyes… front!' },
  sandang: { caution: 'Sandang…', exec: 'SENJATA!', input: 'up', mean: 'Sling… arms!' }, // review (Malay)
  bersurai: { caution: 'Seksyen…', exec: 'BERSURAI!', input: 'auto', mean: 'Dismissed!' }, // review (Malay)
};

// What each control does to Sparky (so a wrong press turns him the wrong way).
const INPUT_TURN = { right: -HALF, left: HALF, back: -Math.PI, stamp: 0, up: 0 };
const KEYS = {
  ArrowRight: 'right', KeyD: 'right', ArrowLeft: 'left', KeyA: 'left', ArrowDown: 'back', KeyS: 'back',
  ArrowUp: 'up', KeyW: 'up', Space: 'stamp',
};
const PAD = { 12: 'up', 13: 'back', 14: 'left', 15: 'right', 0: 'stamp' };

const ICON = {
  right: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M14 36V22a8 8 0 0 1 8-8h14" /><path d="M30 8l7 6-7 6" /></svg>',
  left: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M34 36V22a8 8 0 0 0-8-8H12" /><path d="M18 8l-7 6 7 6" /></svg>',
  back: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M16 38V20a8 8 0 0 1 16 0v14" /><path d="M26 29l6 7 6-7" /></svg>',
  up: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M24 40V10" /><path d="M16 18l8-8 8 8" /></svg>',
  stamp: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M17 8h10v18l10 5v7H13V26z" /><path d="M10 44h28" /></svg>',
  look: '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M4 24s7-11 20-11 20 11 20 11-7 11-20 11S4 24 4 24z" /><circle cx="30" cy="24" r="5" /></svg>',
};
const PAD_BUTTONS = [['left', 'kiri', '←'], ['back', 'belakang', '↓'], ['up', 'jalan', '↑'], ['right', 'kanan', '→'], ['stamp', 'sedia', 'Space']];

const CSS = `
body.drill-open #objective,body.drill-open #prompt,body.drill-open #compass,body.drill-open #toast,body.drill-open #touch-controls{visibility:hidden}
.drill{position:fixed;inset:0;z-index:36;pointer-events:none;font-family:Inter,system-ui,sans-serif;color:#fff8ea}
.drill-call{position:absolute;left:50%;top:calc(14px + var(--safe-t,0px));transform:translateX(-50%);display:flex;align-items:center;gap:18px;text-align:center;min-width:300px;padding:12px 24px 12px 18px;border-radius:16px;background:rgba(24,19,13,.72);border:1px solid rgba(255,248,234,.18);box-shadow:0 10px 30px rgba(0,0,0,.35)}
.drill-who{font-size:11px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:rgba(255,248,234,.6)}
.drill-caut{font:700 30px/1.15 Gelasio,Georgia,serif;color:rgba(255,248,234,.78);min-height:36px;transition:opacity .2s}
.drill-exec{font:800 38px/1.1 Gelasio,Georgia,serif;color:#f4cf7a;min-height:44px;letter-spacing:.02em;transform-origin:50% 60%}
.drill-exec.hit{animation:drill-pop .28s ease-out}
.drill-mean{font-size:13px;font-weight:600;color:rgba(255,248,234,.7);min-height:18px}
@keyframes drill-pop{0%{transform:scale(1.35)}100%{transform:scale(1)}}
.drill-cue{position:relative;flex:none;width:84px;height:84px}
.drill-words{min-width:200px}
.drill-ring{position:absolute;inset:0;border-radius:50%;border:3px solid #f4cf7a;opacity:0;will-change:transform}
.drill-target{position:absolute;inset:0;border-radius:50%;border:2px solid rgba(255,248,234,.45);opacity:0;transition:opacity .2s}
.drill-icon{position:absolute;inset:14px;display:flex;align-items:center;justify-content:center;opacity:0;transition:opacity .2s}
.drill-icon svg,.drill-btn svg{width:100%;height:100%;fill:none;stroke:#f4cf7a;stroke-width:4;stroke-linecap:round;stroke-linejoin:round}
.drill-say{position:absolute;left:50%;bottom:calc(128px + var(--safe-b,0px));transform:translateX(-50%);max-width:min(640px,92vw);text-align:center;padding:8px 16px;border-radius:12px;background:rgba(24,19,13,.72);font-size:17px;line-height:1.35;opacity:0;transition:opacity .25s}
.drill-say.on{opacity:1}
.drill-call,.drill-cue{transition:opacity .35s,transform .35s}
.drill.idle .drill-call{opacity:0;transform:translate(-50%,-10px)}
.drill-pad{transition:opacity .3s}
.drill.idle .drill-pad{opacity:.45}

.drill-say b{color:#f4cf7a;margin-right:6px}
.drill-pad{position:absolute;left:50%;bottom:calc(14px + var(--safe-b,0px));transform:translateX(-50%);display:flex;gap:10px;pointer-events:auto}
.drill-btn{width:92px;height:92px;border-radius:18px;border:1px solid rgba(255,248,234,.3);background:rgba(24,19,13,.72);color:#fff8ea;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:2px;font:700 14px Inter,system-ui,sans-serif;touch-action:manipulation;transition:transform .08s,background .15s}
.drill-btn span.i{width:40px;height:40px}
.drill-btn kbd{font:600 10px Inter,system-ui,sans-serif;opacity:.6;border:1px solid rgba(255,248,234,.3);border-radius:4px;padding:0 4px}
.drill-btn.down{transform:scale(.94);background:rgba(244,207,122,.25)}
.drill-btn.hint{box-shadow:0 0 0 3px rgba(120,200,255,.85)}
.drill-btn.hidden-btn{display:none}
.drill-assist{position:absolute;right:calc(16px + var(--safe-r,0px));bottom:calc(20px + var(--safe-b,0px));pointer-events:auto;border:1px solid rgba(255,248,234,.3);background:rgba(24,19,13,.6);color:#fff8ea;border-radius:999px;padding:8px 14px;font:600 13px Inter,system-ui,sans-serif}
.drill.parade .drill-assist{opacity:.75}
@media (max-width:640px){.drill-assist{bottom:calc(122px + var(--safe-b,0px))}.drill-btn{width:68px;height:78px}.drill-btn span.i{width:30px;height:30px}}
@media (max-height:480px){.drill-cue{width:60px;height:60px}.drill-btn{width:74px;height:74px}.drill-btn span.i{width:30px;height:30px}.drill-caut{font-size:24px}.drill-exec{font-size:30px}.drill-say{bottom:calc(100px + var(--safe-b,0px));font-size:15px}}
@media (prefers-reduced-motion:reduce){.drill-exec.hit{animation:none}}
`;

function ensureCSS() {
  if (document.getElementById('drill-css')) return;
  const st = document.createElement('style');
  st.id = 'drill-css';
  st.textContent = CSS;
  document.head.appendChild(st);
}

const wrap = (a) => Math.atan2(Math.sin(a), Math.cos(a));

/**
 * One drill session on the parade square.
 *   members: [{ key, ch }] in rank order; one of them is the player (Sparky).
 *   mode: 'day' | 'parade'.
 *   copier: key of the member who copies Sparky on day one (Ah Hock); early: { key, at } scripted jump-the-gun.
 *   say(who, text, secs): show a line in the drill's own caption (no dialogue box during drill).
 *   hooks.onEyesRight(api): the chapter's Boon reveal while the file marches on.
 */
export class Drill {
  constructor(game, { members, mode = 'day', copier = null, early = null, names = {}, lines = {}, hooks = {} }) {
    this.game = game;
    this.members = members;
    this.mode = mode;
    this.copier = copier;
    this.early = early;
    this.names = names;
    this.lines = lines;
    this.hooks = hooks;
    this.player = members.find((m) => m.ch.isPlayer).ch;
    this.relaxed = !!settings.relaxedTiming;
    // Forgiving: any press of the right button from just before the word until well after it counts.
    this.perfect = 0.3;                           // ± seconds for a "perfect" (feedback only)
    this.late = this.relaxed ? 3.0 : 1.8;         // give up after this
    this.earlyCut = this.relaxed ? -0.6 : -0.35;  // pressing before this = jumped the gun
    this.marching = false;
    this.speed = 0.95;                            // quick time on the square, m/s (brisk for the camera)
    this.stats = { good: 0, total: 0, misses: 0 };
    this.pending = null;
  }

  // ------------------------------------------------------------------ UI
  mount() {
    ensureCSS();
    const root = document.createElement('div');
    root.className = `drill ${this.mode}`;
    root.innerHTML = `
      <div class="drill-call" role="status" aria-live="assertive">
        <div class="drill-cue"><div class="drill-target"></div><div class="drill-ring"></div><div class="drill-icon"></div></div>
        <div class="drill-words">
          <div class="drill-who">${this.names.caller || 'Sergeant'}</div>
          <div class="drill-caut"></div><div class="drill-exec"></div><div class="drill-mean"></div>
        </div>
      </div>
      <div class="drill-say" aria-live="polite"></div>
      <div class="drill-pad">${PAD_BUTTONS.map(([id, word, key]) => `<button class="drill-btn" data-in="${id}" aria-label="${word}"><span class="i">${ICON[id]}</span><span class="w">${word}</span>${isTouch ? '' : `<kbd>${key}</kbd>`}</button>`).join('')}</div>
      <button class="drill-assist">${this.lines.assist || 'Do it for me'}${isTouch ? '' : ' <kbd>E</kbd>'}</button>`;
    document.body.appendChild(root);
    document.body.classList.add('drill-open');
    this.el = {
      root, caut: root.querySelector('.drill-caut'), exec: root.querySelector('.drill-exec'), mean: root.querySelector('.drill-mean'),
      ring: root.querySelector('.drill-ring'), target: root.querySelector('.drill-target'), icon: root.querySelector('.drill-icon'),
      say: root.querySelector('.drill-say'), btns: [...root.querySelectorAll('.drill-btn')], assist: root.querySelector('.drill-assist'),
    };
    this.el.btns.forEach((b) => b.addEventListener('pointerdown', (e) => { e.preventDefault(); this.press(b.dataset.in); }));
    this.el.assist.addEventListener('click', () => this.assist());
    this.onKey = (e) => {
      if (e.repeat) return;
      if (e.code === 'KeyE') { e.preventDefault(); this.assist(); return; }
      const k = KEYS[e.code];
      if (k) { e.preventDefault(); e.stopPropagation(); this.press(k); }
    };
    addEventListener('keydown', this.onKey, true);
    this.showButtons(['left', 'back', 'right', 'stamp']);
    this.stopTick = this.game.every((dt) => this.tick(dt));
    if (import.meta.env?.DEV) window.__drill = this; // debug: scripted play-throughs
  }

  unmount() {
    this.stopTick?.();
    removeEventListener('keydown', this.onKey, true);
    this.el?.root.remove();
    document.body.classList.remove('drill-open');
  }

  showButtons(ids) { this.el.btns.forEach((b) => b.classList.toggle('hidden-btn', !ids.includes(b.dataset.in))); }

  /** A line in the drill caption (the dialogue box would cover the pad). */
  say(who, text, secs = 2.6) {
    const el = this.el.say;
    el.innerHTML = `${who ? `<b>${this.names[who] || who}</b>` : ''}${text}`;
    el.classList.add('on');
    clearTimeout(this._sayT);
    this._sayT = setTimeout(() => el.classList.remove('on'), secs * 1000);
    return this.game.wait(Math.min(secs, 1.8));
  }

  // ------------------------------------------------------------------ input
  press(kind) {
    const b = this.el.btns.find((x) => x.dataset.in === kind);
    if (b) { b.classList.add('down'); setTimeout(() => b.classList.remove('down'), 120); }
    const p = this.pending;
    if (!p || p.resolved) return;
    if (p.cmd.input === 'look') { if (kind === 'right') this.lookNudge = (this.lookNudge || 0) + 0.9; return; }
    this.resolve(kind, this.now() - p.execAt);
  }

  /** "Do it for me": answers the current command perfectly. */
  assist() {
    const p = this.pending;
    if (!p || p.resolved) return;
    if (p.cmd.input === 'look') { this.lookNudge = 9; return; }
    const wait = Math.max(0, p.execAt - this.now());
    p.assisted = true;
    setTimeout(() => { if (this.pending === p && !p.resolved) this.resolve(p.cmd.input, 0.02); }, wait * 1000 + 30);
  }

  pollPad() {
    const pads = navigator.getGamepads?.() || [];
    for (const gp of pads) {
      if (!gp) continue;
      const prev = this._padPrev || [];
      for (const [i, kind] of Object.entries(PAD)) if (gp.buttons[i]?.pressed && !prev[i]) this.press(kind);
      if (gp.buttons[2]?.pressed && !prev[2]) this.assist();
      this._padPrev = gp.buttons.map((b) => b.pressed);
      return;
    }
  }

  now() { return this.game.time; }

  // ------------------------------------------------------------------ run
  /**
   * sequence: [{ cmd, icon?, gap?, atX? (wait until Sparky's x ≥ atX, while marching) }]
   * Resolves with the stats when the sequence is done.
   */
  async run(sequence) {
    this.mount();
    try {
      for (let i = 0; i < sequence.length; i++) {
        const step = sequence[i];
        if (step.atX !== undefined) await this.game.waitUntil(() => this.player.root.position.x >= step.atX);
        else await this.game.wait(step.gap ?? (this.mode === 'day' ? 0.9 : 1.2));
        if (step.before) await step.before(this);
        let retry = 0;
        for (;;) {
          const res = await this.command(step, i, retry);
          if (res.good || this.mode === 'parade' || res.cmd.input === 'auto' || res.cmd.input === 'look') break;
          retry++;
          await this.game.wait(1.35);
          this.restore(res.baseYaws);
          await this.say('Osman', this.lines.again || 'Again!', 1.4);
        }
        if (this.revealDone) {
          await this.revealDone;
          this.revealDone = null;
          this.game.mode = this.prevMode || 'cutscene';
          this.game.input.lookEnabled = true;
          if (this.player.model) this.player.model.visible = true;
        }
        if (step.after) await step.after(this);
      }
    } finally {
      if (this.player.model) this.player.model.visible = true;
      this.unmount();
    }
    return this.stats;
  }

  /** One command: cautionary word, closing ring, executive word, resolve. */
  command(step, index, retry) {
    const g = this.game;
    const cmd = CMD[step.cmd];
    const caution = this.mode === 'day' ? 1.45 : 1.25;
    const showIcon = step.icon !== false; // always show what to press
    const baseYaws = this.members.map((m) => m.ch.yaw);
    const t0 = this.now();
    const p = { step, cmd, index, retry, t0, execAt: t0 + caution, baseYaws, resolved: false, npcDone: false };
    this.pending = p;
    const E = this.el;
    clearTimeout(this._idleT);
    E.root.classList.remove('idle');
    E.assist.style.visibility = cmd.input === 'auto' ? 'hidden' : '';
    E.caut.textContent = cmd.caution;
    E.exec.textContent = '';
    E.mean.textContent = cmd.mean;
    E.icon.innerHTML = showIcon ? ICON[cmd.input] || '' : '';
    E.icon.style.opacity = showIcon ? 1 : 0;
    E.target.style.opacity = cmd.input === 'auto' ? 0 : 1;
    E.ring.style.opacity = cmd.input === 'auto' ? 0 : 1;
    this.el.btns.forEach((b) => b.classList.toggle('hint', showIcon && b.dataset.in === cmd.input));
    this.el.btns.forEach((b) => { const w = b.querySelector('.w'); w.textContent = step.labels?.[b.dataset.in] || PAD_BUTTONS.find((x) => x[0] === b.dataset.in)[1]; });
    if (step.buttons) this.showButtons(step.buttons);
    else if (step.cmd === 'jalan' || step.cmd === 'berhenti') this.showButtons(['left', 'back', 'up', 'right', 'stamp']);
    return new Promise((resolve) => { p.done = resolve; });
  }

  tick(dt) {
    this.pollPad();
    const p = this.pending;
    const t = this.now();
    if (p && !p.resolved) {
      const k = Math.min(1, (t - p.t0) / (p.execAt - p.t0));
      this.el.ring.style.transform = `scale(${(1.9 - 0.9 * k).toFixed(3)})`;
      // Scripted jump-the-gun (Leo, day one, first try only).
      if (this.early && this.early.at === p.index && p.retry === 0 && !p.earlyDone && t > p.t0 + (p.execAt - p.t0) * 0.5) {
        p.earlyDone = true;
        this.turnMember(this.early.key, p.cmd);
      }
      if (p.cmd.input !== 'look' && p.cmd.input !== 'auto' && t > p.execAt + this.late) this.resolve(null, t - p.execAt);
    }
    // The executive word always happens, even if Sparky already answered a moment early.
    if (p && t >= p.execAt && !p.execShown) {
      p.execShown = true;
      this.el.exec.textContent = p.cmd.exec;
      this.el.exec.classList.remove('hit'); void this.el.exec.offsetWidth; this.el.exec.classList.add('hit');
      if (p.cmd.input === 'auto') this.resolve('auto', 0);
      if (p.cmd.input === 'look') this.startLook(p);
    }
    // Everyone who knows the words moves on the executive word, whatever Sparky does.
    if (p && t >= p.execAt && !p.npcDone) {
      p.npcDone = true;
      for (const m of this.members) {
        if (m.ch.isPlayer || m.key === (this.mode === 'day' ? this.copier : null)) continue;
        if (this.early?.key === m.key && p.earlyDone) continue;
        this.applyCommand(m, p.cmd, Math.random() * 0.06);
      }
      this.stampSound(p.cmd, 0);
      p.onWord?.(); // Sparky's (and Ah Hock's) answer, if it came a moment before the word
      p.onWord = null;
    }
    if (this.marching) this.stepMarch(dt);
    if (this.looking) this.updateLook(dt);
  }

  resolve(kind, dt) {
    const p = this.pending;
    if (!p || p.resolved) return;
    p.resolved = true;
    const cmd = p.cmd;
    let res;
    if (cmd.input === 'auto' || cmd.input === 'look') res = 'good';
    else if (kind === null) res = 'late';
    else if (dt < this.earlyCut) res = 'early';
    else if (kind !== cmd.input) res = 'wrong';
    else res = 'good';
    // Day one never holds you up for long: after two tries, the sergeant lets it go.
    let forgiven = false;
    if (res !== 'good' && this.mode === 'day' && p.retry >= 2) { res = 'good'; forgiven = true; }
    const good = res === 'good';
    if (forgiven) setTimeout(() => this.say('Osman', this.lines.forgive || 'Close enough.', 1.4), 300);
    else if (good && kind && Math.abs(dt) <= this.perfect && this.mode === 'day') p.perfect = true;
    const pl = this.members.find((m) => m.ch.isPlayer);
    if (cmd.input !== 'auto' && cmd.input !== 'look') {
      this.stats.total++;
      if (good) this.stats.good++; else this.stats.misses++;
    }
    // Sparky does what the player pressed (a wrong press turns him the wrong way); day one, Ah Hock copies him a beat later.
    const answer = () => {
      if (good) this.applyCommand(pl, cmd, 0);
      else if (kind) this.turnBy(pl, INPUT_TURN[kind] ?? 0);
      if (this.mode === 'day' && this.copier) {
        const ah = this.members.find((m) => m.key === this.copier);
        setTimeout(() => { if (good) this.applyCommand(ah, cmd, 0); else if (kind) this.turnBy(ah, INPUT_TURN[kind] ?? 0); }, 160);
      }
    };
    // A right answer a moment before the word is carried out on the word, with everyone else.
    if (good && !p.npcDone && cmd.input !== 'auto' && cmd.input !== 'look') p.onWord = answer; else answer();
    const E = this.el;
    E.ring.style.opacity = 0;
    E.assist.style.visibility = 'hidden';
    clearTimeout(this._idleT);
    if (cmd.input === 'look') E.root.classList.add('idle'); // the reveal needs the whole screen
    this._idleT = setTimeout(() => { if (this.pending === p) E.root.classList.add('idle'); }, 1100);
    this.el.btns.forEach((b) => b.classList.remove('hint'));
    if (good && cmd.input !== 'auto') this.stampSound(cmd, 0, true);
    const L = this.lines;
    if (!good && this.mode === 'parade') {
      // No second tries at a parade. Ah Hock's elbow puts Sparky back in line.
      setTimeout(() => { this.applyCommand(pl, cmd, 0); this.bump(pl); }, 450);
      this.say('AhHock', L.nudge?.[res] || '(nudges you back into line)', 1.8);
    } else if (!good) {
      const txt = { early: L.early, wrong: L.wrong, late: L.late }[res];
      if (txt) this.say('Osman', txt, 1.4);
    } else if (good && cmd.input !== 'auto' && L.good && this.mode === 'day' && Math.random() < 0.5) this.say('Osman', L.good[this.stats.good % L.good.length], 1.3);
    // Finish only once the word has been called (so nobody is left behind when the next command starts).
    this.game.wait(Math.max(0.25, p.execAt - this.now() + 0.35)).then(() => p.done({ good, res, cmd, baseYaws: p.baseYaws, dt }));
  }

  /** Apply a command to one member after `delay` seconds (turn, start or stop marching). */
  applyCommand(m, cmd, delay = 0) {
    const run = () => {
      if (cmd.turn) this.turnBy(m, cmd.turn);
      if (cmd.march) this.startMarch(m);
      if (cmd.halt) this.haltMember(m);
      if (cmd.input === 'stamp' && !cmd.halt) this.stampPose(m);
      cmd.onApply?.(m); // e.g. sling arms: the rifle goes up on the shoulder
    };
    if (delay > 0) setTimeout(run, delay * 1000); else run();
  }

  turnMember(key, cmd) { const m = this.members.find((x) => x.key === key); if (m) this.applyCommand(m, cmd, 0); }

  turnBy(m, turn) {
    if (!turn) { this.stampPose(m); return; }
    const ch = m.ch;
    const base = ch.targetYaw ?? ch.yaw;
    ch.targetYaw = wrap(base + turn);
    this.stampPose(m);
  }

  /** A small stamp bob: the heel comes down. */
  stampPose(m) {
    const ch = m.ch;
    if (!ch.model) return;
    const y0 = ch.model.position.y;
    ch.model.position.y = y0 + 0.035;
    setTimeout(() => { ch.model.position.y = y0; }, 110);
  }

  bump(ch) {
    const r = ch.root.position;
    const x0 = r.x, z0 = r.z;
    r.x += 0.06; r.z += 0.04;
    setTimeout(() => { r.x = x0; r.z = z0; }, 140);
  }

  restore(yaws) {
    this.members.forEach((m, i) => { m.ch.targetYaw = yaws[i]; });
  }

  /** Boots on the square: one crisp crack when the section is together. */
  stampSound(cmd, spread = 0, player = false) {
    if (cmd.input === 'look' || cmd.input === 'auto') return;
    const n = player ? 1 : 3;
    for (let i = 0; i < n; i++) {
      setTimeout(() => this.game.audio.play(`footstep-${1 + Math.floor(Math.random() * 5)}`, { volume: 0.9, rate: 0.72 + Math.random() * 0.06, caption: '' }), (spread + i * 0.012) * 1000);
    }
  }

  // ------------------------------------------------------------------ marching
  startMarch(m) {
    m.marching = true;
    const ch = m.ch;
    ch.stop?.();
    // March clips are authored at ~0.78 m/s (120 paces a minute); speed them up to match the square's pace.
    if (ch.isPlayer) { ch.scripted = true; ch.play('Walk'); ch.setSpeed(0.62); } else { ch.play(ch.clips.March ? 'March' : 'Walk'); ch.setSpeed(this.speed / 0.78); }
    this.marching = true;
  }

  haltMember(m) {
    m.marching = false;
    m.ch.play(m.ch.clips.Attention ? 'Attention' : 'Idle');
    this.stampPose(m);
    this.marching = this.members.some((x) => x.marching);
  }

  stepMarch(dt) {
    for (const m of this.members) {
      if (!m.marching) continue;
      const ch = m.ch;
      const y = ch.targetYaw ?? ch.yaw;
      ch.root.position.x += Math.sin(y) * this.speed * dt;
      ch.root.position.z += Math.cos(y) * this.speed * dt;
    }
    this._stepT = (this._stepT || 0) + dt;
    if (this._stepT > 0.52) {
      this._stepT = 0;
      this.game.audio.play(`footstep-${1 + Math.floor(Math.random() * 5)}`, { volume: 0.55, rate: 0.75, caption: '' });
    }
  }

  // ------------------------------------------------------------------ eyes right
  startLook(p) {
    const g = this.game;
    const head = this.eyePos();
    const fwd = V(Math.sin(this.player.yaw), 0, Math.cos(this.player.yaw));
    g.rig.viewfinder(head, head.clone().addScaledVector(fwd, 5), false, 1.6);
    if (this.player.model) this.player.model.visible = false; // we look out of Sparky's eyes
    g.input.lookEnabled = true;
    // Viewfinder mode: the game passes mouse / drag look to the camera (and leaves Sparky's model hidden).
    this.prevMode = g.mode;
    g.mode = 'viewfinder';
    this.lookNudge = 0;
    this.looking = { p, t: 0, baseYaw: g.rig.vf.yaw, found: false };
    this.el.icon.innerHTML = this.mode === 'day' || p.step.icon ? ICON.look : '';
    this.el.icon.style.opacity = this.el.icon.innerHTML ? 1 : 0;
    this.showButtons(['right']);
    this.el.btns.forEach((b) => b.classList.toggle('hint', b.dataset.in === 'right'));
  }

  /** Sparky's eye for "eyes right": his head, leaned 0.4 m to his right so his neighbours stay out of shot. */
  eyePos() {
    const y = this.player.yaw;
    return this.player.headPosition().add(V(-Math.cos(y) * 0.4, 0.05, Math.sin(y) * 0.4));
  }

  updateLook(dt) {
    const L = this.looking;
    const g = this.game;
    const vf = g.rig.vf;
    L.t += dt;
    // Keep the eye at Sparky's head as the file marches on (leaning out of the file, clear of the next man).
    vf.pos.copy(this.eyePos());
    if (this.lookNudge > 0) { const k = Math.min(this.lookNudge, dt * 3.2); vf.yaw -= k; this.lookNudge -= k; }
    if (L.t > 6) vf.yaw -= dt * 1.4; // nobody's stuck: the head turns by itself after a while
    const turned = L.baseYaw - vf.yaw;
    if (!L.found && turned > 0.85) {
      L.found = true;
      this.looking = null;
      g.input.lookEnabled = false; // the reveal aims the eye now
      this.el.btns.forEach((b) => b.classList.remove('hint'));
      this.showButtons([]);
      this.resolve('look', 0);
      this.revealDone = Promise.resolve(this.hooks.onEyesRight?.(this)).then(() => { this.showButtons(['left', 'back', 'up', 'right', 'stamp']); });
    }
  }
}
