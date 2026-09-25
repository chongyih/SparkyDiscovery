import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import T from './ns-text.js';
import T2 from './ind-text.js';
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
import { spawnNowPeople, preloadNowPeople } from './ns-now.js';
import { Drill, CMD } from './ns-drill.js';
import { buildCampFallback } from './ns-fallback.js';
import * as P from './ns-props.js';
import * as D from './ind-decals.js';

// Chapter 3 — "The First Intake" (September 1967 → Saturday 2 March 1968) and the 2026 ending.
// Script: docs/ch3-script.md. Plan and contracts: docs/design.md (Chapter 3; camp set and cast contracts).
// Sets: tools/build_camp.py (camp.glb: parade square, barracks, night scrub, community centre) and Chapter 2's
// kopitiam.glb. Cast: tools/build_1967_npcs.py. The drill: ns-drill.js.

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const load = (k, fb) => { try { return JSON.parse(localStorage.getItem(k)) ?? fb; } catch { return fb; } };
const save = (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch { /* ignore */ } };

const NAMES = {
  OldBoon: 'Mr. Boon', Boon: 'Boon', Siti: 'Siti', Farid: 'Farid', FaridCiv: 'Farid', AhHock: 'Ah Hock', Ravi: 'Ravi', RaviCiv: 'Ravi',
  Leo: 'Leo', Osman: 'Sergeant Osman', Rajan: 'Mr. Rajan', AhHockMa: 'Ah Hock’s Ah Ma', Neighbour: 'Neighbour', Rohani: 'Makcik Rohani',
  AhPek: 'Ah Pek Tan', Letchumi: 'Auntie Letchumi', PA: 'The Minister', Farid77: 'Farid', Irfan: 'Irfan', Narrator: '', caller: 'Sergeant Osman',
};

// fallback: an older model to stand in if a Chapter 3 GLB hasn't been built yet.
const CAST = {
  Boon: { file: 'npc-boon65', height: 1.64, walk: 0.72, run: 1.9 },
  Siti: { file: 'npc-siti65', height: 1.56, walk: 0.64, run: 1.6 },
  Rajan: { file: 'npc-rajan65', height: 1.69, walk: 0.62, run: 1.6 },
  FaridCiv: { file: 'npc-farid', height: 1.62, walk: 0.8, run: 2.09 },
  RaviCiv: { file: 'npc-ravi', height: 1.64, walk: 0.69, run: 1.8 },
  Farid: { file: 'npc-farid-ns', fallback: 'npc-farid', height: 1.667, walk: 0.75, run: 2.09 },
  AhHock: { file: 'npc-ahhock-ns', fallback: 'npc-man-cn-young', height: 1.747, walk: 0.736, run: 1.9 },
  Ravi: { file: 'npc-ravi-ns', fallback: 'npc-ravi', height: 1.687, walk: 0.724, run: 1.85 },
  Leo: { file: 'npc-leo-ns', fallback: 'npc-man-cn-young', height: 1.712, walk: 0.811, run: 2.0 },
  Osman: { file: 'npc-osman', fallback: 'npc-soldier', height: 1.727, walk: 0.71, run: 1.8 },
  Adviser: { file: 'npc-adviser', fallback: 'npc-man-in', height: 1.777, walk: 0.711, run: 1.8 },
  Adviser2: { file: 'npc-adviser', fallback: 'npc-man-in', height: 1.777, walk: 0.711, run: 1.8 },
  AhHockMa: { file: 'npc-ahhockma', fallback: 'npc-woman-cn', height: 1.489, walk: 0.418, run: 1.2 },
  Minister: { file: 'npc-minister', fallback: 'npc-shopkeeper-cn', height: 1.682, walk: 0.625, run: 1.6 },
  Rohani: { file: 'npc-rohani', height: 1.53, walk: 0.57, run: 1.5 },
  AhPek: { file: 'npc-ahpek', height: 1.56, walk: 0.45, run: 1.2 },
  Letchumi: { file: 'npc-letchumi', height: 1.5, walk: 0.47, run: 1.25 },
  Neighbour: { file: 'npc-woman-cn', height: 1.57, walk: 0.55, run: 1.4 },
};
const FINALE = {
  Farid77: { file: 'npc-farid77', fallback: 'npc-oldboon', height: 1.627, walk: 0.544, run: 1.2 },
  Irfan: { file: 'npc-irfan', fallback: 'npc-man-cn-young', height: 1.727, walk: 0.794, run: 2.0 },
};
// Families at the send-off, spectators in the stands: Chapter 1's townsfolk, tinted.
const CROWD = [
  { file: 'npc-shopkeeper-cn', height: 1.62 }, { file: 'npc-woman-cn', height: 1.57 }, { file: 'npc-man-in', height: 1.73 },
  { file: 'npc-woman-my', height: 1.55 }, { file: 'npc-man-cn-young', height: 1.66 },
];
const CROWD_TINTS = [0xffffff, 0xd9e2e8, 0xe8e0c8, 0xd8c8d8, 0xc8d8c0, 0xf0e0d0, 0xd0d8e8];

const AUDIO = {
  'band-march': { loop: true, volume: 0.55 }, 'truck-engine': { loop: true, volume: 0.5 },
  'night-ambience': { loop: true, volume: 0.45 }, cicadas: { loop: true, volume: 0.3 }, murmur: { loop: true, volume: 0.45 },
  street: { loop: true, volume: 0.4 }, 'ceiling-fan': { loop: true, volume: 0.35 }, impact: { volume: 0.5 },
  'footstep-1': { volume: 0.35 }, 'footstep-2': { volume: 0.35 }, 'footstep-3': { volume: 0.35 }, 'footstep-4': { volume: 0.35 }, 'footstep-5': { volume: 0.35 },
  'camera-shutter': {}, 'pickup-chime': { volume: 0.6 }, 'ui-click': { volume: 0.5 }, paper: {},
  'theme-1942': { loop: true, music: true, volume: 0.5 },
};

export const SLOTS = [
  { id: 'ns-MoneyTin', chapter: 'ns', year: '1967', hint: 'Look in Boon’s money tin… (optional)' },
  { id: 'ns-Mexicans', chapter: 'ns', year: '1967', hint: 'Who are the men in straw hats? (optional)' },
  { id: 'ns-Letter', chapter: 'ns', year: 'Feb 1968', hint: 'A letter home.' },
  { id: 'ns-Parade', chapter: 'ns', year: '2 Mar 1968', hint: 'The passing-out parade.' },
  { id: 'ns-Phone', chapter: 'ns', year: '2026', hint: 'The last page.' },
  { id: 'ns-Roll2', chapter: 'ns', year: '?', hint: 'Roll 2: not yet developed.' },
];

// The kopitiam's day calendar in 1967–68 (3 Sep 1967 was a Sunday; 27 Feb 1968 a Tuesday).
const CAL = {
  sendoff: { head: '1967 · SEPTEMBER · 九月', day: 3, weekday: 'SUNDAY · 星期日', malay: 'Ahad' },
  reading: { head: '1968 · FEBRUARY · 二月', day: 27, weekday: 'TUESDAY · 星期二', malay: 'Selasa' },
};

const LIGHTING = {
  day: { bg: '#cfe0ea', fog: '#d9dfe0', near: 60, far: 320, top: '#7fa8c9', horizon: '#e9e3cf', bottom: '#a39d8f',
    hemi: ['#f4f1e6', '#7b7466', 1.2], sun: ['#fff0d6', 2.6], env: 0.35, lamps: 0,
    grade: { saturation: 0.95, sepia: 0, contrast: 1.05, vignette: 0.36 }, tint: [1, 1, 1] },
  parade: { bg: '#d4e2ea', fog: '#dee3e2', near: 70, far: 340, top: '#6f9ccc', horizon: '#eee7d2', bottom: '#a8a292',
    hemi: ['#f6f2e6', '#7b7466', 1.25], sun: ['#fff2dc', 2.8], env: 0.38, lamps: 0,
    grade: { saturation: 1.0, sepia: 0, contrast: 1.06, vignette: 0.34 }, tint: [1.02, 1, 0.97] },
  now: { bg: '#d5e6f2', fog: '#dde6ea', near: 60, far: 340, top: '#6fa3d6', horizon: '#eef0ea', bottom: '#a8a296',
    hemi: ['#f6f7f2', '#7b7466', 1.3], sun: ['#fff6e6', 2.6], env: 0.4, lamps: 0,
    grade: { saturation: 1.05, sepia: 0, contrast: 1.05, vignette: 0.32 }, tint: [1, 1, 1] },
  night: { bg: '#0e1420', fog: '#101622', near: 8, far: 60, top: '#0b1224', horizon: '#1d2638', bottom: '#0a0c10',
    hemi: ['#6f82b0', '#1c1d22', 0.75], sun: ['#a9bde6', 0.8], env: 0.14, lamps: 2.2,
    grade: { saturation: 0.82, sepia: 0, contrast: 1.08, vignette: 0.5 }, tint: [0.94, 0.98, 1.08] },
  kopi: { bg: '#cfe0ea', fog: '#d9dfe0', near: 40, far: 220, top: '#7fa8c9', horizon: '#e6e2d2', bottom: '#a39d8f',
    hemi: ['#f4f1e6', '#7b7466', 1.25], sun: ['#fff0d6', 2.4], env: 0.35, lamps: 0.6,
    grade: { saturation: 0.95, sepia: 0, contrast: 1.05, vignette: 0.38 }, tint: [1, 1, 1] },
  kopiEvening: { bg: '#3e4660', fog: '#4a4a58', near: 25, far: 150, top: '#27324f', horizon: '#d98a5a', bottom: '#3a3530',
    hemi: ['#8a90a8', '#3a3228', 0.55], sun: ['#ff9a5a', 0.7], env: 0.18, lamps: 2.2,
    grade: { saturation: 0.92, sepia: 0.05, contrast: 1.08, vignette: 0.5 }, tint: [1.04, 0.98, 0.92] },
};

async function loadWithFallback(file, fallback, prog) {
  const m = await loadModel(file, prog);
  if (m || !fallback) return m;
  console.warn(`[ns] ${file}.glb not built yet; using ${fallback}`);
  return loadModel(fallback);
}

export class NSChapter extends ChapterKit {
  constructor(game, { skipPrologue = false } = {}) {
    super(game, { id: 'ns', T, names: NAMES });
    this.skipPrologue = skipPrologue;
    this.heirlooms = load('sparky.heirlooms.ww2', []);
    this.kindness = new Set(load('sparky.kindness.ww2', []));
    this.wallChoice = load('sparky.wall.ind', null);
    this.kindness3 = new Set();
    this.letter = { opening: null, openingId: null, body: [], ps: {}, paw: false };
    this.lamps = [];
    this.props = {};
  }

  // ------------------------------------------------------------------ loading
  async load(onProgress) {
    const g = this.game;
    const steps = [];
    const castList = Object.entries(CAST);
    const finaleList = Object.entries(FINALE);
    const total = castList.length + finaleList.length + CROWD.length + 4;
    const prog = (i) => (p) => { steps[i] = p; onProgress?.(steps.reduce((a, b) => a + (b || 0), 0) / total); };
    const [camp, kopi, sparkyNS, sparkyCiv, ...rest] = await Promise.all([
      loadModel('camp', prog(0)), loadModel('kopitiam', prog(1)),
      loadWithFallback('sparky-ns', 'sparky', prog(2)), loadWithFallback('sparky-ind', 'sparky', prog(3)),
      ...castList.map(([, c], i) => loadWithFallback(c.file, c.fallback, prog(4 + i))),
      ...finaleList.map(([, c], i) => loadWithFallback(c.file, c.fallback, prog(4 + castList.length + i))),
      ...CROWD.map((c, i) => loadModel(c.file, prog(4 + castList.length + finaleList.length + i))),
    ]);
    const castModels = rest.slice(0, castList.length);
    this._gltfs = Object.fromEntries(castList.map(([k], i) => [k, castModels[i]]));
    const finaleModels = rest.slice(castList.length, castList.length + finaleList.length);
    this.crowdModels = rest.slice(castList.length + finaleList.length);
    g.audio.setCaptions(T.captions);
    const audioLoad = g.audio.define(AUDIO);
    await D.loadFonts?.();

    const pmrem = new THREE.PMREMGenerator(g.renderer.renderer);
    this.envMap = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    pmrem.dispose();

    // Camp scene (parade square, barracks, night scrub, community centre).
    this.sets = {};
    const campScene = new THREE.Scene();
    const campRoot = camp ? camp.scene : buildCampFallback();
    if (!camp) console.warn('[ns] camp.glb not built yet (tools/build_camp.py); using the stand-in set');
    this.sets.camp = this.makeSet('camp', campScene, campRoot);
    this.setupCamp(this.sets.camp);
    // The kopitiam (Chapter 2's set), for the send-off morning and the reading.
    const kopiScene = new THREE.Scene();
    if (kopi) {
      this.sets.kopi = this.makeSet('kopi', kopiScene, kopi.scene);
      this.setupKopitiam(this.sets.kopi);
    } else {
      console.warn('[ns] kopitiam.glb missing; the kopitiam beats use the community-centre area');
      this.sets.kopi = null;
    }

    // Players: Sparky in 1967 civvies (kopitiam, community centre) and in Temasek green (the camp).
    this.sparkys = {};
    for (const [k, gltf] of Object.entries({ ns: sparkyNS, civ: sparkyCiv })) {
      const p = new Player(gltf);
      p.model.traverse((o) => { if (o.isMesh) o.castShadow = false; if (/rifle/i.test(o.name)) o.visible = false; });
      p.onStep = () => g.audio.play(`footstep-${1 + Math.floor(Math.random() * 5)}`, { volume: 0.7, rate: 0.9 + Math.random() * 0.25, caption: '' });
      const b = createBrownie();
      b.scale.setScalar(0.11); b.position.set(0, 0.5, 0.27); b.visible = false;
      p.root.add(b);
      p.brownieProp = b;
      this.sparkys[k] = p;
    }
    this.player = this.sparkys.civ;
    this.brownie = this.player.brownieProp;

    castList.forEach(([key, cfg], i) => {
      const ch = new Character(key, castModels[i], { height: cfg.height, walkSpeed: cfg.walk, runSpeed: cfg.run, placeholder: { height: cfg.height } });
      ch.model.traverse((o) => { if (o.isMesh) o.castShadow = false; });
      this.cast[key] = ch;
      this.hide(ch);
    });
    this.outfits = { Farid: { civ: this.cast.FaridCiv, ns: this.cast.Farid }, Ravi: { civ: this.cast.RaviCiv, ns: this.cast.Ravi } };
    this.present = new PresentDay(g);
    await Promise.all([this.present.load(this.envMap), preloadNowPeople()]);
    finaleList.forEach(([key, cfg], i) => {
      const ch = new Character(key, finaleModels[i], { height: cfg.height, walkSpeed: cfg.walk, runSpeed: cfg.run, placeholder: { height: cfg.height } });
      ch.model.traverse((o) => { if (o.isMesh) o.castShadow = false; });
      this.cast[key] = ch;
      ch.root.visible = false;
      this.present.scene.add(ch.root);
    });
    this.useScene('camp');
    this.setArea('parade');
    this.setEra('then'); // the title background is the 1968 square, not both eras at once
    await audioLoad;
    onProgress?.(1);
  }

  /** One level scene: sky, lights, colliders, ray meshes and markers. */
  makeSet(name, scene, root) {
    const t = tier();
    scene.background = new THREE.Color('#cfe0ea');
    scene.fog = new THREE.Fog('#d9dfe0', 60, 320);
    const sky = skyDome({ top: '#7fa8c9', horizon: '#e6e2d2', bottom: '#a39d8f', sunDir: V(0.35, 0.7, 0.6), haze: 0.35 });
    scene.add(sky);
    const hemi = new THREE.HemisphereLight('#f4f1e6', '#7b7466', 1.25);
    const sun = new THREE.DirectionalLight('#fff0d6', 2.4);
    sun.castShadow = t.shadows;
    scene.add(hemi, sun, sun.target);
    scene.environment = this.envMap;
    scene.environmentIntensity = 0.35;
    scene.add(root);
    root.updateMatrixWorld(true);
    const world = new World();
    const nodes = {};
    root.traverse((o) => {
      const n = o.name || '';
      if (/^(AREA_|DECAL_|WALL_|TV_Screen|FAN_\d$|THEN_|NOW_|PROP_)/.test(n)) nodes[n] = o;
      if (n.startsWith('COL_')) {
        if (o.isMesh) { const box = world.addBoxFromMesh(o, o.userData.state !== 'now'); if (o.userData.state) box.state = o.userData.state; }
        o.visible = false;
        return;
      }
      if (o.isMesh) {
        o.receiveShadow = true;
        o.castShadow = t.shadows && !/^(DECAL_|WALL_|TV_Screen)/.test(n);
        for (const m of [].concat(o.material)) {
          if (m.map) m.map.anisotropy = t.bloom ? 8 : 2;
          if ('envMapIntensity' in m) m.envMapIntensity = 0.6;
          if (/Decal|Details|Windows/.test(m.name)) { m.polygonOffset = true; m.polygonOffsetFactor = -1; m.polygonOffsetUnits = -2; }
        }
      }
    });
    root.traverse((o) => {
      if (!o.isMesh || o.name.startsWith('COL_')) return;
      let p = o, skip = false;
      while (p && p !== root) { if (/^(NOW_|DECAL_|WALL_|TV_Screen|FAN_|PROP_|THEN_Laundry)/.test(p.name || '')) { skip = true; break; } p = p.parent; }
      if (!skip) world.addRayMesh(o);
    });
    // The fallback set has no COL_ boxes: build its ray meshes from everything (boxes are ground too).
    return { name, scene, root, world, nodes, m: collectMarkers(root), sky, hemi, sun, lamps: [] };
  }

  setupCamp(S) {
    const t = tier();
    const setTex = (name, texture, emissive = false) => {
      const n = S.nodes[name];
      if (!n) return;
      n.traverse((o) => {
        if (!o.isMesh) return;
        o.material = new THREE.MeshStandardMaterial({ map: texture, roughness: 0.8, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4,
          emissive: emissive ? 0xffffff : 0x000000, emissiveMap: emissive ? texture : null, emissiveIntensity: emissive ? 0.3 : 0 });
      });
    };
    setTex('DECAL_Marker', P.markerPlate(T.heritageMarker));
    setTex('DECAL_CCSign', P.ccSign(T.ccSign));
    setTex('DECAL_Banner', P.banner(T.banner));
    // The bed Sparky and Ah Hock carry.
    this.bed = S.nodes.PROP_Bed || P.bedFrame();
    if (!this.bed.parent) S.scene.add(this.bed);
    this.bed.visible = false;
    // Barrack bulbs (lit at night only).
    const lampMarks = Object.keys(S.m).filter((k) => /^LAMP_Bar/.test(k)).map((k) => markerPose(S.m[k]).pos);
    for (const p of lampMarks.slice(0, Math.max(1, t.maxLights - 1))) {
      const l = new THREE.PointLight('#ffd9a0', 0, 8, 1.6);
      l.position.copy(p);
      S.scene.add(l);
      S.lamps.push(l);
    }
    // A torch for the night exercise (Ravi's).
    this.torch = new THREE.SpotLight('#fff1c8', 0, 14, 0.5, 0.6, 1.5);
    S.scene.add(this.torch, this.torch.target);
    // Shadows cover the area in use; fitted per area in setArea().
    S.world.bounds = null;
  }

  setupKopitiam(S) {
    const t = tier();
    const setTex = (name, texture) => {
      const n = S.nodes[name];
      if (!n) return;
      n.traverse((o) => { if (o.isMesh) o.material = new THREE.MeshStandardMaterial({ map: texture, roughness: 0.8, polygonOffset: true, polygonOffsetFactor: -2, polygonOffsetUnits: -4 }); });
    };
    setTex('DECAL_ShopSign', D.shopSign(T2.shopSign));
    Object.entries(T2.neighbourSigns).forEach(([k, v], i) => setTex(`DECAL_Sign_${k}`, D.neighbourSign(v, i)));
    setTex('DECAL_OrderBoard', D.orderBoard(T2.orderBoard));
    // The tear-off calendar, and the coffee-powder calendar poster beside it, show the scene's year.
    this.kopiCalendar = (page) => {
      setTex('DECAL_Calendar', P.calendarPage(page));
      const year = JSON.stringify(page).match(/19\d\d/)?.[0] || T2.poster.year;
      if (this._posterYear !== year) { this._posterYear = year; setTex('DECAL_Poster', D.calendarPoster({ ...T2.poster, year })); }
    };
    this.kopiCalendar(CAL.sendoff);
    setTex('DECAL_Notice', D.notice(T2.notice));
    setTex('DECAL_Portrait_AhMa', D.portrait('ahma'));
    setTex('DECAL_Portrait_Papa', this.heirlooms.includes('photo') ? D.portrait('papa') : D.fuDiamond());
    setTex('DECAL_Mirror', D.congratsMirror(T2.mirror));
    setTex('WALL_Newspaper', D.newspaper());
    setTex('WALL_Flag', D.flag());
    // 1967: Boon has painted Farid's name, small, at the bottom of the 1965 sign.
    const sign = D.fourLanguageSign(T2.newSign);
    if (sign.image?.getContext) {
      const c = sign.image, x = c.getContext('2d');
      x.font = `italic 700 ${Math.round(c.height * 0.075)}px Gelasio, Georgia, serif`;
      x.fillStyle = '#7a2a22'; x.textAlign = 'right'; x.textBaseline = 'bottom';
      x.fillText('— Farid, 1967', c.width * 0.95, c.height * 0.97);
      sign.needsUpdate = true;
    }
    setTex('WALL_Sign', sign);
    setTex('WALL_Calendar', D.calendarPage());
    // 1967: the thing chosen for the wall in 1965 is still up.
    for (const k of ['WALL_Newspaper', 'WALL_Flag', 'WALL_Sign', 'WALL_Calendar']) {
      const n = S.nodes[k];
      if (n) n.visible = !!this.wallChoice && k.toLowerCase() === `wall_${this.wallChoice}`;
    }
    for (const [n, o] of Object.entries(S.nodes)) {
      if (n.startsWith('NOW_') || n.startsWith('DECAL_Now')) o.visible = false;
      else if (n.startsWith('THEN_')) o.visible = true;
    }
    S.world.applyStates(['then']);
    // Boon's television, switched off: dark glass that still catches the lamps (as in Chapter 2).
    if (S.nodes.TV_Screen) {
      S.nodes.TV_Screen.visible = true;
      S.nodes.TV_Screen.traverse((o) => { if (o.isMesh) o.material = new THREE.MeshStandardMaterial({ color: 0x1b211f, roughness: 0.18, metalness: 0.1 }); });
    }
    const lampMarks = Object.keys(S.m).filter((k) => /^LAMP/.test(k)).map((k) => markerPose(S.m[k]).pos);
    for (const p of lampMarks.slice(0, Math.max(1, t.maxLights - 1))) {
      const l = new THREE.PointLight('#eef4ff', 0.6, 7, 1.6);
      l.position.copy(p);
      S.scene.add(l);
      S.lamps.push(l);
    }
    S.world.bounds = { minX: -14.4, maxX: 14.4, minZ: -11.7, maxZ: 9.5 };
    // Ceiling fans spin about their own centres (as in Chapter 2).
    this.fans = [];
    for (const k of ['FAN_1', 'FAN_2']) {
      const n = S.nodes[k];
      let mesh = n?.isMesh ? n : null;
      n?.traverse((o) => { if (!mesh && o.isMesh) mesh = o; });
      if (!mesh) continue;
      mesh.geometry.computeBoundingBox();
      const c = mesh.geometry.boundingBox.getCenter(new THREE.Vector3());
      mesh.geometry.translate(-c.x, 0, -c.z);
      mesh.position.x += c.x * mesh.scale.x;
      mesh.position.z += c.z * mesh.scale.z;
      this.fans.push(mesh);
    }
    // Papa's tiffin carrier (or Boon's own) waits on the counter; the Brownie sits on the shelf.
    this.props.tiffin = P.tiffinCarrier(this.heirlooms.includes('tiffin'));
    this.props.tiffin.scale.setScalar(1.25);
    this.props.tiffin.visible = false;
    S.scene.add(this.props.tiffin);
    this.props.shelfBrownie = createBrownie();
    this.props.shelfBrownie.scale.setScalar(0.11);
    this.props.shelfBrownie.visible = false;
    S.scene.add(this.props.shelfBrownie);
  }

  // ------------------------------------------------------------------ scenes, areas, lighting
  useScene(name) {
    const S = name === 'kopi' ? (this.sets.kopi || this.sets.camp) : this.sets.camp;
    this.set = S;
    this.scene = S.scene;
    this.m = S.m;
    this.world = S.world;
    this.nodes = S.nodes;
    this.sky = S.sky; this.hemi = S.hemi; this.sun = S.sun;
    const g = this.game;
    g.world = this.world;
    // Both outfits of Farid and Ravi come along, whichever one is currently in the cast.
    const people = new Set([...Object.values(this.cast), ...Object.values(this.outfits || {}).flatMap((o) => Object.values(o))]);
    for (const ch of people) if (!FINALE[ch.name]) S.scene.add(ch.root);
    for (const p of Object.values(this.sparkys)) S.scene.add(p.root);
    if (this.bed) S.scene.add(this.bed);
    this.world.dynamic = Object.values(this.cast).filter((c) => !FINALE[c.name]).map((c) => c.collider);
    g.setScene(S.scene);
    g.npcs = [...Object.values(this.cast), ...this.extras];
  }

  usePlayer(kind, pose = null) {
    const g = this.game;
    for (const [k, p] of Object.entries(this.sparkys)) p.root.visible = k === kind;
    this.player = this.sparkys[kind];
    this.brownie = this.player.brownieProp;
    g.player = this.player;
    if (pose) this.player.place(pose.pos, pose.yaw);
    g.rig.setSubject(this.player);
  }

  outfit(key, which) {
    const o = this.outfits[key];
    if (!o) return this.cast[key];
    const ch = o[which], other = o[which === 'ns' ? 'civ' : 'ns'];
    this.cast[key] = ch;
    this.hide(other);
    // The swapped-in character must live in the current scene (it may have been left in the other set) and be
    // updated with the rest; otherwise he stands in line in a scene nobody is looking at.
    if (this.scene && ch.root.parent !== this.scene) this.scene.add(ch.root);
    const g = this.game;
    g.npcs = [...g.npcs.filter((n) => n !== other && n !== ch), ch];
    if (this.world) this.world.dynamic = [...this.world.dynamic.filter((c) => c !== other.collider && c !== ch.collider), ch.collider];
    return ch;
  }

  /** Show one area of the camp set ('parade' | 'barracks' | 'night' | 'cc'); fit the sun's shadows to it. */
  setArea(area) {
    const names = { parade: 'AREA_Parade', barracks: 'AREA_Barracks', night: 'AREA_Night', cc: 'AREA_CC' };
    const S = this.sets.camp;
    for (const [k, n] of Object.entries(names)) if (S.nodes[n]) S.nodes[n].visible = k === area;
    this.area = area;
    const centre = { parade: V(0, 0, -4), barracks: V(200, 0, -2), night: V(-200, 0, -2), cc: V(0, 0, 200) }[area];
    const r = area === 'parade' ? 48 : 22;
    this.fitShadows(S, centre, r);
  }

  fitShadows(S, c, r) {
    if (!S.sun.castShadow) return;
    const dir = V(0.35, 0.8, 0.5).normalize();
    S.sun.position.copy(c).addScaledVector(dir, r + 30);
    S.sun.target.position.copy(c);
    S.sun.target.updateMatrixWorld();
    const size = tier().shadowSize >= 2048 ? 4096 : 2048;
    S.sun.shadow.mapSize.set(size, size);
    Object.assign(S.sun.shadow.camera, { left: -r, right: r, top: r, bottom: -r, near: 1, far: r * 2 + 70 });
    S.sun.shadow.camera.updateProjectionMatrix();
    S.sun.shadow.bias = -0.0006;
    S.sun.shadow.normalBias = 0.03;
    this.game.renderer.renderer.shadowMap.autoUpdate = true;
  }

  setLighting(name) {
    const p = LIGHTING[name];
    const S = this.set;
    const s = S.scene;
    s.background.set(p.bg);
    s.fog.color.set(p.fog); s.fog.near = p.near; s.fog.far = p.far;
    const u = S.sky.material.uniforms;
    u.top.value.set(p.top); u.horizon.value.set(p.horizon); u.bottom.value.set(p.bottom);
    S.hemi.color.set(p.hemi[0]); S.hemi.groundColor.set(p.hemi[1]); S.hemi.intensity = p.hemi[2];
    S.sun.color.set(p.sun[0]); S.sun.intensity = p.sun[1];
    s.environmentIntensity = p.env;
    for (const l of S.lamps) l.intensity = p.lamps;
    Object.assign(this.game.renderer.grade, p.grade);
    this.game.renderer.grade.tint.setRGB(...p.tint);
    this.lighting = name;
  }

  /** 'then' (1967–68) or 'now' (present-day park, for Then & Now). */
  setEra(era) {
    const now = era === 'now';
    for (const [n, o] of Object.entries(this.sets.camp.nodes)) {
      if (n === 'THEN_BedPile') o.visible = false; // the beds for the cut bed-carry scene, stacked by the stairs
      else if (n.startsWith('NOW_')) o.visible = now;
      else if (n.startsWith('THEN_')) o.visible = !now;
    }
    this.sets.camp.world.applyStates(now ? ['now'] : ['then']);
    this.era = era;
  }

  // ------------------------------------------------------------------ cast placement
  place(ch, markerName, clip = 'Idle', fallback = null) {
    const s = this.marker(markerName, fallback || V(0, 0, 0));
    ch.stop();
    ch.place(s.pos, s.yaw);
    ch.play(ch.clips[clip] || ch.procedural ? clip : 'Idle');
    ch.root.userData.show = true;
    ch.root.visible = true;
    return ch;
  }

  hide(ch) { if (!ch) return; ch.stop?.(); ch.root.userData.show = false; ch.root.visible = false; ch.indicator?.(null); }

  hideAll() { for (const ch of Object.values(this.cast)) if (!FINALE[ch.name]) this.hide(ch); this.clearExtras(); }

  placeCast() {
    // Title background: the parade square at work.
    this.usePlayer('ns', this.marker('SPAWN_Sparky'));
    this.player.root.visible = false;
    this.titleCrowd();
  }

  /**
   * Title background: a platoon marching across the square with rifles slung (Sergeant Osman calling the step
   * beside it), a squad at attention in front of an adviser, and a few recruits crossing by the blocks.
   * Marchers walk off one side and come back in off the other, out of shot of the title camera.
   */
  titleCrowd() {
    this.stopTitle?.();
    this.clearExtras();
    const keys = ['Farid', 'AhHock', 'Ravi', 'Leo'];
    const east = Math.PI / 2, west = -Math.PI / 2;
    const groups = [];
    let i = 0;
    const recruit = (pos, yaw, clip) => {
      const ch = this.spawnExtra(i, pos, yaw, this.modelOf(keys[i % keys.length]));
      i++;
      ch.play(ch.clips[clip] ? clip : 'Idle');
      return ch;
    };
    const marching = (files, ranks, lead, yaw, spacing = 1.05) => {
      const dir = Math.sign(Math.sin(yaw));
      const out = [];
      for (let f = 0; f < files; f++) for (let r = 0; r < ranks; r++) {
        const ch = recruit(lead.clone().add(V(-dir * r * spacing, 0, f * 1.1)), yaw, 'March');
        ch.setSpeed(0.95 / 0.78); // the March clip covers ~0.78 m/s
        this.giveRifle(ch, 'sling');
        out.push(ch);
      }
      return out;
    };
    // Framed for the title camera (CAM_Title): the platoon crosses the middle of the frame, above the title
    // text and clear of the chapter prints in the bottom-right corner.
    const platoon = marching(3, 8, V(-12.5, 0, 5.5), east);
    const { Osman, Adviser } = this.cast;
    for (const ch of [Osman, Adviser]) { ch.stop(); ch.root.visible = true; ch.root.userData.show = true; }
    Osman.place(V(-13.5, 0, 9.1), east);
    Osman.play('Walk');
    Osman.setSpeed(0.95 / Osman.walkSpeed);
    groups.push({ chs: [...platoon, Osman], speed: 0.95, dir: 1, from: -46, to: 24 });
    // A second, smaller squad marching the other way at the back of the square.
    const back = marching(2, 6, V(-7.5, 0, -12.5), west);
    groups.push({ chs: back, speed: 0.95, dir: -1, from: 26, to: -44 });
    // A squad at attention, rifles slung (the order is hidden behind the leg at this distance), facing the adviser
    // and the camera.
    const face = -0.43;
    const fwd = V(Math.sin(face), 0, Math.cos(face));
    const right = V(fwd.z, 0, -fwd.x);
    const squadAt = V(-3, 0, 0.3);
    for (let r = 0; r < 3; r++) for (let c = 0; c < 6; c++) {
      const ch = recruit(squadAt.clone().addScaledVector(right, (c - 2.5) * 1.05).addScaledVector(fwd, -r * 1.2), face, 'Attention');
      this.giveRifle(ch, 'sling');
    }
    Adviser.place(squadAt.clone().addScaledVector(fwd, 3.2), face + Math.PI);
    Adviser.play('Idle');
    // Two recruits heading for the blocks along the far walk.
    const walkers = [recruit(V(-19, 0, -9.3), east, 'Walk'), recruit(V(-20.2, 0, -9.9), east, 'Walk')];
    groups.push({ chs: walkers, speed: 0.78, dir: 1, from: -46, to: 24 }); // the Walk clip covers ~0.78 m/s
    // Marchers leave one side of the square and come back in off the other, out of the title camera's view.
    this.stopTitle = this.game.every((dt) => {
      for (const G of groups) {
        for (const ch of G.chs) ch.root.position.x += G.dir * G.speed * dt;
        const xs = G.chs.map((ch) => ch.root.position.x * G.dir);
        if (Math.min(...xs) > G.to * G.dir) for (const ch of G.chs) ch.root.position.x += G.from - G.to;
      }
    });
  }

  titleShot(t) {
    const c = this.marker('CAM_Title', V(-26, 6, 26)).pos;
    const s = Math.sin(t * 0.04);
    return [c.clone().add(V(s * 4, Math.sin(t * 0.06) * 0.3, 0)), V(s * 2, 3.5, -30)];
  }

  // ------------------------------------------------------------------ main flow
  async run() {
    const g = this.game;
    g.album.setSlots(SLOTS);
    g.album.setPages({ realVsImagined: T.realVsImagined, sources: T.sources.map((s) => ({ title: `${s.title} — ${s.publisher}`, url: s.url })), credits: T.credits.audio });
    // Debug: ?beat=morning|sendoff|arrival|drill|rifles|letter|reading|parade|ending jumps straight to a beat.
    this.stopTitle?.(); this.stopTitle = null;
    this.hideAll();
    const beats = ['bridge', 'morning', 'sendoff', 'arrival', 'drill', 'rifles', 'letter', 'reading', 'parade', 'ending'];
    const jump = new URLSearchParams(location.search).get('beat');
    const from = Math.max(0, beats.indexOf(jump));
    if (from === 0 && !this.skipPrologue) { await this.bridge(); await this.thenNow(); }
    if (from <= 1) await this.sendoffMorning();
    if (from <= 2) await this.sendoff();
    if (from <= 3) await this.arrival();
    if (from <= 4) await this.dayOneDrill();
    if (from <= 5) await this.rifles();
    if (from <= 6) await this.letterRound();
    if (from <= 7) await this.reading();
    if (from <= 8) await this.parade();
    await this.ending();
  }

  /** Cut to a new place: fade out, set up, fade in with a title card. */
  async cutTo(fn, card = null) {
    const g = this.game;
    g.mode = 'cutscene';
    g.objective(null);
    await g.ui.fade(true, 0.8);
    this.clearInteracts();
    await fn();
    await g.ui.fade(false, 0.9);
    if (card) await this.cardLine(card.text);
  }

  clearInteracts() {
    this.stopBarks?.(); this.stopBarks = null;
    this.game.interactables = [];
    for (const ch of Object.values(this.cast)) ch.indicator?.(null);
  }

  ambience(list) {
    const g = this.game;
    (this.amb || []).forEach((h) => h?.stop?.(1.2));
    this.amb = (list || []).map(([name, vol]) => g.audio.play(name, { volume: vol, loop: true, fadeIn: 1.5, caption: '' }));
  }

  // ------------------------------------------------------------------ present day: bridge + Then & Now
  async bridge() {
    const g = this.game;
    const Pd = this.present;
    Pd.show();
    g.mode = 'cutscene';
    Object.assign(g.renderer.grade, { sepia: 0, saturation: 0.95, vignette: 0.45, contrast: 1.05, flash: 0 });
    g.renderer.grade.tint.setRGB(1, 1, 1);
    Pd.wideShot(true);
    await g.ui.fade(false, 1.5);
    g.audio.music('theme-1942', { fade: 3, volume: 0.6 });
    await g.ui.card('Queenstown, Singapore', 'Today', '', 2.4);
    await this.lines(T.bridge.slice(0, 1), { frame: false });
    Pd.closeShot();
    await this.lines(T.bridge.slice(1), { frame: false });
    await Pd.pushIn();
    g.audio.play('camera-shutter');
    g.audio.music(null, { fade: 2 });
    Pd.active = false;
  }

  /** Line up the old view of the parade ground with the park today. */
  async thenNow() {
    const g = this.game;
    const X = T.thenNow;
    this.useScene('camp');
    this.setArea('parade');
    this.hideAll();
    for (const p of Object.values(this.sparkys)) p.root.visible = false;
    const pose = this.marker('THEN_NOW_Camera', V(-26, 1.45, 26));
    const pitch = 0.04;
    const dirAt = (yaw, p) => V(Math.sin(yaw) * Math.cos(p), -Math.sin(p), Math.cos(yaw) * Math.cos(p));
    const eye = pose.pos.clone();
    // 1) The 1968 view from this exact spot: ranks on the square, the blocks behind (for the ghost overlay).
    this.setEra('then');
    this.setLighting('parade');
    const ranks = this.spawnRanks(eye.clone().add(dirAt(pose.yaw, 0).multiplyScalar(15)).setY(0), pose.yaw);
    const grade = { ...g.renderer.grade };
    Object.assign(g.renderer.grade, { sepia: 0, saturation: 1, vignette: 0, flash: 0 });
    g.rig.viewfinder(eye, eye.clone().add(dirAt(pose.yaw, pitch)), true);
    g.rig.update(0, null, null);
    g.renderer.render(0);
    const ghost = capturePhoto(g.canvas, { size: 512 });
    Object.assign(g.renderer.grade, grade);
    ranks.forEach((ch) => this.removeExtra(ch));
    // 2) Today, with people out in the park (as in Chapters 1 and 2).
    const clearNowPeople = await spawnNowPeople(this);
    this.setEra('now');
    this.setLighting('now');
    const amb = g.audio.play('cicadas', { volume: 0.3, loop: true, fadeIn: 2, caption: '[Cicadas, a distant bus, joggers]' });
    g.rig.viewfinder(eye, eye.clone().add(dirAt(pose.yaw + 0.45, pitch - 0.1)), true, 1.3);
    // Coming in through the Brownie's lens (the prologue's push-in closed the iris on it): open it onto
    // today's park, as Chapters 1 and 2 do. Otherwise (e.g. no prologue) just fade in.
    if (g.ui.irisClosed) { g.ui.fade(false, 0); await g.ui.iris(false, 1.5, { y: 50, soft: 6 }); } else await g.ui.fade(false, 1.2);
    await this.cardLine(X.card.text);
    await this.lines(X.before, { frame: false });
    await this.alignGhost(ghost, pose.yaw, pitch, X);
    g.rig.viewfinder(eye, eye.clone().add(dirAt(pose.yaw, pitch)), true);
    await g.wait(0.5);
    await this.lines(X.locked, { frame: false });
    amb?.stop(1.5);
    await g.ui.fade(true, 0.7, 'sepia');
    clearNowPeople();
    this.closeViewfinder();
    this.setEra('then');
  }

  /** Recruits in ranks on the square, for the 1968 ghost photo only. */
  spawnRanks(centre, camYaw) {
    const out = [];
    let i = 0;
    // Three ranks across the camera's view, facing it.
    const right = V(-Math.cos(camYaw), 0, Math.sin(camYaw));
    const back = V(Math.sin(camYaw), 0, Math.cos(camYaw));
    for (let r = 0; r < 3; r++) for (let c = 0; c < 10; c++) {
      const pos = centre.clone().addScaledVector(right, (c - 4.5) * 1.1).addScaledVector(back, r * 1.3);
      const ch = this.spawnExtra(i++, pos, camYaw + Math.PI, this.modelOf(['Farid', 'AhHock', 'Ravi', 'Leo'][(r + c) % 4]));
      ch.play(ch.clips.Attention ? 'Attention' : 'Idle');
      out.push(ch);
    }
    return out;
  }

  modelOf(key) { return this._gltfs?.[key] || null; }

  async alignGhost(ghost, yaw0, pitch0, X) {
    const g = this.game;
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
    this._hintWas = hintEl.innerHTML;
    hintEl.innerHTML = g.input.isTouch ? 'Drag to turn the camera until the old view matches' : 'Move the mouse (or <kbd>WASD</kbd>) until the old view matches';
    vf.classList.remove('hidden');
    document.body.classList.add('aiming');
    let lockedFor = 0;
    await new Promise((resolve) => {
      const off = g.every((dt) => {
        const v = g.rig.vf;
        const dy = Math.atan2(Math.sin(v.yaw - yaw0), Math.cos(v.yaw - yaw0));
        const dp = v.pitch - pitch0;
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
    g.mode = 'cutscene';
    g.audio.play('camera-shutter');
    img.style.opacity = '1';
    note.classList.add('hidden');
  }

  closeViewfinder() {
    const $ = (id) => document.getElementById(id);
    const vf = $('viewfinder');
    vf.classList.add('hidden');
    vf.querySelector('.vf-frame').classList.remove('found');
    $('vf-ghost').classList.add('hidden');
    $('btn-shutter').classList.remove('hidden');
    $('btn-vf-cancel').classList.remove('hidden');
    if (this._hintWas) $('vf-hint').innerHTML = this._hintWas;
    document.body.classList.remove('aiming');
    this.game.input.lookEnabled = true;
  }

  // ------------------------------------------------------------------ beat 2: send-off morning (kopitiam)
  async sendoffMorning() {
    const g = this.game;
    const X = T.sendoffMorning;
    const hasKopi = !!this.sets.kopi;
    await this.cutTo(async () => {
      this.hideAll();
      this.useScene(hasKopi ? 'kopi' : 'camp');
      if (!hasKopi) this.setArea('cc');
      this.setLighting('kopi');
      this.usePlayer('civ', hasKopi ? this.kopiSpawn() : this.marker('CC_Spawn'));
      const Boon = this.place(this.cast.Boon, hasKopi ? 'NPC_Boon' : 'NPC_Rajan_CC');
      const Farid = this.place(this.outfit('Farid', 'civ'), hasKopi ? 'NPC_Farid' : 'NPC_Farid_CC');
      Boon.faceTowards(Farid.root.position, true);
      Farid.faceTowards(Boon.root.position, true);
      this.kopiCalendar?.(CAL.sendoff);
      if (hasKopi) {
        this.props.tiffin.visible = false;
        this.ambience([['ceiling-fan', 0.3], ['street', 0.2]]);
        // Sparky starts in the doorway off the five-foot way; the scene opens looking out at the street.
        const door = this.marker('SPAWN_Sparky').pos.clone().add(V(0, 0, 0.6));
        this.player.place(door, Math.PI);
        g.rig.cut(V(2.6, 1.6, -10.1), door.clone().add(V(-0.3, 0.75, -1.5)), 1, true);
      } else g.rig.frameTwo(Farid, Boon, { instant: true, dist: 4.2, height: 0.35 });
    }, hasKopi ? null : X.card);
    // The place card runs while Sparky walks in.
    if (hasKopi) await Promise.all([this.cardLine(X.card.text), this.walkIntoKopitiam()]);
    const { Boon } = this.cast;
    const Farid = this.cast.Farid;
    await this.lines(X.lines, { frame: false });
    // Boon goes into the back. When Farid picks up his bag, the tiffin carrier is on the counter.
    const cupAt = hasKopi && this.m.COUNTER_Cup ? this.marker('COUNTER_Cup').pos : Farid.root.position.clone().add(V(0.6, 0.9, 0));
    const tif = this.props.tiffin || P.tiffinCarrier(this.heirlooms.includes('tiffin'));
    if (!tif.parent) this.scene.add(tif);
    await g.ui.fade(true, 0.45);
    this.hide(Boon);
    tif.position.copy(cupAt);
    tif.visible = true;
    g.rig.cut(cupAt.clone().add(V(-0.75, 0.42, 1.05)), cupAt.clone().add(V(0, 0.12, 0)), 1, true);
    await g.ui.fade(false, 0.45);
    g.audio.play('cup-clink', { volume: 0.4, caption: '' });
    await g.wait(0.9);
    await this.lines(this.heirlooms.includes('tiffin') ? X.tiffin : X.tiffinFallback, { frame: false });
    // Chapter 2's wall item, one line.
    const w = X.wall[this.wallChoice];
    if (w) {
      if (w.some((l) => l.who === 'Siti')) {
        const Siti = this.place(this.cast.Siti, hasKopi ? 'SEAT_T3_a' : 'NPC_Siti_CC');
        Siti.faceTowards(Farid.root.position, true);
      }
      if (hasKopi && this.m.WALL_Focus) g.rig.cut(this.marker('WALL_Focus').pos.clone().add(V(0.3, 0.05, 2.3)), this.marker('WALL_Focus').pos.clone().add(V(0, 0.25, 0)), 2);
      await this.lines(w, { frame: !hasKopi });
    }
    // Look closer: the new dollar in the money tin, while Farid gets his bag.
    g.objective(X.objective, cupAt);
    this.resume();
    await this.interactOnce(cupAt, 'Take the tiffin carrier', { radius: 1.8 });
    tif.visible = false;
    this.carryProp(P.tiffinCarrier(this.heirlooms.includes('tiffin')));
    g.audio.play('pickup-chime', { volume: 0.5 });
    g.objective(null);
  }

  /** Sparky walks in from the street to the counter beside Farid; cut to a three-shot for the last few steps. */
  async walkIntoKopitiam() {
    const g = this.game;
    const { Boon, Farid } = this.cast;
    const sp = this.player;
    const spot = Farid.root.position.clone().add(V(-1.25, 0, 0.6));
    const mid = spot.clone().lerp(Farid.root.position, 0.5).add(V(-0.75, 0.9, 0.1)); // in front of the counter's collider
    // In the doorway: a wave to the two at the counter. Farid waves back; Boon looks up and nods.
    const doorShot = { pos: g.camera.position.clone(), look: g.rig.shot.look.clone() };
    sp.faceTowards(Boon.root.position.clone().lerp(Farid.root.position, 0.5), true);
    sp.play('Wave', { loop: false, speed: 1.25 });
    await g.wait(1.0);
    // Their answer, from the aisle between the tables (they turn towards the door, so towards this camera).
    Farid.faceTowards(sp.root.position, true);
    Boon.faceTowards(sp.root.position, true);
    // (Look at a point in front of the counter: one over it sits inside its collider and the rig pulls in.)
    g.rig.cut(V(1.1, 1.55, -5.9), V(-0.35, 1.25, -8.95), 1, true);
    Farid.play('Wave', { loop: false });
    await g.wait(0.35);
    Boon.play('Nod', { loop: false });
    await g.wait(1.3);
    g.rig.cut(doorShot.pos, doorShot.look, 1, true);
    sp.scripted = true;
    // Down the aisle between the tables (they sit at x = -2.7, 0, 2.7), then across to the counter.
    const walk = sp.moveTo([V(1.35, spot.y, -3.8), V(1.35, spot.y, -8.2), spot], { speed: 1.2 });
    await g.waitUntil(() => sp.root.position.z < -4.4);
    g.rig.cut(mid.clone().add(V(-2.9, 0.95, 3.15)), mid, 1, true);
    await walk;
    sp.scripted = false;
    sp.faceTowards(Boon.root.position.clone().lerp(Farid.root.position, 0.5));
    Boon.faceTowards(spot);
    Farid.faceTowards(spot);
    await g.wait(0.5);
  }

  kopiSpawn() {
    const sp = this.marker('SPAWN_Sparky');
    return { pos: sp.pos.clone().add(V(0, 0, -4.2)), yaw: sp.yaw };
  }

  carryProp(obj) {
    this.dropProp();
    obj.position.set(0.12, 0.42, 0.22);
    this.player.root.add(obj);
    this.carrying = obj;
  }

  dropProp() { if (this.carrying) { this.carrying.parent?.remove(this.carrying); this.carrying = null; } }

  // ------------------------------------------------------------------ beat 3: the send-off (community centre)
  async sendoff() {
    const g = this.game;
    const X = T.sendoff;
    await this.cutTo(async () => {
      this.hideAll();
      this.useScene('camp');
      this.setArea('cc');
      this.setEra('then');
      this.setLighting('day');
      this.usePlayer('civ', this.marker('CC_Spawn', V(-3, 0, 206)));
      if (!this.carrying) this.carryProp(P.tiffinCarrier(this.heirlooms.includes('tiffin')));
      this.place(this.cast.Rajan, 'NPC_Rajan_CC');
      this.place(this.outfit('Ravi', 'civ'), 'NPC_Ravi_CC');
      this.place(this.cast.Siti, 'NPC_Siti_CC');
      this.place(this.outfit('Farid', 'civ'), 'NPC_Farid_CC');
      this.place(this.cast.AhHockMa, 'NPC_AhMa_CC');
      if (this.kindness.has('bundles')) this.place(this.cast.Neighbour, 'NPC_Neighbour_CC');
      this.cast.Rajan.faceTowards(this.cast.Ravi.root.position, true);
      this.cast.Ravi.faceTowards(this.cast.Rajan.root.position, true);
      // Families all round, but not on top of the people we film (room for the camera beside Mr. Rajan and Ravi).
      this.markersWith('CC_Family_').forEach((mk, i) => { if (!this.crowded(mk.pos, 2.2)) this.spawnExtra(i, mk.pos, mk.yaw); });
      this.markersWith('CC_Band_').forEach((mk, i) => this.spawnExtra(20 + i, mk.pos, mk.yaw));
      this.ambience([['band-march', 0.4], ['murmur', 0.4], ['truck-engine', 0.25]]);
      this.sendoffTwoShot();
    }, null);
    await this.eventCard(X.card, X.fact);
    await this.lines(X.lines.slice(0, 1), { frame: false });
    this.frameSpeaker('Siti');
    await this.lines(X.lines.slice(1));
    if (this.kindness.has('bundles')) await this.lines(X.neighbour);
    // Free to walk: optional oranges for Ah Hock's Ah Ma, then the truck.
    const tail = this.marker('CC_Truck_Tail', V(3.4, 0, 204));
    const ma = this.cast.AhHockMa;
    ma.indicator('chat');
    const maIt = g.addInteract({
      pos: () => ma.root.position, radius: 1.9, label: `Talk to ${NAMES.AhHockMa}`,
      onUse: async () => {
        g.removeInteract(maIt);
        g.mode = 'cutscene'; g.ui.prompt(null); ma.indicator(null);
        await this.lines(X.ahMa);
        await this.lines(X.ahMaThanks);
        this.kindness3.add('oranges');
        this.oranges = P.orangeBag();
        this.oranges.position.set(-0.14, 0.4, 0.2);
        this.player.root.add(this.oranges);
        this.resume();
      },
    });
    g.objective(X.objective, tail.pos);
    this.resume();
    await this.interactOnce(tail.pos, X.truckPrompt, { radius: 2.0 });
    g.removeInteract(maIt);
    ma.indicator(null);
    g.objective(null);
    if (this.oranges) { this.oranges.parent?.remove(this.oranges); this.oranges = null; g.audio.play('paper', { volume: 0.4, caption: '' }); }
    // Farid climbs in; Sparky climbs up after him and looks back at the gate. Nobody there.
    const Farid = this.cast.Farid;
    // The tail marker is on the tailboard itself: stop just behind it, then he's up and in.
    g.rig.cut(tail.pos.clone().add(V(-5.5, 2.0, 3.2)), tail.pos.clone().add(V(-1.0, 1.0, 0)), 1, true);
    await Farid.moveTo([tail.pos.clone().add(V(-1.3, 0, 0))]);
    this.hide(Farid);
    const spot = this.marker('CC_Boon_Spot', V(-1.2, 0, 197.4)).pos;
    this.player.place(tail.pos, tail.yaw);
    this.player.faceTowards(spot, true);
    // Just outside the tailboard (inside the canopy is dark), looking back at the gate.
    g.rig.cut(tail.pos.clone().add(V(-0.9, 1.45, 0.25)), spot.clone().add(V(0, 1.0, 0)), 1, true);
    await g.wait(2.6);
    g.ui.toast(X.fact.title, X.fact.text, 11);
    await g.wait(1.2);
    this.dropProp();
    this.ambience(null);
  }

  // ------------------------------------------------------------------ beat 4: day one — the bed carry
  /** The lorry pulls into Taman Jurong Camp; Sergeant Osman lines up his new section and learns their names. */
  async arrival() {
    const g = this.game;
    const X = T.arrival;
    const truck = this.campTruck();
    const stopX = 9, z = -23.2;
    await this.cutTo(async () => {
      this.hideAll();
      this.useScene('camp');
      this.setArea('parade');
      this.setEra('then');
      this.setLighting('day');
      this.usePlayer('ns');
      this.player.root.visible = false;
      this.outfit('Farid', 'ns'); this.outfit('Ravi', 'ns');
      truck.position.set(42, truck.userData.y, z);
      truck.rotation.set(0, -Math.PI / 2, 0); // cab first, driving west along the road in front of the blocks
      truck.visible = true;
      this.ambience([['truck-engine', 0.55], ['cicadas', 0.2]]);
      g.rig.cut(V(3.5, 2.2, -14.5), V(16, 1.3, z), 1, true);
    }, X.card);
    // It drives in and stops.
    const k = { x: 42 };
    const follow = g.every(() => { truck.position.x = k.x; g.rig.cut(V(3.5, 2.2, -14.5), V(Math.max(stopX + 1, k.x - 2), 1.3, z), 3); });
    await g.tween(k, { x: stopX }, 3.6, (t) => 1 - (1 - t) * (1 - t));
    follow();
    g.audio.play('impact', { volume: 0.3, rate: 0.7, caption: '' });
    // Osman is waiting at the tailboard.
    const tail = V(stopX + 3.6, 0, z);
    const Osman = this.cast.Osman;
    Osman.place(tail.clone().add(V(1.6, 0, 2.4)), -2.4);
    Osman.root.visible = true; Osman.root.userData.show = true;
    Osman.play('Idle');
    g.rig.cut(tail.clone().add(V(4.5, 1.8, 4.8)), tail.clone().add(V(0, 1.2, 0)), 2);
    await this.lines(X.fallIn, { frame: false });
    // A beat later, one line in front of the lorry.
    await g.ui.fade(true, 0.35);
    const order = ['Leo', 'Farid', 'Sparky', 'AhHock', 'Ravi'];
    const lineZ = z + 2.6;
    this.arrivalLine = order.map((key, i) => {
      const ch = key === 'Sparky' ? this.player : this.cast[key];
      ch.stop?.();
      ch.place(V(stopX - 2 + i * 1.0, 0, lineZ), 0);
      ch.root.visible = true; ch.root.userData.show = true;
      ch.play(ch.clips?.Attention ? 'Attention' : 'Idle');
      return { key, ch };
    });
    // Osman stands off the left end of the line, so he never hides a recruit from the camera.
    Osman.place(V(stopX - 3.6, 0, lineZ + 1.9), 0);
    Osman.faceTowards(V(stopX, 0, lineZ), true);
    Osman.play('Idle');
    const eye = V(stopX + 3.2, 1.75, lineZ + 5.2);
    g.rig.cut(eye, V(stopX, 1.1, lineZ), 1, true);
    await g.ui.fade(false, 0.35);
    // Osman walks the line: the camera turns to whoever is speaking (one dialogue run, no flicker).
    this.customFrame = (who) => {
      const ch = who === 'Osman' ? null : this.cast[who];
      const target = ch ? ch.headPosition() : V(stopX, 1.1, lineZ);
      g.rig.cut(eye, target.lerp(V(stopX, 1.1, lineZ), 0.35), 2.5);
    };
    await this.lines(X.lines);
    this.customFrame = null;
    // The lorry pulls away behind them.
    g.rig.cut(V(stopX + 1, 1.9, lineZ + 6.5), V(stopX - 4, 1.3, z), 2);
    const k2 = { x: stopX };
    const off = g.every(() => { truck.position.x = k2.x; });
    await g.tween(k2, { x: -45 }, 4.2, (t) => t * t);
    off();
    this.ambience([['cicadas', 0.25]]);
    truck.visible = false;
  }

  frameSpeaker(who) {
    if (this.customFrame) { this.customFrame(who); return; }
    super.frameSpeaker(who);
  }

  /** A copy of the community centre's lorry for the camp (the level has one, in AREA_CC). */
  campTruck() {
    if (this.truck2) return this.truck2;
    const src = this.sets.camp.nodes.PROP_Truck;
    const t = src ? src.clone() : new THREE.Mesh(new THREE.BoxGeometry(6, 2.8, 2.4), new THREE.MeshStandardMaterial({ color: '#56603f' }));
    t.userData.y = src ? src.position.y : 1.4;
    t.visible = false;
    this.sets.camp.scene.add(t);
    this.truck2 = t;
    return t;
  }

  // ------------------------------------------------------------------ beat 4b: the first drill
  sectionMembers(startPrefix) {
    const order = ['Leo', 'Farid', 'Sparky', 'AhHock', 'Ravi'];
    return order.map((key, i) => {
      const ch = key === 'Sparky' ? this.player : this.cast[key];
      const mk = this.marker(`${startPrefix}${i + 1}`, V(i - 2, 0, 0), Math.PI);
      ch.stop?.();
      ch.place(mk.pos, mk.yaw);
      ch.root.visible = true; ch.root.userData.show = true;
      ch.play(ch.clips?.Attention ? 'Attention' : 'Idle');
      return { key, ch, startYaw: mk.yaw };
    });
  }

  /** Speakers turn to face Sparky; before a drill everyone faces front again. */
  squareUp(members) {
    for (const m of members) { m.ch.place(m.ch.root.position, m.startYaw); m.ch.play(m.ch.clips?.Attention ? 'Attention' : 'Idle'); }
  }

  async dayOneDrill() {
    const g = this.game;
    const X = T.dayOne;
    let members;
    await this.cutTo(async () => {
      this.hideAll();
      this.useScene('camp');
      this.setArea('parade');
      this.setEra('then');
      this.setLighting('day');
      this.usePlayer('ns');
      this.outfit('Farid', 'ns'); this.outfit('Ravi', 'ns');
      members = this.sectionMembers('DRILL_');
      this.place(this.cast.Osman, 'NPC_Osman_Drill');
      this.place(this.cast.Adviser, 'NPC_Adviser_1');
      this.place(this.cast.Adviser2, 'NPC_Adviser_2');
      this.ambience([['cicadas', 0.25]]);
      this.drillCamera(members);
    }, X.card);
    await this.lines(X.drillIntro, { frame: false });
    this.squareUp(members);
    const drill = new Drill(g, {
      members, mode: 'day', copier: 'AhHock', early: { key: 'Leo', at: 2 }, names: NAMES, lines: T.drill,
    });
    g.mode = 'cutscene';
    g.input.releaseLock();
    g.objective(X.drillHint);
    const leoLine = async (d) => { if (d.pending?.index === 2) await d.say('Osman', T.drill.leo, 2.6); };
    await drill.run([
      { cmd: 'sedia', gap: 0.8 },
      { cmd: 'kanan' },
      { cmd: 'kiri', after: leoLine },
      { cmd: 'belakang' },
    ]);
    g.objective(null);
    // "Four boys, four directions": the others scramble as they're stood at ease.
    // Everyone faces a different way (they started facing north, yaw π): Leo west, Farid south, Ah Hock east.
    const yawOf = { Leo: Math.PI * 1.5, Farid: 0, AhHock: Math.PI * 0.5, Ravi: Math.PI, Sparky: Math.PI };
    for (const m of members) if (yawOf[m.key] !== undefined) m.ch.targetYaw = yawOf[m.key];
    await g.wait(0.7);
    // From in front of the line, beside the sergeant, so the muddle is plain to see.
    const mid = members[2].ch.root.position;
    g.rig.cut(mid.clone().add(V(1.6, 1.7, -4.8)), mid.clone().add(V(0, 0.8, 0)), 1, true);
    await this.lines(X.end, { frame: false });
    this.drillStats = drill.stats;
    this.stopCam?.();
  }

  /** From in front of the line, beside the sergeant: faces (and rifles) in view. */
  frontCamera(members, instant = true) {
    const mid = members[2].ch.root.position;
    const fwd = V(Math.sin(members[2].startYaw ?? Math.PI), 0, Math.cos(members[2].startYaw ?? Math.PI));
    const side = V(-fwd.z, 0, fwd.x);
    this.game.rig.cut(mid.clone().addScaledVector(fwd, 5.2).addScaledVector(side, 1.8).add(V(0, 1.7, 0)), mid.clone().add(V(0, 0.85, 0)), 1, instant);
  }

  /** Fixed 3/4 shot over the line for the day-one drill (Osman's face in view). */
  drillCamera(members) {
    const g = this.game;
    const mid = members[2].ch.root.position;
    const cam = this.m.CAM_DrillDay ? this.marker('CAM_DrillDay').pos : mid.clone().add(V(-3.6, 2.3, 4.6));
    g.rig.cut(cam, mid.clone().add(V(0, 0.7, -1.2)), 2, true);
  }

  // ------------------------------------------------------------------ beat 5: rifles
  async rifles() {
    const g = this.game;
    const X = T.rifles;
    let members;
    await this.cutTo(async () => {
      this.hideAll();
      this.useScene('camp');
      this.setArea('parade');
      this.setEra('then');
      this.setLighting('day');
      this.usePlayer('ns');
      this.outfit('Farid', 'ns'); this.outfit('Ravi', 'ns');
      members = this.sectionMembers('DRILL_');
      this.place(this.cast.Osman, 'NPC_Osman_Drill');
      // The rack stands between the sergeant and the section.
      const o = this.cast.Osman.root.position, mid = members[2].ch.root.position;
      this.rack ||= P.rifleRack(6);
      this.rack.position.copy(o).lerp(mid, 0.45).setY(0);
      this.rack.rotation.y = Math.atan2(mid.x - o.x, mid.z - o.z);
      this.rack.rifles.forEach((r) => { r.visible = true; });
      this.scene.add(this.rack);
      this.rack.visible = true;
      this.ambience([['cicadas', 0.25]]);
      this.drillCamera(members);
    }, X.card);
    await this.lines(X.issue, { frame: false });
    // Sparky takes one; everyone else follows.
    g.objective(X.take, this.rack.position);
    this.resume();
    await this.interactOnce(this.rack.position, X.take, { radius: 2.2 });
    g.objective(null);
    this.rack.rifles.forEach((r) => { r.visible = false; });
    g.audio.play('pickup-chime', { volume: 0.4 });
    this.sectionMembers('DRILL_');
    for (const m of members) this.giveRifle(m.ch, 'order');
    this.frontCamera(members);
    await this.lines(X.after, { frame: false });
    this.squareUp(members);
    // One command: sling arms.
    CMD.sandang.onApply = (m) => this.giveRifle(m.ch, 'sling');
    const drill = new Drill(g, { members, mode: 'day', copier: 'AhHock', names: NAMES, lines: T.drill });
    g.mode = 'cutscene';
    g.input.releaseLock();
    g.objective(X.slingHint);
    await drill.run([{ cmd: 'sandang', gap: 0.8, buttons: ['up'], labels: { up: 'sandang' } }]);
    for (const m of members) this.giveRifle(m.ch, 'sling');
    g.objective(null);
    await this.lines(X.done, { frame: false });
    g.ui.toast(X.fact.title, X.fact.text, 11);
    this.rack.visible = false;
  }

  /** Rifles: 'order' (butt by the right foot) or 'sling' (behind the shoulder). Sparky's is scaled to him. */
  giveRifle(ch, pose) {
    const r = ch.isPlayer
      ? P.rifleOn(ch, pose, { scale: 0.6, lift: pose === 'sling' ? 0.12 : 0, out: pose === 'order' ? 0.38 : 0.34 })
      : P.rifleOn(ch, pose);
    this.lockRifleArm(ch, pose === 'sling');
    return r;
  }

  /**
   * Hold the right arm still (in its Attention pose, hanging at the side) so the hand stays on the rifle's butt
   * while the rest of the body marches. Applied after the animation mixer, every frame, in update().
   */
  lockRifleArm(ch, on) {
    this.armLocks ||= new Map();
    if (!on) { this.armLocks.delete(ch); return; }
    if (this.armLocks.has(ch) || !ch.mixer) return;
    const bones = [];
    ch.model.traverse((o) => { if (o.isBone && /^(upperarm\.?R|forearm\.?R|hand\.?R|arm_R)$/i.test(o.name)) bones.push(o); });
    if (!bones.length) return;
    // Sample the pose (Attention for NPCs, Idle for Sparky) with a throwaway mixer, then let the real one carry on.
    const clip = ch.clips.Attention || ch.clips.Idle;
    const prev = bones.map((b) => b.quaternion.clone());
    const m2 = new THREE.AnimationMixer(ch.model);
    m2.clipAction(clip).play();
    m2.update(0.001);
    const pose = bones.map((b) => b.quaternion.clone());
    m2.stopAllAction();
    m2.uncacheRoot(ch.model);
    bones.forEach((b, i) => b.quaternion.copy(prev[i]));
    this.armLocks.set(ch, { bones, pose });
  }

  // ------------------------------------------------------------------ beat 5b: Farid's letter
  async letterRound() {
    const g = this.game;
    const X = T.letter;
    await this.cutTo(async () => {
      this.hideAll();
      if (this.nightTiffin) { this.nightTiffin.parent?.remove(this.nightTiffin); this.nightTiffin = null; }
      this.useScene('camp');
      this.setArea('barracks');
      this.setLighting('night');
      this.usePlayer('ns', this.marker('BAR_Spawn', V(192, 0, 1.4)));
      this.outfit('Farid', 'ns'); this.outfit('Ravi', 'ns');
      this.place(this.cast.Farid, 'BAR_Farid');
      this.place(this.cast.Ravi, 'BAR_Ravi');
      this.place(this.cast.Leo, 'BAR_Leo');
      this.cast.Leo.root.position.y = 0; // his marker is on the top bunk; he stands beside it
      for (const k of ['Farid', 'AhHock', 'Ravi', 'Leo']) P.rifleOff(this.cast[k]);
      P.rifleOff(this.player);
      // Boon's tiffin carrier on Farid's bed: dinner.
      const tif = P.tiffinCarrier(this.heirlooms.includes('tiffin'));
      tif.scale.setScalar(1.3);
      tif.position.copy(this.cast.Farid.root.position).add(V(0.45, 0.45, 0));
      this.scene.add(tif);
      this.barTiffin = tif;
      this.ambience([['night-ambience', 0.25]]);
      // Dinner on Farid's bed: Ah Hock squeezes in beside him; Sparky stands in front. Filmed from the front.
      const F = this.cast.Farid;
      const f = F.root.position;
      const fwd = V(Math.sin(F.yaw), 0, Math.cos(F.yaw));
      const side = V(-fwd.z, 0, fwd.x);
      this.cast.AhHock.place(f.clone().addScaledVector(side, -0.8), F.yaw);
      this.cast.AhHock.root.visible = true; this.cast.AhHock.root.userData.show = true;
      this.cast.AhHock.play('Idle');
      this.barTiffin.position.copy(f).addScaledVector(side, -0.4).addScaledVector(fwd, -0.45).add(V(0, 0.45, 0)); // on the bed
      this.player.place(f.clone().addScaledVector(fwd, 1.05).addScaledVector(side, 0.6), 0);
      this.player.faceTowards(f, true);
      // Inside the room (its front wall with the door is ~2 m in front of the beds).
      this.barShot = { pos: f.clone().addScaledVector(fwd, 1.9).addScaledVector(side, 0.3).add(V(0, 1.6, 0)), look: f.clone().addScaledVector(side, -0.4).add(V(0, 1.05, 0)) };
      g.rig.cut(this.barShot.pos, this.barShot.look, 1, true);
    }, X.card);
    await this.lines(X.dinner, { frame: false });
    await this.lines(X.start, { frame: false });
    g.input.releaseLock();
    const [id] = await g.ui.pick({ title: X.choiceTitle, sub: 'Choose one.', options: X.openings.map((o) => ({ id: o.id, label: `${o.label}: “${o.text}”`, icon: { honest: '💬', brave: '💪', funny: '😄' }[o.id] })), n: 1 });
    const op = X.openings.find((o) => o.id === id) || X.openings[0]; // a quick double-tap can deselect: never crash
    this.letter.openingId = op.id;
    this.letter.opening = op.text;
    save('sparky.letter.ns', op.id);
    const view = new P.LetterView(X);
    this.letterView = view;
    this.letter.body = [];
    view.render(this.letter);
    g.audio.play('paper');
    for (const b of X.body) { await g.wait(1.1); this.letter.body.push(b); view.render(this.letter); }
    // The player reads it, then closes it (it never vanishes on its own).
    const closeHint = g.input.isTouch ? 'Tap to close the letter' : 'Click (or press E) to close the letter';
    await g.wait(0.6);
    await view.waitClose(g, closeHint);
    await this.lines(X.takeRound, { frame: false });
    // Out into the corridor: the rooms are too small for the follow camera to start in.
    const sp = this.marker('BAR_Spawn', V(192, 0, -0.9));
    this.player.place(sp.pos, sp.yaw);
    g.rig.snapBehind?.();
    view.unmount();
    // The P.S. round: any order.
    const pending = new Set(['AhHock', 'Ravi', 'Leo']);
    // The beacon always points at the nearest buddy still to add a P.S. (then back to Farid).
    const aim = () => {
      if (!pending.size) { g.objective(X.backToFarid, this.cast.Farid); this.cast.Farid.indicator('important'); return; }
      const here = this.player.root.position;
      const next = [...pending].map((k) => this.cast[k]).sort((a, b) => a.root.position.distanceTo(here) - b.root.position.distanceTo(here))[0];
      g.objective(X.objective, next);
    };
    aim();
    const its = [];
    const donePS = async (key) => {
      pending.delete(key);
      this.letter.ps[key] = true;
      g.audio.play('paper', { volume: 0.6 });
      view.render(this.letter);
      await g.wait(0.6);
      await view.waitClose(g, closeHint);
    };
    for (const key of pending) {
      const ch = this.cast[key];
      ch.indicator('important');
      const it = g.addInteract({
        pos: () => ch.root.position, radius: 1.9, label: X.ps[key].prompt,
        onUse: async () => {
          g.removeInteract(it);
          g.mode = 'cutscene'; g.ui.prompt(null); ch.indicator(null);
          // Sparky steps round in front of him (he may have come up behind a bunk or a locker door).
          const f = V(Math.sin(ch.yaw), 0, Math.cos(ch.yaw));
          const chest = ch.root.position.clone().add(V(0, 0.8, 0));
          if (this.world.rayDistance(chest, f, 1.5) > 1.4) {
            this.player.place(ch.root.position.clone().addScaledVector(f, 1.1), 0);
            this.player.faceTowards(ch.root.position, true);
            ch.faceTowards(this.player.root.position, true);
          }
          await this.lines(X.ps[key].lines);
          await donePS(key);
          aim();
          this.resume();
        },
      });
      its.push(it);
    }
    this.resume();
    // Back to Farid (any time): the paw print, then it's sent.
    const farid = this.cast.Farid;
    await g.waitUntil(() => !pending.size || (this.player.root.position.distanceTo(farid.root.position) < 1.9 && pending.size < 3 && g.input.keys.has('KeyE')));
    await this.interactOnce(farid, X.paw.prompt);
    farid.indicator(null);
    its.forEach((it) => g.removeInteract(it));
    for (const k of ['AhHock', 'Ravi', 'Leo']) this.cast[k].indicator(null);
    g.mode = 'cutscene';
    if (pending.size) {
      if (pending.has('Ravi')) { await this.lines(X.ravisMap); this.letter.ps.Ravi = true; }
      await this.lines(X.enough);
    }
    this.letter.paw = true;
    view.render(this.letter);
    g.audio.play('pickup-chime', { volume: 0.5 });
    await g.wait(0.6);
    await view.waitClose(g, closeHint);
    g.objective(null);
    if (this.barTiffin) { this.barTiffin.parent?.remove(this.barTiffin); this.barTiffin = null; }
    // The letter goes into the album.
    await this.developPhoto('Letter', P.letterImage(X, this.letter));
  }

  // ------------------------------------------------------------------ beat 5c: the reading (kopitiam)
  async reading() {
    const g = this.game;
    const X = T.reading;
    const L = T.letter;
    const hasKopi = !!this.sets.kopi;
    if (!this.letter.opening) { // debug jump: a default letter
      this.letter = { openingId: 'honest', opening: L.openings[0].text, body: L.body.slice(), ps: { AhHock: true, Ravi: true, Leo: true }, paw: true };
    }
    await this.cutTo(async () => {
      this.hideAll();
      this.useScene(hasKopi ? 'kopi' : 'camp');
      if (!hasKopi) this.setArea('cc');
      this.setLighting('kopiEvening');
      this.kopiCalendar?.(CAL.reading);
      this.usePlayer('civ', hasKopi ? this.kopiSpawn() : this.marker('CC_Spawn'));
      this.player.root.visible = false; // Sparky is at camp: this scene is Boon and Siti alone
      this.place(this.cast.Boon, hasKopi ? 'NPC_Boon' : 'NPC_Rajan_CC');
      // Siti leans on the customer side of the counter; Boon is behind it.
      this.place(this.cast.Siti, hasKopi ? 'COUNTER_Serve' : 'NPC_Siti_CC');
      this.cast.Siti.faceTowards(this.cast.Boon.root.position, true);
      this.cast.Boon.faceTowards(this.cast.Siti.root.position, true);
      if (hasKopi && this.m.COUNTER_Cup) {
        this.props.shelfBrownie.position.copy(this.marker('COUNTER_Cup').pos).add(V(-0.6, 0.02, 0));
        this.props.shelfBrownie.visible = true;
      }
      this.ambience([['ceiling-fan', 0.25]]);
      this.readShot = () => {
        if (!hasKopi || !this.m.CAM_Counter) { g.rig.frameTwo(this.cast.Siti, this.cast.Boon, { instant: true }); return; }
        const pair = this.cast.Siti.root.position.clone().lerp(this.cast.Boon.root.position, 0.5).add(V(0, 1.15, 0));
        g.rig.cut(this.marker('CAM_Counter').pos, pair, 1, true);
      };
      this.readShot();
    }, X.card);
    await this.lines(X.start, { frame: false });
    // Siti reads it aloud, line by line.
    const view = new P.LetterView(L);
    const full = this.letter;
    let shown = 0;
    const step = async (n, secs = 1.4) => { shown += n; view.render(full, shown); g.audio.play('paper', { volume: 0.3, caption: '' }); await g.wait(secs); };
    view.render(full, 0);
    await step(3, 1.6);
    view.dim(true);
    await this.lines(X.react[full.openingId] || X.react.honest, { frame: false });
    view.dim(false);
    await step(full.body.length + 1, 2.4);
    view.dim(true);
    if (full.ps.AhHock) { view.dim(false); await step(1); view.dim(true); await this.lines(X.ahHock, { frame: false }); }
    if (full.ps.Ravi) { view.dim(false); await step(1); view.dim(true); await this.lines(X.ravi, { frame: false }); }
    if (full.ps.Leo) { view.dim(false); await step(1); view.dim(true); await this.lines(X.leo, { frame: false }); }
    view.dim(false); await step(1, 1.2); view.dim(true);
    await this.lines(X.paw, { frame: false });
    view.unmount();
    // Boon takes the Brownie down, winds on, looks at the frame counter.
    const b = this.props.shelfBrownie;
    if (b?.visible) {
      g.rig.cut(b.position.clone().add(V(-0.6, 0.35, 0.8)), b.position.clone(), 2);
      await g.wait(1.4);
      b.visible = false;
      g.audio.play('camera-shutter', { volume: 0.4, caption: '[The film winds on]' });
    }
    await g.wait(1);
    this.readShot();
    await this.lines(X.end, { frame: false });
    this.ambience(null);
  }

  // ------------------------------------------------------------------ beat 6: the passing-out parade
  async parade() {
    const g = this.game;
    const X = T.parade;
    let members;
    await this.cutTo(async () => {
      this.hideAll();
      this.useScene('camp');
      this.setArea('parade');
      this.setEra('then');
      this.setLighting('parade');
      this.usePlayer('ns');
      this.outfit('Farid', 'ns'); this.outfit('Ravi', 'ns');
      members = this.sectionMembers('PARADE_');
      this.paradeMembers = members;
      for (const m of members) this.giveRifle(m.ch, 'sling');
      this.fillStands();
      this.place(this.cast.Minister, 'NPC_Minister');
      // Osman stands by the dais, where the file passes.
      const dais = this.marker('NPC_Minister', V(8, 0.6, 24)).pos;
      this.cast.Osman.place(V(dais.x + 3, 0, 15.2), Math.PI);
      this.cast.Osman.root.visible = true; this.cast.Osman.root.userData.show = true;
      this.cast.Osman.play('Attention');
      this.ambience([['band-march', 0.35], ['murmur', 0.3]]);
      this.paradeDressing();
      this.paradeCamera(members, true);
    }, null);
    await this.eventCard(X.card, X.fact);
    this.stopCam = g.every(() => { if (!this.revealing && !this.drillLooking) this.paradeCamera(members); });
    await this.drillLines(X.start);
    this.squareUp(members);
    // Stands chatter while the file marches.
    const barks = [...X.stands.always];
    if (this.kindness.has('bundles')) barks.unshift(X.stands.neighbour);
    if (this.kindness3.has('oranges')) barks.push(X.stands.ahMa);
    const haltX = this.marker('PARADE_Halt', V(22, 0, 12)).pos.x;
    const drill = new Drill(g, {
      members, mode: 'parade', names: NAMES, lines: T.drill,
      hooks: { onEyesRight: (d) => this.revealBoon(d) },
    });
    g.mode = 'cutscene';
    g.input.releaseLock();
    g.objective(X.hint);
    const startX = members[4].ch.root.position.x;
    const daisX = this.marker('NPC_Minister', V(8, 0.6, 24)).pos.x;
    await drill.run([
      { cmd: 'sedia', gap: 1.2 },
      { cmd: 'kanan' },
      { cmd: 'jalan', gap: 1.0, after: async (d) => { for (const b of barks) { await g.wait(1.2); d.say(b.who, b.text, 2.4); } } },
      { cmd: 'pandang', atX: Math.min(daisX - 4, startX + 12), before: async () => { g.objective(X.lookHint); this.drillLooking = true; } },
      { cmd: 'depan', gap: 0.6, after: async () => { this.drillLooking = false; this.revealing = false; g.objective(null); } },
      { cmd: 'berhenti', atX: Math.min(haltX - 2.2, daisX + 8) },
      { cmd: 'bersurai', gap: 1.4 },
    ]);
    this.stopCam?.();
    g.objective(null);
    await this.passOut(members);
  }

  /** Short lines in the drill caption style (no dialogue box on the parade square). */
  async drillLines(list) {
    const g = this.game;
    for (const l of list) {
      await g.ui.say(this.nameOf(l.who), l.text, { auto: 2.4 });
    }
    g.ui.endDialogue();
  }

  /** Tracking shot ahead and to the left of the file, the stands and dais behind it. */
  paradeCamera(members, instant = false) {
    const g = this.game;
    const sp = members[2].ch.root.position;
    const pos = V(sp.x + 4.2, 1.7, sp.z - 5.6);
    const look = V(sp.x + 0.2, 1.0, sp.z + 1.2);
    g.rig.cut(pos, look, instant ? 1 : 2.2, instant);
  }

  /** The big-day title card (day · event · place), then a short fact about it. */
  async eventCard(card, fact) {
    const g = this.game;
    await g.ui.card(card.day, card.title, card.place, 4);
    if (fact) g.ui.toast(fact.title, fact.text, 10);
  }

  /** Mr. Rajan and Ravi, side-on from the road side, both faces in shot (not over his shoulder). */
  sendoffTwoShot() {
    const a = this.cast.Rajan.root.position, b = this.cast.Ravi.root.position;
    const mid = a.clone().lerp(b, 0.5);
    const ab = b.clone().sub(a).setY(0).normalize();
    const perp = V(-ab.z, 0, ab.x);
    const spawn = this.marker('CC_Spawn', V(-3, 0, 206)).pos;
    if (perp.dot(spawn.clone().sub(mid)) < 0) perp.negate();
    // The families stand all around: of a few spots (either side, a few distances and heights), take the one
    // with the fewest people in the foreground (in view and nearer than the pair), nobody at the lens and
    // nobody hiding a face.
    const rig = this.game.rig, pair = [this.cast.Rajan, this.cast.Ravi];
    const heads = pair.map((c) => c.headPosition());
    const others = [...this.game.npcs, this.player].filter((c) => c.root.visible && !pair.includes(c));
    const target = mid.clone().add(V(0, 1.2, 0));
    let best = null;
    for (const side of [1, -1]) for (const d of [3.1, 2.6, 3.7]) for (const h of [1.6, 2.2]) {
      const p = mid.clone().addScaledVector(perp, side * d).addScaledVector(ab, -0.5).add(V(0, h, 0));
      const toMid = target.clone().sub(p), dist = toMid.length();
      toMid.normalize();
      let score = 0;
      for (const c of others) {
        const q = c.root.position.clone().add(V(0, 1.1, 0)).sub(p);
        const along = q.dot(toMid);
        if (Math.hypot(q.x, q.z) < 1.3) score += 10;                                    // at the lens
        else if (along > 0 && along < dist - 0.4 && q.clone().normalize().dot(toMid) > 0.72) score += 3; // in the foreground (in frame)
      }
      if (heads.some((hd) => rig.blocked(p, hd, pair))) score += 5;
      score += d * 0.05 + (h > 2 ? 0.2 : 0); // prefer the closer, eye-level shot when it's as clear
      if (!best || score < best.score) best = { p, score };
    }
    rig.cut(best.p, target, 1, true);
  }

  /** The passing-out parade is a big day: a full stand, families waving at the front, bunting and a banner. */
  paradeDressing() {
    const S = this.sets.camp;
    for (const o of this.paradeProps || []) o.parent?.remove(o);
    this.paradeProps = [];
    const add = (o) => { S.scene.add(o); this.paradeProps.push(o); return o; };
    // Bunting along the front of both stands' roofs, and across the dais.
    for (const [x0, x1] of [[-10.5, 3.6], [12.4, 26.6]]) add(P.bunting(V(x0, 2.85, 24.2), V(x1, 2.85, 24.2), { n: 22, sag: 0.3 }));
    add(P.bunting(V(4.9, 2.5, 22.1), V(11.1, 2.5, 22.1), { n: 10, sag: 0.25 }));
    // A banner on the front of the dais.
    const banner = new THREE.Mesh(new THREE.PlaneGeometry(5.8, 0.72), new THREE.MeshStandardMaterial({ map: P.banner(T.parade.banner), roughness: 0.85 }));
    banner.position.set(8, 1.05, 22.13);
    banner.rotation.y = Math.PI; // facing the square
    add(banner);
    // The national flag at the top of the flagpole by the dais, stirring a little.
    const flag = new THREE.Mesh(new THREE.PlaneGeometry(1.5, 1.0, 12, 1), new THREE.MeshStandardMaterial({ map: D.flag(), roughness: 0.8, side: THREE.DoubleSide }));
    flag.position.set(3.6 + 0.8, 11.05, 22); // the pole (tools/build_camp.py) tops out at 11.85 m
    flag.rotation.y = Math.PI;
    add(flag);
    const fp = flag.geometry.attributes.position, fx0 = Float32Array.from(fp.array);
    this.stopFlag?.();
    this.stopFlag = this.game.every(() => {
      const t = this.game.time;
      for (let k = 0; k < fp.count; k++) { const x = fx0[k * 3] + 0.75; fp.array[k * 3 + 2] = fx0[k * 3 + 2] + Math.sin(t * 2.4 + x * 3.2) * 0.07 * x; }
      fp.needsUpdate = true;
    });
    // More families in the stands (between the seat markers), seated.
    const seats = this.markersWith('STAND_Seat_').map((m) => m.pos);
    let i = 40;
    for (const [x0, x1] of [[-10.3, 3.3], [12.7, 26.3]]) {
      for (const [z, y] of [[24.9, 0.3], [26.1, 0.7]]) {
        for (let x = x0; x <= x1; x += 1.45) {
          const p = V(x, y, z);
          if (seats.some((q) => q.distanceTo(p) < 0.9)) continue;
          const ch = this.spawnExtra(i++, p, Math.PI);
          ch.play(ch.clips.Sit ? 'Sit' : 'Idle');
        }
      }
    }
    // A loose row standing at the front, some of them waving as the file goes by (clear of Boon's X, the
    // flagpole and the dais).
    const stand = this.marker('STAND_X', V(12, 0, 19.5)).pos;
    for (let x = -9; x <= 26; x += 1.3) {
      if (Math.abs(x - stand.x) < 2.2 || Math.abs(x - 3.6) < 0.9 || (x > 4.6 && x < 11.4)) continue;
      const p = V(x + Math.sin(x * 7.3) * 0.25, 0, 22.3 + Math.sin(x * 3.1) * 0.35);
      if (this.crowded(p, 1.0)) continue;
      const ch = this.spawnExtra(i++, p, Math.PI + Math.sin(x) * 0.2);
      if (i % 3 !== 0 && ch.clips.Wave) ch.play('Wave', { speed: 0.8 + ((i * 37) % 10) / 25 });
    }
  }

  fillStands() {
    const stand = (k, mk) => { if (this.cast[k]) this.place(this.cast[k], mk); };
    stand('Siti', 'NPC_Siti_Stand');
    stand('Rajan', 'NPC_Rajan_Stand');
    stand('Rohani', 'NPC_Rohani_Stand');
    stand('AhPek', 'NPC_AhPek_Stand');
    stand('Letchumi', 'NPC_Letchumi_Stand');
    if (this.kindness.has('bundles')) stand('Neighbour', 'NPC_Neighbour_Stand');
    if (this.kindness3.has('oranges')) stand('AhHockMa', 'NPC_AhMa_Stand');
    this.markersWith('STAND_Seat_').forEach((mk, i) => { const ch = this.spawnExtra(i, mk.pos, mk.yaw); ch.play(ch.clips.Sit ? 'Sit' : 'Idle'); });
  }

  /** "Pandang kanan!": the player turns Sparky's head, and finds Boon standing on Ravi's X. */
  async revealBoon(d) {
    const g = this.game;
    this.revealing = true;
    const Boon = this.place(this.cast.Boon, 'STAND_X');
    Boon.play('Idle');
    const tif = P.tiffinCarrier(this.heirlooms.includes('tiffin'));
    tif.position.copy(Boon.root.position).add(V(0.35, 0, -0.2));
    tif.scale.setScalar(1.3);
    this.scene.add(tif);
    this.paradeTiffin = tif;
    // Ease the eye onto Boon's face.
    const vf = g.rig.vf;
    const stopAim = g.every((dt) => {
      const head = Boon.headPosition();
      const dir = head.clone().sub(vf.pos);
      const yaw = Math.atan2(dir.x, dir.z);
      const pitch = -Math.atan2(dir.y, Math.hypot(dir.x, dir.z));
      const k = 1 - Math.exp(-3 * dt);
      vf.yaw += Math.atan2(Math.sin(yaw - vf.yaw), Math.cos(yaw - vf.yaw)) * k;
      vf.pitch += (pitch - vf.pitch) * k;
      vf.pos.copy(d.eyePos());
    });
    g.rig.targetFov = 28; // lean in on him
    await g.wait(1.2);
    await d.say('Farid', T.parade.reveal.text, 2.4);
    await d.say('PA', T.parade.minister.text, 5.2);
    stopAim();
    // Eyes front: straight back to the tracking shot beside the file (it kept marching while we looked),
    // at the normal field of view, and keep tracking from here on.
    g.rig.targetFov = g.camera.fov = 55;
    g.camera.updateProjectionMatrix();
    this.revealing = false;
    this.drillLooking = false;
    if (this.paradeMembers) this.paradeCamera(this.paradeMembers, true);
  }

  async passOut(members) {
    const g = this.game;
    const X = T.parade;
    const Boon = this.cast.Boon;
    const Farid = this.cast.Farid;
    g.mode = 'cutscene';
    this.player.scripted = false;
    // Broken ranks: everyone turns and loosens up before Farid steps out to meet Boon.
    const loose = { Leo: V(-1.3, 0, -0.8), AhHock: V(1.5, 0, -0.9), Ravi: V(2.1, 0, 0.2) }; // away from where Farid meets Boon
    for (const m of members) {
      if (m.ch.isPlayer) continue;
      m.ch.play('Idle');
      if (loose[m.key]) m.ch.moveTo([m.ch.root.position.clone().add(loose[m.key])], { speed: 0.8 }).then(() => m.ch.faceTowards(V(m.ch.root.position.x, 0, 30), false));
    }
    await g.wait(0.8);
    // Dismissed. Farid steps out of the file; Boon walks straight to him. Filmed side-on, clear of the others.
    const fp = Farid.root.position.clone().add(V(0, 0, 1.4));
    Farid.moveTo([fp], { speed: 0.9 });
    const meet = fp.clone().add(V(0, 0, 1.25));
    const pair = fp.clone().lerp(meet, 0.5);
    g.rig.cut(pair.clone().add(V(3.4, 1.5, 0.3)), pair.clone().add(V(0, 1.15, 0)), 1.6);
    // Sparky follows Farid out and stands on the far side of the pair, facing the camera.
    const sp = this.player;
    const sparkySpot = pair.clone().add(V(-0.85, 0, 0.05));
    sp.scripted = true;
    const sparkyWalk = sp.moveTo([sp.root.position.clone().add(V(-0.8, 0, 0.5)), sparkySpot], { speed: 0.9 });
    await Promise.all([Boon.moveTo([meet], { speed: 1.1 }), sparkyWalk]);
    Boon.faceTowards(Farid.root.position, true);
    Farid.faceTowards(Boon.root.position, true);
    sp.scripted = false;
    sp.faceTowards(pair.clone().add(V(1, 0, 0)), true);
    await this.lines(X.after.slice(0, 2), { frame: false });
    // The photo: the section squeezes in, Sparky in the middle.
    const mid = this.player.root.position.clone();
    const order = ['Leo', 'Farid', 'Sparky', 'AhHock', 'Ravi'];
    order.forEach((k, i) => {
      const ch = k === 'Sparky' ? this.player : this.cast[k];
      ch.stop?.();
      ch.place(mid.clone().add(V((i - 2) * 0.62, 0, Math.abs(i - 2) * 0.12)), Math.PI);
      ch.play('Idle');
    });
    const eye = mid.clone().add(V(0, 1.45, -4.2));
    Boon.place(eye.clone().setY(0).add(V(0, 0, -0.3)), 0);
    Boon.play('Idle');
    // Over Boon's shoulder: the section squeezing in.
    g.rig.cut(eye.clone().add(V(0.9, 0.25, -1.5)), mid.clone().add(V(0, 0.9, 0)), 1, true);
    await this.lines(X.after.slice(2, 3), { frame: false });
    g.rig.cut(eye, mid.clone().add(V(0, 0.85, 0)), 2);
    await g.wait(1.4);
    await this.lines(X.after.slice(3), { frame: false });
    g.rig.cut(eye, mid.clone().add(V(0, 0.85, 0)), 1, true);
    g.rig.update(0, null, null);
    g.renderer.render(0);
    const img = capturePhoto(g.canvas, { size: 512 });
    g.audio.play('camera-shutter');
    g.ui.flash?.();
    await g.wait(0.6);
    await this.developPhoto('Parade', img);
    g.mode = 'cutscene';
    this.ambience(null);
    if (this.paradeTiffin) { this.paradeTiffin.parent?.remove(this.paradeTiffin); this.paradeTiffin = null; }
  }

  // ------------------------------------------------------------------ the ending (2026)
  async ending() {
    const g = this.game;
    const X = T.ending;
    const Pd = this.present;
    g.mode = 'cutscene';
    await g.tween(g.renderer.grade, { sepia: 1, saturation: 0 }, 2.2);
    await g.ui.fade(true, 1.2, 'sepia');
    this.hideAll();
    this.stopFlag?.(); this.stopFlag = null;
    Pd.show();
    Pd.active = true;
    Object.assign(g.renderer.grade, { sepia: 0, saturation: 0.95, vignette: 0.45 });
    g.renderer.grade.tint.setRGB(1, 1, 1);
    Pd.wideShot(true);
    await g.ui.fade(false, 1.5);
    // Farid (77) and Irfan are already on their way across the void deck as the scene opens.
    const { Farid77, Irfan } = this.cast;
    const table = Pd.tablePos || V(0, 0.75, 0);
    const bs = Pd.pose('PRO_Stool_Boon', table.clone().add(V(0, -0.75, 0.9))).pos;
    const ss = Pd.pose('PRO_Stool_Sparky', table.clone().add(V(0, -0.75, -0.9))).pos;
    const axis = bs.clone().sub(ss).setY(0).normalize();
    const perp = V(-axis.z, 0, axis.x);
    const wide = Pd.pose('PRO_Camera_Wide', table.clone().add(V(2.4, 1.4, 3))).pos;
    if (perp.dot(wide.clone().sub(table).setY(0)) > 0) perp.negate();
    const floor = table.clone().setY(bs.y);
    // Between Sparky and Mr. Boon as the wide shot sees them (not hidden behind Mr. Boon's head).
    const faridSpot = floor.clone().addScaledVector(perp, 1.05).addScaledVector(axis, -0.55);
    const irfanSpot = floor.clone().addScaledVector(perp, 1.55).addScaledVector(axis, 0.85);
    // They come in from the playground, through the gap in the hedge behind the table (in the back of the
    // wide shot), Irfan a step behind his grandfather, who carries the tiffin carrier.
    const gap = Pd.pose('PRO_HedgeGap', V(-2.0, 0, 4.6)).pos.setY(floor.y);
    const inside = gap.clone().add(V(0.8, 0, -1.4)); // past the scooter, onto the tiles
    Farid77.place(gap.clone().add(V(0, 0, 3.6)), Math.PI);
    Irfan.place(gap.clone().add(V(-0.1, 0, 4.7)), Math.PI);
    Farid77.root.visible = true; Irfan.root.visible = true;
    g.npcs = [...g.npcs.filter((c) => c !== Farid77 && c !== Irfan), Farid77, Irfan];
    const endTiffin = P.tiffinCarrier(this.heirlooms.includes('tiffin'));
    endTiffin.position.set(-0.27, 0.42, 0.06); // hanging from his right hand
    Farid77.root.add(endTiffin);
    const arrive = Promise.all([
      Farid77.moveTo([gap, inside, faridSpot], { speed: 0.8 }),
      g.wait(1.3).then(() => Irfan.moveTo([gap, inside.clone().add(V(-0.5, 0, 0.1)), irfanSpot], { speed: 0.85 })),
    ]);
    await this.presentLines(T.oldBoon.slice(0, 2));
    await this.presentLines(T.oldBoon.slice(2));
    await arrive;
    Farid77.faceTowards(table, true); Irfan.faceTowards(table, true);
    this.endingLayout = { table, floor, perp, axis };
    Pd.closeShot();
    const talk = (list) => this.presentLines(list);
    // He sets the tiffin carrier down on the table ("Your turn to fill it, Abang").
    Farid77.root.remove(endTiffin);
    endTiffin.position.copy(table).add(V(-0.26, 0.004, 0.02)); // beyond the Brownie from the close-up, not in front of Sparky
    Pd.scene.add(endTiffin);
    this.endTiffin = endTiffin;
    await talk(X.arrive);
    const env = new THREE.Mesh(new THREE.BoxGeometry(0.22, 0.012, 0.15), new THREE.MeshStandardMaterial({ color: '#c9a86a', roughness: 0.8 }));
    env.position.copy(table).add(V(-0.1, 0.012, 0.15));
    Pd.scene.add(env);
    await talk(X.envelope);
    // The player opens it.
    await this.waitForPress(X.envelopePrompt);
    env.visible = false;
    g.audio.play('paper');
    const roll = [
      ['ww2', ['ww2-Banana', 'ww2-Headline'], 'February 1942'],
      ['ind', ['ind-Wall', 'ind-Anguish'], '9 August 1965'],
      ['ns', ['ns-Parade'], '2 March 1968'],
    ];
    for (const [ch, ids, year] of roll) {
      const photo = ids.map((id) => g.album.photos[id]).find(Boolean);
      g.input.releaseLock();
      await g.ui.develop(photo ? { ...photo, caption: photo.title } : { title: 'A frame from the roll', year, text: 'This photo develops when you play that chapter.', image: this.blankPrint(year) });
      await talk(X.photos[ch]);
    }
    await talk(X.reunion);
    await talk(X.selfie);
    // The phone photo, in colour: Irfan steps round to the open side and holds up his phone.
    const L = this.endingLayout;
    Irfan.place(L.floor.clone().addScaledVector(L.perp, -2.4), 0);
    Irfan.faceTowards(table, true);
    Farid77.place(L.floor.clone().addScaledVector(L.perp, 0.75), 0);
    Farid77.faceTowards(L.floor.clone().addScaledVector(L.perp, -2), true);
    const eye = L.floor.clone().addScaledVector(L.perp, -2.25).add(V(0, 1.35, 0));
    const aim = L.floor.clone().addScaledVector(L.perp, 0.2).add(V(0, 0.95, 0));
    Irfan.root.visible = false; // he's behind the phone
    g.rig.cut(eye, aim, 1, true);
    g.rig.update(0, null, null);
    g.renderer.render(0);
    const phone = capturePhoto(g.canvas, { size: 512, tone: 'colour' });
    g.audio.play('camera-shutter');
    await this.developPhoto('Phone', phone);
    g.mode = 'cutscene'; // developPhoto hands control back; the ending stays a cutscene at the table
    Irfan.root.visible = true;
    g.rig.cut(eye.clone().addScaledVector(L.perp, -0.6).add(V(0, 0.2, 0)), aim, 1.2);
    await talk(X.last);
    await talk(X.nextTime);
    await g.ui.fade(true, 1.4);
    await g.ui.card('The End', 'Footsteps of a Nation', 'Three days on one roll of film. Thank you for remembering them.', 5);
    g.audio.music(null, { fade: 3 });
    this.game.onChapterComplete?.('ns');
  }

  /** Dialogue at the void deck (no framing: the present-day set has its own shots). */
  async presentLines(list) {
    const g = this.game;
    for (const l of list) {
      if (l.who === 'Card') { g.ui.endDialogue(); await this.cardLine(l.text); continue; }
      const ch = l.who === 'OldBoon' ? this.present.boon : this.cast[l.who];
      if (ch?.has?.('Talk')) ch.play('Talk');
      await g.ui.say(this.nameOf(l.who), l.text);
      if (ch?.currentName === 'Talk') ch.play(ch.idleClip);
    }
    g.ui.endDialogue();
  }

  waitForPress(label) {
    const g = this.game;
    g.ui.prompt(label);
    return new Promise((resolve) => {
      const off = g.input.on('action', () => { off(); g.ui.prompt(null); resolve(); });
      const offTap = g.input.on('tap', () => { offTap(); off(); g.ui.prompt(null); resolve(); });
    });
  }

  blankPrint(label) {
    const c = document.createElement('canvas');
    c.width = c.height = 512;
    const x = c.getContext('2d');
    x.fillStyle = '#d8ccb0'; x.fillRect(0, 0, 512, 512);
    x.fillStyle = '#8a7a5a'; x.font = '600 34px Gelasio, Georgia, serif'; x.textAlign = 'center';
    x.fillText(label, 256, 256);
    return c.toDataURL('image/jpeg', 0.8);
  }

  // ------------------------------------------------------------------ extras
  spawnExtra(i, pos, yaw, gltfOverride = null) {
    const m = CROWD[i % CROWD.length];
    const gltf = gltfOverride || this.crowdModels[i % CROWD.length];
    const ch = new Character(`Extra${i}`, gltf, { height: m.height, placeholder: { height: m.height } });
    const tint = new THREE.Color(gltfOverride ? 0xffffff : CROWD_TINTS[i % CROWD_TINTS.length]); // uniforms stay Temasek green
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
    this.armLocks?.delete(ch);
    ch.root.parent?.remove(ch.root);
    this.extras = this.extras.filter((x) => x !== ch);
    this.game.npcs = this.game.npcs.filter((x) => x !== ch);
    this.world.dynamic = this.world.dynamic.filter((x) => x !== ch.collider);
  }

  /** Is a spot too close to a named character (so a background extra would crowd the speakers)? */
  crowded(pos, r = 1.4) {
    return Object.values(this.cast).some((c) => c.root.visible && c.root.parent === this.scene && c.root.position.distanceTo(pos) < r);
  }

  clearExtras() { [...this.extras].forEach((ch) => this.removeExtra(ch)); }

  // ------------------------------------------------------------------ per-frame
  update(dt) {
    if (this.present?.active) this.present.update(dt);
    for (const { bones, pose } of this.armLocks?.values() || []) bones.forEach((b, i) => b.quaternion.copy(pose[i]));
    if (this.sets && this.set === this.sets.kopi) for (const f of this.fans || []) f.rotation.y += dt * (this.lighting === 'kopiEvening' ? 5 : 4.2);
    if (this.torchFollow && this.torch) {
      const r = this.torchFollow.root;
      this.torch.position.copy(r.position).add(V(0, 1.2, 0));
      this.torch.target.position.copy(r.position).add(V(Math.sin(this.torchFollow.yaw) * 4, 0, Math.cos(this.torchFollow.yaw) * 4));
    }
  }

  dispose() {
    this.aborted = true;
    this.stopFlag?.();
    this.stopCam?.();
    document.querySelectorAll('.drill,.letter').forEach((e) => e.remove());
    document.body.classList.remove('drill-open');
    for (const S of Object.values(this.sets || {})) {
      S?.scene.traverse((o) => {
        o.geometry?.dispose?.();
        if (o.material) [].concat(o.material).forEach((m) => { m.map?.dispose?.(); m.dispose?.(); });
      });
    }
  }
}
