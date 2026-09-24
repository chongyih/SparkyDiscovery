import * as THREE from 'three';
import { RoundedBoxGeometry } from 'three/examples/jsm/geometries/RoundedBoxGeometry.js';

function leatherTexture() {
  const s = 256;
  const c = document.createElement('canvas');
  c.width = c.height = s;
  const g = c.getContext('2d');
  g.fillStyle = '#1d1a18';
  g.fillRect(0, 0, s, s);
  const img = g.getImageData(0, 0, s, s);
  for (let i = 0; i < img.data.length; i += 4) {
    const n = Math.random() * 22;
    img.data[i] += n; img.data[i + 1] += n * 0.9; img.data[i + 2] += n * 0.8;
  }
  g.putImageData(img, 0, 0);
  g.strokeStyle = 'rgba(0,0,0,0.35)';
  for (let i = 0; i < 400; i++) {
    const x = Math.random() * s, y = Math.random() * s;
    g.beginPath(); g.moveTo(x, y); g.lineTo(x + Math.random() * 6 - 3, y + Math.random() * 6 - 3); g.stroke();
  }
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping;
  return t;
}

function faceplateTexture() {
  const s = 256;
  const c = document.createElement('canvas');
  c.width = c.height = s;
  const g = c.getContext('2d');
  const grd = g.createLinearGradient(0, 0, s, s);
  grd.addColorStop(0, '#b9b2a2'); grd.addColorStop(0.5, '#8d877a'); grd.addColorStop(1, '#6e695e');
  g.fillStyle = grd;
  g.fillRect(0, 0, s, s);
  // Art-deco stripes (inspired by 1930s box-camera faceplates; no brand marks).
  g.strokeStyle = 'rgba(40,36,30,0.55)';
  g.lineWidth = 3;
  for (let i = 0; i < 9; i++) { g.beginPath(); g.moveTo(0, 20 + i * 26); g.lineTo(s, 20 + i * 26); g.stroke(); }
  g.fillStyle = 'rgba(30,26,22,0.7)';
  g.font = 'bold 20px Georgia, serif';
  g.textAlign = 'center';
  g.fillText('BOX CAMERA', s / 2, s - 16);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return t;
}

/** A 1930s-style box camera. Unit ≈ 1 = 10 cm; scale the group as needed. Faces +Z. */
export function createBrownie() {
  const g = new THREE.Group();
  const leather = new THREE.MeshStandardMaterial({ map: leatherTexture(), roughness: 0.75, metalness: 0.0 });
  const metal = new THREE.MeshStandardMaterial({ color: 0x9a948a, roughness: 0.35, metalness: 0.85 });
  const plate = new THREE.MeshStandardMaterial({ map: faceplateTexture(), roughness: 0.4, metalness: 0.6 });
  const glass = new THREE.MeshPhysicalMaterial({ color: 0x223040, roughness: 0.05, metalness: 0.1, clearcoat: 1, clearcoatRoughness: 0.05 });
  const black = new THREE.MeshStandardMaterial({ color: 0x0c0b0a, roughness: 0.6 });

  const body = new THREE.Mesh(new RoundedBoxGeometry(1.0, 1.25, 1.55, 3, 0.06), leather);
  g.add(body);
  const face = new THREE.Mesh(new THREE.PlaneGeometry(0.9, 1.1), plate);
  face.position.z = 0.781;
  g.add(face);
  // Lens with a metal bezel.
  const bezel = new THREE.Mesh(new THREE.TorusGeometry(0.16, 0.035, 10, 24), metal);
  bezel.position.set(0, -0.12, 0.8);
  const lens = new THREE.Mesh(new THREE.CircleGeometry(0.15, 24), glass);
  lens.position.set(0, -0.12, 0.79);
  g.add(bezel, lens);
  // Two reflecting viewfinders (top-front).
  for (const [x, y, rx] of [[0.28, 0.42, 0], [-0.28, 0.42, 0]]) {
    const vf = new THREE.Mesh(new THREE.CircleGeometry(0.07, 16), glass);
    vf.position.set(x, y, 0.79);
    vf.rotation.x = rx;
    g.add(vf);
  }
  const topVf = new THREE.Mesh(new THREE.PlaneGeometry(0.16, 0.14), glass);
  topVf.rotation.x = -Math.PI / 2;
  topVf.position.set(0.25, 0.626, 0.55);
  g.add(topVf);
  // Winding knob on the side, shutter lever.
  const knob = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.08, 20), metal);
  knob.rotation.z = Math.PI / 2;
  knob.position.set(0.53, 0.35, -0.3);
  const lever = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.2, 0.05), metal);
  lever.position.set(0.52, -0.05, 0.62);
  g.add(knob, lever);
  // Carry handle strap.
  const strap = new THREE.Mesh(new THREE.TorusGeometry(0.28, 0.03, 6, 16, Math.PI), black);
  strap.position.set(0, 0.62, 0);
  strap.rotation.y = Math.PI / 2;
  g.add(strap);
  g.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
  g.userData.lever = lever;
  g.userData.knob = knob;
  return g;
}
