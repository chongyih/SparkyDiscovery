import * as THREE from 'three';
import { loadModel } from '../engine/assets.js';
import { markerPose } from '../engine/world.js';
import { spawnExtra } from './ww2-night.js';

// Background townsfolk for Chapter 1: shopkeepers behind counters, kopitiam customers, people on
// the street, and the ration queue. They make the street feel lived-in and react to each beat.

const V = (x, y, z) => new THREE.Vector3(x, y, z);

// Generic 1942 townsfolk models (built by tools/build_ww2_npcs.py). Missing ones fall back to a
// recoloured clone of a main-cast model so the scene still works.
const MODELS = {
  shopkeeper: { file: 'npc-shopkeeper-cn', height: 1.62, fallback: ['Hassan', 0xcfc6b0] },
  womanCn: { file: 'npc-woman-cn', height: 1.57, fallback: ['AhMa', 0xb0c4d8] },
  manIn: { file: 'npc-man-in', height: 1.73, fallback: ['Hassan', 0xf2f0ea] },
  womanMy: { file: 'npc-woman-my', height: 1.55, fallback: ['AhMa', 0xd8b8c8] },
  labourer: { file: 'npc-man-cn-young', height: 1.66, fallback: ['Hassan', 0xa8a39a] },
};

// Who stands where. Marker names come from the level; missing markers are skipped.
const ROLES = [
  { marker: 'SHOPKEEPER_1', model: 'shopkeeper', role: 'shop', drop: 'DROP_1' },
  { marker: 'SHOPKEEPER_2', model: 'manIn', role: 'shop', drop: 'DROP_2' },
  { marker: 'SHOPKEEPER_3', model: 'womanMy', role: 'shop', drop: 'DROP_3' },
  { marker: 'KOPI_Customer_1', model: 'labourer', role: 'customer' },
  { marker: 'KOPI_Customer_2', model: 'shopkeeper', role: 'customer', tint: 0xd9e2e8 },
  { marker: 'KOPI_Customer_3', model: 'manIn', role: 'customer', tint: 0xe8e0c8 },
  { marker: 'STREET_Extra_1', model: 'womanCn', role: 'street' },
  { marker: 'STREET_Extra_2', model: 'labourer', role: 'street', walk: 6 },
  { marker: 'STREET_Extra_3', model: 'womanMy', role: 'street' },
  { marker: 'STREET_Extra_4', model: 'manIn', role: 'street', walk: -5 },
  { marker: 'STREET_Extra_5', model: 'womanCn', role: 'street', tint: 0xe0d0b8 },
  { marker: 'STREET_Extra_6', model: 'shopkeeper', role: 'street', tint: 0xc8d0c0 },
];

export class Town {
  constructor(c) {
    this.c = c;
    this.people = [];
    this.byDrop = {};
  }

  async load() {
    const loaded = await Promise.all(Object.entries(MODELS).map(async ([k, m]) => [k, await loadModel(m.file)]));
    for (const [k, gltf] of loaded) this.c.gltf[`T_${k}`] = gltf;
  }

  spawn(modelKey, { tint = 0xffffff, name } = {}) {
    const c = this.c;
    const m = MODELS[modelKey];
    if (c.gltf[`T_${modelKey}`]) return spawnExtra(c, `T_${modelKey}`, { tint, name: name || modelKey, height: m.height });
    const [base, fbTint] = m.fallback;
    const col = new THREE.Color(fbTint).multiply(new THREE.Color(tint));
    return spawnExtra(c, base, { tint: col.getHex(), name: name || modelKey, height: m.height });
  }

  /** Morning street: everyone at their spots. */
  populate() {
    const c = this.c;
    for (const r of ROLES) {
      const n = c.m[r.marker];
      if (!n) continue;
      const pose = markerPose(n);
      const ch = this.spawn(r.model, { tint: r.tint });
      ch.role = r.role;
      ch.home = pose;
      ch.place(pose.pos, pose.yaw);
      ch.play(r.role === 'customer' ? 'Sit' : 'Idle');
      if (r.role === 'customer') ch.root.position.add(V(-Math.sin(pose.yaw) * 0.2, 0, -Math.cos(pose.yaw) * 0.2));
      if (r.walk) ch.walkRoute = [pose.pos.clone(), pose.pos.clone().add(V(r.walk, 0, 0))];
      if (r.drop) this.byDrop[r.drop] = ch;
      this.people.push(ch);
    }
    // Slow strolls between two points (some people are still going about their day).
    this.stroll = c.game.every(() => {
      for (const ch of this.people) {
        if (!ch.walkRoute || ch.path || ch.fleeing) continue;
        ch.walkRoute.reverse();
        ch.moveTo(ch.walkRoute[0], { speed: ch.walkSpeed * 0.9 });
      }
    });
  }

  /** Air raid: street people run for the shelter / indoors; shopkeepers duck behind counters. */
  panic(shelterPos) {
    const g = this.c.game;
    this.stroll?.();
    for (const ch of this.people) {
      if (ch.role === 'street') {
        ch.fleeing = true;
        const to = shelterPos.clone().add(V((Math.random() - 0.5) * 2, 0, 0));
        Promise.race([ch.moveTo(to, { speed: 2.4 }), g.wait(12)]).then(() => { ch.stop(); ch.root.visible = false; });
      } else if (ch.role === 'customer') {
        ch.stop();
        ch.place(ch.root.position, ch.yaw);
        ch.play('Cower');
      } else ch.play('Cower');
    }
  }

  hideAll() { for (const ch of this.people) { ch.stop(); ch.root.visible = false; } }

  /** Syonan-to ration queue: townsfolk fill the queue markers the main cast doesn't use. */
  queue(markers) {
    this.hideAll();
    const kinds = ['womanCn', 'labourer', 'manIn', 'womanMy', 'shopkeeper', 'womanCn'];
    const out = [];
    markers.forEach((pose, i) => {
      const ch = this.people.find((p) => !p.root.visible && !p.queued && p.name === kinds[i % kinds.length]) || this.spawn(kinds[i % kinds.length]);
      ch.queued = true;
      ch.fleeing = false;
      ch.walkRoute = null;
      ch.root.visible = true;
      ch.place(pose.pos, pose.yaw);
      ch.play('Idle');
      out.push(ch);
    });
    return out;
  }

  /** The person who takes a delivered newspaper (if the level provides one). */
  shopkeeperFor(dropMarker) { return this.byDrop[dropMarker] || null; }
}
