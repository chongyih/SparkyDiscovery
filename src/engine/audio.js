import { Howl, Howler } from 'howler';
import { settings, onSettings } from './settings.js';
import { assetURL, loadJSON } from './assets.js';

/**
 * Howler-based sound manager.
 *  - `define({ name: { file, volume, loop, trim:[startSec,endSec], music } })`
 *  - `play(name, { volume, rate, caption })` → handle with stop()/fade()
 *  - emitters: looping sounds whose volume follows distance to the listener.
 */
export class Audio {
  constructor(ui) {
    this.ui = ui;
    this.defs = {};
    this.howls = {};
    this.emitters = [];
    this.captions = {};
    this.musicHandle = null;
    this.duck = 1;
    Howler.volume(settings.volume);
    onSettings((s) => {
      Howler.volume(s.volume);
      if (this.musicHandle) this.musicHandle.setVolume(this.musicHandle.baseVolume);
    });
  }

  setCaptions(map) { Object.assign(this.captions, map || {}); }

  /** Loop metadata (wrap-padded loops: play only loopStart..loopEnd, see audio/README.md). */
  async loadMeta() {
    if (!this.meta) this.meta = (await loadJSON('audio/loops.json')) || {};
    return this.meta;
  }

  async define(defs) {
    await this.loadMeta();
    const loads = [];
    for (const [name, d] of Object.entries(defs)) {
      const info = this.meta[name];
      const def = { ...d };
      if (info?.loop && info.loopStart !== undefined && !def.trim) { def.trim = [info.loopStart, info.loopEnd]; def.loop = true; }
      if (this.howls[name] !== undefined) continue;
      this.defs[name] = def;
      const opts = {
        src: [assetURL(`audio/${def.file || name + '.mp3'}`)],
        preload: true,
        volume: def.volume ?? 1,
        loop: !!def.loop,
      };
      if (def.trim) {
        const [a, b] = def.trim;
        opts.sprite = { main: [a * 1000, (b - a) * 1000, !!def.loop] };
      }
      loads.push(new Promise((resolve) => {
        opts.onload = () => resolve(true);
        opts.onloaderror = () => { console.warn('[audio] missing', name); this.howls[name] = null; resolve(false); };
        this.howls[name] = new Howl(opts);
      }));
    }
    return Promise.all(loads);
  }

  unlock() { try { if (Howler.ctx?.state === 'suspended') Howler.ctx.resume(); } catch { /* ignore */ } }

  play(name, { volume = 1, rate = 1, caption, loop, fadeIn = 0 } = {}) {
    const howl = this.howls[name];
    const def = this.defs[name] || {};
    const cap = caption ?? this.captions[name];
    if (cap && settings.subtitles) this.ui?.caption(cap);
    if (!howl) return nullHandle;
    const id = def.trim ? howl.play('main') : howl.play();
    const base = (def.volume ?? 1) * volume * (def.music ? settings.music : 1);
    howl.rate(rate, id);
    if (loop !== undefined) howl.loop(loop, id);
    if (fadeIn > 0) { howl.volume(0, id); howl.fade(0, base, fadeIn * 1000, id); } else howl.volume(base, id);
    const handle = {
      baseVolume: volume,
      id,
      setVolume: (v) => { handle.baseVolume = v; howl.volume((def.volume ?? 1) * v * (def.music ? settings.music : 1), id); },
      setRate: (r) => howl.rate(r, id),
      fade: (to, secs = 1) => { const from = howl.volume(id); howl.fade(from, (def.volume ?? 1) * to * (def.music ? settings.music : 1), secs * 1000, id); handle.baseVolume = to; },
      stop: (secs = 0) => {
        if (secs > 0) { howl.fade(howl.volume(id), 0, secs * 1000, id); setTimeout(() => howl.stop(id), secs * 1000 + 30); } else howl.stop(id);
      },
      playing: () => howl.playing(id),
    };
    return handle;
  }

  music(name, { fade = 2, volume = 1 } = {}) {
    if (this.musicHandle) this.musicHandle.stop(fade);
    this.musicHandle = name ? this.play(name, { volume, loop: true, fadeIn: fade }) : null;
    return this.musicHandle;
  }

  /** A looping sound whose volume follows distance from the listener. */
  emitter(name, position, { radius = 12, volume = 1, minVolume = 0 } = {}) {
    const h = this.play(name, { volume: 0, loop: true });
    const e = { name, handle: h, position, radius, volume, minVolume, enabled: true, current: 0 };
    this.emitters.push(e);
    return e;
  }

  removeEmitter(e, fade = 0.5) { e.handle.stop(fade); this.emitters = this.emitters.filter((x) => x !== e); }

  stopAll(fade = 0.4) {
    for (const e of this.emitters) e.handle.stop(fade);
    this.emitters = [];
    if (this.musicHandle) { this.musicHandle.stop(fade); this.musicHandle = null; }
    for (const h of Object.values(this.howls)) {
      if (!h) continue;
      const ids = h._getSoundIds().filter((id) => h.playing(id));
      ids.forEach((id) => h.fade(h.volume(id), 0, fade * 1000, id));
      setTimeout(() => ids.forEach((id) => h.stop(id)), fade * 1000 + 50);
    }
  }

  pauseAll(paused) {
    for (const h of Object.values(this.howls)) {
      if (!h) continue;
      if (paused) { h._pausedIds = h._getSoundIds().filter((id) => h.playing(id)); h._pausedIds.forEach((id) => h.pause(id)); } else { (h._pausedIds || []).forEach((id) => h.play(id)); h._pausedIds = []; }
    }
  }

  update(listenerPos) {
    for (const e of this.emitters) {
      const d = listenerPos.distanceTo(e.position);
      const t = Math.max(0, 1 - d / e.radius);
      const target = e.enabled ? Math.max(e.minVolume, t * t) * e.volume * this.duck : 0;
      e.current += (target - e.current) * 0.08;
      e.handle.setVolume(e.current);
    }
  }
}

const nullHandle = { setVolume() {}, setRate() {}, fade() {}, stop() {}, playing: () => false, baseVolume: 0 };
