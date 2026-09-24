import * as THREE from 'three';
import { Game } from './engine/game.js';
import { WW2Chapter } from './chapters/ww2.js';
import T from './chapters/ww2-text.js';

const $ = (id) => document.getElementById(id);
const game = new Game($('game'));
window.__game = game; // handy for debugging in the console

let chapter = null;
let titleSpin = null;

// Loading screen: the print in the tray develops with progress (CSS reads --p). The shown value
// eases toward the real one so the image comes up smoothly rather than in jumps.
const LOAD_STEPS = [[0, 'Winding on the film'], [0.25, 'Mixing the developer'], [0.5, 'Rocking the tray'], [0.8, 'Fixing the print'], [0.98, 'Hanging it up to dry']];
const load = { target: 0, shown: 0, raf: 0, step: '' };
function drawLoading() {
  load.shown += (load.target - load.shown) * 0.12;
  if (load.target - load.shown < 0.002) load.shown = load.target;
  const el = $('loading');
  el.style.setProperty('--p', load.shown.toFixed(4));
  const pct = Math.round(load.shown * 100);
  $('loading-pct').textContent = `${pct}%`;
  $('loading-progress').setAttribute('aria-valuenow', pct);
  const step = LOAD_STEPS.filter(([at]) => load.shown >= at).pop()[1];
  if (step !== load.step) {
    load.step = step;
    const s = $('loading-step');
    s.textContent = step;
    s.style.animation = 'none'; void s.offsetWidth; s.style.animation = ''; // replay the fade-in
  }
  load.raf = load.shown < load.target || load.target < 1 ? requestAnimationFrame(drawLoading) : 0;
}
function setLoading(p) {
  load.target = Math.max(load.target, Math.min(1, p));
  if (!load.raf) load.raf = requestAnimationFrame(drawLoading);
}
// A different Singapore scene develops each time (never the same one twice running).
function pickPhoto() {
  const scenes = [...document.querySelectorAll('.dv-scene')];
  let last = -1;
  try { last = +(localStorage.getItem('sparky.loadingPhoto') ?? -1); } catch { /* storage unavailable */ }
  let i = Math.floor(Math.random() * (scenes.length - 1));
  if (i >= last && last >= 0) i++;
  scenes.forEach((g, k) => g.classList.toggle('on', k === i));
  $('loading-caption').textContent = scenes[i].dataset.caption;
  try { localStorage.setItem('sparky.loadingPhoto', i); } catch { /* ignore */ }
}
function showLoading() {
  const el = $('loading');
  clearTimeout(load.hideT);
  pickPhoto();
  el.classList.remove('hidden', 'done');
  load.target = load.shown = 0;
  setLoading(0);
}
function hideLoading() {
  const el = $('loading');
  if (el.classList.contains('hidden')) return;
  setLoading(1); // the print finishes developing as the screen fades
  el.classList.add('done');
  load.hideT = setTimeout(() => { el.classList.add('hidden'); cancelAnimationFrame(load.raf); load.raf = 0; }, 700);
}

async function loadChapter(opts = {}) {
  showLoading();
  if (chapter) { await game.endChapter(); }
  chapter = new WW2Chapter(game, opts);
  game.chapter = chapter;
  await chapter.load(setLoading);
  setLoading(1);
  return chapter;
}

/** Title: the 1942 street as a slowly drifting sepia photograph behind the menu. */
function showTitle() {
  game.mode = 'menu';
  game.ui.showHUD(false);
  game.setScene(chapter.scene);
  game.player = chapter.player;
  game.npcs = Object.values(chapter.cast);
  game.world = chapter.world;
  chapter.placeCast();
  const sp = chapter.marker('SPAWN_Sparky');
  const fwd = new THREE.Vector3(Math.sin(sp.yaw), 0, Math.cos(sp.yaw));
  const g = game.renderer.grade;
  Object.assign(g, { sepia: 0.75, saturation: 0.35, vignette: 0.75, contrast: 1.05, flash: 0 });
  let t = 0;
  titleSpin?.();
  titleSpin = game.every((dt) => {
    t += dt;
    // Slow drift above the middle of the road, looking down the street.
    const x = sp.pos.x + fwd.x * (4 + Math.sin(t * 0.05) * 3);
    game.rig.cut(new THREE.Vector3(x, 2.8 + Math.sin(t * 0.07) * 0.3, Math.sin(t * 0.04) * 0.8), new THREE.Vector3(x + fwd.x * 14, 2.6, 0), 0.6);
  });
  hideLoading();
  $('title').classList.remove('hidden');
  $('title-hint').textContent = `${T.contentNote} Best played with sound.`;
  $('btn-begin').focus();
}

async function begin(opts = {}) {
  $('title').classList.add('hidden');
  game.audio.unlock();
  titleSpin?.();
  titleSpin = null;
  if (opts.fresh) {
    game.album.clearChapter('ww2');
    await game.ui.fade(true, 0.6);
    await loadChapter(opts);
    hideLoading();
  } else await game.ui.fade(true, 0.6);
  game.ui.showHUD(true);
  game.mode = 'cutscene';
  chapter.run().catch((e) => { if (e?.message !== 'aborted') console.error(e); });
}

$('btn-begin').onclick = () => { game.album.clearChapter('ww2'); begin(); };
$('btn-chapters').onclick = () => $('chapter-list').classList.toggle('hidden');
$('btn-settings-title').onclick = () => game.showTitleSettings(true);
document.querySelectorAll('.chapter-card[data-chapter]').forEach((b) => { b.onclick = () => { game.album.clearChapter('ww2'); begin({ skipPrologue: true, fresh: true }); }; });

game.onRestart = () => begin({ skipPrologue: true, fresh: true });
game.onQuit = () => location.reload();
game.onChapterComplete = async () => {
  game.input.releaseLock();
  game.ui.showHUD(false);
  await game.ui.fade(false, 0.8);
  game.album.open();
  await new Promise((r) => { const prev = game.album.onToggle; game.album.onToggle = (open) => { prev?.(open); if (!open) { game.album.onToggle = prev; r(); } }; });
  await game.ui.fade(false, 0.1);
  location.reload();
};

// Quality changes swap asset variants and shadow setup: simplest robust path is a reload
// at a safe moment (title) — mid-chapter we only change renderer settings.
(async () => {
  await loadChapter();
  showTitle();
  // Dev-only playthrough audit: ?autoplay (see src/debug/autoplay.js).
  if (new URLSearchParams(location.search).has('autoplay')) {
    const { installAutoplay } = await import('./debug/autoplay.js');
    installAutoplay(game);
    game.album.clearChapter('ww2');
    setTimeout(() => $('btn-begin').click(), 500);
  }
})();
