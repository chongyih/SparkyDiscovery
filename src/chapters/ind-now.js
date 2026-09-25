import * as THREE from 'three';
import { Character } from '../engine/character.js';
import { loadModel } from '../engine/assets.js';

// Present-day Queenstown (Chapter 2's Then & Now opening): a light crowd of 2026 residents so today's
// block feels lived in, as Chapter 1's Telok Ayer does (same models as ww2-now.js). They exist only
// in the 'now' era, stay off the photo's centre line and walk along the corridor or the car park,
// clear of the pillars (x = 0, ±4.5, ±9) and the parked cars.
// Positions are three.js (x, z): the corridor is z -0.4 .. -2.8, the car park z > 0.

const V = (x, y, z) => new THREE.Vector3(x, y, z);

const PEOPLE = [
  { file: 'npc-now-office', height: 1.73, at: [-8.6, -1.9], to: [8.2, -1.9], act: 'walk' },          // along the corridor
  { file: 'npc-now-auntie', height: 1.56, at: [3.1, -2.2], to: [-3.6, -2.2], act: 'walk' },          // out of the minimart
  { file: 'npc-now-barista', height: 1.6, at: [-6.9, -2.3], face: [-6.3, -1.6], act: 'talk' },        // eating-house counter
  { file: 'npc-now-tourist', height: 1.68, at: [-2.9, 1.5], face: [-2.25, 0.8], act: 'look' },        // reading the plaque
  { file: 'npc-now-teen', height: 1.61, at: [-8.3, 5.5], face: [0, 3], act: 'idle' },                 // beside the linkway, on her phone
  { file: 'npc-now-jogger', height: 1.75, at: [-6.6, 9.3], to: [-6.6, 0.9], act: 'run' },            // along the covered linkway
];

export async function preloadNowPeople() {
  return Promise.all(PEOPLE.map((p) => loadModel(p.file)));
}

/** Spawn today's residents around the block. Returns a cleanup function. */
export async function spawnNowPeople(c) {
  const g = c.game;
  const gltfs = await preloadNowPeople();
  const spawned = [];
  const ground = (x, z) => {
    const gy = c.world.groundHeight(x, 0.6, z, 0.8, 2);
    return gy === null ? 0 : Math.max(0, gy);
  };
  PEOPLE.forEach((p, i) => {
    const gltf = gltfs[i];
    if (!gltf) return; // model not built: leave them out
    const ch = new Character(`ind-now-${i}`, gltf, { height: p.height, walkSpeed: 0.85, runSpeed: 2.0 });
    const at = V(p.at[0], ground(p.at[0], p.at[1]), p.at[1]);
    const look = p.face || p.to;
    ch.place(at, Math.atan2(look[0] - at.x, look[1] - at.z));
    c.scene.add(ch.root);
    g.npcs.push(ch);
    spawned.push(ch);
    if (p.act === 'talk') ch.play('Talk');
    else if (p.act === 'walk' || p.act === 'run') {
      const a = at.clone();
      const b = V(p.to[0], ground(p.to[0], p.to[1]), p.to[1]);
      const speed = p.act === 'run' ? 2.4 : 0.95;
      let toB = true;
      const loop = () => {
        if (!ch.root.parent) return;
        const target = toB ? b : a;
        toB = !toB;
        ch.moveTo(target, { speed }).then(loop);
      };
      loop();
    } else ch.play('Idle');
  });
  return () => {
    for (const ch of spawned) {
      ch.stop();
      c.scene.remove(ch.root);
      g.npcs = g.npcs.filter((n) => n !== ch);
    }
  };
}
