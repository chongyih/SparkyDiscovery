import * as THREE from 'three';
import { Renderer } from './renderer.js';
import { Input } from './input.js';
import { UI } from './ui.js';
import { Audio } from './audio.js';
import { Album, capturePhoto } from './album.js';
import { CameraRig } from './camera.js';
import { settings, saveSettings, resetSettings, onSettings, isTouch, TIERS } from './settings.js';
import { radialTexture } from './assets.js';
import { Character } from './character.js';

const $ = (id) => document.getElementById(id);
const tmp = new THREE.Vector3();

/** Gold objective beacon: soft light column + bobbing chevron. */
class Beacon extends THREE.Group {
  constructor() {
    super();
    const col = new THREE.Mesh(
      new THREE.CylinderGeometry(0.35, 0.35, 3.2, 20, 1, true),
      new THREE.MeshBasicMaterial({ color: 0xffc85a, transparent: true, opacity: 0.16, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, fog: false }),
    );
    col.position.y = 1.6;
    const ring = new THREE.Mesh(
      new THREE.RingGeometry(0.34, 0.5, 32),
      new THREE.MeshBasicMaterial({ color: 0xffd77a, transparent: true, opacity: 0.8, depthWrite: false, blending: THREE.AdditiveBlending, fog: false }),
    );
    ring.rotation.x = -Math.PI / 2;
    ring.position.y = 0.04;
    const chev = new THREE.Mesh(new THREE.ConeGeometry(0.16, 0.3, 4), new THREE.MeshBasicMaterial({ color: 0xffd77a, fog: false }));
    chev.rotation.x = Math.PI;
    this.chev = chev;
    this.ring = ring;
    const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: radialTexture('glow', 'rgba(255,215,122,0.9)', 'rgba(255,215,122,0)'), depthWrite: false, blending: THREE.AdditiveBlending, fog: false }));
    glow.scale.set(0.9, 0.9, 1);
    this.glow = glow;
    this.add(col, ring, chev, glow);
    this.t = 0;
    this.renderOrder = 5;
    this.visible = false;
    this.height = 2.1;
  }

  update(dt) {
    this.t += dt;
    this.chev.position.y = this.height + Math.sin(this.t * 3) * 0.08;
    this.chev.rotation.y += dt * 2;
    this.glow.position.y = this.chev.position.y;
    const s = 1 + Math.sin(this.t * 3) * 0.08;
    this.ring.scale.set(s, s, s);
  }
}

export class Game {
  constructor(canvas) {
    this.canvas = canvas;
    this.renderer = new Renderer(canvas);
    this.input = new Input(canvas);
    this.ui = new UI();
    this.audio = new Audio(this.ui);
    this.album = new Album();
    // near/far kept tight for depth precision (a huge far/near ratio causes z-fighting flicker).
    this.camera = new THREE.PerspectiveCamera(55, innerWidth / innerHeight, 0.12, 1500);
    this.rig = new CameraRig(this.camera);
    this.rig.blockers = () => (this.player ? [...this.npcs, this.player] : this.npcs); // people who can block a framed shot
    this.time = 0;
    this.timers = [];
    this.waiters = [];
    this.interactables = [];
    this.updaters = new Set();
    this.paused = false;
    this.chapter = null;
    this.player = null;
    this.npcs = [];
    this.world = null;
    this.beacon = new Beacon();
    this.objectiveTarget = null;
    this.mode = 'menu'; // menu | play | cutscene | viewfinder
    this.fpsSamples = [];
    this.bindUI();
    this.last = performance.now();
    this.loop = this.loop.bind(this);
    requestAnimationFrame(this.loop);
    // ?test keeps the simulation running in a hidden tab (automated playtests).
    this.runHidden = new URLSearchParams(location.search).has('test');
    if (new URLSearchParams(location.search).has('stats')) {
      this.statsEl = document.createElement('div');
      this.statsEl.style.cssText = 'position:fixed;left:8px;bottom:8px;z-index:99;font:12px monospace;color:#fff;background:rgba(0,0,0,.6);padding:4px 8px;border-radius:4px;pointer-events:none';
      document.body.appendChild(this.statsEl);
      this.renderer.renderer.info.autoReset = false;
      const r = this.renderer.renderer;
      const orig = this.renderer.render.bind(this.renderer);
      this.renderer.render = (dt) => { r.info.reset(); orig(dt); };
    }
    if (this.runHidden) setInterval(() => { if (document.hidden) this.loop(performance.now(), true); }, 33);
  }

  // ---------------- timing helpers (pause-aware) ----------------
  wait(secs) { return new Promise((resolve) => this.timers.push({ at: this.time + secs, resolve })); }
  waitUntil(fn) { return new Promise((resolve) => this.waiters.push({ fn, resolve })); }
  every(fn) { this.updaters.add(fn); return () => this.updaters.delete(fn); }

  /** Tween any numeric props on an object in game time. */
  tween(obj, to, secs, ease = (t) => t * t * (3 - 2 * t)) {
    const from = {};
    for (const k of Object.keys(to)) from[k] = obj[k];
    const start = this.time;
    return new Promise((resolve) => {
      const off = this.every(() => {
        const k = Math.min(1, (this.time - start) / secs);
        const e = ease(k);
        for (const key of Object.keys(to)) obj[key] = from[key] + (to[key] - from[key]) * e;
        if (k >= 1) { off(); resolve(); }
      });
    });
  }

  // ---------------- scene/chapter ----------------
  setScene(scene) {
    this.scene = scene;
    scene.add(this.beacon);
    this.renderer.setScene(scene, this.camera);
  }

  async startChapter(ChapterClass, opts = {}) {
    if (this.chapter) await this.endChapter();
    this.chapter = new ChapterClass(this, opts);
    await this.chapter.load((p) => this.onLoadProgress?.(p));
    this.mode = 'cutscene';
    this.ui.showHUD(true);
    this.chapter.run().catch((e) => { if (e?.message !== 'aborted') console.error(e); });
  }

  async endChapter() {
    // Tear down anything a beat might have left mid-flight.
    this._vfCancel?.();
    this._snapOpen = false;
    document.querySelectorAll('.puzzle').forEach((el) => el.remove());
    ['viewfinder', 'develop', 'choices'].forEach((id) => $(id).classList.add('hidden'));
    document.body.classList.remove('aiming', 'talking');
    $('iris').classList.remove('on');
    this.input.moveEnabled = true;
    this.input.lookEnabled = true;
    this.audio.duck = 1;
    this.frozen = false;
    this.chapter?.dispose();
    this.chapter = null;
    this.timers = [];
    this.waiters = [];
    this.updaters.clear();
    this.interactables = [];
    this.audio.stopAll(0.3);
    this.ui.endDialogue();
    this.ui.objective(null);
    this.ui.prompt(null);
    this.ui.counter(null);
  }

  // ---------------- interactions ----------------
  addInteract(opts) {
    const it = { radius: 1.6, enabled: true, label: 'Interact', ...opts };
    this.interactables.push(it);
    return it;
  }

  removeInteract(it) { this.interactables = this.interactables.filter((x) => x !== it); }

  /** Set objective text and beacon target (Vector3 or Character or null). */
  objective(text, target = null, { height = 2.1 } = {}) {
    this.ui.objective(text);
    this.objectiveTarget = target;
    this.beacon.height = height;
    this.beacon.visible = !!target;
  }

  /** Dialogue: array of [speakerKey|null, text] or {who,text,style}. Speaker characters play Talk. */
  async talk(lines, { cast = {}, frame = null, names = {} } = {}) {
    const prevMode = this.mode;
    this.mode = 'cutscene';
    this.input.moveEnabled = false;
    this.ui.prompt(null);
    for (const line of lines) {
      const [who, text, style] = Array.isArray(line) ? line : [line.who, line.text, line.style];
      const ch = cast[who];
      if (frame) frame(who, ch);
      if (ch && ch.has('Talk')) ch.play('Talk');
      await this.ui.say(names[who] ?? who ?? '', text, { style: style || (who ? '' : 'narrator') });
      if (ch && ch.currentName === 'Talk') ch.play(ch.idleClip);
    }
    this.ui.endDialogue();
    this.input.moveEnabled = true;
    this.mode = prevMode === 'cutscene' ? 'cutscene' : 'play';
  }

  /** Enter viewfinder; resolves with a captured data URL, or null if cancelled. */
  /**
   * Viewfinder. hotspots: [{ id, pos, note, label }] — when one sits near the frame centre with a
   * clear line of sight, the frame turns gold and shows its note; `this.snapHotspot` is set to the
   * framed hotspot's id when the shutter fires (null otherwise). limit = max aim swing (radians).
   */
  snap({ eye, aim, label = '', allowCancel = true, onCovered = null, hotspots = null, limit = 0.9 }) {
    if (this._snapOpen) return Promise.resolve(null);
    this._snapOpen = true;
    return new Promise(async (resolve) => {
      const prev = this.mode;
      this.mode = 'viewfinder';
      this.input.moveEnabled = false;
      this.ui.prompt(null);
      // Iris-cut into the viewfinder (a hard cut hides the move, so the camera never flies
      // through Sparky, the Brownie prop or nearby walls).
      await this.ui.iris(true, 0.22);
      onCovered?.();
      this.rig.viewfinder(eye, aim, true, limit);
      // WASD / the left stick walk Sparky (toward where the lens points); the eye rides along at
      // the same offset from him, so the player can step in closer or round an obstacle.
      this._vfWalk = this.player ? eye.clone().sub(this.player.root.position) : null;
      this.input.moveEnabled = true;
      this.snapHotspot = null;
      if (this.player) this.player.root.visible = false;
      $('vf-hint').innerHTML = this.input.isTouch
        ? 'Drag to aim · Left thumb to walk · Tap the shutter to snap'
        : 'Mouse to aim · <kbd>WASD</kbd> to walk · <kbd>Space</kbd> or <kbd>Click</kbd> to snap';
      document.body.classList.add('aiming');
      const vf = $('viewfinder');
      $('vf-label').textContent = label;
      vf.classList.remove('hidden');
      $('btn-vf-cancel').classList.toggle('hidden', !allowCancel);
      this.ui.iris(false, 0.3);
      const offs = [];
      const frame = vf.querySelector('.vf-frame');
      const note = $('vf-note');
      if (hotspots?.length) {
        let found = null;
        offs.push(this.every(() => {
          let best = null, bestD = 0.22;
          for (const h of hotspots) {
            tmp.copy(h.pos).project(this.camera);
            if (tmp.z > 1) continue;
            const d = Math.hypot(tmp.x * this.camera.aspect, tmp.y + 0.08);
            if (d < bestD && this.rig.clear(this.camera.position, h.pos)) { best = h; bestD = d; }
          }
          if (best !== found) {
            found = best;
            frame.classList.toggle('found', !!best);
            $('vf-label').textContent = best ? (best.label || label) : label;
            note.textContent = best?.note || '';
            note.classList.toggle('hidden', !best?.note);
          }
          this.snapHotspot = found?.id ?? null;
        }));
        offs.push(() => { frame.classList.remove('found'); note.classList.add('hidden'); });
      }
      const finish = async (img) => {
        offs.forEach((f) => f());
        this._vfWalk = null;
        this.input.moveEnabled = false;
        vf.classList.add('hidden');
        document.body.classList.remove('aiming');
        if (img) await this.wait(0.35); // let the shutter flash read before cutting back
        await this.ui.iris(true, 0.18);
        if (this.player) this.player.root.visible = true;
        this.rig.follow();
        this.rig.placeFollow(true, this.world);
        this.ui.iris(false, 0.25);
        this.input.moveEnabled = true;
        this.mode = prev === 'viewfinder' ? 'play' : prev;
        this._snapOpen = false;
        resolve(img);
      };
      const shoot = async () => {
        if (this._shooting) return;
        this._shooting = true;
        await this.wait(0.05);
        this.renderer.render(0);
        const img = capturePhoto(this.canvas);
        this.audio.play('camera-shutter');
        this.ui.flash();
        this._shooting = false;
        finish(img);
      };
      const onShutter = (e) => { e?.preventDefault?.(); shoot(); };
      $('btn-shutter').addEventListener('click', onShutter);
      offs.push(() => $('btn-shutter').removeEventListener('click', onShutter));
      offs.push(this.input.on('snap', shoot));
      offs.push(this.input.on('click', shoot));
      offs.push(this.input.on('action', shoot));
      const cancel = () => { if (allowCancel) finish(null); };
      $('btn-vf-cancel').onclick = cancel;
      offs.push(this.input.on('back', cancel));
      this._vfCancel = cancel;
      offs.push(() => { this._vfCancel = null; });
    });
  }

  // ---------------- UI wiring ----------------
  bindUI() {
    this.input.on('action', () => {
      if (this.paused || this.album.isOpen) return;
      if (this.ui.confirmDevelop()) return;
      if (this.ui.dialogueActive) { this.ui.advance(); return; }
      if (this.mode === 'play' && this.activeInteract) { const it = this.activeInteract; this.activeInteract = null; this.ui.prompt(null); it.onUse(it); }
    });
    this.input.on('action-space', () => { if (this.ui.dialogueActive && !this.paused) this.ui.advance(); });
    this.input.on('click', () => { if (this.ui.dialogueActive && !this.paused) this.ui.advance(); });
    this.input.on('tap', () => { if (this.ui.dialogueActive && !this.paused) this.ui.advance(); });
    this.input.on('album', () => this.toggleAlbum());
    this.input.on('pause', () => {
      if (this.titleSettings) { this.showTitleSettings(false); return; }
      if (this.album.isOpen) { this.album.close(); return; }
      if (this.mode === 'viewfinder' && this._vfCancel) { this._vfCancel(); return; }
      if (this.mode !== 'menu') this.setPaused(!this.paused);
    });
    this.input.on('lock-lost', () => { if (this.mode === 'play' && !this.album.isOpen && !this.paused) this.setPaused(true); });
    this.input.on('recenter', () => { if (this.mode === 'play') this.rig.snapBehind(); });
    this.input.on('camera', () => { if (this.mode === 'play' && !this.paused && !this.album.isOpen && !this.ui.dialogueActive) this.chapter?.freeCamera?.(); });
    this.input.on('zoom', (s) => this.rig.zoom(s));
    $('btn-album').onclick = () => this.toggleAlbum();
    $('btn-cam-hud').onclick = () => this.input.emit('camera');
    $('btn-pause').onclick = () => this.setPaused(true);
    const closePanel = () => { if (this.titleSettings) this.showTitleSettings(false); else this.setPaused(false); };
    $('btn-resume').onclick = closePanel;
    $('btn-settings-close').onclick = closePanel;
    $('pause').addEventListener('pointerdown', (e) => { if (e.target === e.currentTarget) closePanel(); });
    $('btn-restart').onclick = () => { this.setPaused(false); this.onRestart?.(); };
    $('btn-quit').onclick = () => { this.setPaused(false); this.onQuit?.(); };
    this.album.onToggle = (open) => {
      this.frozen = open;
      if (open) this.input.releaseLock(); else if (this.mode === 'play') this.input.requestLock();
      this.audio.pauseAll(open);
    };

    this.bindSettings();
  }

  bindSettings() {
    const radios = [...document.querySelectorAll('input[name=quality]')];
    const vol = $('set-volume'), mus = $('set-music'), sub = $('set-subtitles'), mot = $('set-motion'), inv = $('set-invert'), rel = $('set-relaxed');
    const loadedVariant = TIERS[settings.quality]?.assetVariant;
    const notes = {
      low: 'No shadows and fewer particles — smoothest on phones.',
      medium: 'Soft shadows and film grading, lighter effects.',
      high: 'Sharp shadows, bloom and high-detail textures.',
    };
    const pct = (el, out) => { el.style.setProperty('--fill', `${el.value * 100}%`); $(out).textContent = `${Math.round(el.value * 100)}%`; };
    const sync = () => {
      radios.forEach((r) => { r.checked = r.value === settings.quality; });
      const reload = TIERS[settings.quality]?.assetVariant !== loadedVariant;
      $('quality-note').textContent = notes[settings.quality] + (reload ? ' Texture detail updates next time the game loads.' : '');
      vol.value = settings.volume; mus.value = settings.music;
      pct(vol, 'out-volume'); pct(mus, 'out-music');
      sub.checked = settings.subtitles; mot.checked = settings.reduceMotion; inv.checked = settings.invertY;
      if (rel) rel.checked = !!settings.relaxedTiming;
    };
    sync();
    onSettings(sync);
    radios.forEach((r) => { r.onchange = () => saveSettings({ quality: r.value }); });
    vol.oninput = () => saveSettings({ volume: +vol.value });
    mus.oninput = () => saveSettings({ music: +mus.value });
    sub.onchange = () => saveSettings({ subtitles: sub.checked });
    mot.onchange = () => saveSettings({ reduceMotion: mot.checked });
    inv.onchange = () => saveSettings({ invertY: inv.checked });
    if (rel) rel.onchange = () => saveSettings({ relaxedTiming: rel.checked });
    $('btn-settings-reset').onclick = () => resetSettings();

    const tabs = [...document.querySelectorAll('.sp-tabs [data-tab]')];
    this.showSettingsTab = (name) => tabs.forEach((t) => {
      const on = t.dataset.tab === name;
      t.classList.toggle('active', on);
      t.setAttribute('aria-selected', on);
      $(`sp-${t.dataset.tab}`).classList.toggle('hidden', !on);
    });
    tabs.forEach((t) => { t.onclick = () => this.showSettingsTab(t.dataset.tab); });

    const row = (keys, what) => `<div class="ctl"><span class="ctl-keys">${keys}</span><span>${what}</span></div>`;
    const k = (...ks) => ks.map((x) => `<kbd>${x}</kbd>`).join('');
    $('controls-help').innerHTML = isTouch
      ? [row('Left thumb', 'Move'), row('Drag right side', 'Look around'), row('Double-tap', 'Recentre camera'), row('Gold button', 'Talk / use'), row('Run', 'Toggle running'), row('Camera button', 'Look closer / take a photo'), row('Album button', 'Open Sparky’s album')].join('')
      : [row(k('W', 'A', 'S', 'D'), 'Move'), row(k('Shift'), 'Run'), row('Mouse', 'Look around'), row(k('E'), 'Talk / use'), row(`${k('C')} or right-click`, 'Raise camera'), row(k('Space'), 'Snap photo / continue'), row(k('J'), 'Photo album'), row(k('R'), 'Recentre camera'), row(k('Esc'), 'Pause / back')].join('')
        + '<p class="sp-note">Gamepads are supported too.</p>';
  }

  /** Shared panel in two modes: in-game pause menu, or plain settings over the title screen. */
  setPanelMode(fromTitle) {
    $('pause').classList.toggle('from-title', fromTitle);
    const meta = this.chapter?.T?.meta || this.chapter?.meta;
    $('pause-kicker').textContent = fromTitle ? 'Footsteps of a Nation' : (meta ? `Chapter ${meta.chapter} · ${meta.title}` : 'Game paused');
    $('pause-title').textContent = fromTitle ? 'Settings' : 'Paused';
    $('btn-resume').textContent = fromTitle ? 'Done' : 'Resume';
    this.showSettingsTab('settings');
  }

  showTitleSettings(open) {
    this.titleSettings = open;
    this.setPanelMode(true);
    $('pause').classList.toggle('hidden', !open);
    (open ? $('btn-settings-close') : $('btn-settings-title')).focus();
  }

  /** Keep the viewfinder eye at its offset from the walking player, pulled in short of walls. */
  followViewfinder(p) {
    const off = this._vfWalk;
    const base = tmp.copy(p.root.position); base.y += off.y;
    const flatLen = Math.hypot(off.x, off.z);
    let k = 1;
    if (flatLen > 0.05 && this.world) {
      const dirFlat = new THREE.Vector3(off.x / flatLen, 0, off.z / flatLen);
      k = Math.max(0, Math.min(flatLen, this.world.rayDistance(base, dirFlat, flatLen + 0.25) - 0.25)) / flatLen;
    }
    this.rig.vf.pos.set(base.x + off.x * k, base.y, base.z + off.z * k);
  }

  toggleAlbum() {
    if (this.mode === 'menu' || this.paused) return;
    if (this.album.isOpen) this.album.close(); else this.album.open();
  }

  setPaused(p) {
    if (this.mode === 'menu') p = false;
    this.paused = p;
    if (p) this.setPanelMode(false);
    $('pause').classList.toggle('hidden', !p);
    this.audio.pauseAll(p);
    if (p) this.input.releaseLock(); else if (this.mode === 'play') this.input.requestLock();
    if (p) $('btn-resume').focus();
  }

  // ---------------- main loop ----------------
  loop(now, manual = false) {
    if (!manual) requestAnimationFrame(this.loop);
    const rawDt = (now - this.last) / 1000;
    let dt = Math.min(0.05, rawDt);
    this.last = now;
    if (document.hidden && !manual) return;
    if (!manual && this.mode !== 'menu' && rawDt < 0.5) this.renderer.adapt(rawDt);
    this.input.update();
    const running = !this.paused && !this.frozen;
    if (running) {
      this.time += dt;
      this.update(dt);
    } else dt = 0;
    if (!this.skipRender) this.renderer.render(dt); // the title skips it while a still covers the canvas
    if (this.statsEl) this.updateStats(now);
  }

  updateStats(now) {
    this.fpsSamples.push(now);
    while (this.fpsSamples.length && now - this.fpsSamples[0] > 1000) this.fpsSamples.shift();
    if (now - (this._statsT || 0) < 500) return;
    this._statsT = now;
    const r = this.renderer.renderer.info.render;
    const t = this.renderer.tier;
    this.statsEl.textContent = `${this.fpsSamples.length} fps · ${r.calls} calls · ${(r.triangles / 1000).toFixed(0)}k tris · ${this.renderer.renderer.getPixelRatio().toFixed(2)}x · ${Object.entries(t).filter(([, v]) => v === true).map(([k]) => k).join(' ')}`;
  }

  update(dt) {
    for (let i = this.timers.length - 1; i >= 0; i--) {
      if (this.time >= this.timers[i].at) { const t = this.timers[i]; this.timers.splice(i, 1); t.resolve(); }
    }
    for (let i = this.waiters.length - 1; i >= 0; i--) {
      if (this.waiters[i].fn()) { const w = this.waiters[i]; this.waiters.splice(i, 1); w.resolve(); }
    }
    for (const fn of this.updaters) fn(dt);

    const p = this.player;
    if (p) {
      const walkingVf = this.mode === 'viewfinder' && this._vfWalk && this.rig.mode === 'viewfinder';
      p.controlled = (this.mode === 'play' || walkingVf) && !p.scripted;
      p.update(dt, this.world, this.mode === 'play' || walkingVf ? this.input : null, walkingVf ? this.rig.vf.yaw : this.rig.yaw);
      if (walkingVf) this.followViewfinder(p);
    }
    Character.showIndicators = this.mode === 'play' && !this.ui.dialogueActive;
    document.body.classList.toggle('in-play', this.mode === 'play');
    for (const n of this.npcs) n.update(dt, this.world);
    // Anyone within half a metre of the lens is hidden so they never fill the frame.
    const cam = this.camera.position;
    for (const n of this.npcs) {
      if (n.fadeHidden !== undefined && n.fadeHidden) n.model.visible = true;
      const near = this.mode !== 'viewfinder' && n.root.visible && tmp.copy(n.root.position).setY(n.root.position.y + n.height * 0.6).distanceTo(cam) < n.height * 0.3 + 0.3;
      n.model.visible = !near;
      n.fadeHidden = near;
    }
    if (p && this.mode !== 'viewfinder') p.model.visible = p.root.position.distanceTo(cam) > 0.55 || this.rig.mode === 'follow';
    this.chapter?.update?.(dt);
    this.rig.world = this.renderer.scene === this.chapter?.scene ? this.world : null;
    // Whenever the player has control, the camera must be the follow camera (WASD is camera-relative).
    if (this.mode === 'play' && this.rig.mode === 'shot' && !this.ui.dialogueActive) this.rig.follow();
    this.rig.update(dt, this.mode === 'play' || this.mode === 'viewfinder' ? this.input : null, this.world);
    if (this.mode !== 'play' && this.mode !== 'viewfinder') this.input.consumeLook();

    // Interaction prompt.
    this.activeInteract = null;
    if (p && this.mode === 'play' && !this.ui.dialogueActive) {
      let best = null, bestD = Infinity;
      for (const it of this.interactables) {
        if (!it.enabled) continue;
        const pos = it.pos.isVector3 ? it.pos : it.pos();
        const d = tmp.copy(pos).sub(p.root.position).setY(0).length();
        // Higher priority wins (objectives over ambient chat); then nearest.
        const score = d - (it.priority || 0) * 100;
        if (d < it.radius && score < bestD) { best = it; bestD = score; }
      }
      this.activeInteract = best;
      this.ui.prompt(best ? (typeof best.label === 'function' ? best.label() : best.label) : null);
    }

    // Beacon + compass.
    const tgt = this.objectiveTarget;
    this.beacon.visible = !!tgt && this.mode === 'play' && !this.ui.dialogueActive;
    if (tgt && this.beacon.visible) {
      const tp = tgt.isVector3 ? tgt : tgt.root.position;
      // A character with a speech bubble already marks itself; keep only the ground ring.
      const bubble = !tgt.isVector3 && !!tgt.indicatorKind;
      this.beacon.chev.visible = this.beacon.glow.visible = !bubble;
      this.beacon.position.copy(tp);
      if (tgt.height) this.beacon.height = tgt.height + 0.5;
      this.beacon.update(dt);
      // Always-on pointer while there's a target: direction relative to where the camera faces.
      const dist = p ? Math.hypot(tp.x - p.root.position.x, tp.z - p.root.position.z) : 0;
      if (this.mode === 'play' && dist > 1.8) {
        const f = this.camera.getWorldDirection(this._fwd ||= new THREE.Vector3());
        let ang = Math.atan2(tp.x - this.camera.position.x, tp.z - this.camera.position.z) - Math.atan2(f.x, f.z);
        ang = Math.atan2(Math.sin(ang), Math.cos(ang));
        this.ui.compass(-ang, dist);
      } else this.ui.compass(null);
    } else this.ui.compass(null);

    if (p) this.audio.update(p.root.position);
  }
}
