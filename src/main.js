import * as THREE from 'three';
import { Game } from './engine/game.js';
import { WW2Chapter } from './chapters/ww2.js';
import T from './chapters/ww2-text.js';

const $ = (id) => document.getElementById(id);
const game = new Game($('game'));
window.__game = game; // handy for debugging in the console

let chapter = null;
let titleSpin = null;

function setLoading(p) { $('loading-bar').style.width = `${Math.round(p * 100)}%`; }

async function loadChapter(opts = {}) {
  $('loading').classList.remove('hidden');
  setLoading(0);
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
  $('loading').classList.add('hidden');
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
    $('loading').classList.add('hidden');
  } else await game.ui.fade(true, 0.6);
  game.ui.showHUD(true);
  game.mode = 'cutscene';
  chapter.run().catch((e) => { if (e?.message !== 'aborted') console.error(e); });
}

$('btn-begin').onclick = () => { game.album.clearChapter('ww2'); begin(); };
$('btn-chapters').onclick = () => $('chapter-list').classList.toggle('hidden');
$('btn-settings-title').onclick = () => { $('pause').classList.remove('hidden'); $('pause-title').textContent = 'Settings'; $('btn-restart').classList.add('hidden'); $('btn-quit').classList.add('hidden'); $('btn-resume').textContent = 'Back'; };
$('btn-resume').addEventListener('click', () => {
  $('pause').classList.add('hidden');
  $('pause-title').textContent = 'Paused'; $('btn-restart').classList.remove('hidden'); $('btn-quit').classList.remove('hidden'); $('btn-resume').textContent = 'Resume';
});
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
})();
