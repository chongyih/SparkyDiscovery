import * as THREE from 'three';
import { Character } from '../engine/character.js';
import { loadModel } from '../engine/assets.js';

// Present-day Telok Ayer (the Then & Now opening): a light crowd of 2026 Singaporeans so today's
// street feels alive and contrasts with 1942. They exist only in the 'now' era.

const V = (x, y, z) => new THREE.Vector3(x, y, z);

// `along` = metres ahead of the Then & Now viewpoint down the street; `side` = metres across the
// street from its centreline (negative = the viewpoint's side). The five-foot ways span 4–6.5 m,
// the road ±3.3 m, and today's cars are parked at +1.5–3.4 m. Everyone stays off the photo's
// centre line, nobody walks at the lens, and walkers keep ~0.7 m clear of the arcade pillars
// (z ±4.22) so swinging arms don't pass through them.
const PEOPLE = [
  { file: 'npc-now-office', height: 1.73, along: 7, side: -5.2, act: 'walk', span: 7 },
  { file: 'npc-now-barista', height: 1.6, along: 16.2, side: -5.4, act: 'talk' },
  { file: 'npc-now-teen', height: 1.61, along: 6.5, side: 5.5, act: 'idle' },
  { file: 'npc-now-tourist', height: 1.68, along: 12.6, side: 5.2, act: 'look', faceAhead: true },
  { file: 'npc-now-auntie', height: 1.56, along: 20, side: 5.3, act: 'walk', span: -6 },
  { file: 'npc-now-jogger', height: 1.75, along: 3, side: 0.6, act: 'run', span: 30, faceAhead: true },
];

export async function preloadNowPeople() {
  return Promise.all(PEOPLE.map((p) => loadModel(p.file)));
}

/**
 * Spawn the crowd around the Then & Now viewpoint. `pose` = { pos, yaw } of the viewpoint;
 * Returns a cleanup function.
 */
export async function spawnNowPeople(c, pose) {
  const g = c.game;
  const gltfs = await preloadNowPeople();
  // Walk straight down the street (world x), not along the viewpoint's slightly skewed heading,
  // or walkers drift sideways into the pillars and parked cars.
  const fwd = V(Math.sign(Math.sin(pose.yaw)) || 1, 0, 0);
  const nearSign = Math.sign(pose.pos.z) || -1; // the viewpoint's side of the street
  const spawned = [];
  PEOPLE.forEach((p, i) => {
    const gltf = gltfs[i];
    if (!gltf) return; // model not built yet: simply leave them out
    const ch = new Character(`now-${i}`, gltf, { height: p.height, walkSpeed: 0.85, runSpeed: 2.0 });
    const at = pose.pos.clone().addScaledVector(fwd, p.along);
    at.z = -nearSign * p.side;
    at.y = 0;
    c.world.resolve(at, 0.3, 1.5);
    const gy = c.world.groundHeight(at.x, 0.5, at.z, 0.6, 2);
    at.y = gy === null ? 0 : Math.max(0, gy);
    const facing = p.faceAhead ? pose.yaw : pose.yaw + Math.PI; // most walk toward the viewer
    ch.place(at, facing);
    c.scene.add(ch.root);
    g.npcs.push(ch);
    spawned.push(ch);
    if (p.act === 'talk') ch.play('Talk');
    else if (p.act === 'look') ch.play('Idle');
    else if (p.act === 'idle') ch.play('Idle');
    else if (p.act === 'walk' || p.act === 'run') {
      const a = at.clone();
      const b = at.clone().addScaledVector(fwd, p.span);
      const speed = p.act === 'run' ? 2.4 : 0.95;
      let toB = true;
      const loop = () => {
        if (!ch.root.parent) return;
        const target = toB ? b : a;
        toB = !toB;
        ch.moveTo(target, { speed }).then(loop);
      };
      loop();
    }
  });
  return () => {
    for (const ch of spawned) {
      ch.stop();
      c.scene.remove(ch.root);
      g.npcs = g.npcs.filter((n) => n !== ch);
    }
  };
}
