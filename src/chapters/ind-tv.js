import * as THREE from 'three';
import { assetURL, loadJSON } from '../engine/assets.js';
import { settings, onSettings } from '../engine/settings.js';

// Boon's television: the real 9 August 1965 press conference (118 s excerpt) playing on the 3D set.
// Captions: public/assets/video/lky-1965-en.json (Wikimedia Commons TimedText, CC BY-SA 4.0).
// The picture lives only on the TV screen in the kopitiam; subtitles and the credit are HTML.

const CSS = `
.tv-sub{position:fixed;left:50%;bottom:calc(9vh + var(--safe-b));transform:translateX(-50%);max-width:min(86vw,900px);padding:10px 18px;border-radius:10px;background:rgba(10,8,6,.78);color:#fff8ea;font:600 clamp(16px,2.4vw,24px)/1.35 Inter,system-ui,sans-serif;text-align:center;z-index:30;pointer-events:none;transition:opacity .25s}
.tv-sub.off{opacity:0}
.tv-credit{position:fixed;left:calc(14px + var(--safe-l));bottom:calc(10px + var(--safe-b));max-width:min(60vw,560px);color:rgba(255,248,234,.72);font:500 12px/1.3 Inter,system-ui,sans-serif;z-index:30;pointer-events:none;text-shadow:0 1px 2px #000}
.tv-label{position:fixed;left:50%;top:calc(14px + var(--safe-t));transform:translateX(-50%);color:rgba(255,248,234,.85);font:600 13px/1.3 Inter,system-ui,sans-serif;letter-spacing:.04em;z-index:30;pointer-events:none;text-shadow:0 1px 2px #000;text-align:center}
.tv-skip{position:fixed;right:calc(16px + var(--safe-r));bottom:calc(14px + var(--safe-b));z-index:31;padding:9px 16px;border-radius:999px;border:1px solid rgba(255,248,234,.35);background:rgba(20,16,11,.72);color:#fff8ea;font:600 13px Inter,system-ui,sans-serif;overflow:hidden}
.tv-skip i{position:absolute;left:0;top:0;bottom:0;width:0;background:rgba(232,182,76,.45);pointer-events:none}
.tv-skip span{position:relative}
`;

export class TV {
  constructor(game, screenMesh) {
    this.game = game;
    this.screen = screenMesh;
    const v = document.createElement('video');
    v.src = assetURL('video/lky-1965.mp4');
    v.preload = 'auto';
    v.playsInline = true;
    v.setAttribute('playsinline', '');
    v.crossOrigin = 'anonymous';
    v.volume = settings.volume;
    this.video = v;
    this.offSettings = onSettings((s) => { v.volume = s.volume; });
    this.texture = new THREE.VideoTexture(v);
    this.texture.colorSpace = THREE.SRGBColorSpace;
    this.texture.flipY = false; // glTF UVs on the screen quad
    this.off = new THREE.MeshBasicMaterial({ color: 0x0c0d0d });
    this.on = new THREE.MeshBasicMaterial({ map: this.texture, toneMapped: false });
    if (screenMesh) screenMesh.material = this.off;
    this.cues = [];
    loadJSON('video/lky-1965-en.json').then((c) => { this.cues = c || []; });
    if (!document.getElementById('tv-css')) {
      const st = document.createElement('style');
      st.id = 'tv-css';
      st.textContent = CSS;
      document.head.appendChild(st);
    }
    // iOS / Safari: media with sound must first be started from a user gesture. Prime the video on
    // the first tap / key press of the chapter so the real playback later is allowed.
    this.unlock = () => {
      if (this.unlocked) return;
      this.unlocked = true;
      const was = v.muted;
      v.muted = true;
      v.play().then(() => { v.pause(); v.currentTime = 0; v.muted = was; }).catch(() => { v.muted = was; this.unlocked = false; });
    };
    addEventListener('pointerdown', this.unlock, { once: false, passive: true });
    addEventListener('keydown', this.unlock, { once: false });
  }

  /** Static on the set (before the broadcast starts). */
  standby(on) {
    if (!this.screen) return;
    if (!on) { this.screen.material = this.off; return; }
    if (!this.staticMat) {
      const c = document.createElement('canvas');
      c.width = 128; c.height = 96;
      this.staticCtx = c.getContext('2d');
      this.staticTex = new THREE.CanvasTexture(c);
      this.staticTex.flipY = false;
      this.staticMat = new THREE.MeshBasicMaterial({ map: this.staticTex, toneMapped: false });
    }
    this.screen.material = this.staticMat;
  }

  tickStatic() {
    if (this.screen?.material !== this.staticMat) return;
    const g = this.staticCtx;
    const img = g.createImageData(128, 96);
    for (let i = 0; i < img.data.length; i += 4) { const n = 90 + Math.random() * 120; img.data[i] = img.data[i + 1] = img.data[i + 2] = n; img.data[i + 3] = 255; }
    g.putImageData(img, 0, 0);
    this.staticTex.needsUpdate = true;
  }

  /**
   * Play the whole excerpt. onTime(t) is called every frame with the playback time (for reaction
   * cuts). Resolves when the clip ends or the player holds Skip. Pausing the game pauses the video.
   */
  play({ label, credit, skipLabel = 'Hold to skip', onTime } = {}) {
    const g = this.game;
    const v = this.video;
    if (this.screen) this.screen.material = this.on;
    const sub = el('div', 'tv-sub off');
    const cr = el('div', 'tv-credit', credit || '');
    const lb = el('div', 'tv-label', label || '');
    const skip = el('button', 'tv-skip', `<i></i><span>${skipLabel}</span>`);
    document.body.append(sub, cr, lb, skip);
    v.currentTime = 0;
    v.muted = false;
    v.volume = settings.volume;
    const tryPlay = () => v.play().catch(() => { /* blocked: fall back to muted playback + captions */ v.muted = true; v.play().catch(() => {}); });
    tryPlay();
    let hold = 0, holding = false;
    const down = (e) => { e.preventDefault(); holding = true; };
    const up = () => { holding = false; };
    skip.addEventListener('pointerdown', down);
    addEventListener('pointerup', up);
    const kd = (e) => { if (e.code === 'KeyK' || e.code === 'Enter') holding = true; };
    const ku = (e) => { if (e.code === 'KeyK' || e.code === 'Enter') holding = false; };
    addEventListener('keydown', kd); addEventListener('keyup', ku);
    return new Promise((resolve) => {
      let done = false;
      const finish = () => {
        if (done) return;
        done = true;
        offTick();
        v.pause();
        sub.remove(); cr.remove(); lb.remove(); skip.remove();
        removeEventListener('pointerup', up); removeEventListener('keydown', kd); removeEventListener('keyup', ku);
        resolve();
      };
      v.onended = finish;
      let wasPaused = false;
      const offTick = g.every((dt) => {
        const frozen = g.paused || g.frozen;
        if (frozen && !v.paused) { v.pause(); wasPaused = true; }
        if (!frozen && wasPaused) { wasPaused = false; tryPlay(); }
        const t = v.currentTime;
        const cue = this.cues.find((c) => t >= c.start && t <= c.end);
        const txt = cue && settings.subtitles !== false ? cue.text : '';
        if (sub.textContent !== txt) sub.textContent = txt;
        sub.classList.toggle('off', !txt);
        onTime?.(t);
        hold = holding ? hold + dt : Math.max(0, hold - dt * 2);
        skip.firstElementChild.style.width = `${Math.min(100, hold / 0.8 * 100)}%`;
        if (hold >= 0.8) finish();
        if (v.duration && t >= v.duration - 0.05) finish();
      });
      // Safety net: never wait longer than the clip plus a margin (e.g. if the video fails to load).
      v.onerror = () => { g.ui.caption('The archive clip could not be played.', 4); setTimeout(finish, 1500); };
    });
  }

  dispose() {
    this.video.pause();
    this.video.removeAttribute('src');
    this.video.load();
    this.texture.dispose();
    this.offSettings?.();
    removeEventListener('pointerdown', this.unlock);
    removeEventListener('keydown', this.unlock);
    document.querySelectorAll('.tv-sub,.tv-credit,.tv-label,.tv-skip').forEach((e) => e.remove());
  }
}

function el(tag, cls, html = '') {
  const e = document.createElement(tag);
  e.className = cls;
  e.innerHTML = html;
  return e;
}
