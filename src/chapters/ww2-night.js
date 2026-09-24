import * as THREE from 'three';
import T from './ww2-text.js';
import { Character } from '../engine/character.js';
import { houseFire, disposeEffect } from '../engine/fx.js';
import { radialTexture } from '../engine/assets.js';
import { markerPose } from '../engine/world.js';
import { drawFrontPage, newspaperPuzzle } from '../engine/puzzle.js';

// Beats 4–6 of Chapter 1: shelter transition → blackout search (night of 14 Feb) →
// rumours in the silence (evening of 15 Feb). Each takes the WW2Chapter instance `c`.

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const UP = new THREE.Vector3(0, 1, 0);
const pick = (a) => a[Math.floor(Math.random() * a.length)];

// Fallback text so the beats run before the writer's final copy lands.
const D = {
  shelterTransition: {
    before: [{ who: 'Hassan', text: 'Every blast feels closer than the last one.' }],
    card: { who: 'Card', text: 'Two nights later. Saturday, 14 February 1942.' },
    after: [
      { who: 'AhMa', text: 'Boon? Boon! Where is Boon?' },
      { who: 'Siti', text: 'He kept asking about his papa. I think he went to find him!' },
      { who: 'Rajan', text: 'I must stay with everyone here. Bear — find him. Stay under the five-foot ways.' },
    ],
    objective: 'Find Ah Boon in the blackout.',
  },
  blackout: {
    start: [{ who: 'Narrator', text: 'Blackout. The only light comes from the fires — and the shells.' }],
    hint: 'Search the street for Ah Boon.',
    coverHint: 'When you hear a shell whistle, get under a five-foot way!',
    knockedDown: ['A blast throws Sparky to the ground. His ears ring.', 'Too close. Sparky crawls back to cover.'],
    clues: [
      { title: 'A small slipper', text: 'One of Boon’s rubber slippers, lying in the road.' },
      { title: 'A tiffin carrier', text: 'Papa’s lunch tin, dropped by the kerb. Boon must have taken it with him.' },
      { title: 'A voice', text: 'Somewhere ahead, a small voice is calling: “Papa! Papa!”' },
    ],
    found: [
      { who: 'Boon', text: 'Bear? I wanted to bring Papa his lunch… I got scared.' },
      { who: 'Boon', text: 'Don’t tell Ah Ma I cried. Can we go back now?' },
    ],
    return: [{ who: 'AhMa', text: 'Boon! Never do that again. Never!' }],
  },
  rumours: {
    card: { who: 'Card', text: 'The next evening. Sunday, 15 February 1942.' },
    start: [{ who: 'Hassan', text: 'Listen… the guns have stopped. Why have they stopped?' }],
    hint: 'Find out what people are saying.',
    fragments: [
      { who: 'Siti', lines: [{ who: 'Siti', text: 'I found pieces of the last newspaper blowing down the street.' }] },
      { who: 'Hassan', lines: [{ who: 'Hassan', text: 'A lorry driver said the Americans are coming to save us.' }] },
      { who: 'AhMa', lines: [{ who: 'AhMa', text: 'My neighbour’s wireless caught a far-away station. It said “ceased”.' }] },
      { who: 'Neighbour', lines: [{ who: 'Neighbour', text: 'I saw soldiers with a white flag driving towards Bukit Timah.' }] },
    ],
    puzzle: { title: 'The last newspaper', hint: 'Drag the torn pieces into place.' },
    headline: { text: 'Singapore Must Stand; It SHALL Stand', source: 'The Straits Times, 15 February 1942' },
    reveal: [
      { who: 'Siti', text: '“Singapore must stand. It shall stand.” That’s what it says.' },
      { who: 'Rajan', text: 'It’s over. The British surrendered this evening, at the Ford factory in Bukit Timah.' },
      { who: 'Siti', text: 'The paper said we would stand. I read it out loud. I told everybody.' },
    ],
  },
};
const TXT = (k) => ({ ...D[k], ...(T[k] || {}) });

// ------------------------------------------------------------------ lighting presets
const PRESETS = {
  now: { bg: '#bcd3e6', fog: '#d2dde4', near: 45, far: 240, top: '#5f93c8', horizon: '#dce6ec', bottom: '#9aa3a6', smoke: 0, hemi: ['#f3f6ff', '#7a7466', 1.25], sun: ['#fff1d6', 2.6], env: 0.45, grade: { saturation: 1.05, contrast: 1.03, vignette: 0.3, sepia: 0 }, tint: [1, 1, 1] },
  day: { bg: '#b9b2a2', fog: '#bdb3a0', near: 30, far: 190, top: '#7f8a8e', horizon: '#d4c6a8', bottom: '#8f8676', smoke: 0.35, hemi: ['#e8e1d0', '#6f6352', 1.35], sun: ['#ffe7c4', 2.1], env: 0.35, grade: { saturation: 0.92, contrast: 1.04, vignette: 0.4, sepia: 0 }, tint: [1, 1, 1] },
  night: { bg: '#161b28', fog: '#2a2026', near: 14, far: 130, top: '#0c1120', horizon: '#5a2e16', bottom: '#15100c', smoke: 0.85, hemi: ['#7488c0', '#33251a', 0.62], sun: ['#a8bbee', 0.7], env: 0.1, grade: { saturation: 0.75, contrast: 1.08, vignette: 0.62, sepia: 0 }, tint: [1.0, 0.97, 0.95] },
  dusk: { bg: '#6a5a4c', fog: '#7a6552', near: 14, far: 120, top: '#3c3a40', horizon: '#c07a48', bottom: '#4a3a30', smoke: 0.7, hemi: ['#d8b89a', '#3a2c22', 0.7], sun: ['#ff9a5a', 1.3], env: 0.2, grade: { saturation: 0.7, contrast: 1.08, vignette: 0.6, sepia: 0.1 }, tint: [1.03, 0.98, 0.93] },
  occupation: { bg: '#a9aaa6', fog: '#aeb0ad', near: 25, far: 170, top: '#8a9296', horizon: '#c9c6bb', bottom: '#8a877e', smoke: 0.2, hemi: ['#d6d8d8', '#6f6a60', 1.1], sun: ['#f2efe6', 1.2], env: 0.3, grade: { saturation: 0.42, contrast: 1.08, vignette: 0.5, sepia: 0 }, tint: [0.95, 0.98, 1.02] },
};

export function setLighting(c, name) {
  const p = PRESETS[name];
  const s = c.scene;
  s.background.set(p.bg);
  s.fog.color.set(p.fog); s.fog.near = p.near; s.fog.far = p.far;
  const u = c.sky.material.uniforms;
  u.top.value.set(p.top); u.horizon.value.set(p.horizon); u.bottom.value.set(p.bottom); u.smoke.value = p.smoke;
  c.hemi.color.set(p.hemi[0]); c.hemi.groundColor.set(p.hemi[1]); c.hemi.intensity = p.hemi[2];
  c.sun.color.set(p.sun[0]); c.sun.intensity = p.sun[1];
  s.environmentIntensity = p.env;
  Object.assign(c.game.renderer.grade, p.grade);
  c.game.renderer.grade.tint.setRGB(...p.tint);
  c.lighting = name;
}

// ------------------------------------------------------------------ helpers
function markersWith(c, prefix) {
  return Object.keys(c.m).filter((k) => k.startsWith(prefix)).sort().map((k) => markerPose(c.m[k]));
}

/** A background figure cloned from a loaded NPC model, with tinted clothes. */
export function spawnExtra(c, baseKey, { tint = 0xb0a890, name = 'Extra', height } = {}) {
  const gltf = c.gltf?.[baseKey];
  const ch = new Character(name, gltf, { height: height ?? c.cast[baseKey]?.height ?? 1.7, placeholder: { shirt: '#9a8f78', pants: '#4a4640' } });
  const col = new THREE.Color(tint);
  ch.model.traverse((o) => {
    if (!o.isMesh) return;
    o.material = [].concat(o.material).map((m) => { const mm = m.clone(); mm.color?.multiply(col); return mm; });
    if (o.material.length === 1) o.material = o.material[0];
  });
  c.scene.add(ch.root);
  c.extras.push(ch);
  c.game.npcs.push(ch);
  c.world.dynamic.push(ch.collider);
  return ch;
}

const _from = new THREE.Vector3();
function isCovered(c, pos) {
  _from.copy(pos).setY(pos.y + 1.0);
  return c.world.rayDistance(_from, UP, 7) < 6;
}

// ------------------------------------------------------------------ beat 4: shelter transition
// 12 Feb: the shelter shakes, the candle goes out. Card. Two nights later, by a low candle, everyone
// sleeps; Boon whispers to Sparky, tiptoes out to find his papa; a shell wakes everyone.
export async function shelterTransition(c) {
  const g = c.game;
  const X = TXT('shelterTransition');
  const { Rajan, AhMa, Boon, Hassan, Siti } = c.cast;
  await g.ui.fade(true, 0.9);
  c.siren?.fade(0.12, 1);
  c.fires.forEach((f) => { f.visible = false; c.pool.release(f.light); f.light = null; });
  c.setInterior(true);
  c.town?.hideAll();
  const seats = [1, 2, 3, 4, 5].map((i) => c.marker(`INT_Seat_${i}`, V(198 + i * 0.8, 0.47, 1.72)));
  const sitAt = (ch, seat) => {
    ch.stop();
    ch.place(seat.pos.clone().setY(Math.max(0, seat.pos.y - 0.45)), seat.yaw);
    ch.play('Sit');
  };
  [Hassan, AhMa, Boon, Siti].forEach((ch, i) => sitAt(ch, seats[i]));
  // Mr. Rajan keeps watch by the door; Sparky sits on the bench opposite.
  const door = c.marker('INT_Spawn', V(196.8, 0, -0.3));
  Rajan.stop();
  Rajan.place(door.pos.clone().add(V(0.9, 0, 0.9)), door.yaw);
  Rajan.play('Idle');
  const s5 = seats[4];
  const p = c.player;
  p.scripted = true;
  // Sparky's Sit clip expects the seat's front edge; the bench seat is a touch higher than his.
  p.place(s5.pos.clone().add(V(Math.sin(s5.yaw) * 0.18, 0, Math.cos(s5.yaw) * 0.18)).setY(s5.pos.y - 0.4), s5.yaw);
  p.play('Sit');
  const mid = seats[1].pos.clone().lerp(seats[2].pos, 0.5);
  const candle = c.pool.claim({ color: '#ffb35c', intensity: 6, distance: 9, decay: 1.6 }) || new THREE.Object3D();
  candle.position.copy(mid.clone().lerp(s5.pos, 0.5)).setY(0.9);
  const saved = { hemi: c.hemi.intensity, sun: c.sun.intensity };
  c.hemi.intensity = 0.1; c.sun.intensity = 0;
  let level = 1, t = 0;
  const flicker = g.every((dt) => { t += dt; if (candle.isLight) candle.intensity = Math.max(0, level * (5 + Math.sin(t * 9) * 0.6 + Math.sin(t * 23) * 0.4)); });
  const room = g.audio.play('shelter-room', { loop: true, volume: 0.7, fadeIn: 1 });
  const cam = c.marker('INT_Camera', V(199.4, 1.35, -0.9));
  const look = mid.clone().setY(1.0);
  g.rig.cut(cam.pos, look, 1, true);
  const drift = g.every(() => { g.rig.shot.pos.x = cam.pos.x + Math.sin(g.time * 0.25) * 0.1; });
  await g.ui.fade(false, 1);
  for (let i = 0; i < 2; i++) { g.audio.play('distant-explosion', { volume: 0.7, rate: 0.7 }); g.rig.addShake(0.4); c.dust?.kick(0.5); await g.wait(1.1); }
  await c.lines(X.before, { frame: false });
  // The big one: the candle goes out.
  g.audio.play('impact', { volume: 0.6, rate: 0.6 });
  g.rig.addShake(0.9);
  c.dust?.kick(1);
  level = 0;
  await g.wait(1.6);
  c.siren?.stop(1);
  await g.ui.fade(true, 0.6);
  await c.cardLine(X.card.text);
  // Two nights later: a low candle; everyone asleep except Boon.
  level = 0.45;
  Boon.stop();
  Boon.place(seats[2].pos.clone().setY(0).add(V(0, 0, -0.6)));
  Boon.faceTowards(p.root.position, true);
  Boon.play('Idle');
  g.audio.play('rumble', { volume: 0.35, caption: '[Far-off guns thud]' });
  // Wide shot of the sleeping shelter, centred between Boon and Sparky (the room is too small
  // for a tight two-shot).
  const pair = Boon.root.position.clone().lerp(p.root.position, 0.5).setY(0.85);
  g.rig.cut(cam.pos.clone().add(V(0, 0.15, 0)), pair, 1, true);
  await g.ui.fade(false, 1.2);
  if (X.boonLeaves?.length) await c.lines(X.boonLeaves, { frame: false });
  // He tiptoes to the door and slips out.
  const out = door.pos.clone().add(V(-1.2, 0, 0));
  g.rig.cut(cam.pos.clone().add(V(-1.2, 0.1, 0)), door.pos.clone().setY(0.9), 1.2);
  await Promise.race([Boon.moveTo([door.pos.clone().add(V(0.4, 0, 0)), out], { speed: 0.6 }), g.wait(7)]);
  Boon.stop();
  Boon.root.visible = false;
  g.audio.play('door', { volume: 0.25, caption: '[The door creaks softly]' });
  Boon.place(c.marker('NIGHT_Boon', V(-26, 0.2, -4.6)).pos);
  await g.wait(1.4);
  // A shell lands close by. Everyone wakes.
  g.audio.play('impact', { volume: 0.8, rate: 0.7, caption: '[A shell lands close by]' });
  g.rig.addShake(1);
  c.dust?.kick(1);
  level = 1;
  g.rig.cut(cam.pos, look, 3);
  AhMa.stop(); AhMa.place(seats[1].pos.clone().setY(0).add(V(0, 0, -0.5))); AhMa.faceTowards(seats[2].pos, true); AhMa.play('Idle');
  Siti.stop(); Siti.place(seats[3].pos.clone().setY(0).add(V(0, 0, -0.5))); Siti.faceTowards(p.root.position, true); Siti.play('Idle');
  await g.wait(0.8);
  await c.lines(X.after, { frame: false });
  await g.ui.fade(true, 0.8);
  flicker(); drift();
  room.stop(0.8);
  if (candle.isLight) c.pool.release(candle);
  c.setInterior(false);
  c.hemi.intensity = saved.hemi; c.sun.intensity = saved.sun;
  p.play('Idle');
  p.scripted = false;
}

// ------------------------------------------------------------------ beat 5: blackout search
export async function blackoutBeat(c) {
  const g = c.game;
  const X = TXT('blackout');
  const { Boon, AhMa } = c.cast;
  setLighting(c, 'night');
  // Fires along the street light the dark (point lights limited by tier).
  c.fires.forEach((f) => { f.visible = true; });
  const firePts = markersWith(c, 'FIRE_').map((p) => p.pos);
  if (!firePts.length) firePts.push(V(-18, 6, -9), V(6, 7, 9), V(24, 5, -10));
  // A soft personal fill so Sparky stays readable (kids' game) without breaking the blackout.
  const fill = c.pool.claim({ color: '#9fb4e0', intensity: 0.7, distance: 4, decay: 2 });
  const followFill = fill ? g.every(() => fill.position.copy(c.player.root.position).setY(c.player.root.position.y + 1.4)) : () => {};
  const nightFires = [];
  for (const p of firePts.slice(0, 4)) { const f = houseFire(p, c.pool.claim()); c.scene.add(f); nightFires.push(f); c.fires.push(f); }

  Boon.root.visible = false;
  const spawn = c.marker('NIGHT_Spawn', c.marker('SHELTER_Entrance').pos.clone().add(V(-1.5, 0, 0)));
  c.player.place(spawn.pos, spawn.yaw);
  AhMa.place(c.marker('SHELTER_Entrance').pos.clone().add(V(0.8, 0, 0.4)));
  AhMa.root.visible = false;
  g.rig.setSubject(c.player);
  g.rig.follow();
  const amb = g.audio.play('night-ambience', { loop: true, volume: 0.8, fadeIn: 2, caption: '' });
  const heart = g.audio.play('heartbeat', { loop: true, volume: 0.25, fadeIn: 3, caption: '' });
  const crackles = nightFires.map((f) => g.audio.emitter('fire-crackle', f.position, { radius: 14, volume: 0.7 }));
  await g.ui.fade(false, 1.2);
  await c.lines(X.start, { frame: false });
  g.mode = 'play';
  g.input.requestLock();
  g.ui.caption(X.coverHint, 6);

  // --- cover + shells ---
  let lastCover = c.player.root.position.clone();
  let covered = true;
  let shellAt = g.time + 6; // first shell comes after the tutorial caption
  let warning = null;
  let firstShell = true;
  let nextFlash = g.time + 2;
  const warnEl = document.getElementById('counter');
  const shells = g.every((dt) => {
    const pp = c.player.root.position;
    // Cutscenes (clues, knock-downs) pause the shelling clock, so nothing lands the instant they end.
    if (g.mode !== 'play') { shellAt += dt; if (warning) warning.at += dt; warnEl.style.visibility = 'hidden'; }
    else warnEl.style.visibility = '';
    covered = isCovered(c, pp);
    if (covered && g.mode === 'play') lastCover.copy(pp);
    // Distant flashes: harmless, but they light up the street for a moment.
    if (g.time > nextFlash) {
      nextFlash = g.time + 2.5 + Math.random() * 3;
      const a = Math.random() * Math.PI * 2;
      c.explode(pp.clone().add(V(Math.cos(a) * 60, 2, Math.sin(a) * 60 + (Math.random() < 0.5 ? -30 : 30))), 3, false, { caption: '' });
    }
    if (g.mode !== 'play') return;
    if (!warning && g.time > shellAt) {
      const lead = firstShell ? 3.2 : 2.2;
      warning = { at: g.time + lead };
      g.audio.play('shell-whistle', { volume: 0.9, caption: '[A shell whistles in — take cover!]' });
      warnEl.textContent = 'TAKE COVER!';
      warnEl.classList.remove('hidden');
      warnEl.classList.add('alert');
    }
    if (warning) {
      warnEl.textContent = covered ? 'Under cover' : 'TAKE COVER!';
      warnEl.classList.toggle('safe', covered);
      if (g.time >= warning.at) {
        warning = null;
        firstShell = false;
        shellAt = g.time + 8 + Math.random() * 5;
        warnEl.classList.add('hidden');
        warnEl.classList.remove('alert', 'safe');
        // Lands in the road nearby — never directly on Sparky.
        const a = Math.random() * Math.PI * 2;
        const hit = pp.clone().add(V(Math.cos(a) * 7, 0.5, Math.sin(a) * 3));
        hit.z = THREE.MathUtils.clamp(hit.z, -3, 3);
        c.explode(hit, 2, !covered);
        if (!covered) knockDown(c, X, lastCover);
      }
    }
  });

  // --- clues → Boon ---
  const cluePts = markersWith(c, 'NIGHT_Clue_');
  const bpos = c.marker('NIGHT_Boon', V(-26, 0.2, -4.6)).pos;
  while (cluePts.length < 3) {
    const k = cluePts.length + 1;
    cluePts.push({ pos: spawn.pos.clone().lerp(bpos, k / 4).setZ(k % 2 ? 0 : spawn.pos.z), yaw: 0 });
  }
  for (let i = 0; i < 3; i++) {
    const clue = X.clues[i];
    g.objective(X.hint, cluePts[i].pos, { height: 0.9 });
    const prop = clueProp(i);
    prop.position.copy(cluePts[i].pos);
    c.scene.add(prop);
    await new Promise((resolve) => {
      const it = g.addInteract({
        pos: cluePts[i].pos, radius: 1.6, priority: 10, label: 'Look closer',
        onUse: async () => {
          g.removeInteract(it);
          g.mode = 'cutscene';
          c.scene.remove(prop);
          g.audio.play('pickup-chime', { volume: 0.4 });
          g.ui.toast(clue.title, clue.text, 7);
          if (clue.lines?.length) await c.lines(clue.lines, { frame: false });
          else await g.wait(0.6);
          g.rig.follow();
          g.mode = 'play';
          g.input.requestLock();
          resolve();
        },
      });
    });
  }
  g.objective('Ah Boon is close. Find him.', Boon);
  Boon.root.visible = true;
  Boon.indicator('important');
  await c.interactOnce(Boon, 'Reach Ah Boon');
  Boon.indicator(null);
  await c.lines(X.found);
  Boon.follow(c.player, { gap: 0.9, speed: 2.4 });
  g.rig.follow();
  g.mode = 'play';
  g.input.requestLock();
  const shelter = c.marker('SHELTER_Entrance').pos;
  g.objective('Bring Ah Boon back to the shelter.', shelter);
  await g.waitUntil(() => g.mode === 'play' && c.player.root.position.distanceTo(shelter) < 2.4 && Boon.root.position.distanceTo(shelter) < 5);
  shells();
  warnEl.style.visibility = '';
  warnEl.classList.add('hidden');
  warnEl.classList.remove('alert', 'safe');
  g.objective(null);
  g.mode = 'cutscene';
  AhMa.root.visible = true;
  AhMa.faceTowards(Boon.root.position, true);
  Boon.stop();
  await c.lines(X.return);
  followFill();
  c.pool.release(fill);
  amb.stop(1.5); heart.stop(1);
  crackles.forEach((e) => g.audio.removeEmitter(e, 1));
  await g.ui.fade(true, 1.2);
  for (const f of nightFires) { c.scene.remove(f); c.pool.release(f.light); disposeEffect(f); c.fires = c.fires.filter((x) => x !== f); }
}

async function knockDown(c, X, lastCover) {
  const g = c.game;
  g.mode = 'cutscene';
  const p = c.player;
  p.play('Crouch');
  g.renderer.grade.flash = 1;
  g.tween(g.renderer.grade, { flash: 0 }, 2.2);
  const ring = g.audio.play('ear-ring', { volume: 0.7, caption: '[Ears ringing]' });
  g.audio.duck = 0.25;
  g.ui.caption(pick(X.knockedDown), 3.5);
  await g.wait(2);
  await g.ui.fade(true, 0.5);
  p.place(lastCover, p.yaw);
  p.play('Idle');
  g.rig.snapBehind();
  await g.wait(0.3);
  await g.ui.fade(false, 0.6);
  ring.stop(1);
  g.audio.duck = 1;
  g.mode = 'play';
}

/** Small props for the clue trail (slipper, tiffin carrier, a dropped photo). */
function clueProp(i) {
  const grp = new THREE.Group();
  if (i === 0) {
    const m = new THREE.Mesh(new THREE.CapsuleGeometry(0.045, 0.14, 4, 8), new THREE.MeshStandardMaterial({ color: '#b43c2e', roughness: 0.7 }));
    m.rotation.z = Math.PI / 2; m.rotation.y = 0.6; m.scale.set(1, 1, 0.35); m.position.y = 0.02;
    grp.add(m);
  } else if (i === 1) {
    const mat = new THREE.MeshStandardMaterial({ color: '#b7b3a8', metalness: 0.8, roughness: 0.35 });
    for (let k = 0; k < 3; k++) { const tin = new THREE.Mesh(new THREE.CylinderGeometry(0.08, 0.08, 0.07, 16), mat); tin.position.y = 0.04 + k * 0.075; grp.add(tin); }
    const handle = new THREE.Mesh(new THREE.TorusGeometry(0.07, 0.008, 6, 16, Math.PI), mat);
    handle.position.y = 0.27; grp.add(handle);
    grp.rotation.z = 1.2; grp.position.y = 0.05;
  } else {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(0.12, 0.16), new THREE.MeshStandardMaterial({ color: '#e8dcc0', roughness: 0.9 }));
    m.rotation.x = -Math.PI / 2; m.rotation.z = 0.4; m.position.y = 0.01;
    grp.add(m);
  }
  // A soft glow sprite marks the clue (no real light — keeps the light count constant).
  const glint = new THREE.Sprite(new THREE.SpriteMaterial({ map: radialTexture('glow', 'rgba(255,215,122,0.9)', 'rgba(255,215,122,0)'), blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
  glint.scale.set(0.7, 0.7, 1);
  glint.position.y = 0.15;
  grp.add(glint);
  return grp;
}

// ------------------------------------------------------------------ beat 6: rumours in the silence
export async function rumoursBeat(c) {
  const g = c.game;
  const X = TXT('rumours');
  const { Rajan } = c.cast;
  setLighting(c, 'dusk');
  c.fires.forEach((f) => { c.scene.remove(f); c.pool.release(f.light); disposeEffect(f); });
  c.fires = [];
  const pts = markersWith(c, 'RUMOUR_');
  const fallback = [V(-2, 0.2, -4.6), V(-12, 0, 1.5), V(12, 0, -2.5), V(20, 0.2, 4.6)];
  while (pts.length < 4) pts.push({ pos: fallback[pts.length], yaw: 0 });
  // Rajan has gone to the police post for news; he returns at the reveal.
  Rajan.root.visible = false;
  const { Boon, AhMa } = c.cast;
  // Everyone steps out of the shelter together, just outside the door, facing up the street.
  const out = c.marker('NIGHT_Spawn', c.marker('SHELTER_Entrance').pos.clone().add(V(-1.5, 0, -1.5)));
  const fwd = V(Math.sin(out.yaw), 0, Math.cos(out.yaw));
  const side = V(fwd.z, 0, -fwd.x);
  c.player.place(out.pos, out.yaw);
  // Offsets always spread toward the open road (never into the shelter's sandbag walls), then get
  // pushed clear of any collider.
  const roadSide = Math.sign(-(out.pos.z) * side.z) || 1;
  const around = (k, s) => {
    const q = out.pos.clone().addScaledVector(fwd, k).addScaledVector(side, roadSide * Math.abs(s));
    c.world.resolve(q, 0.3, 1.5);
    return q;
  };
  const speakers = [];
  X.fragments.forEach((f, i) => {
    let ch = c.cast[f.who];
    if (!ch && f.who === 'Soldier' && c.gltf.Soldier) ch = spawnExtra(c, 'Soldier', { tint: 0xffffff, name: 'Soldier', height: 1.7 });
    if (!ch) ch = spawnExtra(c, 'Hassan', { tint: f.who === 'Soldier' ? 0x9a9a6a : 0xc8b8a0, name: f.who });
    ch.stop();
    ch.root.visible = true;
    ch.spot = pts[i];
    if (f.who === 'Soldier') {
      // He sits, exhausted, on a crate by the kerb.
      ch.place(pts[i].pos, pts[i].yaw);
      ch.play('Sit');
      const crate = new THREE.Mesh(new THREE.BoxGeometry(0.5, 0.45, 0.42), new THREE.MeshStandardMaterial({ color: '#7a5a3c', roughness: 0.9 }));
      crate.position.copy(pts[i].pos).add(V(0, 0.225, 0));
      crate.rotation.y = pts[i].yaw;
      c.scene.add(crate);
      c.rumourCrate = crate;
    } else {
      ch.place(around(1.8 + speakers.length * 0.4, 0.6 + (speakers.length % 2) * 1.2), out.yaw + Math.PI);
      ch.play('Idle');
    }
    speakers.push(ch);
  });
  AhMa.stop(); AhMa.root.visible = true;
  AhMa.place(around(1.2, 1.1), out.yaw + Math.PI);
  Boon.stop(); Boon.root.visible = true;
  Boon.place(around(1.0, 1.7), out.yaw + Math.PI);
  Boon.follow(AhMa, { gap: 0.6, speed: 2 });
  for (const ch of [...speakers.filter((x) => x.name !== 'Soldier'), AhMa, Boon]) ch.faceTowards(c.player.root.position, true);
  c.player.faceTowards(AhMa.root.position, true);
  g.rig.setSubject(c.player);
  g.rig.follow();
  await c.cardLine(X.card.text);
  const hush = g.audio.play('murmur', { loop: true, volume: 0.15, fadeIn: 3, caption: '' });
  g.rig.frameTwo(c.player, AhMa, { lambda: 6 });
  g.rig.cut(g.rig.shot.pos, g.rig.shot.look, 1, true);
  await g.ui.fade(false, 1.5);
  await c.lines(X.start);
  // The neighbours drift off along the silent street to talk in little groups.
  speakers.forEach((ch) => { if (ch.name !== 'Soldier') Promise.race([ch.moveTo(ch.spot.pos, { speed: 1.1 }), g.wait(14)]).then(() => ch.faceTowards(c.player.root.position)); });
  g.rig.follow();
  g.mode = 'play';
  g.input.requestLock();

  const remaining = new Set(X.fragments.map((f, i) => i));
  let pieces = 0;
  g.ui.counter(`Newspaper pieces 0/${X.fragments.length}`);
  const retarget = () => {
    const pp = c.player.root.position;
    let best = null;
    for (const i of remaining) if (best === null || speakers[i].root.position.distanceTo(pp) < speakers[best].root.position.distanceTo(pp)) best = i;
    g.objective(X.hint, best === null ? null : speakers[best]);
  };
  retarget();
  await new Promise((resolve) => {
    X.fragments.forEach((f, i) => {
      const ch = speakers[i];
      ch.indicator('important');
      const it = g.addInteract({
        pos: () => ch.root.position, radius: 1.9, priority: 10, label: `Listen to ${({ AhMa: 'Ah Ma', Hassan: 'Pak Hassan', Soldier: 'the soldier', Neighbour: 'the neighbour' })[f.who] || f.who}`,
        onUse: async () => {
          g.removeInteract(it);
          ch.indicator(null);
          g.mode = 'cutscene';
          await c.lines(f.lines);
          remaining.delete(i);
          pieces++;
          g.audio.play('paper-piece', { caption: '' });
          g.ui.counter(`Newspaper pieces ${pieces}/${X.fragments.length}`);
          g.rig.follow();
          g.mode = 'play';
          g.input.requestLock();
          if (!remaining.size) resolve(); else retarget();
        },
      });
    });
  });
  g.ui.counter(null);
  g.objective(null);
  // Puzzle.
  g.mode = 'cutscene';
  g.input.releaseLock();
  g.input.lookEnabled = false;
  const page = drawFrontPage({ headline: X.headline.text });
  // One torn strip per rumour fragment, top (headline) to bottom.
  let offAssist = null;
  await newspaperPuzzle({
    canvas: page, cols: 1, rows: X.fragments.length, title: X.puzzle.title, hint: X.puzzle.hint,
    onPlace: () => g.audio.play('paper-piece', { caption: '' }),
    bindAssist: (fn) => { offAssist = g.input.on('action', fn); },
  });
  offAssist?.();
  g.input.lookEnabled = true;
  g.audio.play('pickup-chime');
  g.ui.toast(X.headline.source, `“${X.headline.text}”`, 8);
  // Reveal: Rajan comes back up the street with the truth.
  const siti = c.cast.Siti;
  const group = speakers.filter((s) => s !== siti);
  const meet = siti.root.position.clone();
  group.filter((s) => s.name !== 'Soldier').forEach((s, i) => {
    s.moveTo(meet.clone().add(V(Math.cos(i * 2.1 + 0.6) * 1.5, 0, Math.sin(i * 2.1 + 0.6) * 1.2)), { speed: 1.4 });
  });
  AhMa.stop();
  AhMa.place(meet.clone().add(V(-1.2, 0, 1.0)));
  AhMa.faceTowards(meet, true);
  Boon.place(AhMa.root.position.clone().add(V(0.5, 0, 0.3)), AhMa.yaw);
  c.player.scripted = true;
  c.player.moveTo(meet.clone().add(V(1.1, 0, 0.6)), { speed: 2 });
  const revealLines = X.reveal;
  const iR = revealLines.findIndex((l) => l.who === 'Rajan');
  await c.lines(revealLines.slice(0, Math.max(0, iR)), {});
  if (iR >= 0) {
    Rajan.root.visible = true;
    Rajan.place(meet.clone().add(V(-7, 0, 0)));
    g.rig.frameTwo(c.player, siti, { lambda: 1.5 });
    await Rajan.moveTo(meet.clone().add(V(-1.4, 0, 0.4)), { speed: 1.5 });
    Rajan.faceTowards(meet);
    await c.lines(revealLines.slice(iR), {});
  }
  c.player.scripted = false;
  // Snap the moment.
  if (T.snaps.Headline) {
    g.objective(X.snapHint || 'Take a photo of your friends in the silent street.');
    const eye = c.player.headPosition().add(V(0, 0.05, 0)).add(V(1.2, 0, 0.8));
    const aim = siti.headPosition().add(V(0, -0.3, 0));
    g.mode = 'play';
    await c.takePhoto('Headline', eye, aim, { allowCancel: false });
    g.objective(null);
  }
  g.mode = 'cutscene';
  hush.stop(2);
  await g.ui.fade(true, 1.4);
  for (const s of speakers) if (c.extras.includes(s)) s.root.visible = false;
  if (c.rumourCrate) c.scene.remove(c.rumourCrate);
}
