import * as THREE from 'three';
import { loadModel } from '../engine/assets.js';
import { markerPose } from '../engine/world.js';
import { Character } from '../engine/character.js';

// Children playing in the void deck's playground (2026): background life behind Mr. Boon and
// Sparky. One goes round and round the slide, one bounces on a spring rider, two play catching
// (tag) on the open rubber floor. Everything is driven by the set's PLAY_* markers
// (tools/build_voiddeck.py); without them the playground simply stays empty.

const V = (x, y, z) => new THREE.Vector3(x, y, z);

// Heights and natural clip speeds (m/s) from tools/build_ww2_npcs.py.
const KIDS = {
  girl: { file: 'npc-kid-girl', height: 1.21, walk: 0.6, run: 1.46 },
  boy: { file: 'npc-kid-boy', height: 1.33, walk: 0.66, run: 1.64 },
  small: { file: 'npc-kid-small', height: 1.089, walk: 0.53, run: 1.25 },
  tween: { file: 'npc-kid-tween', height: 1.424, walk: 0.7, run: 1.79 },
};
// Sit and Ride both put the seat top 0.45 m above the origin, for every body size.
const SEAT_TOP = 0.45;

export function loadKids() {
  return Promise.all(Object.values(KIDS).map((k) => loadModel(k.file)));
}

// How far ahead of the origin the hips sit in a seated clip (measured from the clip itself).
function seatOffset(ch, clip) {
  if (!ch.mixer || !ch.clips[clip]) return { up: SEAT_TOP, fwd: 0 };
  ch.play(clip, { fade: 0 });
  ch.mixer.update(0.5);
  ch.root.updateMatrixWorld(true);
  let hips = null;
  ch.model.traverse((o) => { if (!hips && o.isBone && /hip|pelvis/i.test(o.name)) hips = o; });
  if (!hips) return { up: SEAT_TOP, fwd: 0 };
  const p = ch.root.worldToLocal(hips.getWorldPosition(new THREE.Vector3()));
  return { up: SEAT_TOP, fwd: p.z };
}

export class Playground {
  constructor(scene, markers, gltfs) {
    this.scene = scene;
    this.kids = [];
    this.acts = [];
    this.post = []; // run after the kids' animation has posed their bones
    const m = markers || {};
    if (!m.PLAY_Area) return;
    const byKey = {};
    Object.keys(KIDS).forEach((k, i) => {
      if (!gltfs[i]) return;
      const ch = new Character(`kid-${k}`, gltfs[i], { height: KIDS[k].height, walkSpeed: KIDS[k].walk, runSpeed: KIDS[k].run });
      scene.add(ch.root);
      this.kids.push(ch);
      byKey[k] = ch;
    });
    const area = markerPose(m.PLAY_Area);
    this.floorY = area.pos.y + 0.015; // coloured rubber patches sit 1.5 cm proud of the floor
    if (byKey.girl && m.PLAY_Slide_Top && m.PLAY_Slide_Tower) this.acts.push(this.slide(byKey.girl, m, area));
    if (byKey.small && m.PLAY_Rider_1) this.acts.push(this.rider(byKey.small, m.PLAY_Rider_1));
    if (byKey.boy && byKey.tween) this.acts.push(this.tag(byKey.tween, byKey.boy, area, m));
  }

  update(dt) {
    for (const a of this.acts) a(dt);
    for (const k of this.kids) k.update(dt);
    for (const f of this.post) f(dt);
  }

  /** Climb up the back of the tower, sit, whoosh down, run round, repeat. */
  slide(ch, m, area) {
    const top = markerPose(m.PLAY_Slide_Top);
    const tower = markerPose(m.PLAY_Slide_Tower);
    const sd = m.PLAY_Slide_Top.userData;
    const f = V(Math.sin(top.yaw), 0, Math.cos(top.yaw)); // down the slide
    // She runs back round the inner side, under the bridge (1.23 m clear; she is 1.2 m), leaving
    // the open side to the game of catching.
    const side = V(f.z, 0, -f.x);
    if (side.dot(area.pos.clone().sub(tower.pos)) < 0) side.negate();
    const half = m.PLAY_Slide_Tower.userData.half ?? 0.65;
    const base = top.pos.y - (sd.drop ?? 1.6);
    const surface = (t) => top.pos.clone().addScaledVector(f, (sd.length ?? 2.6) * t)
      .setY(base + (sd.drop ?? 1.6) * (1 - t) ** (sd.curve ?? 1.4) + (sd.exit_height ?? 0.25) * t);
    // Slide pose (legs out in front) if the model has it; Ride otherwise. Sit's dangling legs would
    // sink into the slope.
    const sitClip = ch.clips.Slide ? 'Slide' : ch.clips.Ride ? 'Ride' : 'Sit';
    // Slope of the slide at t (radians below horizontal).
    const slope = (t) => Math.atan(((sd.drop ?? 1.6) * (sd.curve ?? 1.4) * (1 - t) ** ((sd.curve ?? 1.4) - 1) - (sd.exit_height ?? 0.25)) / (sd.length ?? 2.6));
    const seat = seatOffset(ch, sitClip);
    const Y = this.floorY;
    const behind = tower.pos.clone().addScaledVector(f, -(half + 0.45)).setY(Y);
    const onEdge = tower.pos.clone().addScaledVector(f, -(half - 0.2)).setY(top.pos.y);
    const atTop = top.pos.clone().addScaledVector(f, -0.3).setY(top.pos.y);
    const bottom = surface(1);
    // Run-round path from the slide's foot back behind the tower, on the open (outer) side.
    const out = side.clone().multiplyScalar(half + 0.4);
    const loop = [
      bottom.clone().addScaledVector(f, 0.25).add(out).setY(Y), // the slide ends ~0.35 m from the kerb
      tower.pos.clone().addScaledVector(f, half + 0.6).add(out).setY(Y),
      tower.pos.clone().addScaledVector(f, -(half + 0.2)).add(out).setY(Y),
      behind,
    ];
    ch.place(behind, top.yaw);
    let state = 'climb', t = 0, slideT = 0, legTilt = 0;
    const from = new THREE.Vector3();
    // After the clip poses her, swing both thighs down (about her own left-right axis) so her legs
    // lie along the slope while her body stays upright.
    const thighs = ['thighL', 'thighR'].map((n) => ch.findNode?.(n)).filter(Boolean);
    const axis = new THREE.Vector3(), q = new THREE.Quaternion(), pq = new THREE.Quaternion();
    // The mixer only rewrites a bone when the clip's value changes, so a held pose would keep the
    // previous frame's tilt and it would pile up. Remember the clip's pose and put it back before
    // the next animation update (see the start of the per-frame function below).
    const clipPose = thighs.map(() => new THREE.Quaternion());
    let tilted = false;
    const untilt = () => { if (tilted) thighs.forEach((b, i) => b.quaternion.copy(clipPose[i])); tilted = false; };
    this.post.push((dt) => {
      const want = state === 'sit' ? slope(0.03) : state === 'slide' ? slope(slideT) : 0;
      legTilt += (want - legTilt) * Math.min(1, dt * 12);
      if (legTilt < 0.01) return;
      ch.root.updateMatrixWorld(true); // this frame's pose, not last frame's
      axis.set(1, 0, 0).applyQuaternion(ch.root.getWorldQuaternion(q));
      tilted = true;
      for (const [i, b] of thighs.entries()) {
        clipPose[i].copy(b.quaternion);
        b.parent.getWorldQuaternion(pq);
        q.setFromAxisAngle(axis, legTilt);
        b.quaternion.premultiply(pq.clone().invert().multiply(q).multiply(pq));
      }
    });
    // Face down the slide from the climb to the landing. (moveTo leaves a turn target behind that
    // would otherwise keep swinging her back to the direction she last ran in — sideways.)
    const go = (s) => { state = s; t = 0; from.copy(ch.root.position); if (s !== 'run') ch.targetYaw = top.yaw; };
    go('climb');
    ch.play('Walk');
    return (dt) => {
      untilt();
      t += dt;
      const p = ch.root.position;
      if (state === 'climb') { // up the ladder at the back
        const k = Math.min(1, t / 1.3);
        p.lerpVectors(from, onEdge, k);
        p.y = THREE.MathUtils.lerp(from.y, onEdge.y, Math.min(1, k * 1.25));
        if (k >= 1) { go('cross'); }
      } else if (state === 'cross') {
        const k = Math.min(1, t / 0.7);
        p.lerpVectors(from, atTop, k);
        if (k >= 1) { go('sit'); ch.play(sitClip, { fade: 0.2 }); }
      } else if (state === 'sit') {
        const s0 = surface(0.03);
        p.lerpVectors(from, s0.clone().addScaledVector(f, -seat.fwd).setY(s0.y - seat.up), Math.min(1, t / 0.4));
        if (t > 0.8) go('slide');
      } else if (state === 'slide') {
        const k = Math.min(1, (t / 1.5) ** 1.35); // speeds up on the way down
        slideT = 0.03 + 0.97 * k;
        const s = surface(slideT);
        p.copy(s).addScaledVector(f, -seat.fwd).setY(s.y - seat.up);
        if (k >= 1) { go('land'); }
      } else if (state === 'land') { // hop off the end
        const k = Math.min(1, t / 0.35);
        const end = bottom.clone().addScaledVector(f, 0.25).setY(Y);
        p.lerpVectors(from, end, k);
        if (k >= 1) {
          go('pause');
          ch.play(Math.random() < 0.5 ? 'Cheer' : 'Idle', { loop: false, then: 'Idle' });
        }
      } else if (state === 'pause') {
        if (t > 1.3) {
          state = 'run';
          ch.moveTo(loop.map((q) => q.clone()), { speed: ch.runSpeed * 1.05, clip: 'Run' }).then(() => { go('climb'); ch.play('Walk'); });
        }
      }
    };
  }

  /** Rock on a spring rider, facing the deck. */
  rider(ch, marker) {
    const pose = markerPose(marker);
    const clip = ch.clips.Ride ? 'Ride' : 'Sit';
    // Ride is built around the rider's spring: the origin goes straight onto the marker.
    const at = pose.pos.clone();
    at.y += (marker.userData.seat_height ?? 0.774) - SEAT_TOP;
    ch.place(at, pose.yaw);
    ch.play(clip);
    // The rider itself is static, so the kid stays on the seat; the Ride clip rocks the body.
    return () => {};
  }

  /** Catching: the chaser runs the runner down, tags them, they swap and run the other way. */
  tag(a, b, area, m) {
    // An oval on the open side of the play area, clear of the towers, slide and riders.
    const tower = m.PLAY_Slide_Tower ? markerPose(m.PLAY_Slide_Tower) : null;
    const ud = m.PLAY_Area.userData;
    const hx = ud.half_x ?? 5.5, hz = ud.half_y ?? 3.8;
    const edge = area.pos.x + hx - 0.45;
    const inner = tower ? tower.pos.x + (m.PLAY_Slide_Tower.userData.half ?? 0.65) + 0.5 : area.pos.x + 0.5;
    const c = V((edge + inner) / 2, this.floorY, area.pos.z);
    const rx = Math.max(0.8, (edge - inner) / 2), rz = hz - 0.6;
    const at = (th) => V(c.x + rx * Math.cos(th), c.y, c.z + rz * Math.sin(th));
    const S = { runner: a, chaser: b, th: { [a.name]: 0, [b.name]: -1.9 }, dir: 1, pause: 0, wait: 0 };
    for (const k of [a, b]) { k.place(at(S.th[k.name]), 0); k.play('Run'); }
    const speed = { runner: 1.6, chaser: 1.8 };
    return (dt) => {
      if (S.pause > 0) { // just caught: a moment of shrieking, then swap
        S.pause -= dt;
        if (S.pause <= 0) {
          [S.runner, S.chaser] = [S.chaser, S.runner];
          S.dir *= -1;
          S.wait = 0.9; // the new chaser counts to three
          S.runner.play('Run'); S.chaser.play('Idle');
        }
        return;
      }
      for (const role of ['runner', 'chaser']) {
        const k = S[role];
        if (role === 'chaser' && S.wait > 0) { S.wait -= dt; if (S.wait <= 0) k.play('Run'); continue; }
        const th = S.th[k.name];
        const sp = Math.hypot(rx * Math.sin(th), rz * Math.cos(th));
        const nth = th + (S.dir * speed[role] * dt) / Math.max(0.3, sp);
        S.th[k.name] = nth;
        const p = at(nth), d = p.clone().sub(k.root.position);
        k.root.position.copy(p);
        if (d.lengthSq() > 1e-6) { k.yaw = Math.atan2(d.x, d.z); k.root.rotation.y = k.yaw; }
        k.setSpeed(speed[role] / k.runSpeed);
      }
      // Caught? (chaser within ~0.7 m behind the runner)
      const gap = S.runner.root.position.distanceTo(S.chaser.root.position);
      if (S.wait <= 0 && gap < 0.7) {
        S.pause = 1.6;
        S.chaser.play(S.chaser.clips.Jump ? 'Jump' : 'Cheer');
        S.runner.play('Idle');
        S.runner.faceTowards(S.chaser.root.position, true);
        S.chaser.faceTowards(S.runner.root.position, true);
      }
    };
  }
}
