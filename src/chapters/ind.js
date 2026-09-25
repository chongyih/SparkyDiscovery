import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import T from './ind-text.js';
import { ChapterKit } from './chapter-kit.js';
import { loadModel } from '../engine/assets.js';
import { World, collectMarkers, markerPose } from '../engine/world.js';
import { Character } from '../engine/character.js';
import { Player } from '../engine/player.js';
import { skyDome } from '../engine/fx.js';
import { createBrownie } from '../engine/brownie.js';
import { capturePhoto } from '../engine/album.js';
import { tier } from '../engine/settings.js';
import { PresentDay } from './present-day.js';
import { TV } from './ind-tv.js';
import { makeDrink, drinkName, sameDrink, cupMesh } from './ind-kopi.js';
import * as D from './ind-decals.js';

// Chapter 2 — "A Nation Is Born" (Queenstown, 9 August 1965). Script: docs/ch2-script.md.
// Set: tools/build_kopitiam.py (kopitiam.glb). Cast: tools/build_1965_npcs.py.

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const _lv1 = new THREE.Vector3(), _lv2 = new THREE.Vector3();
const _lq1 = new THREE.Quaternion(), _lq2 = new THREE.Quaternion(), _lq3 = new THREE.Quaternion(), _lq4 = new THREE.Quaternion(), _lqI = new THREE.Quaternion();
const load = (k, fb) => { try { return JSON.parse(localStorage.getItem(k)) ?? fb; } catch { return fb; } };
const save = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignore */ } };

const NAMES = {
  OldBoon: 'Mr. Boon', Boon: 'Boon', Siti: 'Siti', Farid: 'Farid', Ravi: 'Ravi', Rajan: 'Mr. Rajan', AhPek: 'Ah Pek Tan',
  Rohani: 'Makcik Rohani', Letchumi: 'Auntie Letchumi', Neighbour: 'Neighbour', Radio: 'Radio Singapura', Barber: 'Barber',
  Schoolboy: 'Schoolboy', Hawker: 'Hawker', Girl: 'Girl', Schoolboy2: 'Schoolboy', Narrator: '',
};

// walk/run: the speeds each clip was authored for (tools/build_ww2_npcs.py walk_speed()), so feet don't slide.
const CAST = {
  Boon: { file: 'npc-boon65', height: 1.64, walk: 0.72, run: 1.9 },
  Siti: { file: 'npc-siti65', height: 1.56, walk: 0.64, run: 1.6 },
  Farid: { file: 'npc-farid', height: 1.58, walk: 0.8, run: 2.09 },
  Ravi: { file: 'npc-ravi', height: 1.62, walk: 0.69, run: 1.8 },
  Rajan: { file: 'npc-rajan65', height: 1.69, walk: 0.62, run: 1.6 },
  AhPek: { file: 'npc-ahpek', height: 1.56, walk: 0.45, run: 1.2 },
  Rohani: { file: 'npc-rohani', height: 1.53, walk: 0.57, run: 1.5 },
  Letchumi: { file: 'npc-letchumi', height: 1.5, walk: 0.47, run: 1.25 },
};

// Evening crowd + corridor extras: the generic townsfolk from Chapter 1 (plain clothes still fit 1965).
const CROWD = [
  { file: 'npc-shopkeeper-cn', height: 1.62 }, { file: 'npc-woman-cn', height: 1.57 }, { file: 'npc-man-in', height: 1.73 },
  { file: 'npc-woman-my', height: 1.55 }, { file: 'npc-man-cn-young', height: 1.66 },
];
const CROWD_TINTS = [0xffffff, 0xd9e2e8, 0xe8e0c8, 0xd8c8d8, 0xc8d8c0, 0xf0e0d0, 0xd0d8e8];

const AUDIO = {
  'ceiling-fan': { loop: true, volume: 0.35 }, 'tv-static': { loop: true, volume: 0.25 }, 'kopi-pour': { volume: 0.8 },
  'cup-clink': { volume: 0.8 }, 'spoon-stir': { volume: 0.6 }, firecrackers: { volume: 0.7 }, 'radio-song': { loop: true, volume: 0.6 },
  'radio-static': { loop: true, volume: 0.45 }, murmur: { loop: true, volume: 0.5 }, street: { loop: true, volume: 0.4 },
  cicadas: { loop: true, volume: 0.3 }, myna: { volume: 0.5 },
  'footstep-1': { volume: 0.35 }, 'footstep-2': { volume: 0.35 }, 'footstep-3': { volume: 0.35 }, 'footstep-4': { volume: 0.35 }, 'footstep-5': { volume: 0.35 },
  'camera-shutter': {}, 'pickup-chime': { volume: 0.6 }, 'ui-click': { volume: 0.5 }, paper: {},
  'theme-1942': { loop: true, music: true, volume: 0.5 },
};

export const SLOTS = [
  { id: 'ind-Rediffusion', chapter: 'ind', year: '1949–', hint: 'Something on the kopitiam wall is always talking… (optional)' },
  { id: 'ind-TV', chapter: 'ind', year: '1963', hint: 'Boon’s pride and joy. (optional)' },
  { id: 'ind-MoneyTin', chapter: 'ind', year: '1965', hint: 'Whose money is in the tin? (optional)' },
  { id: 'ind-Anguish', chapter: 'ind', year: '9 Aug 1965', hint: 'Everyone in front of the television.' },
  { id: 'ind-Wall', chapter: 'ind', year: '1965', hint: 'Something for the wall.' },
];

const LIGHTING = {
  day: { bg: '#cfe0ea', fog: '#d9dfe0', near: 40, far: 220, top: '#7fa8c9', horizon: '#e6e2d2', bottom: '#a39d8f',
    hemi: ['#f4f1e6', '#7b7466', 1.25], sun: ['#fff0d6', 2.4], env: 0.35, lamps: 0.6,
    grade: { saturation: 0.95, sepia: 0, contrast: 1.05, vignette: 0.38 }, tint: [1, 1, 1] },
  now: { bg: '#d5e6f2', fog: '#dde6ea', near: 60, far: 620, top: '#6fa3d6', horizon: '#eef0ea', bottom: '#a8a296',
    hemi: ['#f6f7f2', '#7b7466', 1.3], sun: ['#fff6e6', 2.6], env: 0.4, lamps: 0.4,
    grade: { saturation: 1.05, sepia: 0, contrast: 1.05, vignette: 0.35 }, tint: [1, 1, 1] },
  evening: { bg: '#3e4660', fog: '#4a4a58', near: 25, far: 150, top: '#27324f', horizon: '#d98a5a', bottom: '#3a3530',
    hemi: ['#8a90a8', '#3a3228', 0.55], sun: ['#ff9a5a', 0.7], env: 0.18, lamps: 2.2,
    grade: { saturation: 0.92, sepia: 0.05, contrast: 1.08, vignette: 0.5 }, tint: [1.04, 0.98, 0.92] },
};

export class IndependenceChapter extends ChapterKit {
  constructor(game, { skipPrologue = false } = {}) {
    super(game, { id: 'ind', T, names: NAMES });
    this.skipPrologue = skipPrologue;
    this.heirlooms = load('sparky.heirlooms.ww2', []);
    this.kindness = new Set(load('sparky.kindness.ww2', []));
    this.cups = [];
    this.lamps = [];
    this.fans = []; // the engine may tick update() while the level is still loading
  }

  // ------------------------------------------------------------------ loading
  async load(onProgress) {
    const g = this.game;
    const steps = [];
    const files = Object.values(CAST).map((c) => c.file);
    const total = files.length + CROWD.length + 2;
    const prog = (i) => (p) => { steps[i] = p; onProgress?.(steps.reduce((a, b) => a + (b || 0), 0) / total); };
    const [level, sparky, ...rest] = await Promise.all([
      loadModel('kopitiam', prog(0)), loadModel('sparky-ind', prog(1)),
      ...files.map((f, i) => loadModel(f, prog(2 + i))),
      ...CROWD.map((c, i) => loadModel(c.file, prog(2 + files.length + i))),
    ]);
    const castModels = rest.slice(0, files.length);
    this.crowdModels = rest.slice(files.length);
    g.audio.setCaptions(T.captions);
    const audioLoad = g.audio.define(AUDIO);
    await D.loadFonts();

    const scene = new THREE.Scene();
    this.scene = scene;
    this.buildEnvironment(scene);
    if (!level) throw new Error('kopitiam.glb missing — run tools/build_kopitiam.py');
    this.level = level.scene;
    scene.add(this.level);
    this.m = collectMarkers(this.level);
    this.world = new World();
    this.setupLevel(this.level);
    this.fitStaticShadows();
    g.world = this.world;

    // Characters.
    this.player = new Player(sparky);
    this.player.model.traverse((o) => { if (o.isMesh) o.castShadow = false; });
    scene.add(this.player.root);
    this.player.onStep = () => g.audio.play(`footstep-${1 + Math.floor(Math.random() * 5)}`, { volume: 0.7, rate: 0.9 + Math.random() * 0.25, caption: '' });
    Object.entries(CAST).forEach(([key, cfg], i) => {
      const ch = new Character(key, castModels[i], { height: cfg.height, walkSpeed: cfg.walk, runSpeed: cfg.run, placeholder: { height: cfg.height } });
      ch.model.traverse((o) => { if (o.isMesh) o.castShadow = false; });
      this.cast[key] = ch;
      scene.add(ch.root);
      this.world.dynamic.push(ch.collider);
    });
    this.brownie = createBrownie();
    this.brownie.scale.setScalar(0.11);
    this.brownie.position.set(0, 0.5, 0.27);
    this.brownie.visible = false;
    this.player.root.add(this.brownie);

    this.present = new PresentDay(g);
    await this.present.load(this.envMap);
    await audioLoad;
    this.setEra('then');
    this.setLighting('day');
    onProgress?.(1);
  }

  /** Title background: a slow drift across the car park, looking at the shops. */
  titleShot(t) {
    // Between the corridor pillars (x = 0 and 4.5), so the camera never snags on one.
    const s = Math.sin(t * 0.05);
    return [V(2.25 + s * 1.4, 2.3 + Math.sin(t * 0.07) * 0.25, 8.5), V(2.0 + s * 0.6, 1.9, -5)];
  }

  buildEnvironment(scene) {
    const t = tier();
    scene.background = new THREE.Color('#cfe0ea');
    scene.fog = new THREE.Fog('#d9dfe0', 40, 220);
    this.sky = skyDome({ top: '#7fa8c9', horizon: '#e6e2d2', bottom: '#a39d8f', sunDir: V(0.35, 0.7, 0.6), haze: 0.35 });
    scene.add(this.sky);
    this.hemi = new THREE.HemisphereLight('#f4f1e6', '#7b7466', 1.25);
    scene.add(this.hemi);
    const sun = new THREE.DirectionalLight('#fff0d6', 2.4);
    sun.castShadow = t.shadows;
    scene.add(sun, sun.target);
    this.sun = sun;
    const pmrem = new THREE.PMREMGenerator(this.game.renderer.renderer);
    this.envMap = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = this.envMap;
    scene.environmentIntensity = 0.35;
    pmrem.dispose();
  }

  setupLevel(root) {
    const t = tier();
    this.prepareEraMaterials(root);
    root.updateMatrixWorld(true);
    this.nodes = {};
    root.traverse((o) => {
      if (o.name === 'NOW_Train') this.trainBaseZ = o.position.z;
      const n = o.name || '';
      if (/^(DECAL_|WALL_|TV_Screen|FAN_\d$|THEN_|NOW_)/.test(n)) this.nodes[n] = o;
      if (n.startsWith('COL_')) {
        if (o.isMesh) {
          const box = this.world.addBoxFromMesh(o, o.userData.state !== 'now');
          if (o.userData.state) box.state = o.userData.state;
        }
        o.visible = false;
        return;
      }
      if (o.isMesh) {
        o.receiveShadow = true;
        o.castShadow = t.shadows && !/^(DECAL_|WALL_|TV_Screen)/.test(n);
        for (const m of [].concat(o.material)) {
          if (m.map) m.map.anisotropy = t.bloom ? 8 : 2;
          if ('envMapIntensity' in m) m.envMapIntensity = 0.6;
          // Signs and decals sit just proud of walls: bias them forward to avoid shimmer.
          if (/Decal|Details|Windows/.test(m.name)) { m.polygonOffset = true; m.polygonOffsetFactor = -1; m.polygonOffsetUnits = -2; }
        }
      }
    });
    // Ground + camera ray meshes: everything static that isn't present-day only, laundry or a decal.
    root.traverse((o) => {
      if (!o.isMesh || o.name.startsWith('COL_')) return;
      let p = o, skip = false;
      while (p && p !== root) { if (/^(NOW_|THEN_Laundry|DECAL_|WALL_|TV_Screen|FAN_)/.test(p.name || '')) { skip = true; break; } p = p.parent; }
      if (!skip) this.world.addRayMesh(o);
    });
    // The player stays around the block and the car park.
    this.world.bounds = { minX: -14.4, maxX: 14.4, minZ: -11.7, maxZ: 9.5 };

    // Runtime textures.
    const setTex = (name, texture, emissive = false) => {
      const n = this.nodes[name];
      if (!n) return;
      n.traverse((o) => {
        if (!o.isMesh) return;
        o.material = new THREE.MeshStandardMaterial({ map: texture, roughness: 0.8, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4,
          emissive: emissive ? 0xffffff : 0x000000, emissiveMap: emissive ? texture : null, emissiveIntensity: emissive ? 0.35 : 0 });
      });
    };
    setTex('DECAL_ShopSign', D.shopSign(T.shopSign));
    setTex('DECAL_NowSign', D.nowSign(T.nowSign), true);
    Object.entries(T.neighbourSigns).forEach(([k, v], i) => setTex(`DECAL_Sign_${k}`, D.neighbourSign(v, i)));
    Object.entries(T.nowNeighbourSigns).forEach(([k, v], i) => setTex(`DECAL_NowSign_${k}`, D.nowShopSign(v, i), true));
    setTex('DECAL_NowBlockNo', D.blockNumber(T.blockNumber));
    setTex('DECAL_NowMarker', D.heritageMarker(T.heritageMarker));
    // Distant skyline and train: no shadows (the sun's shadow box only covers the block).
    for (const k of ['NOW_Skyline', 'NOW_Train']) this.nodes[k]?.traverse((o) => { if (o.isMesh) { o.castShadow = false; o.receiveShadow = false; } });
    setTex('DECAL_OrderBoard', D.orderBoard(T.orderBoard));
    setTex('DECAL_Calendar', D.calendarPage());
    setTex('DECAL_Notice', D.notice(T.notice));
    setTex('DECAL_Portrait_AhMa', D.portrait('ahma'));
    setTex('DECAL_Portrait_Papa', this.heirlooms.includes('photo') ? D.portrait('papa') : D.fuDiamond());
    setTex('DECAL_Mirror', D.congratsMirror(T.mirror));
    setTex('DECAL_Poster', D.calendarPoster(T.poster));
    setTex('WALL_Newspaper', D.newspaper());
    setTex('WALL_Flag', D.flag());
    setTex('WALL_Sign', D.fourLanguageSign(T.newSign));
    setTex('WALL_Calendar', D.calendarPage());
    for (const k of ['WALL_Newspaper', 'WALL_Flag', 'WALL_Sign', 'WALL_Calendar']) if (this.nodes[k]) this.nodes[k].visible = false;
    // Heirloom from 1942: the family photo hangs beside Ah Ma's portrait (otherwise a 福 diamond hangs there).

    this.tv = new TV(this.game, this.nodes.TV_Screen?.isMesh ? this.nodes.TV_Screen : this.findMesh(this.nodes.TV_Screen));

    // Ceiling fans spin about their own centres.
    this.fans = [];
    for (const k of ['FAN_1', 'FAN_2']) {
      const n = this.nodes[k];
      const mesh = n && (n.isMesh ? n : this.findMesh(n));
      if (!mesh) continue;
      mesh.geometry.computeBoundingBox();
      const c = mesh.geometry.boundingBox.getCenter(new THREE.Vector3());
      mesh.geometry.translate(-c.x, 0, -c.z);
      mesh.position.x += c.x * mesh.scale.x;
      mesh.position.z += c.z * mesh.scale.z;
      this.fans.push(mesh);
    }

    // Fluorescent battens: a few real lights (tier budget), strongest by the tables and the counter.
    const lampMarks = Object.keys(this.m).filter((k) => /^LAMP/.test(k)).map((k) => markerPose(this.m[k]).pos);
    const n = Math.max(1, Math.min(lampMarks.length, t.maxLights - 1));
    for (const p of lampMarks.slice(0, n)) {
      const l = new THREE.PointLight('#eef4ff', 0.6, 7, 1.6);
      l.position.copy(p);
      this.scene.add(l);
      this.lamps.push(l);
    }
  }

  findMesh(n) {
    let out = null;
    n?.traverse((o) => { if (!out && o.isMesh) out = o; });
    return out;
  }

  /** Present-day look: plaster turns vivid (repainted), as in Chapter 1's Then & Now. */
  prepareEraMaterials(root) {
    this.eraUniform = { value: 0 };
    const U = this.eraUniform;
    root.traverse((o) => {
      if (!o.isMesh) return;
      for (const m of [].concat(o.material)) {
        if (m.userData.eraPatched || !/Plaster/i.test(m.name)) continue;
        m.userData.eraPatched = true;
        m.onBeforeCompile = (sh) => {
          sh.uniforms.eraNow = U;
          sh.fragmentShader = 'uniform float eraNow;\n' + sh.fragmentShader.replace('#include <color_fragment>', `#include <color_fragment>
            {
              float l = dot(diffuseColor.rgb, vec3(0.299, 0.587, 0.114));
              vec3 vivid = mix(vec3(l), diffuseColor.rgb, 1.8) * 1.12 + 0.05;
              diffuseColor.rgb = mix(diffuseColor.rgb, clamp(vivid, 0.0, 1.0), eraNow);
            }`);
        };
        m.customProgramCacheKey = () => 'ind-era-plaster';
        m.needsUpdate = true;
      }
    });
  }

  fitStaticShadows() {
    if (!this.sun.castShadow) return;
    const c = V(0, 3, -4), r = 26;
    const dir = V(0.35, 0.8, 0.5).normalize();
    this.sun.position.copy(c).addScaledVector(dir, r + 20);
    this.sun.target.position.copy(c);
    this.sun.target.updateMatrixWorld();
    const size = tier().shadowSize >= 2048 ? 4096 : 2048;
    this.sun.shadow.mapSize.set(size, size);
    Object.assign(this.sun.shadow.camera, { left: -r, right: r, top: r, bottom: -r, near: 1, far: r * 2 + 50 });
    this.sun.shadow.camera.updateProjectionMatrix();
    this.sun.shadow.bias = -0.0006;
    this.sun.shadow.normalBias = 0.03;
    this.game.renderer.renderer.shadowMap.autoUpdate = false;
    this.refreshShadows();
  }

  refreshShadows() { this.game.renderer.renderer.shadowMap.needsUpdate = true; }

  setLighting(name) {
    const p = LIGHTING[name];
    const s = this.scene;
    s.background.set(p.bg);
    s.fog.color.set(p.fog); s.fog.near = p.near; s.fog.far = p.far;
    const u = this.sky.material.uniforms;
    u.top.value.set(p.top); u.horizon.value.set(p.horizon); u.bottom.value.set(p.bottom);
    this.hemi.color.set(p.hemi[0]); this.hemi.groundColor.set(p.hemi[1]); this.hemi.intensity = p.hemi[2];
    this.sun.color.set(p.sun[0]); this.sun.intensity = p.sun[1];
    s.environmentIntensity = p.env;
    for (const l of this.lamps) l.intensity = p.lamps;
    Object.assign(this.game.renderer.grade, p.grade);
    this.game.renderer.grade.tint.setRGB(...p.tint);
    this.lighting = name;
  }

  /** 'then' (9 Aug 1965) or 'now' (present-day Then & Now view). */
  setEra(era) {
    const now = era === 'now';
    for (const [n, o] of Object.entries(this.nodes)) {
      if (n.startsWith('NOW_') || n.startsWith('DECAL_Now')) o.visible = now;
      else if (n.startsWith('THEN_') || n === 'DECAL_ShopSign' || n.startsWith('DECAL_Sign_')) o.visible = !now;
    }
    // The 1965 kopitiam's own decals (inside the now open-fronted minimart) belong to the past.
    for (const [n, o] of Object.entries(this.nodes)) {
      if (!/^(DECAL_(OrderBoard|Calendar|Portrait|Notice|Mirror|Poster)|WALL_|TV_Screen)/.test(n)) continue;
      if (now) { o.userData.thenVisible ??= o.visible; o.visible = false; } else if (o.userData.thenVisible !== undefined) { o.visible = o.userData.thenVisible; delete o.userData.thenVisible; }
    }
    this.world.applyStates(now ? ['now'] : ['then']);
    this.eraUniform.value = now ? 1 : 0;
    for (const ch of [...Object.values(this.cast), ...this.extras]) ch.root.visible = !now && ch.root.userData.show !== false;
    this.era = era;
    this.refreshShadows();
  }

  // ------------------------------------------------------------------ cast placement
  seat(ch, markerName) {
    const s = this.marker(markerName);
    ch.stop();
    ch.place(s.pos, s.yaw);
    ch.play('Sit');
    ch.root.userData.show = true;
    ch.root.visible = true;
    ch.seatName = markerName;
  }

  stand(ch, markerName, yawTo = null) {
    const s = this.marker(markerName);
    ch.stop();
    ch.place(s.pos, s.yaw);
    if (yawTo) ch.faceTowards(yawTo, true);
    ch.play('Idle');
    ch.root.userData.show = true;
    ch.root.visible = true;
  }

  hide(ch) { ch.stop(); ch.root.userData.show = false; ch.root.visible = false; }

  /** Where Sparky starts: in the corridor between two pillars, so the follow camera has room behind him. */
  spawnPose() {
    const sp = this.marker('SPAWN_Sparky');
    return { pos: V(2.25, sp.pos.y, -1.3), yaw: sp.yaw };
  }

  placeCast() {
    const { Boon, Farid, AhPek, Rohani, Letchumi, Ravi, Siti, Rajan } = this.cast;
    const sp = this.spawnPose();
    this.player.place(sp.pos, sp.yaw);
    this.stand(Boon, 'NPC_Boon');
    this.stand(Farid, 'NPC_Farid');
    this.seat(AhPek, 'SEAT_T1_c');
    this.seat(Rohani, 'SEAT_T4_b');
    this.seat(Letchumi, 'SEAT_T6_a');
    this.seat(Ravi, 'SEAT_T5_d');
    this.stand(Siti, 'NPC_Siti');
    this.hide(Rajan);
  }

  // ------------------------------------------------------------------ main flow
  async run() {
    const g = this.game;
    g.album.setSlots(SLOTS);
    g.album.setPages({ realVsImagined: T.realVsImagined, sources: T.sources.map((s) => ({ title: `${s.title} — ${s.publisher}`, url: s.url })), credits: T.credits.audio });
    g.npcs = Object.values(this.cast);
    g.player = this.player;
    this.placeCast();
    this.setEra('then');
    this.setLighting('day');

    // Debug: ?beat=morning|ten|errand|worries|evening|tv|wall jumps straight to a beat.
    const beats = ['intro', 'morning', 'ten', 'errand', 'worries', 'evening', 'tv', 'wall'];
    const jump = new URLSearchParams(location.search).get('beat');
    const from = Math.max(0, beats.indexOf(jump));
    if (jump && from > 0) {
      g.setScene(this.scene);
      g.rig.setSubject(this.player);
      g.rig.follow();
      this.ambience(true);
      await g.ui.fade(false, 0.3);
      g.mode = 'play';
      if (from >= 4) this.jumpToWorries();
      if (from >= 5) { this.stand(this.cast.Siti, 'NPC_SitiTable'); this.seat(this.cast.Siti, 'SEAT_T3_c'); }
    } else if (!this.skipPrologue) { await this.bridge(); await this.thenNow(); }
    if (from <= 0) await this.intro();
    if (from <= 1) await this.morningBeat();
    if (from <= 2) await this.tenOClock();
    if (from <= 3) await this.errandBeat();
    if (from <= 4) await this.worriesBeat();
    if (from <= 5) await this.eveningBeat();
    if (from <= 6) await this.tvBeat();
    await this.wallBeat();
    await this.codaBeat();
  }

  jumpToWorries() {
    this.seat(this.cast.Siti, 'SEAT_T3_c');
    this.radioEmitter && this.game.audio.removeEmitter(this.radioEmitter, 0.2);
    this.radioEmitter = null;
  }

  ambience(on) {
    const g = this.game;
    if (on) {
      const inside = V(0, 1.5, -7);
      this.ambFan = g.audio.emitter('ceiling-fan', inside, { radius: 9, volume: 0.7, minVolume: 0.1 });
      this.ambMurmur = g.audio.emitter('murmur', inside, { radius: 12, volume: 0.55, minVolume: 0.15 });
      this.ambStreet = g.audio.play('street', { volume: 0.18, loop: true, fadeIn: 2, caption: '' });
      this.ambCicada = g.audio.play('cicadas', { volume: 0.2, loop: true, fadeIn: 2, caption: '' });
    } else {
      [this.ambFan, this.ambMurmur].forEach((e) => e && g.audio.removeEmitter(e, 1));
      this.ambStreet?.stop(1); this.ambCicada?.stop(1);
      this.ambFan = this.ambMurmur = null;
    }
  }

  // ------------------------------------------------------------------ present day
  async bridge() {
    const g = this.game;
    const P = this.present;
    P.show();
    g.mode = 'cutscene';
    Object.assign(g.renderer.grade, { sepia: 0, saturation: 0.95, vignette: 0.45, contrast: 1.05, flash: 0 });
    P.wideShot(true);
    await g.ui.fade(false, 1.5);
    g.audio.music('theme-1942', { fade: 3, volume: 0.6 });
    await g.ui.card('Present day', 'The void deck, Queenstown', '', 2.4);
    await this.lines(T.bridge.slice(0, 1), { frame: false });
    P.closeShot();
    await this.lines(T.bridge.slice(1), { frame: false });
    await P.pushIn();
    g.audio.play('camera-shutter');
    g.audio.music(null, { fade: 2 });
    P.active = false;
  }

  /** Line up Mr. Boon's 1965 photo with the block today; the photo takes over. */
  async thenNow() {
    const g = this.game;
    const X = T.thenNow;
    const pose = this.marker('THEN_NOW_Camera', V(0.8, 1.45, 8.5));
    const pitch = 0.0;
    const dirAt = (yaw, p) => V(Math.sin(yaw) * Math.cos(p), -Math.sin(p), Math.cos(yaw) * Math.cos(p));
    const eye = pose.pos.clone();
    const hideDyn = (h) => { for (const c of [...Object.values(this.cast), this.player]) c.root.visible = !h; };

    // 1) Render the 1965 photograph from this exact viewpoint (behind the sepia fade).
    g.setScene(this.scene);
    hideDyn(true);
    this.setEra('then');
    this.setLighting('day');
    const grade = { ...g.renderer.grade };
    Object.assign(g.renderer.grade, { sepia: 0, saturation: 1, vignette: 0, flash: 0 });
    g.rig.viewfinder(eye, eye.clone().add(dirAt(pose.yaw, pitch)), true);
    g.rig.update(0, null, null);
    this.refreshShadows();
    g.renderer.render(0);
    const ghost = capturePhoto(g.canvas, { size: 512 });
    Object.assign(g.renderer.grade, grade);

    // 2) Today.
    this.setEra('now');
    this.setLighting('now');
    const amb = g.audio.play('street', { volume: 0.35, loop: true, fadeIn: 2, caption: '[Traffic, voices, a scooter passing]' });
    // Start looking past the east end of the block (Dawson's towers, the MRT), then pan back to the shops.
    this.trainT = 110;
    g.rig.viewfinder(eye, eye.clone().add(dirAt(pose.yaw - 1.05, pitch - 0.16)), true, 1.3);
    // Coming in through the Brownie's lens (the prologue's push-in closed the iris on it): open it onto
    // today's Queenstown, as Chapter 1 does. Otherwise (e.g. no prologue) just fade in.
    if (g.ui.irisClosed) { g.ui.fade(false, 0); await g.ui.iris(false, 1.5, { y: 50, soft: 6 }); } else await g.ui.fade(false, 1.2);
    await this.cardLine(X.card.text);
    await this.lines(X.before, { frame: false });

    // 3) Align (mouse / drag / stick / WASD).
    g.mode = 'viewfinder';
    g.input.aimKeys = true;
    g.input.requestLock();
    const $ = (id) => document.getElementById(id);
    const vf = $('viewfinder'), img = $('vf-ghost'), note = $('vf-note'), hintEl = $('vf-hint');
    img.src = ghost;
    img.classList.remove('hidden');
    $('vf-label').textContent = X.hint;
    $('btn-shutter').classList.add('hidden');
    $('btn-vf-cancel').classList.add('hidden');
    const hintWas = hintEl.innerHTML;
    hintEl.innerHTML = g.input.isTouch ? 'Drag to turn the camera until the old photo matches' : 'Move the mouse (or <kbd>WASD</kbd>) until the old photo matches';
    vf.classList.remove('hidden');
    document.body.classList.add('aiming');
    let lockedFor = 0;
    await new Promise((resolve) => {
      const off = g.every((dt) => {
        const v = g.rig.vf;
        const dy = Math.atan2(Math.sin(v.yaw - pose.yaw), Math.cos(v.yaw - pose.yaw));
        const dp = v.pitch - pitch;
        const err = Math.hypot(dy, dp);
        if (err < 0.3) {
          const k = Math.min(1, dt * (err < 0.12 ? 4 : 1.6));
          v.yaw -= dy * k;
          v.pitch -= dp * Math.min(1, k * 1.5);
        }
        img.style.opacity = (0.3 + 0.55 * Math.max(0, 1 - err / 0.6)).toFixed(2);
        note.textContent = X.close;
        note.classList.toggle('hidden', !(err < 0.2 && err > 0.09));
        vf.querySelector('.vf-frame').classList.toggle('found', err < 0.1);
        lockedFor = err < 0.09 ? lockedFor + dt : 0;
        if (lockedFor > 0.2) { off(); resolve(); }
      });
    });
    g.input.aimKeys = false;
    g.input.lookEnabled = false;
    g.mode = 'cutscene';
    g.rig.viewfinder(eye, eye.clone().add(dirAt(pose.yaw, pitch)), true);
    g.audio.play('camera-shutter');
    img.style.opacity = '1';
    note.classList.add('hidden');
    await g.wait(0.5);
    await this.lines(X.locked, { frame: false });
    amb.stop(1.5);
    await g.ui.fade(true, 0.7, 'sepia');
    g.input.lookEnabled = true;
    vf.classList.add('hidden');
    vf.querySelector('.vf-frame').classList.remove('found');
    img.classList.add('hidden');
    $('btn-shutter').classList.remove('hidden');
    $('btn-vf-cancel').classList.remove('hidden');
    hintEl.innerHTML = hintWas;
    document.body.classList.remove('aiming');
    this.setEra('then');
    this.setLighting('day');
    hideDyn(false);
    this.cameFromThenNow = true;
  }

  // ------------------------------------------------------------------ 9 August 1965
  async intro() {
    const g = this.game;
    const p = this.player;
    g.setScene(this.scene);
    g.rig.setSubject(p);
    const sp = this.spawnPose();
    p.place(sp.pos, sp.yaw);
    // From the car park, looking at the shops, the photograph's colour bleeding back.
    const cam = { pos: V(2.25, 1.7, 3.6) };
    const look = sp.pos.clone().add(V(0, 1.0, -4));
    g.rig.cut(cam.pos, look, 1, true);
    Object.assign(g.renderer.grade, { sepia: 1, saturation: 0, vignette: 0.8 });
    this.ambience(true);
    this.radioEmitter = g.audio.emitter('radio-song', this.marker('RADIO').pos, { radius: 10, volume: 0.75, minVolume: 0.08 });
    await g.ui.fade(false, 1.2, 'sepia');
    const card = this.cardLine(T.intro[0].text);
    await g.tween(g.renderer.grade, { sepia: 0, saturation: LIGHTING.day.grade.saturation, vignette: LIGHTING.day.grade.vignette }, 3.5);
    await card;
    g.audio.play('myna', { caption: '' });
    g.rig.follow();
    g.mode = 'play';
    g.input.requestLock();
  }

  async morningBeat() {
    const g = this.game;
    const { Boon, Farid } = this.cast;
    const serve = this.marker('COUNTER_Serve').pos;
    g.objective('Step inside the kopitiam.', serve);
    await g.waitUntil(() => g.mode === 'play' && this.player.root.position.distanceTo(serve) < 2.6);
    g.mode = 'cutscene';
    g.objective(null);
    Boon.faceTowards(this.player.root.position);
    this.player.faceTowards(Boon.root.position);
    await this.lines(T.morning.greet);
    // Farid points out the chalk board.
    g.rig.cut(this.marker('CAM_Counter').pos, this.marker('NPC_Boon').pos.clone().add(V(0, 2.3, -1.3)), 2.5);
    await this.lines(T.morning.board, { frame: false });
    Farid.play('Idle');
    this.endBarks = this.setupBarks(T.barks);
    this.resume();
    await this.serveOrder(T.orders.ahpek1);
    g.objective(null);
    g.ui.toast('Your camera', g.input.isTouch ? 'Tap the camera button (top right) any time to look closer and take photos.' : 'Press C (or right-click) any time to raise your camera, look closer and take photos.', 7);
    // A breather before ten o'clock: a chat with a regular (or a few seconds of looking around).
    g.objective(T.morning.lookAround);
    this.resume();
    const chats = this.chats || 0, t0 = g.time;
    await g.waitUntil(() => g.mode === 'play' && ((this.chats || 0) > chats || g.time - t0 > 16));
    g.objective(null);
  }

  /** Take an order, (optionally ask Siti), make the drink at the counter, carry it over, serve. */
  async serveOrder(spec, { taken = false, ready = false } = {}) {
    const g = this.game;
    const who = this.cast[spec.who];
    const target = this.cast[spec.seat] || who;
    const name = this.nameOf(spec.who);
    const forName = this.nameOf(spec.seat || spec.who);   // who drinks it (the cross-order is for someone else)
    const words = spec.words || drinkName(spec.order);
    // 1) Take the order (unless the customer already gave it).
    if (!taken) {
      who.indicator('important');
      g.objective(`Take ${name}’s order.`, who);
      this.resume();
      await this.interactOnce(who, `Take ${name}’s order`);
      who.indicator(null);
      await this.lines(spec.ask);
    }
    // 2) Worries: Siti has the answer.
    if (spec.siti) {
      const siti = this.cast.Siti;
      siti.indicator('important');
      g.objective(`${T.worries.askSiti}: what should Sparky tell ${name}?`, siti);
      this.resume();
      await this.interactOnce(siti, T.worries.askSiti);
      siti.indicator(null);
      await this.lines(spec.siti);
    }
    // 3a) Boon has already poured it: collect it from the counter and take it over.
    if (ready) {
      const serve = this.marker('COUNTER_Serve');
      g.objective(`Collect ${forName}’s ${words} from Boon.`, serve.pos);
      this.resume();
      await this.interactOnce(serve.pos, `Take the ${words}`, { radius: 1.6 });
      this.cast.Boon.faceTowards(this.player.root.position);
      g.audio.play('cup-clink', { volume: 0.6 });
      this.carry(spec.order);
      g.objective(`Bring the ${words} to ${forName}.`, target);
      target.indicator('important');
      this.resume();
      await this.interactOnce(target, `Serve ${forName}`);
      target.indicator(null);
      this.putDown(target);
      g.audio.play('pickup-chime', { volume: 0.5 });
      g.objective(null);
      await this.lines(spec.correct || spec.after || []);
      if (spec.fact) g.ui.toast(spec.fact.title, spec.fact.text, 11);
      return;
    }
    // 3) Make it (again if needed) and serve.
    let attempts = 0;
    for (;;) {
      g.objective(`Make ${name}’s ${words} at the counter.`, this.marker('COUNTER_Serve').pos);
      this.resume();
      await this.interactOnce(this.marker('COUNTER_Serve').pos, 'Make the drink', { radius: 1.6 });
      const d = await this.counter({ who: name, words }, spec.order, attempts > 0);
      this.carry(d);
      g.objective(`Bring the ${drinkName(d)} to ${forName}.`, target);
      target.indicator('important');
      this.resume();
      await this.interactOnce(target, `Serve ${forName}`);
      target.indicator(null);
      this.putDown(target);
      if (sameDrink(d, spec.order)) {
        g.audio.play('pickup-chime', { volume: 0.5 });
        g.objective(null);
        await this.lines(spec.correct || spec.after || []);
        if (spec.fact) g.ui.toast(spec.fact.title, spec.fact.text, 11);
        return;
      }
      attempts++;
      this.removeLastCup();
      await this.lines(spec.wrong || [{ who: spec.who, text: `That’s not what I asked for, bear. ${words}, please.` }]);
    }
  }

  /** The counter UI. Returns the drink the player built. */
  async counter(ticket, want, hint) {
    const g = this.game;
    const p = this.player;
    g.mode = 'cutscene';
    const serve = this.marker('COUNTER_Serve');
    p.place(serve.pos, serve.yaw);
    p.play('Idle');
    const cup = this.marker('COUNTER_Cup').pos;
    // From the aisle between tables T1 and T2 (Ah Pek sits at T1, right behind Sparky's left shoulder).
    g.rig.cut(serve.pos.clone().add(V(0.8, 1.3, 1.15)), cup.clone().add(V(-0.1, 0.1, 0)), 5);
    this.cast.Boon.faceTowards(p.root.position);
    g.input.releaseLock();
    const d = await makeDrink({ ticket, target: want, hint, onTap: () => g.audio.play('ui-click', { caption: '' }) });
    g.audio.play('kopi-pour');
    await g.wait(1.6);
    g.audio.play('spoon-stir', { caption: '' });
    await g.wait(0.8);
    return d;
  }

  carry(d) {
    const cup = cupMesh(d);
    cup.scale.setScalar(1.6); // Sparky-sized: read at a distance
    cup.position.set(0, 0.52, 0.26);
    this.player.root.add(cup);
    this.carrying = cup;
  }

  putDown(ch) {
    const cup = this.carrying;
    if (!cup) return;
    this.player.root.remove(cup);
    this.carrying = null;
    this.placeCup(cup, ch);
    this.cups.push(cup);
    this.game.audio.play('cup-clink');
  }

  /** Put a cup on the table in front of a seated customer. */
  placeCup(cup, ch) {
    const tableName = ch.seatName ? ch.seatName.replace(/^SEAT_(T\d)_.*/, 'TABLE_$1') : null;
    const top = tableName && this.m[tableName] ? this.marker(tableName).pos : ch.root.position.clone().add(V(0, 0.75, 0));
    const toward = ch.root.position.clone().sub(top).setY(0).normalize().multiplyScalar(0.2);
    cup.position.copy(top).add(toward).add(V(0, 0.005, 0));
    cup.scale.setScalar(1.25);
    this.scene.add(cup);
  }

  removeLastCup() { const c = this.cups.pop(); if (c) this.scene.remove(c); }

  async tenOClock() {
    const g = this.game;
    const { Rohani, Boon } = this.cast;
    this.endBarks?.();
    g.mode = 'cutscene';
    g.objective(null);
    await g.wait(0.6);
    // The song stops mid-verse.
    if (this.radioEmitter) { g.audio.removeEmitter(this.radioEmitter, 0.15); this.radioEmitter = null; }
    this.ambMurmur && (this.ambMurmur.volume = 0.12);
    const st = g.audio.play('radio-static', { volume: 0.25, loop: true });
    const radio = this.marker('RADIO').pos;
    g.rig.cut(radio.clone().add(V(-1.0, 0.25, 1.4)), radio.clone().add(V(0, 0.05, 0)), 3);
    await g.wait(0.8);
    await this.lines(T.tenOClock.radio, { frame: false });
    st.stop(1);
    // While the camera was on the radio, Sparky comes to the middle of the room (wherever he was),
    // so the reactions are framed the same way every time.
    const mid = this.marker('COUNTER_Serve').pos.clone().add(V(1.0, 0, 1.3));
    this.player.place(mid, Math.atan2(Rohani.root.position.x - mid.x, Rohani.root.position.z - mid.z));
    this.player.play('Idle');
    const R = T.tenOClock.react;
    // Makcik understands first: close on her face. Then the room. Then Boon, to Sparky.
    g.rig.frameOne(Rohani, { dist: 1.6, height: 0.02, angle: 0.4, lambda: 3 });
    await this.lines(R.slice(0, 1), { frame: false });
    const wide = this.marker('CAM_Wide');
    g.rig.cut(wide.pos, wide.pos.clone().add(V(Math.sin(wide.yaw), -0.35, Math.cos(wide.yaw)).multiplyScalar(4)), 2.5, true);
    await this.lines(R.slice(1, 3), { frame: false });
    await this.lines(R.slice(3));
    Boon.play('Idle');
    this.ambMurmur && (this.ambMurmur.volume = 0.55);
  }

  async errandBeat() {
    const g = this.game;
    const siti = this.cast.Siti;
    // Corridor voices.
    const spots = this.markersWith('RUMOUR_');
    this.rumourPeople = spots.map((s, i) => {
      const ch = this.spawnExtra(i, s.pos, s.yaw);
      ch.play(i % 2 ? 'Talk' : 'Idle');
      return ch;
    });
    const heard = new Set();
    g.objective(T.errand.hint, siti);
    siti.indicator('important');
    g.audio.play('firecrackers', { volume: 0.5 });
    const watch = g.every(() => {
      if (g.mode !== 'play') return;
      const pp = this.player.root.position;
      this.rumourPeople.forEach((ch, i) => {
        if (heard.has(i) || !T.errand.rumours[i]) return;
        if (pp.distanceTo(ch.root.position) < 3.4) { heard.add(i); this.bark(T.errand.rumours[i]); ch.faceTowards(pp); }
      });
    });
    this.resume();
    await this.interactOnce(siti, 'Talk to Siti');
    watch();
    siti.indicator(null);
    await this.lines(T.errand.siti);
    await this.lines(this.heirlooms.includes('newspaper') ? T.errand.sitiNewspaper : T.errand.sitiNoNewspaper);
    await this.lines(T.errand.sitiGo);
    // Back to the kopitiam together: a fade covers the walk.
    await g.ui.fade(true, 0.6);
    this.seat(siti, 'SEAT_T3_c');
    const sp = this.marker('SPAWN_Sparky');
    this.player.place(sp.pos.clone().add(V(1.0, 0, -1.2)), Math.PI);
    this.rumourPeople.forEach((ch) => this.removeExtra(ch));
    this.rumourPeople = [];
    g.rig.follow();
    g.rig.placeFollow(true, this.world);
    await g.ui.fade(false, 0.6);
  }

  async worriesBeat() {
    const g = this.game;
    const X = T.worries;
    g.mode = 'cutscene';
    await this.lines(X.start);
    // 1) Hear all three worries, in any order.
    const left = X.listen.slice();
    await new Promise((resolve) => {
      const point = () => g.objective(`${X.hint} (${X.listen.length - left.length}/${X.listen.length})`, this.cast[left[0].who]);
      for (const w of X.listen) {
        const ch = this.cast[w.who];
        ch.indicator('important');
        const it = g.addInteract({
          pos: () => ch.root.position, radius: 1.9, priority: 10, label: `Listen to ${this.nameOf(w.who)}`,
          onUse: async () => {
            g.removeInteract(it);
            g.mode = 'cutscene';
            g.ui.prompt(null);
            ch.indicator(null);
            await this.lines(w.lines);
            left.splice(left.indexOf(w), 1);
            if (!left.length) { resolve(); return; }
            point();
            this.resume();
          },
        });
      }
      point();
      this.resume();
    });
    // 2) Siti answers what she can, out loud, and admits what she can't.
    const siti = this.cast.Siti;
    siti.indicator('important');
    g.objective(X.sitiHint, siti);
    this.resume();
    await this.interactOnce(siti, X.askSiti);
    siti.indicator(null);
    g.objective(null);
    await this.lines(X.siti.map((l) => (l.fact ? { fact: X.facts[l.fact] } : l)));
    // 3) The one drink of the rush: Makcik Rohani's tea, and Siti's honest answer with it.
    await this.serveOrder({ ...X.order, fact: null }, { taken: true, ready: true });
    g.mode = 'cutscene';
    // The payoff: across the room, Auntie Letchumi pats the stool beside her; Makcik Rohani smiles back.
    // (Nobody moves now; in the evening they sit together.)
    g.ui.el.toast.classList.add('hidden');       // nothing over the payoff
    g.rig.cut(V(1.0, 2.1, -9.6), V(0, 0.8, -4.7), 2, true);
    await this.lines(X.pat, { frame: false });
    await this.lines(T.worries.done, { frame: false });
    g.ui.toast(X.order.fact.title, X.order.fact.text, 11);
    g.objective(null);
  }

  // ------------------------------------------------------------------ evening
  async eveningBeat() {
    const g = this.game;
    const { Rajan, Ravi, Farid, AhPek, Letchumi, Rohani, Siti, Boon } = this.cast;
    g.mode = 'cutscene';
    await g.ui.fade(true, 1.0);
    for (const c of this.cups) this.scene.remove(c);
    this.cups = [];
    this.setLighting('evening');
    this.tv.standby(true);
    this.tvStatic = g.audio.emitter('tv-static', this.marker('TV').pos, { radius: 6, volume: 0.35 });
    // Evening seating: regulars around the tables, the block's neighbours standing, Farid at the counter end.
    this.seat(AhPek, 'SEAT_T2_c');
    this.seat(Letchumi, 'SEAT_T2_d');
    this.seat(Rohani, 'SEAT_T2_b');
    this.seat(Siti, 'SEAT_T3_c');
    this.seat(Ravi, 'SEAT_T5_d');
    this.stand(Boon, 'NPC_Boon');
    this.stand(Farid, 'NPC_Farid');
    this.crowd = this.markersWith('CROWD_').slice(0, 11).map((s, i) => { const ch = this.spawnExtra(i + 3, s.pos, s.yaw); return ch; });
    const sp = this.marker('SPAWN_Sparky');
    this.player.place(sp.pos.clone().add(V(-0.8, 0, -1.4)), Math.PI);
    g.rig.follow();
    g.rig.placeFollow(true, this.world);
    await this.cardLine(T.evening.card.text);
    this.ambMurmur && (this.ambMurmur.volume = 0.8);
    await g.ui.fade(false, 1.0);
    // Mr. Rajan arrives from the corridor (the east side of the doorway, clear of the crowd) and sits with his son.
    const fy = this.marker('RAJAN_Door').pos.y;
    this.stand(Rajan, 'RAJAN_Door');
    Rajan.place(V(2.5, fy, -2.5));
    this.player.place(V(1.35, fy, -3.25));
    this.player.faceTowards(Rajan.root.position, true);
    Rajan.faceTowards(this.player.root.position, true);
    g.rig.frameTwo(this.player, Rajan, { lambda: 2 });
    await this.lines(T.evening.rajan);
    await this.lines(this.heirlooms.includes('rice') ? T.evening.rajanRice : T.evening.rajanNoRice);
    this.seat(Rajan, 'SEAT_T5_c');
    if (this.heirlooms.includes('photo')) {
      const wf = this.marker('WALL_Focus').pos;
      g.rig.cut(wf.clone().add(V(0.35, 0.3, 2.3)), wf.clone().add(V(0, 0.6, 0)), 3);
      await this.lines(T.evening.photo, { frame: false });
    }
    if (this.kindness.has('bundles')) {
      const nb = this.crowd[1];
      if (nb) { this.cast.Neighbour = nb; await this.lines(T.evening.bundles); delete this.cast.Neighbour; }
    }
    if (this.kindness.has('water')) await this.lines(T.evening.water);
    // The last order of the day: Ah Pek orders for Auntie Letchumi.
    // Boon pours it (no counter this time); Sparky takes it over.
    const x = T.evening.crossOrder;
    g.mode = 'cutscene';
    g.rig.frameTwo(AhPek, Letchumi, { lambda: 2.5 });
    await this.lines(x.ask, { frame: false });
    g.audio.play('kopi-pour');
    await this.serveOrder({ ...x, words: 'Teh-O ga dai' }, { taken: true, ready: true });
    g.mode = 'cutscene';
    // Farid squeezes onto the bench next to Ravi.
    this.seat(Ravi, 'BENCH_2');
    this.seat(Farid, 'BENCH_1');
    // The boys turn on the bench and look up at the set.
    const tvp = this.marker('TV').pos;
    for (const ch of [Ravi, Farid]) ch.place(ch.root.position, Math.atan2(tvp.x - ch.root.position.x, tvp.z - ch.root.position.z));
    this.lookAt([Ravi, Farid], tvp);
    await this.lines(T.evening.tvCall);
    g.objective(null);
  }

  async tvBeat() {
    const g = this.game;
    const X = T.tv;
    g.mode = 'cutscene';
    g.input.releaseLock();
    this.player.root.visible = true;
    const tvM = this.marker('TV');
    const screenPos = tvM.pos;
    const f = V(Math.sin(tvM.yaw), 0, Math.cos(tvM.yaw));
    const close = screenPos.clone().addScaledVector(f, 0.82).add(V(0, 0.04, 0));
    // Reactions from the television's point of view: just under the set, looking back at the room.
    const crowdCam = { pos: screenPos.clone().addScaledVector(f, 0.45).add(V(0, -0.6, 0)) };
    const crowdLook = V(0.9, 1.05, -7.0);
    if (this.tvStatic) { g.audio.removeEmitter(this.tvStatic, 0.3); this.tvStatic = null; }
    this.ambience(false);
    this.lamps.forEach((l) => { l.intensity *= 0.6; });
    // Over the crowd's shoulders first, then slowly in towards the screen.
    g.rig.cut(screenPos.clone().addScaledVector(f, 2.6).add(V(0, -0.35, 0)), screenPos, 1, true);
    g.rig.cut(close, screenPos.clone().add(V(0, -0.01, 0)), 0.35);
    let reaction = 0, crowdUntil = 0;
    const onTime = (t) => {
      const r = X.reactions[reaction];
      if (r && t >= r.at) {
        reaction++;
        crowdUntil = t + 6;
        g.rig.cut(crowdCam.pos, crowdLook, 1.5);
        this.bark(r);
      }
      if (crowdUntil && t > crowdUntil) { crowdUntil = 0; g.rig.cut(close, screenPos, 1.2); }
    };
    // Every face in the room turns to the screen.
    this.lookAt([...Object.values(this.cast), ...(this.crowd || [])].filter((c) => c.root.visible), screenPos);
    await this.tv.play({ label: X.label, credit: X.credit, skipLabel: X.skip, onTime });
    this.tv.standby(false);
    // His words later in the same press conference, over the silent room.
    g.rig.cut(crowdCam.pos, crowdLook, 1.2);
    await this.lines(X.after, { frame: false });
    // Sparky takes the photograph: everyone in front of the television.
    // From the corner under the set, so the photo catches the faces turned to the screen.
    // From the far corner under the set: the boys on the bench (still looking up at it) in the
    // foreground, the room behind them.
    const pos = V(4.1, this.marker('SEAT_T3_b').pos.y, -10.8);
    this.player.place(pos, 0);
    const aim = V(-0.4, 1.0, -6.0);
    g.objective(X.snapHint);
    const eye = this.player.headPosition().add(V(0, 0.1, 0));
    this.player.faceTowards(aim, true);
    g.mode = 'play';
    await this.takePhoto('Anguish', eye, aim, { allowCancel: false });
    g.objective(null);
    this.ambience(true);
    this.ambMurmur && (this.ambMurmur.volume = 0.3);
  }

  async wallBeat() {
    const g = this.game;
    this.lookAt([]);
    const X = T.wallChoice;
    const { Boon, Siti, Farid } = this.cast;
    g.mode = 'cutscene';
    await g.ui.fade(true, 0.9);
    // Later: the crowd has gone home.
    (this.crowd || []).forEach((ch) => this.removeExtra(ch));
    this.crowd = [];
    for (const k of ['AhPek', 'Letchumi', 'Rohani', 'Ravi']) this.hide(this.cast[k]);
    this.hide(this.cast.Rajan);
    const focus = this.marker('WALL_Focus');
    const stand = focus.pos.clone().add(V(0.0, 0, 1.55)).setY(0.15);
    this.player.place(stand, Math.PI);
    Boon.stop(); Boon.place(stand.clone().add(V(-0.9, 0, 0.1)), Math.PI); Boon.play('Idle');
    this.stand(Siti, 'SEAT_T3_a'); Siti.faceTowards(focus.pos, true);
    this.stand(Farid, 'SEAT_T3_d'); Farid.faceTowards(focus.pos, true);
    // Back from the wall, at eye height, so the portraits and the new item fill the frame.
    g.rig.cut(focus.pos.clone().add(V(0.35, 0.05, 2.3)), focus.pos.clone().add(V(0, 0.25, 0)), 1, true);
    await g.ui.fade(false, 0.9);
    g.audio.music('theme-1942', { fade: 3, volume: 0.45 });
    await this.lines(X.lines, { frame: false });
    g.input.releaseLock();
    const ICONS = { newspaper: '📰', flag: '🏳️', sign: '🪧', calendar: '📅' };
    const [id] = await g.ui.pick({ title: X.prompt, sub: 'Choose one.', options: X.options.map((o) => ({ ...o, icon: ICONS[o.id] })), n: 1 });
    this.wallChoice = id;
    save('sparky.wall.ind', id);
    const node = this.nodes[`WALL_${id[0].toUpperCase()}${id.slice(1)}`];
    if (node) node.visible = true;
    g.audio.play('paper');
    const o = X.options.find((x) => x.id === id);
    await this.lines(o.react, { frame: false });
    // Photograph the wall.
    const eye = this.player.headPosition().add(V(0, 0.2, 0));
    const aim = focus.pos.clone().add(V(0, 0.25, 0));
    g.mode = 'play';
    const info = T.snaps[`Wall_${id}`];
    await this.takePhoto('Wall', eye, aim, { allowCancel: false, custom: { id: 'ind-Wall', ...info } });
  }

  async codaBeat() {
    const g = this.game;
    const { Rajan, Farid } = this.cast;
    g.mode = 'cutscene';
    // Mr. Rajan at the doorway, talking back to Boon; Farid and Sparky listening in the foreground.
    const fy = this.marker('RAJAN_Door').pos.y;
    this.stand(Rajan, 'RAJAN_Door');
    Rajan.place(V(-2.2, fy, -2.9));
    Rajan.faceTowards(this.cast.Boon.root.position, true);
    this.stand(Farid, 'CROWD_5');
    Farid.place(V(-1.55, fy, -5.0));
    Farid.faceTowards(Rajan.root.position, true);
    this.player.place(V(-0.75, fy, -4.85), 0);
    this.player.faceTowards(Rajan.root.position, true);
    g.rig.cut(V(0.2, 1.5, -6.6), V(-2.2, 1.25, -2.9), 2, true);
    await this.lines(T.coda.slice(0, 2), { frame: false });
    await this.lines(T.coda.slice(2));
    // Back to the present.
    await g.tween(g.renderer.grade, { sepia: 1, saturation: 0 }, 2.5);
    this.ambience(false);
    await g.ui.fade(true, 1.2, 'sepia');
    this.present.show();
    this.present.closeShot();
    g.rig.cut(g.rig.shot.pos, g.rig.shot.look, 1, true);
    Object.assign(g.renderer.grade, { sepia: 0, saturation: 0.95, vignette: 0.45 });
    g.renderer.grade.tint.setRGB(1, 1, 1);
    await g.ui.fade(false, 1.5);
    this.present.wideShot();
    await this.lines(T.oldBoon, { frame: false });
    await g.ui.fade(true, 1.2);
    await g.ui.card('Chapter 2 complete', 'A Nation Is Born', 'Next: 17 August 1967 — The First Intake (coming soon)', 5);
    g.audio.music(null, { fade: 3 });
    g.mode = 'cutscene';
    this.game.onChapterComplete?.('ind');
  }

  // ------------------------------------------------------------------ extras
  spawnExtra(i, pos, yaw) {
    const m = CROWD[i % CROWD.length];
    const gltf = this.crowdModels[i % CROWD.length];
    const ch = new Character(`Extra${i}`, gltf, { height: m.height, placeholder: { height: m.height } });
    const tint = new THREE.Color(CROWD_TINTS[i % CROWD_TINTS.length]);
    ch.model.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = false;
      o.material = [].concat(o.material).map((mm) => { const c = mm.clone(); c.color?.multiply(tint); return c; });
      if (o.material.length === 1) o.material = o.material[0];
    });
    ch.place(pos, yaw);
    ch.play('Idle');
    this.scene.add(ch.root);
    this.extras.push(ch);
    this.game.npcs.push(ch);
    this.world.dynamic.push(ch.collider);
    return ch;
  }

  removeExtra(ch) {
    this.scene.remove(ch.root);
    this.extras = this.extras.filter((x) => x !== ch);
    this.game.npcs = this.game.npcs.filter((x) => x !== ch);
    this.world.dynamic = this.world.dynamic.filter((x) => x !== ch.collider);
  }

  // ------------------------------------------------------------------ per-frame
  /** Turn these characters' heads towards a point (on top of their animation); lookAt([]) clears. */
  lookAt(list, target = null) {
    for (const L of this.looks || []) if (!list.includes(L.ch)) L.out = true;
    const keep = (this.looks || []).filter((L) => !L.out || L.w > 0);
    for (const ch of list) {
      const L = keep.find((k) => k.ch === ch);
      if (L) { L.target = target.clone(); L.out = false; } else keep.push({ ch, target: target.clone(), w: 0 });
    }
    this.looks = keep;
  }

  updateLooks(dt) {
    if (!this.looks?.length) return;
    for (const L of this.looks) {
      L.w = THREE.MathUtils.clamp(L.w + (L.out ? -dt : dt) * 1.5, 0, 1);
      if (!L.head) {
        // The head bone's own forward axis, from the bind pose (models face +Z at bind).
        L.ch.model?.traverse((o) => {
          if (L.head || !o.isSkinnedMesh) return;
          const i = o.skeleton.bones.findIndex((b) => b.name === 'head');
          if (i < 0) return;
          L.head = o.skeleton.bones[i];
          const q = new THREE.Quaternion();
          o.skeleton.boneInverses[i].clone().invert().decompose(new THREE.Vector3(), q, new THREE.Vector3());
          L.fwd = new THREE.Vector3(0, 0, 1).applyQuaternion(q.invert());
        });
      }
      const head = L.head;
      if (!head || !L.w || !L.ch.root.visible) continue;
      head.updateWorldMatrix(true, false);
      const hp = head.getWorldPosition(_lv1);
      const d = _lv2.copy(L.target).sub(hp).normalize();
      // Limit the turn to what a neck can do, relative to the way the body faces.
      let a = Math.atan2(d.x, d.z) - L.ch.yaw;
      a = Math.atan2(Math.sin(a), Math.cos(a));
      a = THREE.MathUtils.clamp(a, -1.1, 1.1);
      const pitch = THREE.MathUtils.clamp(Math.asin(THREE.MathUtils.clamp(d.y, -1, 1)), -0.3, 0.6);
      const y = L.ch.yaw + a;
      d.set(Math.sin(y) * Math.cos(pitch), Math.sin(pitch), Math.cos(y) * Math.cos(pitch));
      head.getWorldQuaternion(_lq2);
      _lq1.setFromUnitVectors(_lv1.copy(L.fwd).applyQuaternion(_lq2).normalize(), d);
      _lq1.copy(_lq4.copy(_lqI).slerp(_lq1, L.w * L.w * (3 - 2 * L.w)));
      head.parent.getWorldQuaternion(_lq3).invert();
      head.quaternion.copy(_lq3.multiply(_lq1).multiply(_lq2));
    }
    this.looks = this.looks.filter((L) => !(L.out && L.w <= 0));
  }

  /** While carrying a cup, Sparky's arms reach forward and his paws hold the saucer (on top of Walk/Idle). */
  updateCarryArms(dt) {
    const p = this.player;
    if (!p) return;
    this.carryW = THREE.MathUtils.clamp((this.carryW || 0) + (this.carrying ? dt : -dt) * 5, 0, 1);
    if (!this.carryW) return;
    this.carryArms ||= ['L', 'R'].map((sd) => ({ sd, bone: p.model.getObjectByName(`arm_${sd}`) })).filter((a) => a.bone);
    const k = this.carryW * this.carryW * (3 - 2 * this.carryW);
    p.root.updateMatrixWorld(true);
    for (const a of this.carryArms) {
      const b = a.bone;
      b.updateWorldMatrix(true, false);
      const sh = b.getWorldPosition(_lv1);
      // paw target: under the saucer's rim, a little in front of the chest
      const tgt = _lv2.set(a.sd === 'L' ? 0.1 : -0.1, 0.47, 0.25);
      p.root.localToWorld(tgt);
      b.getWorldQuaternion(_lq2);
      const along = new THREE.Vector3(0, 1, 0).applyQuaternion(_lq2).normalize();
      _lq1.setFromUnitVectors(along, tgt.sub(sh).normalize());
      _lq1.copy(_lq4.copy(_lqI).slerp(_lq1, k));
      b.parent.getWorldQuaternion(_lq3).invert();
      b.quaternion.copy(_lq3.multiply(_lq1).multiply(_lq2));
    }
  }

  update(dt) {
    this.updateLooks(dt);
    this.updateCarryArms(dt);
    if (this.present?.active) this.present.update(dt);
    for (const f of this.fans) f.rotation.y += dt * (this.lighting === 'evening' ? 5 : 4.2);
    this.tv?.tickStatic();
    // Today: an East-West Line train glides along the viaduct beyond the block.
    const train = this.nodes?.NOW_Train;
    if (train && this.era === 'now') { this.trainT = ((this.trainT || 0) + dt * 16) % 320; train.position.z = this.trainBaseZ + this.trainT - 150; }
    if (this.carrying) this.carrying.position.y = 0.52 + Math.sin(performance.now() / 180) * 0.006 * Math.min(1, this.player.speedNow);
  }

  dispose() {
    this.aborted = true;
    this.tv?.dispose();
    document.querySelectorAll('.kopi').forEach((e) => e.remove());
    this.scene?.traverse((o) => {
      o.geometry?.dispose?.();
      if (o.material) [].concat(o.material).forEach((m) => { m.map?.dispose?.(); m.dispose?.(); });
    });
  }
}
