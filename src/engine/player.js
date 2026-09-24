import * as THREE from 'three';
import { Character } from './character.js';

const dir = new THREE.Vector3();
const desired = new THREE.Vector3();

/** Sparky: input-driven character with acceleration, gravity, step-up and collisions. */
export class Player extends Character {
  constructor(gltf) {
    super('Sparky', gltf, {
      height: 1.0, radius: 0.28, walkSpeed: 1.9, runSpeed: 3.9,
      placeholder: { height: 1.0, shirt: '#8aa4b8', pants: '#55595c', skin: '#e6d2b0', hair: '#e6d2b0' },
    });
    this.vel = new THREE.Vector3();
    this.vy = 0;
    this.grounded = true;
    this.controlled = true;
    this.speedNow = 0;
    this.stepTimer = 0;
    this.onStep = null;
    this.carry = null;
    this.isPlayer = true;
  }

  control(dt, input, camYaw, world) {
    const pos = this.root.position;
    const mx = input.move.x, my = input.move.y;
    const mag = Math.min(1, Math.hypot(mx, my));
    const fx = Math.sin(camYaw), fz = Math.cos(camYaw);
    desired.set(fx * my - fz * mx, 0, fz * my + fx * mx);
    if (desired.lengthSq() > 1e-6) desired.normalize();
    const running = input.run && mag > 0.3;
    const top = (running ? this.runSpeed : this.walkSpeed) * (running ? 1 : Math.max(mag, 0.35));
    desired.multiplyScalar(mag > 0.08 ? top : 0);
    const accel = mag > 0.08 ? 10 : 12;
    this.vel.x += (desired.x - this.vel.x) * Math.min(1, accel * dt);
    this.vel.z += (desired.z - this.vel.z) * Math.min(1, accel * dt);
    const prevX = pos.x, prevZ = pos.z;
    pos.x += this.vel.x * dt;
    pos.z += this.vel.z * dt;

    world.resolve(pos, this.radius, this.height, 0.38);

    // Ground: step up small ledges (five-foot way kerbs), fall off bigger drops.
    let gy = world.groundHeight(pos.x, pos.y, pos.z, 0.45);
    if (gy !== null) gy = Math.max(0, gy); // walk over the drains, not into them
    if (gy !== null && gy <= pos.y + 0.45 && gy >= pos.y - 0.12 && this.vy <= 0) {
      pos.y += (gy - pos.y) * Math.min(1, dt * 18);
      this.vy = 0; this.grounded = true;
    } else if (gy !== null && gy > pos.y + 0.45) {
      // Too high to step: undo horizontal movement.
      pos.x = prevX; pos.z = prevZ; this.vel.set(0, 0, 0);
    } else {
      this.vy -= 18 * dt;
      pos.y += this.vy * dt;
      if (gy !== null && pos.y < gy) { pos.y = gy; this.vy = 0; this.grounded = true; } else this.grounded = gy === null ? true : false;
      if (gy === null) { pos.y = Math.max(pos.y, 0); this.vy = 0; }
    }

    const actual = Math.hypot(pos.x - prevX, pos.z - prevZ) / Math.max(dt, 1e-4);
    this.speedNow = THREE.MathUtils.damp(this.speedNow, actual, 12, dt);
    if (mag > 0.08) {
      dir.set(this.vel.x, 0, this.vel.z);
      if (dir.lengthSq() > 0.01) this.targetYaw = Math.atan2(dir.x, dir.z);
    }
    this.animateLocomotion(dt);
  }

  animateLocomotion(dt) {
    const s = this.speedNow;
    const special = this.currentName && !['Idle', 'Walk', 'Run'].includes(this.currentName);
    if (special && this.lockAnim) return;
    if (s > 2.6 && this.clips.Run) { this.play('Run', { fade: 0.2 }); this.setSpeed(s / this.runSpeed); }
    else if (s > 0.25) { this.play('Walk', { fade: 0.2 }); this.setSpeed(Math.max(0.7, s / this.walkSpeed)); }
    else if (!special) this.play('Idle', { fade: 0.3 });
    if (s > 0.25) {
      this.stepTimer -= dt * s * (s > 2.6 ? 1.35 : 1.6);
      if (this.stepTimer <= 0) { this.stepTimer = 1; this.onStep?.(s > 2.6); }
    }
  }

  update(dt, world, input, camYaw) {
    if (this.controlled && input) this.control(dt, input, camYaw, world);
    else if (world) {
      // Scripted: base class handles moveTo/follow; keep ground contact.
      super.update(dt, world);
      return;
    }
    if (this.targetYaw !== null) {
      let d = ((this.targetYaw - this.yaw + Math.PI) % (Math.PI * 2)) - Math.PI;
      if (d < -Math.PI) d += Math.PI * 2;
      this.yaw += d * (1 - Math.exp(-12 * dt));
      this.root.rotation.y = this.yaw;
    }
    this.mixer?.update(dt);
    if (this.procedural) this.updateProcedural(dt, this.speedNow > 0.25);
  }
}
