import * as THREE from 'three';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { MeshoptDecoder } from 'three/examples/jsm/libs/meshopt_decoder.module.js';
import { tier } from './settings.js';

const loader = new GLTFLoader();
loader.setMeshoptDecoder(MeshoptDecoder);

const BASE = import.meta.env.BASE_URL + 'assets/';
const cache = new Map();

// Fetch a file and return an ArrayBuffer, or null if it doesn't exist.
// (The dev server answers unknown paths with index.html, so check the content type.)
async function fetchBinary(url, onProgress) {
  let res;
  try { res = await fetch(url); } catch { return null; }
  if (!res.ok) return null;
  const type = res.headers.get('content-type') || '';
  if (type.includes('text/html')) return null;
  const total = +res.headers.get('content-length') || 0;
  if (!res.body || !total || !onProgress) return res.arrayBuffer();
  const reader = res.body.getReader();
  const chunks = [];
  let got = 0;
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    chunks.push(value);
    got += value.length;
    onProgress(got / total);
  }
  const out = new Uint8Array(got);
  let o = 0;
  for (const c of chunks) { out.set(c, o); o += c.length; }
  return out.buffer;
}

/** Load `models/<name>.glb`, preferring `<name>-mobile.glb` on mobile tiers. Resolves null if missing. */
export async function loadModel(name, onProgress) {
  const variant = tier().assetVariant;
  const key = `${name}:${variant}`;
  if (cache.has(key)) return cache.get(key);
  const p = (async () => {
    const urls = variant === 'mobile' ? [`${BASE}models/${name}-mobile.glb`, `${BASE}models/${name}.glb`] : [`${BASE}models/${name}.glb`, `${BASE}models/${name}-mobile.glb`];
    for (const url of urls) {
      const buf = await fetchBinary(url, onProgress);
      if (!buf) continue;
      try {
        return await loader.parseAsync(buf, url.slice(0, url.lastIndexOf('/') + 1));
      } catch (e) {
        console.warn('Failed to parse', url, e);
      }
    }
    console.warn(`[assets] ${name}.glb not found — using placeholder`);
    return null;
  })();
  cache.set(key, p);
  return p;
}

export function clearModelCache() { cache.clear(); }

export async function loadJSON(path) {
  try { const r = await fetch(BASE + path); if (!r.ok) return null; return await r.json(); } catch { return null; }
}

export const assetURL = (path) => BASE + path;

// Small procedural textures shared by effects.
const texCache = {};
export function radialTexture(key = 'soft', inner = 'rgba(255,255,255,1)', outer = 'rgba(255,255,255,0)', size = 128) {
  if (texCache[key]) return texCache[key];
  const c = document.createElement('canvas');
  c.width = c.height = size;
  const g = c.getContext('2d');
  const grd = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  grd.addColorStop(0, inner);
  grd.addColorStop(1, outer);
  g.fillStyle = grd;
  g.fillRect(0, 0, size, size);
  const t = new THREE.CanvasTexture(c);
  t.colorSpace = THREE.SRGBColorSpace;
  return (texCache[key] = t);
}

// Puffy smoke sprite: several overlapping soft blobs, so billboards don't look like discs.
export function smokeTexture() {
  if (texCache.smoke) return texCache.smoke;
  const s = 128;
  const c = document.createElement('canvas');
  c.width = c.height = s;
  const g = c.getContext('2d');
  let seed = 7;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 26; i++) {
    const a = rnd() * Math.PI * 2, r = rnd() * s * 0.22;
    const x = s / 2 + Math.cos(a) * r, y = s / 2 + Math.sin(a) * r, rad = s * (0.12 + rnd() * 0.2);
    const grd = g.createRadialGradient(x, y, 0, x, y, rad);
    grd.addColorStop(0, 'rgba(255,255,255,0.28)');
    grd.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = grd;
    g.fillRect(0, 0, s, s);
  }
  const t = new THREE.CanvasTexture(c);
  return (texCache.smoke = t);
}
