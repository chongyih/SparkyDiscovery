import * as THREE from 'three';
import T from './ww2-text.js';
import { markerPose } from '../engine/world.js';
import { capturePhoto } from '../engine/album.js';

// Chapter 1 features agreed with the user: Then & Now opening, the "room for two things" shelter
// choice, a free "Look closer" camera, and optional kindness tasks. Each takes the WW2Chapter `c`.

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const $ = (id) => document.getElementById(id);
const save = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignore */ } };

// ------------------------------------------------------------------ eras (Then & Now)
/** Switch the street between today ('now') and 12 Feb 1942 ('1942'). */
export function setEra(c, era) {
  const now = era === 'now';
  c.level.traverse((o) => {
    const n = o.name || '';
    if (n.startsWith('COL_')) return;
    // The chalkboard A-frame signs (the only M_Now-textured piece) are removed at the user's request.
    if (o.isMesh && [].concat(o.material).some((m) => m.name === 'M_Now')) { o.visible = false; return; }
    if (n.startsWith('NOW_')) o.visible = now;
    else if (/^(PRE_|WAR_)/.test(n)) o.visible = !now;
  });
  for (const f of c.fx) if (f.isSmokeColumn) f.visible = !now;
  if (c.eraUniform) c.eraUniform.value = now ? 1 : 0;
  for (const ch of Object.values(c.cast)) ch.root.visible = !now;
  for (const ch of c.town?.people || []) ch.root.visible = !now;
  c.era = era;
  c.refreshShadows();
}

function thenNowPose(c) {
  if (c.m.THEN_NOW_Camera) return markerPose(c.m.THEN_NOW_Camera);
  const sp = c.marker('SPAWN_Sparky');
  return { pos: sp.pos.clone().add(V(0, 1.0, 0)), yaw: sp.yaw };
}

/**
 * Present-day Telok Ayer: line up Mr. Boon's 1942 photo (a ghost overlay in the viewfinder) with
 * today's street. When it locks, the street becomes 1942. The ghost is rendered from the 1942
 * version of this exact viewpoint, so a correct alignment really does match.
 */
export async function thenNow(c) {
  const g = c.game;
  const X = T.thenNow;
  const pose = thenNowPose(c);
  const pitch = 0.04;
  const dirAt = (yaw, p) => V(Math.sin(yaw) * Math.cos(p), -Math.sin(p), Math.cos(yaw) * Math.cos(p));
  const eye = pose.pos.clone();

  // 1) Render the 1942 photo from the exact viewpoint (hidden behind the sepia fade).
  g.setScene(c.scene);
  c.player.root.visible = false;
  c.setLightingPreset('day');
  const grade = { ...g.renderer.grade };
  Object.assign(g.renderer.grade, { sepia: 0, saturation: 1, vignette: 0, flash: 0 });
  g.rig.viewfinder(eye, eye.clone().add(dirAt(pose.yaw, pitch)), true);
  g.rig.update(0, null, null);
  g.renderer.renderer.shadowMap.needsUpdate = true;
  g.renderer.render(0);
  const ghost = capturePhoto(g.canvas, { size: 512 });
  Object.assign(g.renderer.grade, grade);

  // 2) Today's street.
  setEra(c, 'now');
  c.setLightingPreset('now');
  const amb = g.audio.play('street', { volume: 0.35, loop: true, fadeIn: 2, caption: '[A busy street: chatter, footsteps, a scooter]' });
  // Start turned a little toward the open road (not into a shop front), tilted slightly up.
  const towardRoad = (sgn) => dirAt(pose.yaw + sgn * 0.5, pitch).z * -Math.sign(eye.z || 1);
  const offYaw = towardRoad(1) >= towardRoad(-1) ? 0.5 : -0.5, offPitch = -0.12;
  g.rig.viewfinder(eye, eye.clone().add(dirAt(pose.yaw + offYaw, pitch + offPitch)), true, 1.3);
  Object.assign(g.renderer.grade, { sepia: 0, saturation: 1.05, vignette: 0.35 });
  await g.ui.fade(false, 1.2);
  await c.cardLine(X.card.text);
  await c.lines(X.before, { frame: false });

  // 3) Align. Aim with mouse / drag / stick / WASD.
  g.mode = 'viewfinder';
  g.input.aimKeys = true;
  g.input.requestLock();
  const vf = $('viewfinder');
  const img = $('vf-ghost');
  img.src = ghost;
  img.classList.remove('hidden');
  $('vf-label').textContent = X.hint;
  $('btn-shutter').classList.add('hidden');
  $('btn-vf-cancel').classList.add('hidden');
  const hintEl = $('vf-hint');
  const hintWas = hintEl.innerHTML;
  hintEl.innerHTML = g.input.isTouch ? 'Drag to turn the camera until the old photo matches' : 'Move the mouse (or <kbd>WASD</kbd>) until the old photo matches the street';
  vf.classList.remove('hidden');
  document.body.classList.add('aiming');
  const note = $('vf-note');
  let lockedFor = 0;
  await new Promise((resolve) => {
    const off = g.every((dt) => {
      const v = g.rig.vf;
      const dy = Math.atan2(Math.sin(v.yaw - pose.yaw), Math.cos(v.yaw - pose.yaw));
      const dp = v.pitch - pitch;
      const err = Math.hypot(dy, dp);
      // Magnetic assist: once close, the view eases onto the photo (tilt is corrected first,
      // since it's the hardest to judge by eye).
      if (err < 0.3) {
        const k = Math.min(1, dt * (err < 0.12 ? 4 : 1.6));
        v.yaw -= dy * k;
        v.pitch -= dp * Math.min(1, k * 1.5);
      }
      img.style.opacity = (0.3 + 0.55 * Math.max(0, 1 - err / 0.6)).toFixed(2);
      note.textContent = X.close;
      note.classList.toggle('hidden', !(err < 0.2 && err > 0.09));
      vf.querySelector('.vf-frame').classList.toggle('found', err < 0.1);
      lockedFor = err < 0.09 ? lockedFor + dt : 0;
      if (lockedFor > 0.2) { off(); resolve(); }
    });
  });
  // Locked: stop taking aim input, snap exactly into alignment, then the photo "takes over".
  g.input.aimKeys = false;
  g.input.lookEnabled = false;
  g.mode = 'cutscene';
  g.rig.viewfinder(eye, eye.clone().add(dirAt(pose.yaw, pitch)), true);
  g.audio.play('camera-shutter');
  img.style.opacity = '1';
  note.classList.add('hidden');
  await g.wait(0.5);
  await c.lines(X.locked, { frame: false });
  amb.stop(1.5);
  await g.ui.fade(true, 0.7, 'sepia');
  // Cleanup viewfinder UI.
  g.input.aimKeys = false;
  g.input.lookEnabled = true;
  vf.classList.add('hidden');
  vf.querySelector('.vf-frame').classList.remove('found');
  img.classList.add('hidden');
  $('btn-shutter').classList.remove('hidden');
  $('btn-vf-cancel').classList.remove('hidden');
  hintEl.innerHTML = hintWas;
  document.body.classList.remove('aiming');
  setEra(c, '1942');
  c.setLightingPreset('day');
  c.player.root.visible = true;
  c.cameFromThenNow = { eye, dir: dirAt(pose.yaw, pitch) };
  g.mode = 'cutscene';
}

// ------------------------------------------------------------------ shelter choice
const ICONS = { photo: '🖼️', rice: '🍚', newspaper: '📰', tiffin: '🍱' };

/** "There's room for two things." Remembered for later chapters. */
export async function shelterChoice(c) {
  const g = c.game;
  const X = T.shelterChoice;
  if (!X) return;
  await c.lines(X.lines);
  g.input.releaseLock();
  const ids = await g.ui.pick({ title: X.prompt, sub: `Choose ${X.pick}.`, options: X.options.map((o) => ({ ...o, icon: ICONS[o.id] })), n: X.pick });
  c.heirlooms = ids;
  save('sparky.heirlooms.ww2', ids);
  for (const id of ids) {
    const o = X.options.find((x) => x.id === id);
    if (o?.react) await c.lines(o.react);
  }
  g.input.requestLock();
}

// ------------------------------------------------------------------ Look closer (free camera)
/** Photo spots the free camera can recognise (the SNAP_ markers, not yet photographed). */
export function hotspots(c) {
  const out = [];
  for (const key of ['Poster', 'Bicycle', 'Smoke']) {
    const mk = c.m[`SNAP_${key}`];
    if (!mk || c.game.album.has(`ww2-${key}`)) continue;
    const pose = markerPose(mk);
    out.push({ id: key, pos: c.snapAim(key, pose), note: T.lookCloser?.[key], label: T.snaps[key].title });
  }
  return out;
}

/** Raise the camera anywhere (C / F / right mouse / camera button). */
export async function freeCamera(c) {
  const g = c.game;
  if (g.mode !== 'play' || c.inFreeCamera) return;
  c.inFreeCamera = true;
  const p = c.player;
  const eye = p.headPosition().add(V(0, -0.05, 0));
  const f = g.camera.getWorldDirection(new THREE.Vector3()).setY(0).normalize();
  p.faceTowards(p.root.position.clone().add(f), true);
  g.mode = 'cutscene';
  p.play('Snap', { loop: false });
  c.brownie.visible = true;
  await g.wait(0.35);
  g.mode = 'play';
  const img = await g.snap({ eye, aim: eye.clone().addScaledVector(f, 5), label: 'Look closer', hotspots: hotspots(c), limit: 1.6, onCovered: () => { c.brownie.visible = false; } });
  c.brownie.visible = false;
  const id = g.snapHotspot;
  c.inFreeCamera = false;
  if (!img) return;
  if (id) {
    await c.developPhoto(id, img);
    c.snapIts?.forEach((it) => { if (it.snapKey === id) it.enabled = false; });
  } else {
    // A free photo: the player's own memory of the day.
    c.freeShots = (c.freeShots || 0) + 1;
    await c.developPhoto(null, img, { id: `ww2-free-${Date.now()}`, title: 'Sparky’s own photo', year: '1942', text: 'A moment from February 1942, just as Sparky saw it.' });
  }
}

// ------------------------------------------------------------------ kindness tasks
/** Optional good deeds on the morning street; remembered for later chapters. */
export function setupKindness(c) {
  const g = c.game;
  const list = T.kindness || [];
  c.kindness = c.kindness || new Set();
  const its = [];
  const done = (id) => { c.kindness.add(id); save('sparky.kindness.ww2', [...c.kindness]); g.audio.play('pickup-chime', { volume: 0.5 }); g.ui.toast('A kindness', 'Someone will remember this.', 3.5); };
  for (const k of list) {
    if (k.id === 'bundles') {
      const n = c.m.STREET_Extra_1 ? markerPose(c.m.STREET_Extra_1) : { pos: c.marker('DROP_1').pos.clone().add(V(3, 0, 0.6)), yaw: 0 };
      let who = c.town?.people.find((p) => p.home && p.home.pos.distanceTo(n.pos) < 0.2);
      if (!who) { who = c.town.spawn('womanCn'); who.place(n.pos, n.yaw); }
      who.walkRoute = null;
      who.indicator('chat');
      c.cast.Neighbour = who;
      const it = g.addInteract({
        pos: () => who.root.position, radius: 1.8, priority: 5, label: k.label,
        onUse: async () => {
          g.removeInteract(it);
          who.indicator(null);
          g.mode = 'cutscene';
          await c.lines(k.ask);
          c.player.play('Crouch');
          g.audio.play('paper', { caption: '[Rope pulled tight]' });
          await g.wait(1.1);
          c.player.play('Idle');
          await c.lines(k.thanks);
          done(k.id);
          g.rig.follow(); g.mode = 'play'; g.input.requestLock();
        },
      });
      its.push(it);
    }
    if (k.id === 'water') {
      const hassan = c.cast.Hassan;
      const tap = c.cast.AhMa.root.position.clone();
      const it = g.addInteract({
        pos: () => hassan.root.position, radius: 1.8, priority: 5, label: k.label,
        onUse: async () => {
          g.removeInteract(it);
          g.mode = 'cutscene';
          await c.lines(k.ask);
          g.rig.follow(); g.mode = 'play'; g.input.requestLock();
          g.ui.toast('Optional', 'Fill a cup at the tap by the kopitiam, then bring it to Pak Hassan.', 6);
          const fill = g.addInteract({
            pos: tap, radius: 2.2, priority: 5, label: 'Fill a cup of water',
            onUse: () => {
              g.removeInteract(fill);
              g.audio.play('paper', { volume: 0.4, caption: '[Water trickles into a tin cup]' });
              c.carryingWater = true;
              const give = g.addInteract({
                pos: () => hassan.root.position, radius: 1.8, priority: 6, label: 'Give Pak Hassan the water',
                onUse: async () => {
                  g.removeInteract(give);
                  c.carryingWater = false;
                  g.mode = 'cutscene';
                  await c.lines(k.thanks);
                  done(k.id);
                  g.rig.follow(); g.mode = 'play'; g.input.requestLock();
                },
              });
              its.push(give);
            },
          });
          its.push(fill);
        },
      });
      its.push(it);
    }
  }
  // Tear down when the morning ends (the siren).
  return () => { its.forEach((it) => g.removeInteract(it)); delete c.cast.Neighbour; c.cast.Hassan && c.cast.Hassan.indicator(null); };
}
