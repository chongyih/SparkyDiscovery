import { isTouch } from './settings.js';

const $ = (id) => document.getElementById(id);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// Glosses: "{Nanyang Siang Pau|Chinese newspaper}" shows a small translation above the word.
const GLOSS = /\{([^|}]+)\|([^}]*)\}/g;
const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c]);
export const plainText = (s) => (s || '').replace(GLOSS, '$1');
const glossHTML = (s) => esc(s).replace(/\{([^|}]+)\|([^}]*)\}/g, '<ruby>$1<rt>$2</rt></ruby>');

/** DOM overlay: dialogue, objectives, prompts, captions, toasts, fades, title cards, photo develop. */
export class UI {
  constructor() {
    this.el = {
      hud: $('hud'), objective: $('objective'), objectiveText: $('objective-text'), prompt: $('prompt'), promptText: $('prompt-text'),
      counter: $('counter'), caption: $('caption'), toast: $('toast'), compass: $('compass'),
      dialogue: $('dialogue'), dlgName: $('dlg-name'), dlgText: $('dlg-text'), choices: $('choices'),
      fade: $('fade'), card: $('card'), touch: $('touch'), action: $('btn-action'), actionLabel: $('action-label'),
      develop: $('develop'), flash: $('flash'),
    };
    this.dialogueActive = false;
    this._typing = null;
    this._advance = null;
    this.el.dialogue.addEventListener('click', () => this.advance());
    this.el.dialogue.addEventListener('touchstart', (e) => { e.preventDefault(); this.advance(); }, { passive: false });
    if (isTouch) this.el.touch.classList.remove('hidden');
    const kbd = this.el.prompt.querySelector('kbd');
    if (isTouch) kbd.remove();
  }

  showHUD(on) { this.el.hud.classList.toggle('hidden', !on); }

  objective(text) {
    const o = this.el.objective;
    if (!text) { o.classList.add('hidden'); this._objText = null; return; }
    if (text === this._objText && !o.classList.contains('hidden')) return; // unchanged: no re-animation
    this._objText = text;
    this.el.objectiveText.textContent = text;
    o.classList.remove('hidden');
    o.style.animation = 'none'; void o.offsetWidth; o.style.animation = '';
  }

  prompt(text) {
    if (text === this._promptText) return;
    this._promptText = text;
    if (!text) {
      this.el.prompt.classList.add('hidden');
      this.el.action.classList.remove('ready');
      this.el.actionLabel.textContent = '';
      return;
    }
    if (!isTouch) { this.el.promptText.textContent = text; this.el.prompt.classList.remove('hidden'); }
    this.el.action.classList.add('ready');
    this.el.actionLabel.textContent = text;
  }

  counter(text) { this.el.counter.textContent = text || ''; this.el.counter.classList.toggle('hidden', !text); }

  caption(text, secs = 3) {
    const c = this.el.caption;
    // Don't repeat the same caption back-to-back (e.g. a string of distant explosions).
    const now = performance.now();
    if (text === this._capText && now - this._capAt < 5000) return;
    this._capText = text; this._capAt = now;
    c.textContent = plainText(text);
    c.classList.remove('hidden');
    clearTimeout(this._capT);
    this._capT = setTimeout(() => c.classList.add('hidden'), secs * 1000);
  }

  toast(title, body, secs = 5) {
    const t = this.el.toast;
    t.querySelector('.toast-title').textContent = plainText(title);
    t.querySelector('.toast-body').textContent = plainText(body);
    t.classList.remove('hidden');
    t.style.animation = 'none'; void t.offsetWidth; t.style.animation = '';
    clearTimeout(this._toastT);
    this._toastT = setTimeout(() => t.classList.add('hidden'), secs * 1000);
  }

  /** Objective pointer. angle: radians clockwise from "straight ahead"; dist in metres. */
  compass(angle, dist) {
    const c = this.el.compass;
    if (angle === null || angle === undefined) { c.classList.add('hidden'); return; }
    c.classList.remove('hidden');
    c.firstElementChild.style.transform = `rotate(${angle}rad)`;
    const txt = dist < 10 ? `${dist.toFixed(0)} m` : `${Math.round(dist / 5) * 5} m`;
    if (txt !== this._distTxt) { this._distTxt = txt; $('compass-dist').textContent = txt; }
    c.classList.toggle('near', dist < 4);
  }

  /** Show a line; resolves when the player advances. style: '' | 'narrator' | 'radio'. */
  async say(name, text, { style = '', auto = 0 } = {}) {
    const d = this.el.dialogue;
    this.dialogueActive = true;
    document.body.classList.add('talking');
    d.className = `dialogue ${style}`;
    this.el.dlgName.textContent = name || '';
    this.el.dlgText.textContent = '';
    this.onLine?.(name, text);
    const glossed = GLOSS.test(text);
    GLOSS.lastIndex = 0;
    this.el.dlgText.classList.toggle('has-gloss', glossed);
    await this.typewrite(plainText(text));
    if (glossed) this.el.dlgText.innerHTML = glossHTML(text);
    await new Promise((resolve) => {
      this._advance = resolve;
      if (auto) setTimeout(resolve, auto * 1000);
    });
    this._advance = null;
  }

  typewrite(text) {
    // Cancel any previous line still typing (each line owns a token; stale ticks stop).
    clearTimeout(this._typeT);
    this._typingResolve?.();
    const token = (this._typeToken = (this._typeToken || 0) + 1);
    return new Promise((resolve) => {
      let i = 0;
      const el = this.el.dlgText;
      const speed = text.length > 90 ? 2 : 1;
      const done = () => { if (this._typeToken === token) { this._typing = null; this._typingResolve = null; } resolve(); };
      this._typing = () => { el.textContent = text; i = text.length; };
      this._typingResolve = done;
      const tick = () => {
        if (this._typeToken !== token) { resolve(); return; }
        if (i >= text.length) { done(); return; }
        i = Math.min(text.length, i + speed);
        el.textContent = text.slice(0, i);
        this._typeT = setTimeout(tick, 18);
      };
      tick();
    });
  }

  advance() {
    if (!this.dialogueActive) return false;
    if (this._typing) { clearTimeout(this._typeT); this._typing(); this._typingResolve?.(); return true; }
    if (this._advance) { this._advance(); return true; }
    return true;
  }

  endDialogue() {
    this.dialogueActive = false;
    document.body.classList.remove('talking');
    this.el.dialogue.classList.add('hidden');
  }

  async choice(options) {
    const c = this.el.choices;
    c.innerHTML = '';
    c.classList.remove('hidden');
    const idx = await new Promise((resolve) => {
      options.forEach((label, i) => {
        const b = document.createElement('button');
        b.className = 'btn';
        b.textContent = label;
        b.onclick = () => resolve(i);
        c.appendChild(b);
      });
      c.firstElementChild?.focus();
    });
    c.classList.add('hidden');
    return idx;
  }

  /** Choose `n` of the options (cards). Resolves with the chosen ids. Keys 1–9 / click / tap. */
  pick({ title, sub = '', options, n = 2 }) {
    const root = $('pick');
    $('pick-title').textContent = title;
    $('pick-sub').textContent = sub || `Choose ${n}.`;
    const grid = $('pick-grid');
    grid.innerHTML = '';
    const chosen = [];
    root.classList.remove('hidden');
    return new Promise((resolve) => {
      const cards = options.map((o, i) => {
        const b = document.createElement('button');
        b.className = 'pick-card';
        b.innerHTML = `<span class="ico">${o.icon || '•'}</span><span>${o.label}</span><span class="num"></span>`;
        const toggle = () => {
          const at = chosen.indexOf(o.id);
          if (at >= 0) chosen.splice(at, 1); else if (chosen.length < n) chosen.push(o.id);
          cards.forEach((c, j) => { const k = chosen.indexOf(options[j].id); c.classList.toggle('on', k >= 0); c.querySelector('.num').textContent = k >= 0 ? `✓ ${k + 1}` : ''; });
          if (chosen.length === n) { document.removeEventListener('keydown', onKey); setTimeout(() => { root.classList.add('hidden'); resolve(chosen.slice()); }, 450); }
        };
        b.onclick = toggle;
        b._toggle = toggle;
        grid.appendChild(b);
        return b;
      });
      const onKey = (e) => { const d = parseInt(e.key, 10); if (d >= 1 && d <= cards.length) cards[d - 1]._toggle(); };
      document.addEventListener('keydown', onKey);
      this._pickCards = cards;
      cards[0]?.focus();
    });
  }

  async fade(on, secs = 0.8, color = 'black') {
    const f = this.el.fade;
    f.style.transitionDuration = `${secs}s`;
    f.classList.remove('sepia', 'white');
    if (color !== 'black') f.classList.add(color);
    f.classList.toggle('on', on);
    await sleep(secs * 1000 + 30);
  }

  async card(kicker, title, sub = '', secs = 3.5) {
    const c = this.el.card;
    $('card-kicker').textContent = kicker || '';
    $('card-title').textContent = title || '';
    $('card-sub').textContent = sub || '';
    c.classList.remove('hidden');
    c.style.animation = 'none'; void c.offsetWidth; c.style.animation = '';
    c.style.opacity = '1';
    c.style.transition = '';
    await sleep(secs * 1000);
    c.style.transition = 'opacity 0.8s';
    c.style.opacity = '0';
    await sleep(800);
    c.classList.add('hidden');
  }

  /** Animate the camera iris: close=true shrinks to black, false opens back up. */
  iris(close, secs = 0.28) {
    const el = document.getElementById('iris');
    if (document.hidden) { el.classList.toggle('on', close); el.style.setProperty('--r', close ? '0vmax' : '150vmax'); return Promise.resolve(); }
    el.classList.add('on');
    const from = close ? 150 : 0, to = close ? 0 : 150;
    const t0 = performance.now();
    return new Promise((resolve) => {
      const step = (now) => {
        const k = Math.min(1, (now - t0) / (secs * 1000));
        const e = k * k * (3 - 2 * k);
        el.style.setProperty('--r', `${from + (to - from) * e}vmax`);
        if (k < 1) requestAnimationFrame(step);
        else { if (!close) el.classList.remove('on'); resolve(); }
      };
      requestAnimationFrame(step);
    });
  }

  flash() {
    const f = this.el.flash;
    f.classList.remove('on'); void f.offsetWidth; f.classList.add('on');
  }

  /** Photo develops next to its fact card; resolves when the player accepts. */
  develop(photo) {
    $('develop-img').src = photo.image;
    $('develop-caption').textContent = photo.caption || photo.title;
    $('develop-year').textContent = photo.year || '';
    $('develop-title').textContent = photo.title;
    $('develop-text').textContent = photo.text;
    this.el.develop.classList.remove('hidden');
    return new Promise((resolve) => {
      const btn = $('btn-develop-ok');
      const done = () => { btn.onclick = null; this.el.develop.classList.add('hidden'); this._developDone = null; resolve(); };
      btn.onclick = done;
      this._developDone = done;
      setTimeout(() => btn.focus(), 50);
    });
  }

  confirmDevelop() { if (this._developDone) { this._developDone(); return true; } return false; }
}
