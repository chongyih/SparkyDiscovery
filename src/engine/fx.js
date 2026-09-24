import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { smokeTexture, radialTexture } from './assets.js';
import { tier } from './settings.js';

/**
 * GPU billboard particle column: puffs rise from `base`, drift with the wind and grow.
 * Everything is computed in the vertex shader from a per-instance seed, so updating costs one uniform.
 */
export class ParticleColumn extends THREE.Mesh {
  constructor({
    base, count = 60, life = 14, height = 120, spread = 6, size = [10, 55], wind = new THREE.Vector2(40, 8),
    color = new THREE.Color(0.05, 0.045, 0.04), color2 = new THREE.Color(0.22, 0.2, 0.18), opacity = 0.85,
    additive = false, texture = smokeTexture(), rise = 1.4,
  }) {
    const n = Math.max(4, Math.round(count * tier().particles));
    const quad = new THREE.PlaneGeometry(1, 1);
    const geo = new THREE.InstancedBufferGeometry();
    geo.index = quad.index;
    geo.attributes.position = quad.attributes.position;
    geo.attributes.uv = quad.attributes.uv;
    const seeds = new Float32Array(n * 4);
    for (let i = 0; i < n; i++) {
      seeds[i * 4] = i / n; // life offset
      seeds[i * 4 + 1] = Math.random();
      seeds[i * 4 + 2] = Math.random();
      seeds[i * 4 + 3] = Math.random();
    }
    geo.setAttribute('seed', new THREE.InstancedBufferAttribute(seeds, 4));
    geo.instanceCount = n;
    const mat = new THREE.ShaderMaterial({
      uniforms: {
        map: { value: texture }, time: { value: Math.random() * 100 }, life: { value: life }, height: { value: height },
        spread: { value: spread }, sizeA: { value: size[0] }, sizeB: { value: size[1] }, wind: { value: wind },
        color: { value: color }, color2: { value: color2 }, opacity: { value: opacity }, rise: { value: rise }, intensity: { value: 1 },
      },
      vertexShader: /* glsl */`
        attribute vec4 seed;
        uniform float time, life, height, spread, sizeA, sizeB, rise, intensity;
        uniform vec2 wind;
        varying vec2 vUv; varying float vAlpha; varying float vShade;
        void main() {
          float age = fract(time / life + seed.x);
          float h = pow(age, 1.0 / rise) * height;
          vec3 c = vec3((seed.y - 0.5) * spread, h, (seed.z - 0.5) * spread);
          c.xz += wind * age * age;
          c.x += sin(time * 0.3 + seed.w * 6.28) * spread * 0.3 * age;
          float s = mix(sizeA, sizeB, sqrt(age)) * (0.75 + seed.w * 0.5) * mix(0.35, 1.0, intensity);
          vec4 mv = modelViewMatrix * vec4(c, 1.0);
          float a = seed.w * 6.28 + time * 0.05 * (seed.y - 0.5);
          vec2 p = mat2(cos(a), -sin(a), sin(a), cos(a)) * position.xy;
          mv.xy += p * s;
          gl_Position = projectionMatrix * mv;
          vUv = uv;
          vAlpha = smoothstep(0.0, 0.08, age) * (1.0 - smoothstep(0.55, 1.0, age)) * intensity;
          vShade = seed.y * 0.6 + age * 0.4;
        }`,
      fragmentShader: /* glsl */`
        uniform sampler2D map; uniform vec3 color, color2; uniform float opacity;
        varying vec2 vUv; varying float vAlpha; varying float vShade;
        void main() {
          vec4 t = texture2D(map, vUv);
          float a = t.a * vAlpha * opacity;
          if (a < 0.01) discard;
          gl_FragColor = vec4(mix(color, color2, vShade), a);
          #include <colorspace_fragment>
        }`,
      transparent: true, depthWrite: false, blending: additive ? THREE.AdditiveBlending : THREE.NormalBlending,
    });
    super(geo, mat);
    this.position.copy(base);
    this.frustumCulled = false;
    this.renderOrder = additive ? 3 : 2;
  }

  update(dt) { this.material.uniforms.time.value += dt; }
  set intensity(v) { this.material.uniforms.intensity.value = v; }
}

/** Distant oil-fire smoke column (Feb 1942: burning oil depots darkened the sky over the city). */
export function oilSmoke(base, scale = 1) {
  const g = new THREE.Group();
  g.add(new ParticleColumn({ base: new THREE.Vector3(), count: 70, life: 22, height: 170 * scale, spread: 14 * scale, size: [16 * scale, 90 * scale], wind: new THREE.Vector2(70, 20).multiplyScalar(scale), opacity: 0.9 }));
  g.add(new ParticleColumn({ base: new THREE.Vector3(0, 2, 0), count: 14, life: 2.5, height: 10 * scale, spread: 8 * scale, size: [8 * scale, 14 * scale], wind: new THREE.Vector2(2, 0), additive: true, color: new THREE.Color(1.0, 0.45, 0.1), color2: new THREE.Color(0.9, 0.2, 0.05), opacity: 0.8, texture: radialTexture('fire', 'rgba(255,255,255,1)', 'rgba(255,255,255,0)') }));
  g.position.copy(base);
  g.update = (dt) => g.children.forEach((c) => c.update(dt));
  return g;
}

/**
 * Fixed pool of point lights. Adding/removing lights forces every material to recompile (a big
 * stutter), so the scene always holds the same lights and effects borrow them.
 */
export class LightPool {
  constructor(scene, count) {
    this.lights = [];
    for (let i = 0; i < count; i++) {
      const l = new THREE.PointLight(0xffffff, 0, 10, 2);
      l.userData.busy = false;
      l.userData.home = scene;
      scene.add(l);
      this.lights.push(l);
    }
  }

  claim({ color = 0xffffff, intensity = 1, distance = 10, decay = 2 } = {}) {
    const l = this.lights.find((x) => !x.userData.busy);
    if (!l) return null;
    l.userData.busy = true;
    l.color.set(color); l.intensity = intensity; l.distance = distance; l.decay = decay;
    return l;
  }

  release(l) {
    if (!l) return;
    l.userData.busy = false;
    l.intensity = 0;
    if (l.parent && l.parent !== l.userData.home) l.userData.home?.add(l);
  }

  releaseAll() { this.lights.forEach((l) => this.release(l)); }
}

/** Close fire with smoke, for a bombed building. `light` (optional) is borrowed from a LightPool. */
export function houseFire(base, light = null) {
  const g = new THREE.Group();
  g.add(new ParticleColumn({ base: new THREE.Vector3(0, 0.3, 0), count: 26, life: 1.6, height: 2.6, spread: 1.4, size: [0.7, 1.6], wind: new THREE.Vector2(0.3, 0.1), additive: true, color: new THREE.Color(1.0, 0.55, 0.15), color2: new THREE.Color(1.0, 0.25, 0.04), opacity: 0.9, texture: radialTexture('fire', 'rgba(255,255,255,1)', 'rgba(255,255,255,0)') }));
  g.add(new ParticleColumn({ base: new THREE.Vector3(0, 1.5, 0), count: 30, life: 7, height: 22, spread: 2, size: [1.5, 7], wind: new THREE.Vector2(6, 2), opacity: 0.75 }));
  g.position.copy(base);
  if (light) {
    light.color.set(0xff7a2a); light.distance = 12; light.decay = 2;
    light.position.copy(base).add(new THREE.Vector3(0, 1.2, 0));
    g.light = light;
  }
  let t = Math.random() * 10;
  g.update = (dt) => {
    t += dt;
    g.children.forEach((c) => c.update?.(dt));
    if (g.light) g.light.intensity = 10 + Math.sin(t * 13) * 2.5 + Math.sin(t * 29) * 1.5;
  };
  return g;
}

/** One-shot explosion: flash light, fireball, dust cloud and debris. CPU sprites (few). */
export class Burst extends THREE.Group {
  constructor(pos, { scale = 1, flashLight = null } = {}) {
    super();
    this.position.copy(pos);
    this.t = 0;
    this.done = false;
    this.parts = [];
    const fireTex = radialTexture('fire', 'rgba(255,255,255,1)', 'rgba(255,255,255,0)');
    const n = Math.round(14 * tier().particles) + 4;
    for (let i = 0; i < n; i++) {
      const fire = i < n * 0.35;
      const m = new THREE.SpriteMaterial({ map: fire ? fireTex : smokeTexture(), color: fire ? 0xffa050 : 0x5a5048, transparent: true, depthWrite: false, blending: fire ? THREE.AdditiveBlending : THREE.NormalBlending, opacity: 0 });
      const s = new THREE.Sprite(m);
      const dir = new THREE.Vector3(Math.random() - 0.5, Math.random() * 0.9 + 0.3, Math.random() - 0.5).normalize();
      this.parts.push({ s, dir, speed: (fire ? 6 : 3.5) * scale * (0.6 + Math.random() * 0.8), size: (fire ? 3 : 5) * scale * (0.6 + Math.random()), fire, life: fire ? 0.6 : 3.5 + Math.random() * 2 });
      this.add(s);
    }
    // One shared flash light for all explosions (never added/removed).
    if (flashLight) {
      this.light = flashLight;
      flashLight.position.copy(pos).add(new THREE.Vector3(0, 2, 0));
      flashLight.distance = 45 * scale;
      flashLight.intensity = Math.max(flashLight.intensity, 90 * scale);
    }
  }

  update(dt) {
    this.t += dt;
    let alive = false;
    for (const p of this.parts) {
      const k = this.t / p.life;
      if (k >= 1) { p.s.visible = false; continue; }
      alive = true;
      const drag = p.fire ? 1 : Math.exp(-this.t * 0.9);
      p.s.position.addScaledVector(p.dir, p.speed * dt * drag);
      if (!p.fire) p.s.position.y += dt * 0.6;
      const sz = p.size * (0.4 + Math.sqrt(k) * (p.fire ? 1.2 : 1.8));
      p.s.scale.set(sz, sz, 1);
      p.s.material.opacity = (p.fire ? (1 - k) : Math.min(1, k * 6) * (1 - k)) * 0.9;
    }
    if (this.light) this.light.intensity = Math.max(0, this.light.intensity - dt * 450);
    if (!alive) this.done = true;
  }

  dispose() { this.parts.forEach((p) => p.s.material.dispose()); }
}

/** Falling dust/grit around a point (e.g. the camera) after nearby blasts. */
export class Dust extends THREE.Points {
  constructor(count = 400) {
    const n = Math.round(count * tier().particles);
    const g = new THREE.BufferGeometry();
    const p = new Float32Array(n * 3);
    for (let i = 0; i < n; i++) { p[i * 3] = (Math.random() - 0.5) * 16; p[i * 3 + 1] = Math.random() * 8; p[i * 3 + 2] = (Math.random() - 0.5) * 16; }
    g.setAttribute('position', new THREE.BufferAttribute(p, 3));
    super(g, new THREE.PointsMaterial({ color: 0xc8b89a, size: 0.05, transparent: true, opacity: 0, depthWrite: false, sizeAttenuation: true }));
    this.frustumCulled = false;
    this.amount = 0;
  }

  kick(a = 1) { this.amount = Math.min(1, this.amount + a); }

  update(dt, center) {
    this.position.set(center.x, 0, center.z);
    this.amount = Math.max(0, this.amount - dt * 0.12);
    this.material.opacity = this.amount * 0.8;
    this.visible = this.amount > 0.01;
    if (!this.visible) return;
    const p = this.geometry.attributes.position;
    for (let i = 0; i < p.count; i++) {
      let y = p.getY(i) - dt * (0.4 + (i % 7) * 0.08);
      if (y < 0) y += 8;
      p.setY(i, y);
      p.setX(i, p.getX(i) + Math.sin(y + i) * dt * 0.1);
    }
    p.needsUpdate = true;
  }
}

/** Low-poly twin-engine bomber silhouette (generic; no insignia). Built once and shared. */
let _bomberGeo = null, _bomberMat = null;
function bomberGeometry() {
  if (_bomberGeo) return _bomberGeo;
  const parts = [];
  const fus = new THREE.CylinderGeometry(0.7, 0.35, 16, 8); fus.rotateX(Math.PI / 2); parts.push(fus);
  const nose = new THREE.SphereGeometry(0.7, 8, 6, 0, Math.PI * 2, 0, Math.PI / 2); nose.rotateX(Math.PI / 2); nose.translate(0, 0, 8); parts.push(nose);
  const wing = new THREE.BoxGeometry(25, 0.25, 3.2); wing.translate(0, 0, 1.5); parts.push(wing);
  const tail = new THREE.BoxGeometry(8, 0.2, 1.8); tail.translate(0, 0.2, -7.2); parts.push(tail);
  const fin = new THREE.BoxGeometry(0.2, 2.6, 2); fin.translate(0, 1.4, -7.2); parts.push(fin);
  for (const x of [-4.5, 4.5]) { const eng = new THREE.CylinderGeometry(0.6, 0.5, 3.4, 8); eng.rotateX(Math.PI / 2); eng.translate(x, -0.2, 2.8); parts.push(eng); }
  _bomberGeo = mergeGeometries(parts.map((p) => p.toNonIndexed()));
  return _bomberGeo;
}

/** A formation of high-altitude bombers crossing the sky. */
export class Formation extends THREE.Group {
  constructor({ count = 9, from, to, altitude = 180, speed = 55 }) {
    super();
    const geo = bomberGeometry();
    _bomberMat ||= new THREE.MeshStandardMaterial({ color: 0x3a3d3a, roughness: 0.8, metalness: 0.2, fog: true });
    const mesh = new THREE.InstancedMesh(geo, _bomberMat, count);
    this.mesh = mesh;
    const m = new THREE.Matrix4();
    for (let i = 0; i < count; i++) {
      const row = Math.floor((i + 1) / 2);
      const side = i === 0 ? 0 : (i % 2 ? -1 : 1);
      m.makeTranslation(side * row * 22, (Math.random() - 0.5) * 4, -row * 18);
      mesh.setMatrixAt(i, m);
    }
    mesh.frustumCulled = false;
    this.add(mesh);
    this.from = from.clone().setY(altitude);
    this.to = to.clone().setY(altitude);
    this.speed = speed;
    this.t = 0;
    this.len = this.from.distanceTo(this.to);
    this.position.copy(this.from);
    this.lookAt(this.to);
    this.done = false;
  }

  update(dt) {
    this.t += dt * this.speed;
    const k = this.t / this.len;
    this.position.lerpVectors(this.from, this.to, Math.min(1, k));
    if (k >= 1) this.done = true;
  }

  dispose() { this.mesh.dispose(); } // shared geometry/material stay cached
}

/** Free GPU resources of a particle effect group (fires, smoke) that is being removed for good. */
export function disposeEffect(obj) {
  obj.traverse((o) => { if (o.isMesh && o.material?.isShaderMaterial) { o.geometry.dispose(); o.material.dispose(); } });
}

/** Overcast sky dome with smoke-stained haze and a soft sun glow. */
export function skyDome({ top = '#8f9aa0', horizon = '#d6c9ae', bottom = '#9b9384', sunDir = new THREE.Vector3(0.3, 0.6, -0.7), haze = 0.4 } = {}) {
  const mat = new THREE.ShaderMaterial({
    uniforms: {
      top: { value: new THREE.Color(top) }, horizon: { value: new THREE.Color(horizon) }, bottom: { value: new THREE.Color(bottom) },
      sunDir: { value: sunDir.clone().normalize() }, haze: { value: haze }, smokeTint: { value: new THREE.Color('#3a3530') }, smoke: { value: 0 },
    },
    vertexShader: 'varying vec3 vDir; void main(){ vDir = normalize(position); vec4 p = projectionMatrix * modelViewMatrix * vec4(position,1.0); gl_Position = p.xyww; }',
    fragmentShader: /* glsl */`
      uniform vec3 top, horizon, bottom, sunDir, smokeTint; uniform float haze, smoke;
      varying vec3 vDir;
      float n2(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
      float noise(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f); return mix(mix(n2(i),n2(i+vec2(1,0)),f.x), mix(n2(i+vec2(0,1)),n2(i+vec2(1,1)),f.x), f.y); }
      void main(){
        vec3 d = normalize(vDir);
        float h = d.y;
        vec3 col = h > 0.0 ? mix(horizon, top, pow(h, 0.55)) : mix(horizon, bottom, pow(-h, 0.4));
        float sun = max(dot(d, sunDir), 0.0);
        col += vec3(1.0, 0.9, 0.7) * (pow(sun, 24.0) * 0.5 + pow(sun, 3.0) * 0.12) * (1.0 - haze * 0.6);
        vec2 uv = d.xz / max(0.15, d.y + 0.25) * 1.5;
        float c = noise(uv) * 0.5 + noise(uv * 2.3) * 0.3 + noise(uv * 5.1) * 0.2;
        col = mix(col, col * 0.86, smoothstep(0.45, 0.8, c) * step(0.0, h) * 0.6);
        col = mix(col, smokeTint, smoke * smoothstep(0.02, 0.45, h) * smoothstep(0.35, 0.75, c + 0.15));
        gl_FragColor = vec4(col, 1.0);
        #include <colorspace_fragment>
      }`,
    side: THREE.BackSide, depthWrite: false, fog: false,
  });
  const m = new THREE.Mesh(new THREE.SphereGeometry(900, 32, 16), mat);
  m.frustumCulled = false;
  m.renderOrder = -10;
  return m;
}
