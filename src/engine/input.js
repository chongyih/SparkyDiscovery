import nipplejs from 'nipplejs';
import { isTouch, settings } from './settings.js';

// Unified input: keyboard + mouse (pointer lock), touch (nipplejs stick + drag-look), gamepad.
// Continuous state is polled (move, look, run); discrete actions are emitted as events.
export class Input {
  constructor(canvas) {
    this.canvas = canvas;
    this.keys = new Set();
    this.move = { x: 0, y: 0 };
    this.look = { x: 0, y: 0 };
    this.run = false;
    this.touchRun = false;
    this.stick = { x: 0, y: 0 };
    this.moveEnabled = true;
    this.lookEnabled = true;
    this.listeners = {};
    this.isTouch = isTouch;
    this.pointerLocked = false;
    this.lastLookTime = -1e9;
    this.bindKeyboard();
    this.bindMouse();
    if (isTouch) this.bindTouch();
  }

  on(evt, fn) { (this.listeners[evt] ||= new Set()).add(fn); return () => this.listeners[evt].delete(fn); }
  emit(evt, data) { this.listeners[evt]?.forEach((fn) => fn(data)); }

  bindKeyboard() {
    addEventListener('keydown', (e) => {
      const k = e.code;
      // Let form controls keep their keys (arrows, space) — but Esc still backs out of menus.
      if ((e.target instanceof HTMLInputElement || e.target instanceof HTMLSelectElement) && k !== 'Escape') return;
      if (!e.repeat) {
        if (k === 'KeyE' || k === 'Enter') this.emit('action');
        if (k === 'Space') { this.emit('snap'); this.emit('action-space'); }
        if (k === 'KeyJ' || k === 'Tab') { e.preventDefault(); this.emit('album'); }
        if (k === 'Escape' || k === 'KeyP') this.emit('pause');
        if (k === 'KeyR') this.emit('recenter');
        if (k === 'KeyC' || k === 'KeyF') this.emit('camera');
      }
      if (['Space', 'ArrowUp', 'ArrowDown', 'ArrowLeft', 'ArrowRight'].includes(k)) e.preventDefault();
      this.keys.add(k);
    });
    addEventListener('keyup', (e) => this.keys.delete(e.code));
    addEventListener('blur', () => this.keys.clear());
  }

  bindMouse() {
    const c = this.canvas;
    let dragging = false;
    c.addEventListener('contextmenu', (e) => e.preventDefault());
    c.addEventListener('mousedown', (e) => {
      if (isTouch) return;
      if (e.button === 2) { this.emit('camera'); return; }
      dragging = true;
      if (this.lockWanted && !this.pointerLocked) { c.requestPointerLock?.()?.catch?.(() => {}); return; }
      this.emit('click');
    });
    addEventListener('mouseup', () => { dragging = false; });
    addEventListener('mousemove', (e) => {
      if (isTouch || !this.lookEnabled) return;
      if (this.pointerLocked || dragging) {
        this.look.x += e.movementX;
        this.look.y += e.movementY * (settings.invertY ? -1 : 1);
        this.lastLookTime = performance.now();
      }
    });
    c.addEventListener('wheel', (e) => this.emit('zoom', Math.sign(e.deltaY)), { passive: true });
    document.addEventListener('pointerlockchange', () => {
      const was = this.pointerLocked;
      this.pointerLocked = document.pointerLockElement === c;
      if (was && !this.pointerLocked) this.emit('lock-lost');
    });
  }

  requestLock() {
    this.lockWanted = true;
    if (!isTouch && !this.pointerLocked) this.canvas.requestPointerLock?.()?.catch?.(() => {});
  }

  releaseLock() {
    this.lockWanted = false;
    if (document.pointerLockElement) document.exitPointerLock();
  }

  bindTouch() {
    const zone = document.getElementById('stick-zone');
    this.nipple = nipplejs.create({ zone, mode: 'dynamic', color: 'rgba(255,248,234,0.85)', size: 120, fadeTime: 150, restOpacity: 0.6 });
    this.nipple.on('move', (evt, data) => {
      const d = data || evt?.data;
      if (!d?.vector) return;
      const f = Math.min(1, (d.distance || 0) / 60);
      this.stick.x = d.vector.x * f;
      this.stick.y = d.vector.y * f;
    });
    this.nipple.on('end', () => { this.stick.x = 0; this.stick.y = 0; });

    // Drag anywhere else on the canvas to look; double-tap to recentre.
    const touches = new Map();
    let lastTap = 0;
    this.canvas.addEventListener('touchstart', (e) => {
      for (const t of e.changedTouches) touches.set(t.identifier, { x: t.clientX, y: t.clientY, sx: t.clientX, sy: t.clientY, t: performance.now() });
    }, { passive: true });
    this.canvas.addEventListener('touchmove', (e) => {
      if (!this.lookEnabled) return;
      for (const t of e.changedTouches) {
        const p = touches.get(t.identifier);
        if (!p) continue;
        this.look.x += (t.clientX - p.x) * 1.6;
        this.look.y += (t.clientY - p.y) * 1.6 * (settings.invertY ? -1 : 1);
        p.x = t.clientX; p.y = t.clientY;
        this.lastLookTime = performance.now();
      }
    }, { passive: true });
    this.canvas.addEventListener('touchend', (e) => {
      for (const t of e.changedTouches) {
        const p = touches.get(t.identifier);
        touches.delete(t.identifier);
        if (p && Math.hypot(t.clientX - p.sx, t.clientY - p.sy) < 12 && performance.now() - p.t < 250) {
          const now = performance.now();
          this.emit('tap', { x: t.clientX, y: t.clientY });
          if (now - lastTap < 320) this.emit('recenter');
          lastTap = now;
        }
      }
    }, { passive: true });

    const runBtn = document.getElementById('btn-run');
    runBtn.addEventListener('touchstart', (e) => { e.preventDefault(); this.touchRun = !this.touchRun; runBtn.classList.toggle('on', this.touchRun); });
    const act = document.getElementById('btn-action');
    act.addEventListener('touchstart', (e) => { e.preventDefault(); this.emit('action'); });
  }

  pollGamepad() {
    const pads = navigator.getGamepads?.() || [];
    for (const gp of pads) {
      if (!gp) continue;
      const dz = (v) => (Math.abs(v) < 0.18 ? 0 : v);
      const gx = dz(gp.axes[0] || 0), gy = dz(gp.axes[1] || 0);
      const lx = dz(gp.axes[2] || 0), ly = dz(gp.axes[3] || 0);
      if (lx || ly) { this.look.x += lx * 14; this.look.y += ly * 10; this.lastLookTime = performance.now(); }
      const btn = (i) => gp.buttons[i]?.pressed;
      const prev = this._padPrev || [];
      const edge = (i) => btn(i) && !prev[i];
      if (edge(0)) { this.emit('action'); this.emit('snap'); }
      if (edge(3)) this.emit('album');
      if (edge(9)) this.emit('pause');
      if (edge(1)) this.emit('back');
      this._padPrev = gp.buttons.map((b) => b.pressed);
      return { x: gx, y: -gy, run: btn(10) || btn(7) };
    }
    return null;
  }

  update() {
    const k = this.keys;
    let x = (k.has('KeyD') || k.has('ArrowRight') ? 1 : 0) - (k.has('KeyA') || k.has('ArrowLeft') ? 1 : 0);
    let y = (k.has('KeyW') || k.has('ArrowUp') ? 1 : 0) - (k.has('KeyS') || k.has('ArrowDown') ? 1 : 0);
    let run = k.has('ShiftLeft') || k.has('ShiftRight');
    const len = Math.hypot(x, y);
    if (len > 1) { x /= len; y /= len; }
    if (this.stick.x || this.stick.y) { x = this.stick.x; y = this.stick.y; run = run || this.touchRun || Math.hypot(x, y) > 0.95; }
    const pad = this.pollGamepad();
    if (pad && (pad.x || pad.y)) { x = pad.x; y = pad.y; run = run || pad.run; }
    // In the viewfinder, WASD/arrows (and the left stick) aim instead of walking.
    if (this.aimKeys) { this.look.x += x * 9; this.look.y -= y * 7; if (x || y) this.lastLookTime = performance.now(); }
    if (!this.moveEnabled) { x = 0; y = 0; run = false; }
    this.move.x = x; this.move.y = y; this.run = run;
  }

  consumeLook() {
    const l = { x: this.look.x, y: this.look.y };
    this.look.x = 0; this.look.y = 0;
    return this.lookEnabled ? l : { x: 0, y: 0 };
  }
}
