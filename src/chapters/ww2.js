import * as THREE from 'three';
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js';
import T from './ww2-text.js';
import { buildFallbackStreet } from './ww2-fallback.js';
import { loadModel, radialTexture, clearModelCache } from '../engine/assets.js';
import { World, collectMarkers, markerPose } from '../engine/world.js';
import { Character } from '../engine/character.js';
import { Player } from '../engine/player.js';
import { oilSmoke, houseFire, Burst, Dust, Formation, skyDome, LightPool, disposeEffect } from '../engine/fx.js';
import { createBrownie } from '../engine/brownie.js';
import { tier } from '../engine/settings.js';
import { shelterTransition, blackoutBeat, rumoursBeat, setLighting } from './ww2-night.js';
import { PresentDay } from './present-day.js';
import { Town } from './ww2-town.js';
import { thenNow, shelterChoice, freeCamera, setupKindness } from './ww2-features.js';
import { preloadNowPeople } from './ww2-now.js';

const V = (x, y, z) => new THREE.Vector3(x, y, z);
const pick = (arr) => arr[Math.floor(Math.random() * arr.length)];

const NAMES = { OldBoon: 'Mr. Boon', AhMa: 'Ah Ma', Boon: 'Ah Boon', Hassan: 'Pak Hassan', Rajan: 'Mr. Rajan', Siti: 'Siti', Shopkeeper: 'Shopkeeper', Radio: 'Wireless', Narrator: null };

const CAST = {
  Siti: { walk: 0.57, run: 1.44, file: 'npc-siti', height: 1.35, placeholder: { shirt: '#6f8fa6', pants: '#7a5a6e', skin: '#b98660', hair: '#1a1410' } },
  Rajan: { walk: 0.71, run: 1.89, file: 'npc-rajan', height: 1.7, placeholder: { shirt: '#b39b6b', pants: '#8a7a55', skin: '#7a4f33', hair: '#15110e', hat: '#4f5446' } },
  AhMa: { walk: 0.46, run: 1.2, file: 'npc-ahma', height: 1.55, placeholder: { shirt: '#e9e4d8', pants: '#1f1d1b', skin: '#d4a57c', hair: '#8c8a86' } },
  Boon: { walk: 0.49, run: 1.2, file: 'npc-boon', height: 1.1, placeholder: { shirt: '#f1ede2', pants: '#4a5563', skin: '#d8a97f', hair: '#16120f' } },
  Hassan: { walk: 0.66, run: 1.74, file: 'npc-hassan', height: 1.65, placeholder: { shirt: '#a7a38e', pants: '#5a4b6b', skin: '#9a6a45', hair: '#16120f', hat: '#2a2a2a' } },
};

const AUDIO = {
  siren: { loop: true, volume: 0.55 }, aircraft: { volume: 0.8 }, impact: { volume: 0.9 }, 'distant-explosion': { volume: 0.7 },
  rumble: { volume: 0.6 }, door: {}, shutter: {}, street: { loop: true, volume: 0.5 }, murmur: { loop: true, volume: 0.5 },
  cicadas: { loop: true, volume: 0.35 }, myna: { volume: 0.5 }, 'koel-short': { volume: 0.4 },
  'footstep-1': { volume: 0.35 }, 'footstep-2': { volume: 0.35 }, 'footstep-3': { volume: 0.35 }, 'footstep-4': { volume: 0.35 }, 'footstep-5': { volume: 0.35 },
  'camera-shutter': {}, 'radio-static': { loop: true, volume: 0.5 }, paper: {}, whistle: { volume: 0.7 }, 'shelter-room': { loop: true, volume: 0.6 },
  'pickup-chime': { volume: 0.6 }, 'ui-click': { volume: 0.5 }, 'theme-1942': { loop: true, music: true, volume: 0.5 },
  'shell-whistle': { volume: 0.85 }, 'ear-ring': { volume: 0.6 }, 'fire-crackle': { loop: true, volume: 0.7 },
  'night-ambience': { loop: true, volume: 0.8 }, heartbeat: { loop: true, volume: 0.5 }, 'paper-piece': { volume: 0.8 },
};

export const SLOTS = [
  { id: 'ww2-Poster', chapter: 'ww2', year: '1942', hint: 'A poster on the street… (optional)' },
  { id: 'ww2-Bicycle', chapter: 'ww2', year: '1941–42', hint: 'Something with two wheels… (optional)' },
  { id: 'ww2-Smoke', chapter: 'ww2', year: '1942', hint: 'Look to the sky at the end of the street… (optional)' },
  { id: 'ww2-Headline', chapter: 'ww2', year: '15 Feb 1942', hint: 'The evening the guns fell silent.' },
  { id: 'ww2-Banana', chapter: 'ww2', year: '1942–45', hint: 'Syonan-to.' },
];

export class WW2Chapter {
  constructor(game, { skipPrologue = false } = {}) {
    this.game = game;
    this.skipPrologue = skipPrologue;
    this.cast = {};
    this.fx = [];
    this.fires = [];
    this.aborted = false;
    this.barkIndex = {};
    this.extras = [];
    this.gltf = {};
  }

  // ------------------------------------------------------------------ loading
  async load(onProgress) {
    const g = this.game;
    const steps = [];
    const prog = (i) => (p) => { steps[i] = p; onProgress?.(steps.reduce((a, b) => a + (b || 0), 0) / 8); };
    const [level, sparky, soldier, ...npcs] = await Promise.all([
      loadModel('ww2-street', prog(0)),
      loadModel('sparky-ww2', prog(1)),
      loadModel('npc-soldier', prog(7)),
      ...Object.values(CAST).map((c, i) => loadModel(c.file, prog(2 + i))),
    ]);
    this.gltf.Soldier = soldier;
    g.audio.setCaptions(T.captions);
    const audioLoad = g.audio.define(AUDIO);

    const scene = new THREE.Scene();
    this.scene = scene;
    this.buildEnvironment(scene);

    // Level.
    const levelRoot = (level || buildFallbackStreet()).scene;
    this.usingFallback = !level;
    scene.add(levelRoot);
    this.level = levelRoot;
    this.m = collectMarkers(levelRoot);
    this.world = new World();
    this.setupLevel(levelRoot);
    this.fitStaticShadows(levelRoot);
    this.setInterior(false);
    g.world = this.world;

    // Characters.
    this.player = new Player(sparky);
    this.player.model.traverse((o) => { if (o.isMesh) o.castShadow = false; });
    scene.add(this.player.root);
    this.player.onStep = () => g.audio.play(`footstep-${1 + Math.floor(Math.random() * 5)}`, { volume: 0.8, rate: 0.9 + Math.random() * 0.25, caption: '' });
    Object.entries(CAST).forEach(([key, cfg], i) => {
      this.gltf[key] = npcs[i];
      // walk/run = the speeds each clip was authored for (from the NPC build), so cadence matches ground speed.
      const ch = new Character(key, npcs[i], { height: cfg.height, placeholder: { height: cfg.height, ...cfg.placeholder }, walkSpeed: cfg.walk, runSpeed: cfg.run, walkClip: key === 'Hassan' ? 'Limp' : 'Walk' });
      if (key === 'Hassan' && !ch.clips.Limp) ch.walkClip = 'Walk';
      this.cast[key] = ch;
      ch.model.traverse((o) => { if (o.isMesh) o.castShadow = false; });
      scene.add(ch.root);
      this.world.dynamic.push(ch.collider);
    });
    // Sparky's box camera: held at the chest while the Snap pose raises his paws (~0.25 m in front).
    this.brownie = createBrownie();
    this.brownie.scale.setScalar(0.11);
    this.brownie.position.set(0, 0.5, 0.27);
    this.brownie.visible = false;
    this.player.root.add(this.brownie);

    this.present = new PresentDay(g);
    this.town = new Town(this);
    await Promise.all([this.present.load(this.envMap), this.town.load(), preloadNowPeople()]);
    await audioLoad;
    onProgress?.(1);
  }

  buildEnvironment(scene) {
    const t = tier();
    scene.background = new THREE.Color('#b9b2a2');
    scene.fog = new THREE.Fog('#bdb3a0', 30, 190);
    this.sky = skyDome({ top: '#7f8a8e', horizon: '#d4c6a8', bottom: '#8f8676', sunDir: V(0.4, 0.55, -0.6), haze: 0.6 });
    this.sky.material.uniforms.smoke.value = 0.35;
    scene.add(this.sky);
    // Soft overcast light: strong sky fill + a hazy sun for form and (on higher tiers) shadows.
    this.hemi = new THREE.HemisphereLight('#e8e1d0', '#6f6352', 1.35);
    scene.add(this.hemi);
    const sun = new THREE.DirectionalLight('#ffe7c4', 2.1);
    sun.position.set(18, 30, -14);
    sun.castShadow = t.shadows;
    if (t.shadows) {
      sun.shadow.mapSize.set(t.shadowSize, t.shadowSize);
      const s = 22;
      Object.assign(sun.shadow.camera, { left: -s, right: s, top: s, bottom: -s, near: 1, far: 90 });
      sun.shadow.bias = -0.0004;
      sun.shadow.normalBias = 0.03;
      sun.shadow.radius = 3;
    }
    scene.add(sun, sun.target);
    this.sun = sun;
    // Constant light set for the whole chapter (see LightPool): fires, candle, Sparky's night fill,
    // plus one shared explosion flash. Nothing is ever added or removed afterwards.
    this.pool = new LightPool(scene, t.maxLights >= 6 ? 4 : t.maxLights >= 4 ? 3 : 1);
    this.flash = new THREE.PointLight(0xffb070, 0, 40, 2);
    scene.add(this.flash);
    const pmrem = new THREE.PMREMGenerator(this.game.renderer.renderer);
    this.envMap = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
    scene.environment = this.envMap;
    scene.environmentIntensity = 0.35;
    pmrem.dispose();
  }

  /**
   * Present-day look without new textures: facades get vivid conservation pastels (saturation +
   * brightness boost of their per-house vertex colours), the road becomes dark modern asphalt.
   */
  prepareEraMaterials(root) {
    this.eraUniform = { value: 0 };
    const U = this.eraUniform;
    root.traverse((o) => {
      if (!o.isMesh) return;
      for (const m of [].concat(o.material)) {
        if (m.userData.eraPatched) continue;
        const plaster = /Plaster/i.test(m.name), road = /Road/i.test(m.name);
        if (!plaster && !road) continue;
        m.userData.eraPatched = true;
        m.onBeforeCompile = (sh) => {
          sh.uniforms.eraNow = U;
          sh.fragmentShader = 'uniform float eraNow;\n' + sh.fragmentShader.replace('#include <color_fragment>', `#include <color_fragment>
            {
              float l = dot(diffuseColor.rgb, vec3(0.299, 0.587, 0.114));
              ${plaster
                ? 'vec3 vivid = mix(vec3(l), diffuseColor.rgb, 1.75) * 1.1 + 0.05; diffuseColor.rgb = mix(diffuseColor.rgb, clamp(vivid, 0.0, 1.0), eraNow);'
                : 'diffuseColor.rgb = mix(diffuseColor.rgb, vec3(l) * vec3(0.42, 0.43, 0.46), eraNow);'}
            }`);
        };
        m.customProgramCacheKey = () => (plaster ? 'era-plaster' : 'era-road');
        m.needsUpdate = true;
      }
    });
  }

  setupLevel(root) {
    const t = tier();
    this.prepareEraMaterials(root);
    const toggles = [];
    root.updateMatrixWorld(true);
    root.traverse((o) => {
      const n = o.name || '';
      if (n.startsWith('COL_')) {
        // COL_Step_* are walkable ledges (ground comes from the visible mesh), not walls.
        if (o.isMesh && !o.userData.walkable && !n.startsWith('COL_Step')) {
          const st = o.userData.state;
          const box = this.world.addBoxFromMesh(o, !n.startsWith('COL_DMG') && st !== 'now' && st !== 'occ');
          if (st) box.state = st;
        }
        o.visible = false;
        return;
      }
      if (/^(OCC_|DMG_|NOW_)/.test(n) && !/^DMG_Fire/.test(n)) { o.visible = false; toggles.push(o); }
      if (o.isMesh) {
        o.receiveShadow = true;
        o.castShadow = t.shadows;
        for (const m of [].concat(o.material)) {
          if (m.map) m.map.anisotropy = t.bloom ? 8 : 2;
          if ('envMapIntensity' in m) m.envMapIntensity = 0.6;
        }
      }
    });
    // Static ray meshes for ground + camera: everything visible that isn't a toggleable/collider node.
    root.traverse((o) => {
      if (!o.isMesh || o.name.startsWith('COL_')) return;
      let p = o, skip = false;
      // Toggle groups are included (hidden ones are ignored at hit time); thin wires/laundry are not.
      while (p && p !== root) { if (/^(WIRES_|LAUNDRY_)/.test(p.name || '')) { skip = true; break; } p = p.parent; }
      if (!skip) this.world.addRayMesh(o);
    });
    // Smoke columns on the horizon.
    const smokes = Object.keys(this.m).filter((k) => k.startsWith('SMOKE_'));
    for (const k of smokes) {
      const s = oilSmoke(markerPose(this.m[k]).pos, 1);
      s.isSmokeColumn = true;
      this.scene.add(s);
      this.fx.push(s);
    }
    this.world.bounds = null;
  }

  /**
   * The sun never moves, so street shadows are rendered once into a map covering the whole street
   * and only refreshed when geometry changes (e.g. the bombed house). Characters use blob shadows.
   * This removes a full extra render of the level every frame.
   */
  fitStaticShadows(root) {
    if (!this.sun.castShadow) return;
    const box = new THREE.Box3();
    root.traverse((o) => {
      if (!o.isMesh || !o.visible || /^(COL_|Backdrop)/.test(o.name)) return;
      const b = new THREE.Box3().setFromObject(o);
      if (b.min.x > 150) return; // shelter interior lives far away
      box.union(b);
    });
    if (box.isEmpty()) return;
    box.min.x = Math.max(box.min.x, -60); box.max.x = Math.min(box.max.x, 60);
    box.min.z = Math.max(box.min.z, -30); box.max.z = Math.min(box.max.z, 30);
    const c = box.getCenter(new THREE.Vector3());
    const r = box.getSize(new THREE.Vector3()).length() / 2;
    const dir = V(18, 30, -14).normalize();
    this.sun.position.copy(c).addScaledVector(dir, r + 20);
    this.sun.target.position.copy(c);
    this.sun.target.updateMatrixWorld();
    const size = tier().shadowSize >= 2048 ? 4096 : 2048;
    this.sun.shadow.mapSize.set(size, size);
    Object.assign(this.sun.shadow.camera, { left: -r, right: r, top: r, bottom: -r, near: 1, far: r * 2 + 40 });
    this.sun.shadow.camera.updateProjectionMatrix();
    this.sun.shadow.bias = -0.0006;
    this.game.renderer.renderer.shadowMap.autoUpdate = false;
    this.refreshShadows();
  }

  /** Only draw the shelter room while inside it, and only the street while outside. */
  setInterior(inside) {
    this.level.traverse((o) => {
      if (!o.name) return;
      if (o.name === 'ShelterInterior') o.visible = inside;
      else if (/^(Street_Static|Backdrop|WIRES_|LAUNDRY_)/.test(o.name)) o.visible = !inside;
    });
    this.fx.forEach((f) => { if (f.isGroup && !f.isBurst) f.visible = !inside; });
    this.sky.visible = !inside;
  }

  refreshShadows() { this.game.renderer.renderer.shadowMap.needsUpdate = true; }

  marker(name, fallback = V(0, 0, 0), yaw = 0) {
    const n = this.m[name];
    if (!n) { console.warn('[ww2] missing marker', name); return { pos: fallback.clone(), yaw }; }
    return markerPose(n);
  }

  show(prefix, on) {
    this.level.traverse((o) => {
      const n = o.name || '';
      if (n.startsWith(prefix) && !n.startsWith('COL_')) o.visible = on;
    });
    this.refreshShadows();
  }

  // ------------------------------------------------------------------ dialogue helper
  frameSpeaker(who) {
    const ch = this.cast[who];
    if (!ch || !this.framing) return;
    this.game.rig.frameTwo(this.player, ch, { lambda: 2.5 });
  }

  /** Play an array of text lines (handles Card, Sparky reactions, Radio, `requires`). */
  lines(list, opts = {}) {
    // Conversations never overlap: a second one waits for the first to finish.
    const run = () => this._lines(list, opts);
    this._linesQueue = (this._linesQueue || Promise.resolve()).then(run, run);
    return this._linesQueue;
  }

  async _lines(list, { frame = true, following = null } = {}) {
    const g = this.game;
    this.framing = frame;
    let framedFor = null;
    for (const line of list) {
      if (this.aborted) throw new Error('aborted');
      if (line.requires && following && !following.has(line.requires)) continue;
      if (line.who === 'Card') { g.ui.endDialogue(); await this.cardLine(line.text); continue; }
      if (line.who === 'Sparky') { await this.react(line.react); continue; }
      const style = line.who === 'Radio' ? 'radio' : (line.who === 'Narrator' ? 'narrator' : '');
      const ch = this.cast[line.who];
      if (ch) this.lastSpeaker = line.who;
      if (frame && ch && framedFor !== line.who) { this.frameSpeaker(line.who); framedFor = line.who; }
      // Seated/cowering characters keep their pose (turning them would lift them off their seat).
      const posed = ['Cower', 'Sit'].includes(ch?.currentName);
      if (ch && !posed) { ch.faceTowards(this.player.root.position); if (ch.has('Talk')) ch.play('Talk'); }
      g.input.moveEnabled = false;
      await g.ui.say(NAMES[line.who] ?? line.who, line.text, { style });
      if (ch && ch.currentName === 'Talk') ch.play(ch.idleClip);
    }
    g.ui.endDialogue();
    g.input.moveEnabled = true;
  }

  async cardLine(text) {
    const [kicker, ...rest] = text.split('. ');
    const g = this.game;
    if (rest.length) await g.ui.card(kicker, rest.join('. ').replace(/\.$/, ''), '', 3.2);
    else await g.ui.card('', text, '', 3);
  }

  async react(kind) {
    const p = this.player;
    if (kind === 'hug') {
      // Step in close to whoever just spoke and hold still for a moment.
      const who = this.cast[this.lastSpeaker];
      // No walking (it could pull Sparky through props): turn to each other and hold the moment.
      if (who) {
        this.player.faceTowards(who.root.position, true);
        if (!['Sit', 'Cower'].includes(who.currentName)) who.faceTowards(this.player.root.position);
      }
      await this.game.wait(1.4);
      this.player.play('Idle');
      return;
    }
    const map = { nod: 'Cheer', startle: 'Crouch', peer: 'Snap' };
    const clip = map[kind];
    if (clip && p.clips[clip]) {
      if (clip === 'Crouch') { p.play('Crouch'); await this.game.wait(0.8); p.play('Idle'); } else await p.play(clip, { loop: false });
    } else await this.game.wait(0.4);
  }

  /** Short non-blocking bark as a toast. */
  bark(line) { if (line) this.game.ui.toast(NAMES[line.who] ?? line.who, line.text, 4); }

  /** Photo sequence: viewfinder → capture → develop card → album. */
  async takePhoto(key, eye, aim, { allowCancel = true } = {}) {
    const g = this.game;
    const info = T.snaps[key];
    const p = this.player;
    // A quick front-on shot of Sparky raising the Brownie, then an iris cut into the viewfinder.
    const prevMode = g.mode;
    g.mode = 'cutscene';
    p.faceTowards(aim, true);
    // Side-on, on whichever side has room — never between Sparky and what he's photographing.
    const head = p.headPosition();
    const sideDir = (s) => V(Math.sin(p.yaw + s * 1.25), 0, Math.cos(p.yaw + s * 1.25));
    const roomL = this.world.rayDistance(head, sideDir(1), 2.5), roomR = this.world.rayDistance(head, sideDir(-1), 2.5);
    const sd = roomL >= roomR ? 1 : -1;
    g.rig.cut(head.clone().addScaledVector(sideDir(sd), Math.min(1.9, Math.max(roomL, roomR) - 0.3)).add(V(0, -0.05, 0)), head.clone().add(V(0, -0.15, 0)), 5, true);
    p.play('Snap', { loop: false });
    await g.wait(0.38); // paws meet in front of the chest at ~0.4 s
    this.brownie.visible = true;
    await g.wait(0.4);
    g.mode = prevMode;
    const img = await g.snap({ eye, aim, label: info.title, allowCancel, onCovered: () => { this.brownie.visible = false; } });
    this.brownie.visible = false;
    if (!img) return false;
    await this.developPhoto(key, img);
    return true;
  }

  /** Show the developing photo + fact card, then add it to the album. */
  async developPhoto(key, img, custom = null) {
    const g = this.game;
    const info = custom || T.snaps[key];
    g.audio.play('pickup-chime');
    const photo = { id: custom?.id || `ww2-${key}`, chapter: 'ww2', title: info.title, year: info.year, text: info.text, image: img, free: !!custom };
    g.mode = 'cutscene';
    g.input.releaseLock();
    await g.ui.develop(photo);
    g.album.add(photo);
    g.input.requestLock();
    g.mode = 'play';
  }

  freeCamera() { return freeCamera(this); }

  setLightingPreset(name) { setLighting(this, name); }

  // ------------------------------------------------------------------ main flow
  async run() {
    const g = this.game;
    g.album.setSlots(SLOTS);
    g.album.setPages({ realVsImagined: T.realVsImagined, sources: T.sources.map((s) => ({ title: `${s.title} — ${s.publisher}`, url: s.url })), credits: T.credits.audio });
    g.npcs = Object.values(this.cast);
    g.player = this.player;
    this.placeCast();
    this.town.populate();

    // Debug: ?beat=papers|raid|shelter|epilogue jumps straight to a beat.
    const beats = ['intro', 'papers', 'raid', 'shelter', 'blackout', 'rumours', 'epilogue'];
    const jump = new URLSearchParams(location.search).get('beat');
    let from = Math.max(0, beats.indexOf(jump));
    if (jump && from > 0) {
      g.setScene(this.scene);
      g.rig.setSubject(this.player);
      g.rig.follow();
      Object.assign(g.renderer.grade, { sepia: 0, saturation: 0.92, vignette: 0.4 });
      await g.ui.fade(false, 0.3);
      if (from >= 3) this.siren = null;
    } else if (!this.skipPrologue) { await this.prologue(); await thenNow(this); }
    if (from <= 0) await this.intro();
    if (from <= 1) await this.papersBeat();
    if (from <= 2) await this.raidBeat();
    if (from <= 3) await shelterTransition(this);
    if (from <= 4) await blackoutBeat(this);
    if (from <= 5) await rumoursBeat(this);
    await this.epilogueBeat();
  }

  placeCast() {
    const sp = this.marker('SPAWN_Sparky');
    this.player.place(sp.pos, sp.yaw);
    for (const key of Object.keys(CAST)) {
      const mk = this.marker(`NPC_${key}`, sp.pos.clone().add(V(2, 0, 0)));
      // Siti stands a few metres further up the five-foot way than her marker, so Sparky's
      // first move is a short walk to her (and she's in the same spot in the Then & Now photo).
      if (key === 'Siti') {
        mk.pos.add(V(Math.sin(sp.yaw), 0, Math.cos(sp.yaw)).multiplyScalar(4.5));
        this.world.resolve(mk.pos, 0.3, 1.4);
        mk.yaw = sp.yaw + Math.PI;
      }
      this.cast[key].place(mk.pos, mk.yaw);
      this.cast[key].home = mk;
    }
  }

  async prologue() {
    const g = this.game;
    const P = this.present;
    P.show();
    g.mode = 'cutscene';
    Object.assign(g.renderer.grade, { sepia: 0, saturation: 0.95, vignette: 0.45, contrast: 1.05, flash: 0 });
    P.wideShot(true);
    await g.ui.fade(false, 1.5);
    g.audio.music('theme-1942', { fade: 3, volume: 0.7 });
    g.audio.play('myna', { caption: '' });
    await g.ui.card('Present day', 'A void deck in Queenstown', '', 2.6);
    const lines = T.prologue.filter((l) => l.who !== 'Sparky');
    await this.lines(lines.slice(0, 2), { frame: false });
    P.closeShot();
    await this.lines(lines.slice(2), { frame: false });
    await P.pushIn();
    g.audio.play('camera-shutter');
    P.active = false;
  }

  async intro() {
    const g = this.game;
    g.setScene(this.scene);
    this.streetAmbience(true);
    const sp = this.marker('SPAWN_Sparky');
    const p = this.player;
    const fwd = V(Math.sin(sp.yaw), 0, Math.cos(sp.yaw));
    g.renderer.grade.sepia = 1; g.renderer.grade.saturation = 0; g.renderer.grade.vignette = 0.8;
    const tn = this.cameFromThenNow;
    let flat = null, streetYaw = 0;
    if (tn) {
      // We've stepped into Mr. Boon's photograph. Sparky stands just ahead, facing forward down the
      // street; the camera is in front of him (we see his face) until the narration ends.
      flat = tn.dir.clone().setY(0).normalize();
      streetYaw = Math.atan2(flat.x, flat.z);
      const at = tn.eye.clone().addScaledVector(flat, 1.2);
      if (Math.abs(flat.x) > Math.abs(flat.z)) at.z = sp.pos.z; else at.x = sp.pos.x;
      at.y = sp.pos.y;
      this.world.resolve(at, 0.3, 1);
      const gy = this.world.groundHeight(at.x, at.y + 0.5, at.z, 0.2, 3);
      if (gy !== null) at.y = Math.max(0, gy);
      p.place(at, streetYaw);
      const head = p.headPosition();
      g.rig.cut(head.clone().addScaledVector(flat, 2.1).add(V(0, 0.05, 0)), head.clone().add(V(0, -0.12, 0)), 1, true);
    } else {
      // High over the middle of the road (never inside the upper floors), looking along the street.
      g.rig.cut(V(sp.pos.x + fwd.x * 12, 7.5, 0), V(sp.pos.x - fwd.x * 4, 2.5, sp.pos.z * 0.6), 1, true);
    }
    await g.ui.fade(false, 1.2, 'sepia');
    const bleed = g.tween(g.renderer.grade, { sepia: 0, saturation: 0.92, vignette: 0.4 }, 4.5);
    await this.cardLine(T.intro[0].text);
    g.audio.play('rumble', { volume: 0.8 });
    g.rig.addShake(0.25);
    await this.lines(T.intro.slice(1), { frame: false });
    await bleed;
    if (tn) {
      // After the narration: an eased orbit from his face round to his back. It swings out on
      // whichever side has more room and lifts over his shoulder, so it clears the pillars.
      const head0 = p.headPosition();
      const perp = V(flat.z, 0, -flat.x);
      const room = (sgn) => this.world.rayDistance(head0, perp.clone().multiplyScalar(sgn), 3);
      const side = room(1) >= room(-1) ? 1 : -1;
      const lateral = Math.min(1.6, Math.max(0.6, room(side) - 0.35));
      const T0 = g.time, dur = 2.8;
      const ease = (k) => (k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2);
      g.rig.mode = 'shot';
      g.rig.shot.lambda = 20;
      await new Promise((resolve) => {
        const off = g.every(() => {
          const k = Math.min(1, (g.time - T0) / dur);
          const e = ease(k);
          const ang = Math.PI * e; // 0 = in front, π = behind
          const head = p.headPosition();
          const along = Math.cos(ang) * THREE.MathUtils.lerp(2.1, 2.7, e); // + ahead of him, − behind
          const across = Math.sin(ang) * lateral * side;
          const h = 0.05 + 0.55 * e + 0.45 * Math.sin(ang);
          const pos = head.clone().addScaledVector(flat, along).addScaledVector(perp, across).add(V(0, h, 0));
          const look = head.clone().add(V(0, -0.12 + 0.1 * e, 0)).addScaledVector(flat, 3 * e);
          g.rig.safePos(pos, look);
          g.rig.shot.pos.copy(pos);
          g.rig.shot.look.copy(look);
          if (k >= 1) { off(); resolve(); }
        });
      });
    } else {
      // Settle on Sparky from along the five-foot way (not through the pillars or beams).
      g.rig.cut(sp.pos.clone().addScaledVector(fwd, 2.6).add(V(0, 1.05, 0)), p.headPosition().add(V(0, -0.1, 0)), 0.6);
      await g.wait(1);
    }
    g.audio.music(null, { fade: 4 });
    g.rig.subject = p;
    g.rig.follow(); // continue smoothly from the intro shot
  }

  streetAmbience(on) {
    const g = this.game;
    if (on) {
      const pos = this.player.root.position;
      this.ambStreet = g.audio.play('street', { volume: 0.4, loop: true, fadeIn: 2, caption: '' });
      this.ambCicada = g.audio.play('cicadas', { volume: 0.3, loop: true, fadeIn: 2, caption: '' });
      const kop = this.marker('NPC_AhMa', pos).pos;
      this.ambMurmur = g.audio.emitter('murmur', kop, { radius: 14, volume: 0.6 });
    } else {
      this.ambStreet?.stop(1.5); this.ambCicada?.stop(1.5);
      if (this.ambMurmur) g.audio.removeEmitter(this.ambMurmur, 1);
    }
  }

  /** Distant guns every so often: the calm morning is not calm. */
  startDread() {
    const g = this.game;
    let next = g.time + 6;
    this.stopDread = g.every(() => {
      if (g.time < next) return;
      next = g.time + 9 + Math.random() * 9;
      g.audio.play(Math.random() < 0.6 ? 'rumble' : 'distant-explosion', { volume: 0.5 + Math.random() * 0.3 });
      g.rig.addShake(0.12);
      if (Math.random() < 0.3) g.audio.play(Math.random() < 0.5 ? 'myna' : 'koel-short', { caption: '' });
    });
  }

  setupBarks() {
    const g = this.game;
    this.barkIts = [];
    for (const key of Object.keys(CAST)) {
      const list = T.papers.barks[key];
      if (!list) continue;
      const ch = this.cast[key];
      this.barkIndex[key] = 0;
      if (!ch.indicatorKind) ch.indicator('chat');
      const it = g.addInteract({
        pos: () => ch.root.position, radius: 1.8, label: `Talk to ${NAMES[key]}`,
        onUse: async () => {
          const line = list[this.barkIndex[key] % list.length];
          this.barkIndex[key]++;
          ch.indicator(null);
          g.mode = 'cutscene';
          await this.lines([line]);
          g.rig.follow();
          g.mode = 'play';
          g.input.requestLock();
        },
      });
      this.barkIts.push(it);
    }
  }

  setupOptionalSnaps() {
    const g = this.game;
    this.snapIts = [];
    for (const key of ['Poster', 'Bicycle', 'Smoke']) {
      const mk = this.m[`SNAP_${key}`];
      if (!mk) continue;
      const pose = markerPose(mk);
      const it = g.addInteract({
        pos: pose.pos, radius: key === 'Smoke' ? 3 : 2.2, label: 'Take a photo',
        onUse: async () => {
          it.enabled = false; // re-enabled below if the player backs out
          const aim = this.snapAim(key, pose);
          const eye = pose.pos.clone().setY(pose.pos.y + 0.95);
          const ok = await this.takePhoto(key, eye, aim);
          it.enabled = !ok;
          g.input.requestLock();
        },
      });
      it.snapKey = key;
      this.snapIts.push(it);
    }
  }

  /** Aim point for a snap marker: along its facing, raised for the sky shot. */
  snapAim(key, pose) {
    const f = V(Math.sin(pose.yaw), 0, Math.cos(pose.yaw));
    if (key === 'Smoke') {
      const smoke = Object.keys(this.m).filter((k) => k.startsWith('SMOKE_')).map((k) => markerPose(this.m[k]).pos);
      if (smoke.length) {
        let best = smoke[0];
        for (const s of smoke) if (s.clone().sub(pose.pos).normalize().dot(f) > best.clone().sub(pose.pos).normalize().dot(f)) best = s;
        return best.clone().setY(60);
      }
      return pose.pos.clone().addScaledVector(f, 100).setY(40);
    }
    return pose.pos.clone().addScaledVector(f, 2).setY(pose.pos.y + 1.0);
  }

  async papersBeat() {
    const g = this.game;
    const siti = this.cast.Siti;
    this.startDread();
    g.mode = 'play';
    g.input.requestLock();
    // Siti waits a few steps up the five-foot way and waves Sparky over.
    siti.faceTowards(this.player.root.position);
    siti.play('Beckon');
    g.objective('Someone is waving at you. Talk to the newspaper girl.', siti);
    siti.indicator('important');
    await this.interactOnce(siti, 'Talk to Siti');
    siti.indicator(null);
    await this.lines(T.papers.start);
    g.audio.play('paper');
    this.setupBarks();
    this.setupOptionalSnaps();
    this.endKindness = setupKindness(this);
    g.ui.toast('Your camera', g.input.isTouch ? 'Tap the camera button (top right) any time to look closer and take photos.' : 'Press C (or right-click) any time to raise your camera, look closer and take photos.', 8);
    g.rig.follow();
    g.mode = 'play';
    g.input.requestLock();

    const drops = T.drops.map((d) => ({ ...d, pose: this.marker(d.marker) }));
    let delivered = 0;
    g.ui.counter(`Papers 0/${drops.length}`);
    let hinted = false;
    await new Promise((resolve) => {
      const remaining = new Set(drops);
      const nextTarget = () => {
        const pp = this.player.root.position;
        let best = null;
        for (const d of remaining) if (!best || d.pose.pos.distanceTo(pp) < best.pose.pos.distanceTo(pp)) best = d;
        g.objective(`${T.papers.hint}`, best?.pose.pos || null);
      };
      nextTarget();
      for (const d of drops) {
        const it = g.addInteract({
          pos: d.pose.pos, radius: 1.7, priority: 10, label: `Deliver ${d.paper}`,
          onUse: async () => {
            it.enabled = false;
            remaining.delete(d);
            delivered++;
            g.audio.play('paper');
            g.mode = 'cutscene';
            this.player.faceTowards(d.pose.pos);
            const sk = this.town.shopkeeperFor(d.marker);
            if (sk) { this.cast.Shopkeeper = sk; sk.faceTowards(this.player.root.position); }
            await this.lines(d.handoff, { frame: !!sk });
            delete this.cast.Shopkeeper;
            g.rig.follow();
            g.ui.counter(`Papers ${delivered}/${drops.length}`);
            g.audio.play('pickup-chime');
            g.ui.toast(d.factTitle || d.shop, d.fact, 10);
            g.mode = 'play';
            g.input.requestLock();
            if (!hinted) { hinted = true; setTimeout(() => g.ui.caption(T.papers.snapHint, 5), 2500); }
            if (!remaining.size) resolve(); else nextTarget();
          },
        });
      }
      const retarget = g.every(() => { if (remaining.size && Math.floor(g.time * 2) % 2 === 0) nextTarget(); if (!remaining.size) retarget(); });
    });
    g.ui.counter(null);
    // Back to Siti — and the siren.
    g.objective('All delivered. Go back to Siti.', siti);
    siti.indicator('important');
    await this.interactOnce(siti, 'Talk to Siti');
    Object.values(this.cast).forEach((c) => c.indicator(null));
    this.barkIts.forEach((it) => g.removeInteract(it));
    this.snapIts.forEach((it) => g.removeInteract(it));
    await this.lines(T.papers.done.filter((l) => l.who !== 'Sparky'));
  }

  /** Wait until the player uses an interactable on a character. */
  interactOnce(ch, label) {
    const g = this.game;
    return new Promise((resolve) => {
      const it = g.addInteract({ pos: () => ch.root.position, radius: 1.9, label, priority: 10, onUse: () => { g.removeInteract(it); g.mode = 'cutscene'; resolve(); } });
    });
  }

  // ------------------------------------------------------------------ raid
  async raidBeat() {
    const g = this.game;
    const { Rajan, AhMa, Boon, Hassan, Siti } = this.cast;
    this.stopDread?.();
    this.endKindness?.();
    this.streetAmbience(false);
    g.mode = 'cutscene';
    this.siren = g.audio.play('siren', { volume: 0.8, loop: true, fadeIn: 0.3 });
    this.react('startle');
    this.player.faceTowards(Rajan.root.position);
    // Mood: darker, dirtier sky.
    g.tween(this.hemi, { intensity: 0.95 }, 4);
    g.tween(this.sun, { intensity: 1.0 }, 4);
    g.tween(this.sky.material.uniforms.smoke, { value: 0.8 }, 6);
    g.tween(g.renderer.grade, { saturation: 0.75, contrast: 1.1, vignette: 0.55 }, 4);
    // Rajan runs up, blowing his whistle.
    g.audio.play('whistle');
    // Rajan comes running up the road from just out of shot, not from the far end of the street.
    const pp0 = this.player.root.position;
    Rajan.place(V(pp0.x + 9, 0, 0.5));
    const toward = pp0.clone().add(Rajan.root.position.clone().sub(pp0).setY(0).normalize().multiplyScalar(1.6));
    g.rig.frameTwo(this.player, Rajan, { lambda: 2 });
    await Rajan.moveTo(toward, { speed: 2.8, clip: Rajan.clips.Run ? 'Run' : 'Walk' });
    await this.lines(T.raid.start);
    // Siti goes with Rajan to the shelter; the others must be found.
    const shelter = this.marker('SHELTER_Entrance');
    const outside = shelter.pos.clone().add(V(0, 0, -Math.sign(shelter.pos.z || 1) * 0.6));
    Siti.moveTo(outside.clone().add(V(0.9, 0, 0)), { speed: 2.4, clip: Siti.clips.Run ? 'Run' : 'Walk' });
    Rajan.moveTo(outside.clone().add(V(-0.9, 0, 0)), { speed: 2.8, clip: Rajan.clips.Run ? 'Run' : 'Walk' }).then(() => { Rajan.faceTowards(this.player.root.position); Rajan.play('Beckon'); });
    AhMa.play('Idle');
    Boon.play('Cower');
    Hassan.play('Idle');
    this.town.panic(shelter.pos);
    this.planes();
    this.startBombing();
    g.rig.follow();
    g.mode = 'play';
    g.input.requestLock();

    const following = new Set();
    const toFind = ['AhMa', 'Boon', 'Hassan'];
    const updateObj = () => {
      const left = toFind.filter((k) => !following.has(k));
      g.ui.counter(`Found ${following.size}/3`);
      if (left.length) {
        const pp = this.player.root.position;
        left.sort((a, b) => this.cast[a].root.position.distanceTo(pp) - this.cast[b].root.position.distanceTo(pp));
        g.objective(T.raid.hint, this.cast[left[0]]);
      } else g.objective('Lead everyone to the shelter!', shelter.pos);
    };
    updateObj();
    const objTimer = g.every(() => { if (Math.random() < 0.02) updateObj(); });

    // Follow barks.
    let nextBark = g.time + 7;
    const barker = g.every(() => {
      if (!following.size || g.time < nextBark || g.mode !== 'play') return;
      nextBark = g.time + 7 + Math.random() * 5;
      const opts = T.raid.follow.filter((l) => following.has(l.who) || l.who === 'Rajan');
      this.bark(pick(opts));
    });

    const hitHouse = this.m.PRE_Intact_House || this.m.DMG_House;
    // Use the house's bounds centre (merged objects often have their origin at the world origin).
    // Aim at the street-facing facade (the bounds centre is deep inside the building).
    let hitPos = null;
    if (hitHouse) {
      const hb = new THREE.Box3().setFromObject(hitHouse);
      const faceZ = Math.abs(hb.min.z) < Math.abs(hb.max.z) ? hb.min.z : hb.max.z;
      hitPos = V((hb.min.x + hb.max.x) / 2, 0, faceZ);
    }

    await new Promise((resolve) => {
      for (const key of toFind) {
        const ch = this.cast[key];
        ch.indicator('important');
        const it = g.addInteract({
          pos: () => ch.root.position, radius: 1.9, priority: 10, label: key === 'Boon' ? 'Coax Ah Boon out' : `Help ${NAMES[key]}`,
          onUse: async () => {
            g.removeInteract(it);
            ch.indicator(null);
            g.mode = 'cutscene';
            await this.lines(T.raid.found[key], { following });
            following.add(key);
            // Boon holds Ah Ma's hand if she's already with us; otherwise trails Sparky.
            const slot = following.size - 1;
            if (key === 'Boon' && following.has('AhMa')) ch.follow(AhMa, { gap: 0.7, speed: 2.8 });
            else if (key === 'AhMa' && following.has('Boon')) { ch.follow(this.player, { gap: 1.3, slot, speed: 2.6 }); Boon.follow(AhMa, { gap: 0.7, speed: 2.8 }); }
            else ch.follow(this.player, { gap: 1.3, slot, speed: key === 'Hassan' ? 1.3 : 2.6 });
            g.audio.play('pickup-chime', { volume: 0.5 });
            updateObj();
            g.rig.follow();
            g.mode = 'play';
            g.input.requestLock();
            if (following.size === 3) resolve();
          },
        });
      }
      // The hit: once anyone is following and Sparky nears the doomed shophouse.
      if (hitPos) {
        this.hitWatch = g.every(() => {
          if (this.houseHit) { this.hitWatch(); return; }
          if (g.mode !== 'play' || !following.size) return;
          const pp = this.player.root.position;
          if (Math.hypot(pp.x - hitPos.x, pp.z - hitPos.z) < 13) { this.hitWatch(); this.houseHitSequence(hitPos, following); }
        });
      }
    });

    // Everyone found — make sure the hit happens on the way if it hasn't yet.
    if (hitPos && !this.houseHit) {
      await g.waitUntil(() => this.houseHit || this.player.root.position.distanceTo(shelter.pos) < 9);
      if (!this.houseHit) await this.houseHitSequence(hitPos, following);
    }
    await g.waitUntil(() => this.houseHitDone !== false);
    let waitingShown = false;
    await g.waitUntil(() => {
      if (g.mode !== 'play') return false;
      const pp = this.player.root.position;
      if (pp.distanceTo(shelter.pos) > 2.4) { if (waitingShown) { waitingShown = false; g.objective('Lead everyone to the shelter!', shelter.pos); } return false; }
      const lagging = toFind.filter((k) => this.cast[k].root.position.distanceTo(pp) > 5.5);
      if (lagging.length && !waitingShown) { waitingShown = true; g.objective(`Wait for ${lagging.map((k) => NAMES[k]).join(' and ')} to catch up!`, null); }
      return !lagging.length;
    });
    objTimer(); barker();
    g.ui.counter(null);
    g.objective(null);
    g.mode = 'cutscene';
    this.stopBombing?.();
    await this.lines(T.raid.arrive);
    await shelterChoice(this);
    g.audio.play('door');
  }

  async houseHitSequence(pos, following) {
    const g = this.game;
    this.houseHit = true;
    this.houseHitDone = false;
    g.mode = 'cutscene';
    g.audio.play('whistle', { volume: 0.3, rate: 0.6, caption: '[A falling bomb whistles]' });
    // From across the road, a little down the street, with Sparky in the foreground.
    const side = Math.sign(pos.z) || -1;
    const camPos = V(pos.x - 6, 1.7, -side * 3.2);
    g.rig.cut(camPos, pos.clone().add(V(0, 3.2, 0)), 3, true);
    await g.wait(1.1);
    this.explode(pos.clone().setY(2), 2.2, true, { caption: '[A bomb hits a shophouse across the road!]' });
    this.show('PRE_Intact_House', false);
    this.show('DMG_', true);
    this.world.setEnabled('COL_DMG', true);
    const firePts = Object.keys(this.m).filter((k) => k.startsWith('DMG_Fire')).map((k) => markerPose(this.m[k]).pos);
    if (!firePts.length) firePts.push(pos.clone());
    for (const fp of firePts) { const f = houseFire(fp, this.pool.claim()); this.scene.add(f); this.fires.push(f); }
    this.player.play('Crouch');
    for (const k of following) if (this.cast[k].has('Cower')) { this.cast[k].stop(); this.cast[k].play('Cower'); }
    await g.wait(1.8);
    await this.lines(T.raid.hit, { frame: false });
    this.player.play('Idle');
    // Resume following.
    const { AhMa, Boon, Hassan } = this.cast;
    let slot = 0;
    for (const k of following) {
      const ch = this.cast[k];
      if (k === 'Boon' && following.has('AhMa')) ch.follow(AhMa, { gap: 0.7, speed: 2.8 });
      else ch.follow(this.player, { gap: 1.3, slot: slot++, speed: k === 'Hassan' ? 1.3 : 2.6 });
    }
    void Boon; void Hassan;
    g.rig.follow();
    g.mode = 'play';
    g.input.requestLock();
    this.houseHitDone = true;
  }

  explode(pos, scale = 1, close = false, { caption } = {}) {
    const g = this.game;
    const b = new Burst(pos, { scale, flashLight: this.flash });
    this.scene.add(b);
    this.fx.push(b);
    const d = this.player.root.position.distanceTo(pos);
    g.audio.play(d < 40 ? 'impact' : 'distant-explosion', { volume: Math.min(1, 25 / Math.max(8, d)), rate: 0.9 + Math.random() * 0.2, caption });
    g.rig.addShake(close ? 1.1 : Math.min(0.8, 18 / Math.max(10, d)));
    if (close) { g.renderer.grade.flash = 0.7; g.tween(g.renderer.grade, { flash: 0 }, 0.6); }
    this.dust?.kick(close ? 1 : 0.35);
  }

  planes() {
    const pp = this.player.root.position;
    const f = new Formation({ count: tier().particles > 0.6 ? 9 : 5, from: V(pp.x - 500, 0, pp.z - 120), to: V(pp.x + 600, 0, pp.z + 80), altitude: 170, speed: 45 });
    this.scene.add(f);
    this.fx.push(f);
    this.game.audio.play('aircraft', { volume: 0.9 });
  }

  startBombing() {
    const g = this.game;
    if (!this.dust) { this.dust = new Dust(500); this.scene.add(this.dust); }
    let next = g.time + 2.5;
    let planeNext = g.time + 28;
    this.stopBombing = g.every(() => {
      if (g.time > planeNext) { planeNext = g.time + 30; this.planes(); }
      if (g.time < next) return;
      next = g.time + 3.5 + Math.random() * 4;
      // Explosions off the street (behind the rooftops), never on the player.
      const pp = this.player.root.position;
      const side = Math.random() < 0.5 ? -1 : 1;
      const pos = V(pp.x + (Math.random() - 0.5) * 60, 1, pp.z + side * (22 + Math.random() * 40));
      this.explode(pos, 2.5 + Math.random() * 2);
    });
  }

  // ------------------------------------------------------------------ epilogue
  async epilogueBeat() {
    const g = this.game;
    const { Rajan, AhMa, Boon, Hassan, Siti } = this.cast;
    // Occupied street: desaturated, cold, quiet. Damage remains; fires are out.
    this.show('PRE_', false);
    this.show('OCC_', true);
    this.show('DMG_', true);
    this.fires.forEach((f) => { this.scene.remove(f); this.pool.release(f.light); disposeEffect(f); });
    this.fires = [];
    setLighting(this, 'occupation');
    this.world.applyStates(['war', 'occ']);
    for (const ch of Object.values(this.cast)) ch.root.visible = true;
    for (const ex of this.extras) ex.root.visible = false;
    // A long, silent ration queue: townsfolk, with Rajan, Pak Hassan and Siti among them.
    const qMarks = Object.keys(this.m).filter((k) => /^EPI_Queue_\d+$/.test(k)).sort((a, b) => +a.split('_')[2] - +b.split('_')[2]).map((k) => markerPose(this.m[k]));
    while (qMarks.length < 4) qMarks.push({ pos: V(20 + qMarks.length, 0.24, -5.5), yaw: Math.PI / 2 });
    const castSlots = [1, 2, 3].map((i) => Math.min(i, qMarks.length - 1));
    [Rajan, Hassan, Siti].forEach((ch, i) => { ch.stop(); ch.root.visible = true; ch.place(qMarks[castSlots[i]].pos, qMarks[castSlots[i]].yaw); ch.play('Idle'); });
    this.town.queue(qMarks.filter((_, i) => !castSlots.includes(i)));
    // Ah Ma sits outside her shuttered kopitiam, Boon close beside her.
    const seat = this.m.EPI_AhMa ? markerPose(this.m.EPI_AhMa) : { pos: qMarks[qMarks.length - 1].pos.clone().add(V(-2.2, 0, 0)), yaw: Math.PI / 2 };
    AhMa.stop(); AhMa.root.visible = true; AhMa.place(seat.pos, seat.yaw); AhMa.play(this.m.EPI_AhMa ? 'Sit' : 'Idle');
    Boon.stop(); Boon.root.visible = true;
    Boon.place(seat.pos.clone().add(V(Math.cos(seat.yaw) * 0.6, 0, -Math.sin(seat.yaw) * 0.6)), seat.yaw); Boon.play('Idle');
    const sp = this.marker('EPI_Spawn', V(-8, 0.2, 4.6));
    this.player.place(sp.pos, sp.yaw);
    g.rig.setSubject(this.player);
    g.rig.yaw = sp.yaw;
    await this.cardLine(T.epilogue.card.text);
    this.ambStreet = g.audio.play('street', { volume: 0.12, loop: true, fadeIn: 2, caption: '' });
    await g.ui.fade(false, 1.5);
    g.mode = 'play';
    g.input.requestLock();
    g.objective('Find your friends in the rice queue.', Siti);
    Siti.indicator('important');
    await g.waitUntil(() => this.player.root.position.distanceTo(Siti.root.position) < 3);
    g.mode = 'cutscene';
    Siti.indicator(null);
    await this.lines(T.epilogue.street);
    g.objective('Go to Ah Ma.', AhMa);
    AhMa.indicator('important');
    g.mode = 'play';
    await this.interactOnce(AhMa, 'Talk to Ah Ma');
    AhMa.indicator(null);
    g.audio.music('theme-1942', { fade: 4, volume: 0.45 });
    await this.lines(T.epilogue.absence);
    await this.lines(T.epilogue.bananaGift);
    g.objective(T.epilogue.snapHint);
    // Step back a pace so Ah Ma (and the note she holds up) fits the frame.
    const away = this.player.root.position.clone().sub(AhMa.root.position).setY(0).normalize();
    const back = AhMa.root.position.clone().addScaledVector(away, 2.3);
    this.world.resolve(back, 0.3, 1);
    this.player.place(back, this.player.yaw);
    const eye = this.player.headPosition().add(V(0, -0.05, 0));
    if (AhMa.currentName !== 'Sit') AhMa.faceTowards(this.player.root.position, true);
    const aim = AhMa.headPosition().add(V(0, AhMa.currentName === 'Sit' ? -0.5 : -0.25, 0));
    g.mode = 'play';
    await this.takePhoto('Banana', eye, aim, { allowCancel: false });
    g.objective(null);
    g.mode = 'cutscene';
    // Final narration over a rising crane shot; fade back to the present.
    const pp = this.player.root.position;
    g.rig.cut(V(pp.x - 6, 9, pp.z * 0.2), pp.clone().add(V(4, 1, 0)), 0.3);
    await this.lines([{ who: 'Narrator', text: T.epilogue.narration }], { frame: false });
    await g.tween(g.renderer.grade, { sepia: 1, saturation: 0 }, 3);
    this.ambStreet?.stop(1);
    await g.ui.fade(true, 1.2, 'sepia');
    this.present.show();
    this.present.closeShot();
    g.rig.cut(g.rig.shot.pos, g.rig.shot.look, 1, true);
    Object.assign(g.renderer.grade, { sepia: 0, saturation: 0.95, vignette: 0.45 });
    g.renderer.grade.tint.setRGB(1, 1, 1);
    await g.ui.fade(false, 1.5);
    this.present.wideShot();
    await this.lines(T.epilogue.oldBoon, { frame: false });
    await g.ui.fade(true, 1.2);
    await g.ui.card('Chapter 1 complete', 'The Fortress Falls', 'Next: 9 August 1965 — A Nation Is Born (coming soon)', 5);
    g.audio.music(null, { fade: 3 });
    g.mode = 'cutscene';
    this.game.onChapterComplete?.('ww2');
  }

  // ------------------------------------------------------------------ per-frame
  update(dt) {
    if (this.present?.active) this.present.update(dt);
    for (const f of this.fx) f.update(dt);
    for (const f of this.fires) f.update(dt);
    this.fx = this.fx.filter((f) => { if (f.done) { this.scene.remove(f); f.dispose?.(); return false; } return true; });
    this.dust?.update(dt, this.game.camera.position);

  }

  dispose() {
    this.aborted = true;
    this.scene?.traverse((o) => {
      o.geometry?.dispose?.();
      if (o.material) [].concat(o.material).forEach((m) => m.dispose?.());
    });
    this.envMap?.dispose();
    clearModelCache();
    this.game.npcs = [];
    this.game.player = null;
  }
}
