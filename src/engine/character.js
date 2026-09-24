import * as THREE from 'three';
import * as SkeletonUtils from 'three/examples/jsm/utils/SkeletonUtils.js';
import { radialTexture } from './assets.js';
import { tier } from './settings.js';

const tmp = new THREE.Vector3();

// Speech-bubble indicators over NPCs: 'chat' (… optional) and 'important' (! needed for the objective).
const bubbleTex = {};
function bubbleTexture(kind) {
  if (bubbleTex[kind]) return bubbleTex[kind];
  const s = 128;
  const c = document.createElement('canvas');
  c.width = c.height = s;
  const g = c.getContext('2d');
  const important = kind === 'important';
  g.fillStyle = important ? '#ffd77a' : '#fff8ea';
  g.strokeStyle = 'rgba(27,23,18,0.85)';
  g.lineWidth = 6;
  g.beginPath();
  g.ellipse(64, 54, 50, 40, 0, 0, Math.PI * 2);
  g.moveTo(46, 88); g.lineTo(38, 116); g.lineTo(66, 92);
  g.fill(); g.stroke();
  g.fillStyle = '#1b1712';
  if (important) {
    g.font = 'bold 64px Georgia, serif'; g.textAlign = 'center'; g.textBaseline = 'middle';
    g.fillText('!', 64, 57);
  } else {
    for (const x of [40, 64, 88]) { g.beginPath(); g.arc(x, 56, 8, 0, Math.PI * 2); g.fill(); }
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return (bubbleTex[kind] = t);
}

export function dampAngle(a, b, lambda, dt) {
  let d = ((b - a + Math.PI) % (Math.PI * 2)) - Math.PI;
  if (d < -Math.PI) d += Math.PI * 2;
  return a + d * (1 - Math.exp(-lambda * dt));
}

/** Soft circular contact shadow — grounds characters on every tier. */
export function blobShadow(radius = 0.45, opacity = 0.45) {
  const m = new THREE.Mesh(
    new THREE.PlaneGeometry(radius * 2, radius * 2),
    new THREE.MeshBasicMaterial({ map: radialTexture('blob', 'rgba(0,0,0,1)', 'rgba(0,0,0,0)'), transparent: true, opacity, depthWrite: false }),
  );
  m.rotation.x = -Math.PI / 2;
  m.position.y = 0.02;
  m.renderOrder = 1;
  return m;
}

/**
 * Stylised stand-in person used until the Blender NPCs arrive (or if a GLB fails to load).
 * Built from a few primitives with simple procedural limbs so the game stays playable.
 */
function placeholderPerson({ height = 1.6, shirt = '#c9b99a', pants = '#3b3a36', skin = '#c8936a', hair = '#1d1a17', hat = null }) {
  const g = new THREE.Group();
  const s = height / 1.6;
  const mat = (c) => new THREE.MeshStandardMaterial({ color: c, roughness: 0.85 });
  const headR = 0.2 * s;
  const body = new THREE.Mesh(new THREE.CapsuleGeometry(0.2 * s, 0.42 * s, 4, 10), mat(shirt));
  body.position.y = 0.95 * s;
  const head = new THREE.Mesh(new THREE.SphereGeometry(headR, 16, 12), mat(skin));
  head.position.y = 1.42 * s;
  const hairM = new THREE.Mesh(new THREE.SphereGeometry(headR * 1.04, 16, 10, 0, Math.PI * 2, 0, Math.PI * 0.5), mat(hair));
  hairM.position.copy(head.position);
  const legs = [-1, 1].map((side) => {
    const pivot = new THREE.Group();
    pivot.position.set(0.09 * s * side, 0.62 * s, 0);
    const leg = new THREE.Mesh(new THREE.CapsuleGeometry(0.075 * s, 0.45 * s, 3, 8), mat(pants));
    leg.position.y = -0.3 * s;
    pivot.add(leg);
    return pivot;
  });
  const arms = [-1, 1].map((side) => {
    const pivot = new THREE.Group();
    pivot.position.set(0.26 * s * side, 1.15 * s, 0);
    const arm = new THREE.Mesh(new THREE.CapsuleGeometry(0.06 * s, 0.38 * s, 3, 8), mat(shirt));
    arm.position.y = -0.24 * s;
    pivot.add(arm);
    return pivot;
  });
  const eyes = [-1, 1].map((side) => {
    const e = new THREE.Mesh(new THREE.SphereGeometry(0.022 * s, 8, 6), mat('#111'));
    e.position.set(0.07 * s * side, 1.45 * s, headR * 0.92);
    return e;
  });
  g.add(body, head, hairM, ...legs, ...arms, ...eyes);
  if (hat) {
    const h = new THREE.Mesh(new THREE.CylinderGeometry(headR * 1.25, headR * 1.3, 0.08 * s, 16), mat(hat));
    h.position.y = 1.58 * s;
    g.add(h);
  }
  g.traverse((o) => { if (o.isMesh) { o.castShadow = true; } });
  g.userData.procedural = { legs, arms, body, head };
  return g;
}

/**
 * Animated character (NPC or player). Wraps a glTF scene with an AnimationMixer and provides
 * clip crossfading, locomotion (moveTo / follow) and facing.
 */
export class Character {
  static showIndicators = true;

  constructor(name, gltf, opts = {}) {
    this.name = name;
    this.root = new THREE.Group();
    this.root.name = `char_${name}`;
    this.height = opts.height ?? 1.6;
    this.radius = opts.radius ?? 0.28;
    this.walkSpeed = opts.walkSpeed ?? 1.4;
    this.runSpeed = opts.runSpeed ?? 3.4;
    this.walkClip = opts.walkClip ?? 'Walk';
    this.idleClip = opts.idleClip ?? 'Idle';
    this.clips = {};
    this.actions = {};
    this.current = null;
    this.yaw = 0;
    this.targetYaw = null;
    this.velocity = new THREE.Vector3();
    this.path = null;
    this.followTarget = null;
    this.frozen = false;
    this.animTime = 0;
    this.collider = { pos: this.root.position, radius: this.radius * 0.9, enabled: true };

    if (gltf) {
      this.model = SkeletonUtils.clone(gltf.scene);
      this.normalize(opts.fitHeight !== false);
      this.mixer = new THREE.AnimationMixer(this.model);
      for (const clip of gltf.animations) this.clips[clip.name] = clip;
    } else {
      this.model = placeholderPerson({ height: this.height, ...(opts.placeholder || {}) });
      this.procedural = this.model.userData.procedural;
    }
    this.model.traverse((o) => {
      if (o.isMesh) {
        o.castShadow = true;
        o.receiveShadow = false;
        o.frustumCulled = !o.isSkinnedMesh; // skinned bounds are unreliable once animated
        if (o.material?.map) o.material.map.anisotropy = 4;
      }
    });
    this.root.add(this.model);
    this.shadow = blobShadow(this.radius * 1.7, tier().shadows ? 0.3 : 0.5);
    this.root.add(this.shadow);
    this.play(this.idleClip);
  }

  /** Scale the model so its bind-pose height matches `this.height`; feet on y=0. */
  normalize(fit) {
    const box = new THREE.Box3().setFromObject(this.model, true);
    const h = box.max.y - box.min.y;
    if (fit && h > 0.01 && Math.abs(h - this.height) / this.height > 0.2) { // only rescale clearly mis-sized models
      this.model.scale.multiplyScalar(this.height / h);
      box.setFromObject(this.model, true);
    }
    this.model.position.y -= box.min.y;
  }

  has(clip) { return !!this.clips[clip] || !!this.procedural; }

  /** Show a floating speech bubble ('chat' | 'important') or remove it (null). */
  indicator(kind) {
    this.indicatorKind = kind;
    if (!kind) { if (this.bubble) this.bubble.visible = false; return; }
    if (!this.bubble) {
      this.bubble = new THREE.Sprite(new THREE.SpriteMaterial({ map: bubbleTexture(kind), depthWrite: false, fog: false, transparent: true }));
      this.bubble.scale.set(0.38, 0.38, 1);
      this.bubble.renderOrder = 6;
      this.root.add(this.bubble);
    }
    this.bubble.material.map = bubbleTexture(kind);
    this.bubble.visible = true;
  }

  /**
   * Crossfade to a clip. opts: { loop=true, fade=0.25, speed=1, clamp=true, then='Idle' }.
   * Returns a promise that resolves when a one-shot finishes.
   */
  play(name, opts = {}) {
    const { loop = true, fade = 0.25, speed = 1 } = opts;
    this.currentName = name;
    if (this.procedural) { this.procClip = name; return Promise.resolve(); }
    const clip = this.clips[name];
    if (!clip) return Promise.resolve();
    let action = this.actions[name];
    if (!action) action = this.actions[name] = this.mixer.clipAction(clip);
    action.setEffectiveTimeScale(speed);
    if (this.current === action && loop) return Promise.resolve();
    action.reset();
    action.setLoop(loop ? THREE.LoopRepeat : THREE.LoopOnce, loop ? Infinity : 1);
    action.clampWhenFinished = !loop;
    action.enabled = true;
    action.setEffectiveWeight(1);
    if (this.current && this.current !== action) action.crossFadeFrom(this.current, fade, false);
    action.play();
    this.current = action;
    if (loop) return Promise.resolve();
    return new Promise((resolve) => {
      const onDone = (e) => {
        if (e.action !== action) return;
        this.mixer.removeEventListener('finished', onDone);
        if (opts.then !== null && this.current === action) this.play(opts.then ?? this.idleClip, { fade: 0.3 });
        resolve();
      };
      this.mixer.addEventListener('finished', onDone);
    });
  }

  setSpeed(scale) { if (this.current) this.current.setEffectiveTimeScale(scale); }

  place(pos, yaw = this.yaw) {
    this.root.position.copy(pos);
    this.yaw = yaw;
    this.root.rotation.y = yaw;
    this.targetYaw = null;
  }

  faceTowards(p, instant = false) {
    const y = Math.atan2(p.x - this.root.position.x, p.z - this.root.position.z);
    if (instant) { this.yaw = y; this.root.rotation.y = y; this.targetYaw = null; } else this.targetYaw = y;
  }

  /** Walk along waypoints (Vector3[]). Resolves on arrival. */
  moveTo(points, { speed = this.walkSpeed, clip = null, arrive = 0.15 } = {}) {
    const list = Array.isArray(points) ? points.map((p) => p.clone()) : [points.clone()];
    // Pick Walk or Run from the requested speed unless a clip is forced.
    if (!clip) clip = speed > this.walkSpeed * 1.8 && this.clips.Run && this.walkClip === 'Walk' ? 'Run' : this.walkClip;
    this.followTarget = null;
    return new Promise((resolve) => {
      this.path = { list, speed, clip, arrive, resolve };
      this.play(clip);
    });
  }

  stop() {
    if (this.path) { const r = this.path.resolve; this.path = null; r(); }
    this.followTarget = null;
    this.play(this.idleClip);
  }

  /** Trail behind another character (or anything with .root.position). */
  follow(target, { gap = 1.2, speed = this.runSpeed, clip = null, slot = 0 } = {}) {
    this.path = null;
    this.followTarget = { target, gap: gap + slot * 0.9, speed, clip, slot };
  }

  update(dt, world) {
    this.collider.enabled = this.root.visible;
    if (this.frozen) { this.mixer?.update(0); return; }
    const pos = this.root.position;
    let moving = false;
    let moveSpeed = 0;
    if (this.path) {
      const p = this.path;
      const tgt = p.list[0];
      tmp.set(tgt.x - pos.x, 0, tgt.z - pos.z);
      const d = tmp.length();
      // Stuck guard: if we stop closing in on the waypoint (snagged on a pillar), hop onto it.
      if (p.bestD === undefined || d < p.bestD - 0.05) { p.bestD = d; p.stall = 0; } else p.stall = (p.stall || 0) + dt;
      // NPCs hop onto the waypoint; the player (scripted) just gives up that waypoint.
      if (p.stall > 1.2 && !this.isPlayer) { pos.x = tgt.x; pos.z = tgt.z; }
      if (d < p.arrive || p.stall > 1.2) {
        p.bestD = undefined;
        p.list.shift();
        if (!p.list.length) { this.path = null; this.play(this.idleClip); p.resolve(); }
      } else {
        const step = Math.min(d, p.speed * dt);
        pos.addScaledVector(tmp.normalize(), step);
        this.targetYaw = Math.atan2(tmp.x, tmp.z);
        moving = true; moveSpeed = p.speed;
        // Match cadence to speed so feet don't slide (e.g. a Walk clip used at running speed).
        this.setSpeed(THREE.MathUtils.clamp(p.speed / (p.clip === 'Run' ? this.runSpeed : this.walkSpeed), 0.6, 1.8));
      }
    } else if (this.followTarget) {
      const f = this.followTarget;
      const tp = f.target.root.position;
      tmp.set(tp.x - pos.x, 0, tp.z - pos.z);
      const d = tmp.length();
      if (d > f.gap) {
        const catchUp = d > f.gap + 3 ? 1.25 : 1;
        const sp = Math.min(f.speed * catchUp, (d - f.gap) * 3 + 0.6);
        pos.addScaledVector(tmp.normalize(), Math.min(sp * dt, d - f.gap));
        this.targetYaw = Math.atan2(tmp.x, tmp.z);
        moving = true; moveSpeed = sp;
      }
      // Anti-stuck: if we're lagging but not making progress (snagged on a pillar or rubble),
      // quietly reappear just behind the leader. Nobody can be lost; no soft-locks.
      const lagging = d > f.gap + 2.2;
      const progress = f.lastD === undefined ? 1 : f.lastD - d;
      f.lastD = d;
      f.stuck = lagging && progress < dt * 0.25 ? (f.stuck || 0) + dt : (d > f.gap + 12 ? (f.stuck || 0) + dt : 0);
      if (f.stuck > 2.2) {
        const ty = f.target.yaw ?? 0;
        pos.set(tp.x - Math.sin(ty) * (f.gap + 0.3), tp.y, tp.z - Math.cos(ty) * (f.gap + 0.3));
        f.stuck = 0; f.lastD = undefined;
      }
      const clip = f.clip || (this.walkClip === 'Walk' && moveSpeed > this.walkSpeed * 1.3 && this.clips.Run ? 'Run' : this.walkClip);
      if (moving) { if (this.currentName !== clip) this.play(clip); this.setSpeed(THREE.MathUtils.clamp(moveSpeed / (clip === 'Run' ? this.runSpeed : this.walkSpeed), 0.6, 1.8)); }
      else if (this.currentName === clip || this.currentName === this.walkClip || this.currentName === 'Run') this.play(this.idleClip);
    }
    if (world && (moving || this._needsGround !== false)) {
      if (moving) world.resolve(pos, this.radius, this.height, 0.35, this.collider);
      // Never sink below street level (open monsoon drains would swallow their legs).
      const gy = world.groundHeight(pos.x, pos.y, pos.z);
      if (gy !== null) pos.y += (Math.max(0, gy) - pos.y) * Math.min(1, dt * 14);
      this._needsGround = moving;
    }
    if (this.targetYaw !== null) {
      this.yaw = dampAngle(this.yaw, this.targetYaw, 10, dt);
      this.root.rotation.y = this.yaw;
    }
    this.mixer?.update(dt);
    if (this.procedural) this.updateProcedural(dt, moving);
    if (this.bubble) {
      this.bubble.visible = !!this.indicatorKind && Character.showIndicators;
      this.bubble.position.y = this.height + 0.32 + Math.sin(performance.now() / 320 + this.height * 7) * 0.04;
    }
  }

  updateProcedural(dt, moving) {
    const P = this.procedural;
    this.animTime += dt * (moving ? 9 : 2);
    const t = this.animTime;
    const clip = this.procClip;
    const walk = moving || clip === 'Walk' || clip === 'Run' || clip === 'Limp';
    const sw = walk ? Math.sin(t) * 0.6 : 0;
    P.legs[0].rotation.x = sw; P.legs[1].rotation.x = -sw;
    P.arms[0].rotation.x = -sw * 0.8; P.arms[1].rotation.x = sw * 0.8;
    P.arms[0].rotation.z = 0; P.arms[1].rotation.z = 0;
    P.body.position.y = 0.95 * (this.height / 1.6) + (walk ? Math.abs(Math.sin(t)) * 0.04 : Math.sin(t) * 0.01);
    if (clip === 'Talk' || clip === 'Beckon') { P.arms[1].rotation.x = -1.2 + Math.sin(t * 2) * 0.35; }
    if (clip === 'Wave' || clip === 'Cheer') { P.arms[1].rotation.z = 2.6 + Math.sin(t * 4) * 0.3; }
    if (clip === 'Cower' || clip === 'Crouch') {
      P.arms[0].rotation.x = -2.8; P.arms[1].rotation.x = -2.8;
      this.model.scale.y = THREE.MathUtils.damp(this.model.scale.y, 0.7, 8, dt);
    } else this.model.scale.y = THREE.MathUtils.damp(this.model.scale.y, 1, 8, dt);
  }

  /** World position of the character's head (for speech anchors / camera framing). */
  headPosition(out = new THREE.Vector3()) {
    return out.copy(this.root.position).setY(this.root.position.y + this.height * 0.92);
  }

  /** Find a bone/node by (partial) name in the model. */
  findNode(name) {
    let hit = null;
    this.model.traverse((o) => { if (!hit && o.name && o.name.toLowerCase().includes(name.toLowerCase())) hit = o; });
    return hit;
  }
}
