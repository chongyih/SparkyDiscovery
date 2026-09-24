import * as THREE from 'three';
import { Game } from './engine/game.js';
import { WW2Chapter } from './chapters/ww2.js';
import { IndependenceChapter } from './chapters/ind.js';
import T from './chapters/ww2-text.js';
import T2 from './chapters/ind-text.js';
import { thenNowPose } from './chapters/ww2-features.js';
import { capturePhoto } from './engine/album.js';
import { settings } from './engine/settings.js';

// Chapter id -> class. ?chapter=ind opens straight on Chapter 2 (title background + Begin).
const CHAPTERS = { ww2: WW2Chapter, ind: IndependenceChapter };
const startChapter = CHAPTERS[new URLSearchParams(location.search).get('chapter')] ? new URLSearchParams(location.search).get('chapter') : 'ww2';

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
  const id = opts.chapter || chapter?.chapterId || startChapter;
  chapter = new CHAPTERS[id](game, opts);
  chapter.chapterId = id;
  game.chapter = chapter;
  await chapter.load(setLoading);
  setLoading(1);
  return chapter;
}

/** Mr. Boon's 1942 frame for the title's chapter print, from the same viewpoint as the Then & Now photo. */
function developTitlePrint() {
  const img = $('print-1942');
  if (img.src || chapter.chapterId !== 'ww2') return;
  const cam = game.rig.camera, fov = cam.fov, targetFov = game.rig.targetFov;
  const pose = thenNowPose(chapter);
  const eye = pose.pos.clone();
  const grade = { ...game.renderer.grade };
  Object.assign(game.renderer.grade, { sepia: 0, saturation: 1, vignette: 0, flash: 0 });
  chapter.player.root.visible = false;
  game.rig.viewfinder(eye, eye.clone().add(new THREE.Vector3(Math.sin(pose.yaw), -0.04, Math.cos(pose.yaw))), true);
  game.rig.update(0, null, null);
  game.renderer.renderer.shadowMap.needsUpdate = true;
  game.renderer.render(0);
  img.src = capturePhoto(game.canvas, { size: 384 });
  chapter.player.root.visible = true;
  Object.assign(game.renderer.grade, grade);
  cam.fov = fov; game.rig.targetFov = targetFov; cam.updateProjectionMatrix();
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
  developTitlePrint();
  const g = game.renderer.grade;
  Object.assign(g, { sepia: 0.75, saturation: 0.35, vignette: 0.75, contrast: 1.05, flash: 0 });
  let t = 0;
  titleSpin?.();
  titleSpin = game.every((dt) => {
    t += dt;
    // A chapter can provide its own slow title drift; otherwise drift above the middle of Chapter 1's
    // street, looking down it.
    const shot = chapter.titleShot?.(t);
    if (shot) { game.rig.cut(shot[0], shot[1], 0.6); return; }
    const x = sp.pos.x + fwd.x * (4 + Math.sin(t * 0.05) * 3);
    game.rig.cut(new THREE.Vector3(x, 2.8 + Math.sin(t * 0.07) * 0.3, Math.sin(t * 0.04) * 0.8), new THREE.Vector3(x + fwd.x * 14, 2.6, 0), 0.6, t === dt);
  });
  hideLoading();
  const title = $('title');
  title.classList.toggle('intro', !settings.reduceMotion);
  document.body.classList.toggle('calm', settings.reduceMotion);
  // Drop the intro once it has played, so re-showing the prints doesn't replay the deal delays.
  clearTimeout(title.introT);
  title.introT = setTimeout(() => title.classList.remove('intro'), 3200);
  title.classList.remove('hidden');
  selectChapter(selected.id);
  showBackdrop(Math.max(0, TITLE_CHAPTERS.indexOf(selected)));
  $('btn-begin').focus({ preventScroll: true });
}

// ---------------- Title chapter select + backdrop cycle ----------------
// Chapters 1 and 2 are playable; Chapter 3 can be picked to preview it.
const TITLE_CHAPTERS = [
  { id: 'ww2', n: 1, place: 'Chinatown', when: 'Chinatown · February 1942', blurb: 'Bombs are falling on the city everyone called a fortress.', note: T.contentNote, playable: true },
  { id: 'ind', n: 2, place: 'Queenstown', when: 'Queenstown · 9 August 1965', blurb: 'Separated from Malaysia overnight, a worried island must stand on its own.', note: T2.contentNote, playable: true },
  { id: 'ns', n: 3, place: 'Taman Jurong', when: 'Taman Jurong Camp · 1967–68', blurb: 'The first national servicemen report for duty. Few families want them to go.' },
].map((c) => ({ ...c, year: document.querySelector(`.print[data-chapter="${c.id}"] .print-yr`).textContent }));
let selected = TITLE_CHAPTERS.find((c) => c.id === startChapter) || TITLE_CHAPTERS[0];
const prints = [...document.querySelectorAll('.print[data-chapter]')];

function selectChapter(id, { focus = false } = {}) {
  selected = TITLE_CHAPTERS.find((c) => c.id === id);
  prints.forEach((p) => {
    const on = p.dataset.chapter === id;
    p.setAttribute('aria-checked', on);
    p.tabIndex = on ? 0 : -1;
    if (on && focus) p.focus();
  });
  $('ci-kicker').textContent = `Chapter ${selected.n} · ${selected.when}`;
  $('ci-blurb').textContent = selected.blurb;
  const info = document.querySelector('.chapter-info');
  info.classList.remove('swap'); void info.offsetWidth; info.classList.add('swap');
  $('title-note').classList.toggle('hidden', !selected.note);
  $('title-hint').textContent = selected.note || '';
  const b = $('btn-begin');
  b.disabled = !selected.playable;
  b.textContent = selected.playable ? 'Begin' : 'Coming soon';
}

// The backdrop steps through the chapters: 1942 is the live street (the canvas behind), the others
// are stills. Picking a print jumps to its chapter; the cycle carries on from there.
const backdrop = { i: 0, timer: 0, idle: 0 };
function showBackdrop(i) {
  backdrop.i = i;
  const ch = TITLE_CHAPTERS[i];
  document.querySelectorAll('.backdrop').forEach((el) => el.classList.toggle('on', el.dataset.chapter === ch.id));
  // Skip rendering the 3D street while a still fully covers it (after its fade-in).
  clearTimeout(backdrop.idle);
  game.skipRender = false;
  if (ch.id !== 'ww2') backdrop.idle = setTimeout(() => { game.skipRender = true; }, 1800);
  const cap = $('backdrop-caption');
  cap.classList.add('swap');
  setTimeout(() => { cap.textContent = `${ch.place}, ${ch.year}`; cap.classList.remove('swap'); }, 400);
  clearTimeout(backdrop.timer);
  backdrop.timer = setTimeout(() => showBackdrop((i + 1) % TITLE_CHAPTERS.length), 9000);
}
function stopBackdrops() {
  clearTimeout(backdrop.timer);
  clearTimeout(backdrop.idle);
  game.skipRender = false;
  document.querySelectorAll('.backdrop').forEach((el) => el.classList.remove('on'));
}

prints.forEach((p, i) => {
  p.onclick = () => {
    selectChapter(p.dataset.chapter);
    if (backdrop.i !== i) showBackdrop(i);
    // Small screens pick from an overlay: close it once the choice has registered.
    if ($('chapter-list').classList.contains('open')) setTimeout(() => showPrints(false), 350);
  };
  // Radio-group keys: arrows move the selection.
  p.onkeydown = (e) => {
    const step = { ArrowRight: 1, ArrowDown: 1, ArrowLeft: -1, ArrowUp: -1 }[e.key];
    if (!step) return;
    e.preventDefault();
    const next = prints[(i + step + prints.length) % prints.length];
    selectChapter(next.dataset.chapter, { focus: true });
    showBackdrop(prints.indexOf(next));
  };
});

async function begin(opts = {}) {
  $('title').classList.add('hidden');
  stopBackdrops();
  game.audio.unlock();
  titleSpin?.();
  titleSpin = null;
  if (opts.fresh) {
    game.album.clearChapter(opts.chapter || chapter.chapterId);
    await game.ui.fade(true, 0.6);
    await loadChapter(opts);
    hideLoading();
  } else await game.ui.fade(true, 0.6);
  game.ui.showHUD(true);
  game.mode = 'cutscene';
  chapter.run().catch((e) => { if (e?.message !== 'aborted') console.error(e); });
}

$('btn-begin').onclick = () => {
  if (!selected.playable) return;
  game.album.clearChapter(selected.id);
  // The loaded chapter (behind the title) starts with its prologue; another one loads fresh.
  if (selected.id === chapter.chapterId) begin(); else begin({ fresh: true, chapter: selected.id });
};
// Small screens only: the prints open over the title (on larger ones they're always shown).
function showPrints(open) {
  $('chapter-list').classList.toggle('open', open);
  $('btn-chapters').setAttribute('aria-expanded', open);
  (open ? document.querySelector('.print[aria-checked="true"]') : $('btn-chapters')).focus();
}
$('btn-chapters').onclick = () => showPrints(true);
$('btn-prints-back').onclick = () => showPrints(false);
$('chapter-list').addEventListener('click', (e) => { if (e.target === e.currentTarget) showPrints(false); });
game.input.on('pause', () => { if (game.mode === 'menu' && $('chapter-list').classList.contains('open') && !game.titleSettings) showPrints(false); });
$('btn-settings-title').onclick = () => game.showTitleSettings(true);

game.onRestart = () => begin({ skipPrologue: true, fresh: true, chapter: chapter.chapterId });
game.onQuit = () => location.reload();
game.onChapterComplete = async (id) => {
  game.input.releaseLock();
  game.ui.showHUD(false);
  await game.ui.fade(false, 0.8);
  game.album.open();
  await new Promise((r) => { const prev = game.album.onToggle; game.album.onToggle = (open) => { prev?.(open); if (!open) { game.album.onToggle = prev; r(); } }; });
  await game.ui.fade(false, 0.1);
  // 1942 leads straight on to 1965 (the same roll of film); after that, back to the title.
  if (id === 'ww2') { begin({ fresh: true, chapter: 'ind' }); return; }
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
