import * as THREE from 'three';
import { settings } from './settings.js';

const tmp = new THREE.Vector3();
const tmp2 = new THREE.Vector3();
const dirV = new THREE.Vector3();

/**
 * Third-person orbit camera with collision, auto-follow, cinematic shots and a viewfinder mode.
 * yaw = heading of the camera's forward vector in XZ (forward = (sin yaw, 0, cos yaw)).
 */
export class CameraRig {
  constructor(camera) {
    this.camera = camera;
    this.mode = 'follow';
    this.yaw = 0;
    this.pitch = 0.28;
    this.distance = 3.4;
    this.targetDistance = 3.4;
    this.minDist = 1.6;
    this.maxDist = 5.5;
    this.target = new THREE.Vector3();
    this.lookAt = new THREE.Vector3();
    this.shot = { pos: new THREE.Vector3(), look: new THREE.Vector3(), lambda: 3 };
    this.shake = 0;
    this.shakeT = 0;
    this.autoFollow = true;
    this.fov = 55;
    this.targetFov = 55;
    this.subject = null;
    this.vf = { yaw: 0, pitch: 0, pos: new THREE.Vector3() };
  }

  setSubject(ch) { this.subject = ch; this.snapBehind(); }

  snapBehind() {
    if (!this.subject) return;
    this.yaw = this.subject.yaw;
    this.subject.headPosition(this.target).y -= 0.15;
    this.placeFollow(true);
  }

  /** Back to the third-person camera, continuing from wherever the camera is looking now. */
  follow() {
    if (this.mode !== 'follow' && this.subject) {
      const f = this.camera.getWorldDirection(tmp);
      this.yaw = Math.atan2(f.x, f.z);
      this.pitch = THREE.MathUtils.clamp(-Math.asin(THREE.MathUtils.clamp(f.y, -1, 1)) + 0.1, 0.05, 0.8);
      this.subject.headPosition(this.target).y -= 0.15;
      // No room behind Sparky from this angle (e.g. just talked across a counter)? Swing round
      // behind the way he's facing instead.
      if (this.world) {
        const cp = Math.cos(this.pitch);
        dirV.set(-Math.sin(this.yaw) * cp, Math.sin(this.pitch), -Math.cos(this.yaw) * cp);
        if (this.world.rayDistance(this.target, dirV, 3) < 1.6) { this.yaw = this.subject.yaw; this.pitch = 0.35; }
      }
      this.currentDist = Math.max(0.6, this.camera.position.distanceTo(this.target));
    }
    this.mode = 'follow';
    this.targetFov = 55;
  }

  /** Pull a camera position in toward `look` so it never sits inside geometry. */
  safePos(pos, look, margin = 0.3) {
    if (!this.world) return pos;
    dirV.copy(pos).sub(look);
    const len = dirV.length();
    if (len < 1e-4) return pos;
    dirV.divideScalar(len);
    const hit = this.world.rayDistance(look, dirV, len + margin);
    if (hit < len + margin) pos.copy(look).addScaledVector(dirV, Math.max(0.35, hit - margin));
    return pos;
  }

  /** Is the straight line between two points clear of level geometry? */
  clear(a, b) {
    if (!this.world) return true;
    dirV.copy(b).sub(a);
    const len = dirV.length();
    return this.world.rayDistance(a, dirV.divideScalar(len), len) >= len - 0.05;
  }

  /**
   * Cinematic shot: move to `pos`, look at `look`. lambda = smoothing speed.
   * Positions are collision-corrected; if the glide would pass through a wall, it cuts instead.
   */
  cut(pos, look, lambda = 3, instant = false) {
    this.mode = 'shot';
    const p = this.safePos(pos.clone(), look);
    if (!instant && !this.clear(this.camera.position, p)) instant = true;
    this.shot.pos.copy(p);
    this.shot.look.copy(look);
    this.shot.lambda = lambda;
    if (instant) { this.camera.position.copy(p); this.lookAt.copy(look); this.camera.lookAt(look); }
  }

  /** Frame two characters in an over-the-shoulder two-shot, from the side the camera is already on. */
  frameTwo(a, b, { side = 0, dist = null, height = 0.2, lambda = 3, instant = true } = {}) {
    const pa = a.headPosition(new THREE.Vector3());
    const pb = b.headPosition(new THREE.Vector3());
    const mid = pa.clone().lerp(pb, 0.5);
    const ab = pb.clone().sub(pa).setY(0);
    const sep = Math.max(0.8, ab.length());
    const perp = new THREE.Vector3(-ab.z, 0, ab.x).normalize();
    const abn = ab.clone().normalize();
    const d = dist ?? sep * 1.25 + 1.6;
    const look = mid.clone();
    look.y -= 0.12;
    // Try both sides (and a higher over-the-shoulder angle); keep the candidate that sees both
    // heads with the most room. Prefer the side the camera is already on, for continuity.
    const current = perp.dot(tmp.copy(this.camera.position).sub(mid)) >= 0 ? 1 : -1;
    const sides = side ? [side] : [current, -current];
    let best = null;
    const consider = (pos, bonus = 0) => {
      this.safePos(pos, look);
      const seesA = this.clear(pos, pa), seesB = this.clear(pos, pb);
      const room = Math.min(pos.distanceTo(look), d);
      const score = (seesA && seesB ? 3 : (seesA || seesB ? 1 : 0)) + room / (d * 4) + bonus;
      if (!best || score > best.score) best = { pos, score };
    };
    // Side-on two-shots (good in the open road)…
    for (const sd of sides) {
      for (const [dk, hk] of [[1, 0], [0.8, 0.5], [0.6, 1.0]]) {
        const pos = mid.clone().addScaledVector(perp, sd * d * dk).addScaledVector(abn, -0.35 * sep);
        pos.y = Math.min(pa.y, pb.y) + height + hk;
        consider(pos, sd === current ? 0.05 : 0);
      }
    }
    // …and over-the-shoulder shots along the line between them (good in narrow five-foot ways,
    // where side-on shots hit pillars or shop walls). Behind `a`, looking at `b`'s face, first.
    for (const [from, to, bonus] of [[pa, pb, 0.08], [pb, pa, 0.02]]) {
      const back = from.clone().sub(to).setY(0).normalize();
      for (const [lat, up, dist] of [[0.45, 0.35, 1.5], [-0.45, 0.35, 1.5], [0.35, 0.9, 1.3], [-0.35, 0.9, 1.3]]) {
        const pos = from.clone().addScaledVector(back, dist).addScaledVector(perp, lat).add(new THREE.Vector3(0, up + height, 0));
        consider(pos, bonus);
      }
    }
    this.cut(best.pos, look, lambda, instant);
  }

  /** Close shot of one character from the front. */
  frameOne(ch, { dist = 2.2, height = 0.05, angle = 0.35, lambda = 3 } = {}) {
    const head = ch.headPosition(new THREE.Vector3());
    const yaw = ch.yaw + angle;
    const pos = head.clone().add(new THREE.Vector3(Math.sin(yaw) * dist, height, Math.cos(yaw) * dist));
    this.cut(pos, head.clone().setY(head.y - 0.08), lambda);
  }

  /** First-person viewfinder from `eye`, initially aimed at `aim`. */
  viewfinder(eye, aim, instant = false, limit = 0.9) {
    this.mode = 'viewfinder';
    this.vf.limit = limit;
    this.vf.pos.copy(eye);
    if (instant) { this.camera.position.copy(eye); this.camera.fov = this.targetFov = 45; this.camera.updateProjectionMatrix(); }
    dirV.copy(aim).sub(eye);
    this.vf.yaw = Math.atan2(dirV.x, dirV.z);
    this.vf.pitch = -Math.atan2(dirV.y, Math.hypot(dirV.x, dirV.z));
    this.vf.baseYaw = this.vf.yaw;
    this.vf.basePitch = this.vf.pitch;
    this.targetFov = 45;
  }

  addShake(amount) { if (!settings.reduceMotion) this.shake = Math.min(1.2, this.shake + amount); else this.shake = Math.min(0.15, this.shake + amount * 0.1); }

  zoom(sign) { this.targetDistance = THREE.MathUtils.clamp(this.targetDistance + sign * 0.4, this.minDist, this.maxDist); }

  placeFollow(instant, world) {
    const cp = Math.cos(this.pitch);
    dirV.set(-Math.sin(this.yaw) * cp, Math.sin(this.pitch), -Math.cos(this.yaw) * cp);
    let d = this.distance;
    if (world) {
      let hit = world.rayDistance(this.target, dirV, d + 0.3);
      // Boxed in (sandbags, counters, walls)? Lift the camera and look down over the obstacle.
      if (hit < 1.4) {
        const lift = Math.min(1.0, this.pitch + 0.55);
        const cl = Math.cos(lift);
        tmp2.set(-Math.sin(this.yaw) * cl, Math.sin(lift), -Math.cos(this.yaw) * cl);
        const hit2 = world.rayDistance(this.target, tmp2, d + 0.3);
        if (hit2 > hit + 0.4) { dirV.copy(tmp2); hit = hit2; this.pitch += (lift - this.pitch) * Math.min(1, (this._dt || 0.016) * 3); }
      }
      d = Math.max(0.6, Math.min(d, hit - 0.3));
    }
    this.currentDist = instant ? d : THREE.MathUtils.damp(this.currentDist ?? d, d, d < (this.currentDist ?? d) ? 30 : 4, this._dt || 0.016);
    tmp.copy(this.target).addScaledVector(dirV, this.currentDist);
    this.camera.position.copy(tmp);
    this.lookAt.copy(this.target);
    this.camera.lookAt(this.lookAt);
  }

  update(dt, input, world) {
    this._dt = dt;
    const look = input ? input.consumeLook() : { x: 0, y: 0 };
    const sens = input?.isTouch ? 0.0042 : 0.0026;
    if (this.mode === 'follow' && this.subject) {
      this.yaw -= look.x * sens;
      this.pitch = THREE.MathUtils.clamp(this.pitch + look.y * sens, -0.25, 1.05);
      // Gentle auto-follow behind the direction of travel when the player isn't steering the camera.
      const idleLook = performance.now() - (input?.lastLookTime ?? 0) > 1400;
      if (this.autoFollow && idleLook && this.subject.speedNow > 0.6 && input && Math.abs(input.move.y) > 0.2) {
        let d = ((this.subject.yaw - this.yaw + Math.PI) % (Math.PI * 2)) - Math.PI;
        if (d < -Math.PI) d += Math.PI * 2;
        if (Math.abs(d) < 2.4) this.yaw += d * (1 - Math.exp(-1.2 * dt)) * Math.min(1, this.subject.speedNow / 2);
      }
      this.distance = THREE.MathUtils.damp(this.distance, this.targetDistance, 6, dt);
      this.subject.headPosition(tmp2).y -= 0.15;
      this.target.x = THREE.MathUtils.damp(this.target.x, tmp2.x, 12, dt);
      this.target.z = THREE.MathUtils.damp(this.target.z, tmp2.z, 12, dt);
      this.target.y = THREE.MathUtils.damp(this.target.y, tmp2.y, 6, dt);
      this.placeFollow(false, world);
    } else if (this.mode === 'shot') {
      const k = 1 - Math.exp(-this.shot.lambda * dt);
      this.camera.position.lerp(this.shot.pos, k);
      this.lookAt.lerp(this.shot.look, k);
      this.safePos(this.camera.position, this.lookAt, 0.2);
      this.camera.lookAt(this.lookAt);
    } else if (this.mode === 'viewfinder') {
      const vf = this.vf;
      const lim = vf.limit ?? 0.9;
      vf.yaw = THREE.MathUtils.clamp(vf.yaw - look.x * sens * 0.6, vf.baseYaw - lim, vf.baseYaw + lim);
      vf.pitch = THREE.MathUtils.clamp(vf.pitch + look.y * sens * 0.6, -1.0, 0.8);
      this.camera.position.lerp(vf.pos, 1 - Math.exp(-10 * dt));
      const cp = Math.cos(vf.pitch);
      tmp.set(Math.sin(vf.yaw) * cp, -Math.sin(vf.pitch), Math.cos(vf.yaw) * cp);
      this.lookAt.copy(this.camera.position).add(tmp);
      this.camera.lookAt(this.lookAt);
    }

    if (Math.abs(this.camera.fov - this.targetFov) > 0.05) {
      this.camera.fov = THREE.MathUtils.damp(this.camera.fov, this.targetFov, 5, dt);
      this.camera.updateProjectionMatrix();
    }

    if (this.shake > 0.001) {
      this.shakeT += dt * 38;
      const s = this.shake * this.shake * 0.12;
      this.camera.position.x += Math.sin(this.shakeT * 1.1) * s;
      this.camera.position.y += Math.sin(this.shakeT * 1.7 + 1) * s;
      this.camera.rotation.z += Math.sin(this.shakeT * 0.9) * s * 0.3;
      this.shake = Math.max(0, this.shake - dt * 1.6);
    }
  }

  /** Forward vector used for aiming checks. */
  forward(out = new THREE.Vector3()) { return this.camera.getWorldDirection(out); }
}
