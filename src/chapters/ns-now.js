import * as THREE from 'three';
import { Character } from '../engine/character.js';
import { loadModel } from '../engine/assets.js';

// Today's park on the old camp (Chapter 3's Then & Now): 2026 residents so it feels lived in, as Chapter 1's
// Telok Ayer and Chapter 2's Queenstown do (the same present-day adults, plus the void deck's kids). They exist
// only in the 'now' era and stay off the photo's centre line (from THEN_NOW_Camera at (-26, 26), heading
// (+x, -z)). The opening view looks further right, towards (+0.33, -0.94), so most of the lawn life is there.
// Positions are three.js (x, z). The jogging path's near side runs along z ≈ 17–19 (x -24 .. 24); bench 1 is at
// (-8, 21.4); the heritage marker at (4, 16), its plate facing +z.

const V = (x, y, z) => new THREE.Vector3(x, y, z);

const PATH = [[-24, 17.2], [-16, 18.5], [-8, 19], [4, 19.1], [16, 18.5], [22, 17.6]];
const ring = (cx, cz, r, n = 6) => Array.from({ length: n }, (_, i) => [cx + r * Math.cos((i / n) * Math.PI * 2), cz + r * Math.sin((i / n) * Math.PI * 2)]);

// Models: height and natural walk / run speeds (so feet don't slide). Kids from tools/build_ww2_npcs.py.
const M = {
  office: { file: 'npc-now-office', height: 1.73 }, auntie: { file: 'npc-now-auntie', height: 1.56 },
  barista: { file: 'npc-now-barista', height: 1.6 }, tourist: { file: 'npc-now-tourist', height: 1.68 },
  teen: { file: 'npc-now-teen', height: 1.61 }, jogger: { file: 'npc-now-jogger', height: 1.75 },
  girl: { file: 'npc-kid-girl', height: 1.21, walk: 0.6, run: 1.46 }, boy: { file: 'npc-kid-boy', height: 1.33, walk: 0.66, run: 1.64 },
  small: { file: 'npc-kid-small', height: 1.089, walk: 0.53, run: 1.25 }, tween: { file: 'npc-kid-tween', height: 1.424, walk: 0.7, run: 1.79 },
};

// act: 'run' / 'walk' along `route` (there and back, or round and round with `circuit`), 'idle', 'talk',
// 'frisbee' (a pair, see below) or 'kite'. `tint` recolours a reused model's clothes a little.
const PEOPLE = [
  // On the path.
  { m: 'jogger', route: PATH, act: 'run' },
  { m: 'office', route: PATH.slice().reverse(), act: 'run', speed: 2.1, tint: 0xb8d8ff, delay: 4 },          // a second jogger, the other way
  { m: 'auntie', route: PATH.slice(1, 5).reverse(), act: 'walk' },
  { m: 'barista', route: [[-24, 17.6], [-12, 19.2], [-2, 19.4]], act: 'walk', speed: 0.55, tint: 0xffe0c8 },   // a parent and small child
  { m: 'small', route: [[-24.4, 16.9], [-12.4, 18.6], [-2.4, 18.8]], act: 'walk', speed: 0.55 },
  // By the bench and the marker.
  { m: 'teen', at: [-6.7, 21.1], face: [-9.1, 20.5], act: 'idle' },
  { m: 'barista', at: [-9.1, 20.5], face: [-6.7, 21.1], act: 'talk' },
  { m: 'tourist', at: [4.1, 17.9], face: [4.1, 16], act: 'idle' },
  // On the lawn, in the opening view.
  { m: 'boy', route: ring(-23, 11.8, 2.4), act: 'run', circuit: true },                                      // two kids chasing
  { m: 'girl', route: ring(-23, 11.8, 2.4).slice(3).concat(ring(-23, 11.8, 2.4).slice(0, 3)), act: 'run', circuit: true },
  { m: 'tween', at: [-16.6, 8.2], face: [-22.8, 4.9], act: 'frisbee' },                                      // frisbee
  { m: 'teen', at: [-22.8, 4.9], face: [-16.6, 8.2], act: 'frisbee', tint: 0xd8f0d0 },
  { m: 'boy', at: [-11.8, 3.5], face: [-4, -8], act: 'kite', tint: 0xffd8d8 },                              // flying a kite
  { m: 'office', route: [[-12, -4], [-24, -12]], act: 'walk' },                                              // cutting across to the blocks
  { m: 'auntie', route: [[-30, -8], [-14, -18]], act: 'walk', tint: 0xe0d8ff },                              // a couple, far off
  { m: 'tourist', route: [[-30.8, -7.4], [-14.8, -17.4]], act: 'walk', tint: 0xfff0c0 },
];

export async function preloadNowPeople() {
  const keys = [...new Set(PEOPLE.map((p) => p.m))];
  const gltfs = await Promise.all(keys.map((k) => loadModel(M[k].file)));
  return Object.fromEntries(keys.map((k, i) => [k, gltfs[i]]));
}

function tintClothes(ch, hex) {
  const tint = new THREE.Color(hex);
  ch.model.traverse((o) => {
    if (!o.isMesh) return;
    o.material = [].concat(o.material).map((m) => { const c = m.clone(); c.color?.multiply(tint); return c; });
    if (o.material.length === 1) o.material = o.material[0];
  });
}

function frisbeeDisc() {
  const d = new THREE.Mesh(new THREE.CylinderGeometry(0.13, 0.12, 0.025, 20), new THREE.MeshStandardMaterial({ color: '#ff6a2a', roughness: 0.5 }));
  d.castShadow = true;
  return d;
}

function kiteProp() {
  const g = new THREE.Group();
  const shape = new THREE.Shape([new THREE.Vector2(0, 0.55), new THREE.Vector2(0.38, 0), new THREE.Vector2(0, -0.75), new THREE.Vector2(-0.38, 0)]);
  const sail = new THREE.Mesh(new THREE.ShapeGeometry(shape), new THREE.MeshStandardMaterial({ color: '#e0342c', side: THREE.DoubleSide, roughness: 0.7 }));
  const stripe = new THREE.Mesh(new THREE.PlaneGeometry(0.06, 1.3), new THREE.MeshStandardMaterial({ color: '#ffd23a', side: THREE.DoubleSide }));
  stripe.position.set(0, -0.1, 0.002);
  g.add(sail, stripe);
  for (let i = 0; i < 4; i++) {
    const bow = new THREE.Mesh(new THREE.PlaneGeometry(0.16, 0.08), new THREE.MeshStandardMaterial({ color: i % 2 ? '#2a7de0' : '#ffd23a', side: THREE.DoubleSide }));
    bow.position.set(0, -0.95 - i * 0.28, 0);
    g.add(bow);
  }
  return g;
}

/** Spawn today's park-goers. Returns a cleanup function. */
export async function spawnNowPeople(c) {
  const g = c.game;
  const gltfs = await preloadNowPeople();
  const spawned = [], props = [], tickers = [];
  const ground = (x, z) => {
    const gy = c.world.groundHeight(x, 0.6, z, 0.8, 2);
    return gy === null ? 0 : Math.max(0, gy);
  };
  const at3 = ([x, z]) => V(x, ground(x, z), z);
  const frisbee = [];
  PEOPLE.forEach((p, i) => {
    const gltf = gltfs[p.m];
    if (!gltf) return; // model not built: leave them out
    const spec = M[p.m];
    const ch = new Character(`ns-now-${i}`, gltf, { height: spec.height, walkSpeed: spec.walk ?? 0.85, runSpeed: spec.run ?? 2.0 });
    if (p.tint) tintClothes(ch, p.tint);
    const route = p.route?.map(at3);
    const at = route ? route[0] : at3(p.at);
    const look = route ? route[1] : at3(p.face);
    ch.place(at, Math.atan2(look.x - at.x, look.z - at.z));
    c.scene.add(ch.root);
    g.npcs.push(ch);
    spawned.push(ch);
    if (p.act === 'talk') ch.play('Talk');
    else if (route) {
      const speed = p.speed ?? (p.act === 'run' ? (spec.run ?? 2.0) * 1.05 : (spec.walk ?? 0.85) * 1.05);
      let fwd = true;
      const loop = () => {
        if (!ch.root.parent) return;
        const next = p.circuit ? route.slice(1).concat([route[0]]) : (fwd ? route.slice(1) : route.slice(0, -1).reverse());
        fwd = !fwd;
        ch.moveTo(next, { speed }).then(loop);
      };
      if (p.delay) { ch.play('Idle'); g.wait(p.delay).then(loop); } else loop();
    } else {
      ch.play('Idle');
      if (p.act === 'frisbee') frisbee.push(ch);
      if (p.act === 'kite') {
        // A kite high up the breeze from the kid, on a string from the raised hand.
        const kite = kiteProp();
        const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([V(), V()]), new THREE.LineBasicMaterial({ color: '#f4f0e6' }));
        c.scene.add(kite, line);
        props.push(kite, line);
        ch.play(ch.clips.Wave ? 'Wave' : 'Idle', { speed: 0.35 });
        const up = look.clone().sub(at).setY(0).normalize();
        let t = 0;
        tickers.push((dt) => {
          t += dt;
          const hand = ch.headPosition(V()).add(V(0, 0.35, 0));
          kite.position.copy(at).addScaledVector(up, 9 + Math.sin(t * 0.4) * 0.6).add(V(Math.sin(t * 0.7) * 0.8, 11 + Math.sin(t * 0.9) * 0.5, 0));
          kite.lookAt(hand);
          kite.rotateZ(Math.sin(t * 1.3) * 0.25);
          line.geometry.setFromPoints([hand, kite.position.clone().add(V(0, -0.05, 0))]);
        });
      }
    }
  });
  // Frisbee: back and forth between the pair, a flat arc each way.
  if (frisbee.length === 2) {
    const disc = frisbeeDisc();
    c.scene.add(disc);
    props.push(disc);
    let from = 0, t = 0;
    const flight = 1.5, rest = 0.7;
    const hand = (ch) => ch.root.position.clone().add(V(0, ch.height * 0.62, 0));
    tickers.push((dt) => {
      t += dt;
      const a = frisbee[from], b = frisbee[1 - from];
      if (t < rest) { disc.position.copy(hand(a)); return; }
      if (t < rest + dt * 1.5) a.play(a.clips.Beckon ? 'Beckon' : 'Idle', { loop: false, speed: 1.4 });
      const k = Math.min(1, (t - rest) / flight);
      disc.position.lerpVectors(hand(a), hand(b), k).add(V(0, Math.sin(Math.PI * k) * 1.4, 0));
      disc.rotation.set(0.12, t * 14, 0.08);
      if (k >= 1) { from = 1 - from; t = 0; }
    });
  }
  const stopTick = tickers.length ? g.every((dt) => { for (const f of tickers) f(dt); }) : null;
  return () => {
    stopTick?.();
    for (const o of props) c.scene.remove(o);
    for (const ch of spawned) {
      ch.stop();
      c.scene.remove(ch.root);
      g.npcs = g.npcs.filter((n) => n !== ch);
    }
  };
}
