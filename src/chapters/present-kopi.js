import * as THREE from 'three';
import { reflective, hookEnv } from '../engine/brownie.js';

// Mr. Boon's takeaway kopi ("kopi dabao"): milky coffee in a thin clear plastic bag that slumps on
// the table, the neck gathered and tied off with raffia string (wound round, with a carrying loop)
// and a straw poking out of the knot. Built here rather than in voiddeck.glb because the bag is
// translucent. Metres, origin at the bag's base; sits on the set's PRO_Kopi marker.

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const smooth = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };

// Liquid (and the bag hugging it): flat slumped base, widest low down, tapering to the gathered neck.
const BODY = [[0.0005, 0], [0.028, 0], [0.038, 0.003], [0.0445, 0.012], [0.047, 0.026], [0.0455, 0.042],
  [0.04, 0.057], [0.032, 0.07], [0.024, 0.08], [0.018, 0.087]];
const TOP = 0.089; // liquid level (a little below the neck: the air pocket under the knot)
const NECK = 0.112;

// The filled bag leans a few millimetres, like it has settled to one side.
const lean = (y) => 0.004 * (y / NECK) ** 2;

/** Gathered-plastic pleats, growing towards the neck. */
function pleat(theta, y) {
  const a = smooth(0.03, 0.1, y) * 0.16;
  return 1 + a * (0.6 * Math.sin(9 * theta + 1.3) + 0.4 * Math.sin(14 * theta + 3.1 + y * 80));
}

function shape(geo, fn) {
  const p = geo.attributes.position;
  for (let i = 0; i < p.count; i++) {
    const x = p.getX(i), y = p.getY(i), z = p.getZ(i);
    const r = Math.hypot(x, z), th = Math.atan2(z, x);
    const [rr, yy] = fn(r, th, y);
    p.setXYZ(i, Math.cos(th) * rr + lean(yy), yy, Math.sin(th) * rr);
  }
  geo.computeVertexNormals();
  return geo;
}

const lathe = (pts, n = 48) => new THREE.LatheGeometry(pts.map(([r, y]) => new THREE.Vector2(r, y)), n);

export function createKopi() {
  const g = new THREE.Group();
  // Kopi with condensed milk: caramel brown, glossy through the plastic; froth on top. The faint
  // emissive stands in for light scattering through the milky coffee (it glows amber when backlit).
  const kopi = reflective(new THREE.MeshPhysicalMaterial({ color: 0x6a3512, emissive: 0x4a2008, emissiveIntensity: 0.7, roughness: 0.4, clearcoat: 0.7, clearcoatRoughness: 0.08, vertexColors: true }), 1.2);
  // Thin clear film: a dim base colour so it reads through highlights rather than a white haze.
  const film = reflective(new THREE.MeshPhysicalMaterial({ color: 0x8a8882, transparent: true, opacity: 0.14, roughness: 0.15, clearcoat: 1, clearcoatRoughness: 0.06, depthWrite: false }), 3);
  const loose = reflective(new THREE.MeshPhysicalMaterial({ color: 0xf2f0ea, transparent: true, opacity: 0.5, roughness: 0.25, clearcoat: 0.6, side: THREE.DoubleSide, depthWrite: false }), 2.5);
  const raffia = new THREE.MeshStandardMaterial({ color: 0xd8344a, roughness: 0.55 });
  const straw = new THREE.MeshPhysicalMaterial({ color: 0xf2a0b4, roughness: 0.3, clearcoat: 0.5, side: THREE.DoubleSide });

  // Liquid, with a domed froth cap; vertex colours lighten the froth.
  const liquid = shape(lathe([...BODY, [0.01, TOP - 0.0005], [0.0005, TOP]]), (r, th, y) => [r * pleat(th, y), y]);
  const col = new Float32Array(liquid.attributes.position.count * 3);
  for (let i = 0; i < liquid.attributes.position.count; i++) {
    const y = liquid.attributes.position.getY(i);
    const f = smooth(0.084, TOP, y), dark = 1 - 0.18 * smooth(0.03, 0, y); // deeper colour at the base
    col.set([(1 + f * 0.9) * dark, (1 + f * 1.1) * dark, (1 + f * 1.4) * dark], i * 3);
  }
  liquid.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const body = new THREE.Mesh(liquid, kopi);
  body.castShadow = body.receiveShadow = true;

  // The bag: hugs the liquid, then carries on empty and creased up to the neck.
  const bagPts = [...BODY.map(([r, y]) => [r + 0.0012, y]), [0.016, 0.092], [0.011, 0.098], [0.0075, 0.104], [0.0056, 0.11], [0.005, NECK + 0.002]];
  const bag = new THREE.Mesh(shape(lathe(bagPts), (r, th, y) => [r * pleat(th, y) * (1 + 0.25 * smooth(TOP, NECK, y) * Math.sin(7 * th + y * 300)), y]), film);

  // Loose plastic ends above the knot: a pleated, ragged flare.
  const ruffle = new THREE.Mesh(shape(lathe([[0.0055, NECK + 0.001], [0.009, NECK + 0.008], [0.015, NECK + 0.018], [0.021, NECK + 0.03]], 40), (r, th, y) => {
    const up = smooth(NECK, NECK + 0.03, y);
    const rr = r * (1 + 0.45 * up * (0.6 * Math.sin(6 * th + 0.7) + 0.4 * Math.sin(11 * th + 2.2)));
    return [rr, y + up * 0.006 * Math.sin(5 * th + 1.9)];
  }), loose);

  // Knot, raffia wound round the neck, and the carrying loop flopped over one side.
  const knot = new THREE.Mesh(new THREE.SphereGeometry(0.0085, 14, 10), loose);
  knot.scale.set(1, 0.75, 1);
  knot.position.set(lean(NECK), NECK + 0.001, 0);
  const wrap = new THREE.Mesh(new THREE.TorusGeometry(0.0066, 0.0016, 6, 20), raffia);
  wrap.rotation.x = Math.PI / 2 + 0.15;
  wrap.position.set(lean(NECK), NECK - 0.002, 0);
  const loopCurve = new THREE.CatmullRomCurve3([V(0.004, NECK, 0.003), V(0.011, 0.104, 0.008), V(0.02, 0.09, 0.011), V(0.031, 0.074, 0.009),
    V(0.036, 0.066, 0), V(0.031, 0.074, -0.009), V(0.02, 0.09, -0.011), V(0.011, 0.104, -0.008), V(0.004, NECK - 0.002, -0.003)], true);
  const loop = new THREE.Mesh(new THREE.TubeGeometry(loopCurve, 64, 0.0013, 5, true), raffia);

  // Straw: down into the kopi through the knot, poking out at an angle.
  const s0 = V(-0.012, 0.03, 0.006), s1 = V(lean(NECK), NECK, 0);
  const dir = s1.clone().sub(s0).normalize();
  const s2 = s1.clone().addScaledVector(dir, 0.095);
  const len = s0.distanceTo(s2);
  const strawGeo = new THREE.CylinderGeometry(0.003, 0.003, len, 12, 1, true);
  const st = new THREE.Mesh(strawGeo, straw);
  st.position.copy(s0).add(s2).multiplyScalar(0.5);
  st.quaternion.setFromUnitVectors(V(0, 1, 0), dir);
  st.castShadow = true;

  // Transparent layers draw after the kopi, innermost first.
  bag.renderOrder = 1; knot.renderOrder = 2; ruffle.renderOrder = 3;
  g.add(body, st, bag, knot, wrap, loop, ruffle);
  for (const m of [wrap, loop]) m.castShadow = true;
  hookEnv(g);
  return g;
}
