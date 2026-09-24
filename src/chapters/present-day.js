import * as THREE from 'three';
import { loadModel } from '../engine/assets.js';
import { collectMarkers, markerPose } from '../engine/world.js';
import { Character } from '../engine/character.js';
import { createBrownie } from '../engine/brownie.js';
import { tier } from '../engine/settings.js';
import { Playground, loadKids } from './present-kids.js';
import { createKopi } from './present-kopi.js';

// Present-day framing scenes (2026): a Queenstown HDB void deck where 91-year-old Mr. Boon shows
// Sparky the Brownie camera. Used for every chapter's prologue and closing, so it lives on its own.

const V = (x, y, z) => new THREE.Vector3(x, y, z);

export class PresentDay {
  constructor(game) {
    this.game = game;
  }

  async load(envMap) {
    const [set, boon, sparky, kids] = await Promise.all([loadModel('voiddeck'), loadModel('npc-oldboon'), loadModel('sparky'), loadKids()]);
    const s = new THREE.Scene();
    this.scene = s;
    const t = tier();
    if (set) {
      s.add(set.scene);
      set.scene.traverse((o) => {
        if (!o.isMesh) return;
        o.receiveShadow = true; o.castShadow = t.shadows;
        // Decals/signs sit just above their surfaces: bias them forward in depth to avoid shimmer.
        for (const m of [].concat(o.material)) if (/Atlas|Paint/.test(m.name)) { m.polygonOffset = true; m.polygonOffsetFactor = -1; m.polygonOffsetUnits = -2; }
      });
      this.m = collectMarkers(set.scene);
      // Golden hour: low warm sun from the open side, warm haze.
      s.background = new THREE.Color('#e8cfae');
      s.fog = new THREE.Fog('#e8cfae', 30, 140);
      s.add(new THREE.HemisphereLight('#ffeedd', '#5e574c', 0.5));
      const sun = new THREE.DirectionalLight('#ffc98a', 2.2);
      const sunP = this.m.PRO_Sun ? markerPose(this.m.PRO_Sun).pos : V(20, 14, 12);
      sun.position.copy(sunP.clone().normalize().multiplyScalar(30));
      sun.castShadow = t.shadows;
      if (t.shadows) {
        sun.shadow.mapSize.set(t.shadowSize * 2, t.shadowSize * 2);
        Object.assign(sun.shadow.camera, { left: -8, right: 8, top: 8, bottom: -8, near: 1, far: 80 });
        sun.shadow.bias = -0.0005; sun.shadow.normalBias = 0.06;
      }
      s.add(sun, sun.target);
      // Fluorescent tubes: a few cool fills (the sun and Sparky's face fill take the rest).
      Object.keys(this.m).filter((k) => k.startsWith('PRO_Lamp')).slice(0, Math.max(0, t.maxLights - 3)).forEach((k) => {
        const l = new THREE.PointLight('#e8f2ff', 1.2, 6, 2);
        l.position.copy(markerPose(this.m[k]).pos);
        s.add(l);
      });
    } else this.buildFallback(s);
    s.environment = envMap;
    s.environmentIntensity = set ? 0.25 : 0.22;

    const tablePos = this.pose('PRO_Table', V(0, 0.75, 0)).pos;
    this.camera = createBrownie();
    this.camera.scale.setScalar(0.12);
    // Rest the camera's base on the table's mosaic board (0.15 m tall body → centre +0.075).
    const boardTop = this.m?.PRO_Table?.userData?.board_top ?? tablePos.y;
    this.camera.position.set(tablePos.x, boardTop + 0.075, tablePos.z);
    s.add(this.camera);
    // Turn the lens toward the close-up camera, so the push-in travels down the lens axis
    // (never through the camera body).
    const close = this.pose('PRO_Camera_Close', tablePos.clone().add(V(0.7, 0.4, 0.8))).pos;
    this.camera.lookAt(close.x, this.camera.position.y, close.z);
    this.camera.rotateY(0.25); // a slight three-quarter angle reads better than dead-on
    // Mr. Boon's bag of kopi beside it, its carrying loop towards the close-up camera.
    this.kopi = createKopi();
    this.kopi.position.copy(this.pose('PRO_Kopi', V(tablePos.x - 0.27, boardTop + 0.006, tablePos.z + 0.24)).pos);
    this.kopi.lookAt(close.x, this.kopi.position.y, close.z);
    this.kopi.rotateY(-Math.PI / 2 - 0.4);
    s.add(this.kopi);

    // Mr. Boon and Sparky on opposite stools (only when the real set provides seats).
    if (set) {
      // NPC Sit clips expect the origin on the seat's centre line. Sparky's Sit has his bottom just
      // behind the origin and his thighs dipping to 0.375 m under it, so he goes a little short of
      // the centre (knees at the front edge) and is lifted until that low point meets the seat.
      const bs = this.pose('PRO_Stool_Boon', tablePos.clone().add(V(0, -0.75, 0.9)));
      const off = this.m.PRO_Stool_Boon?.userData?.seat_centre_offset ?? 0.17;
      bs.pos.add(V(-Math.sin(bs.yaw) * off, 0, -Math.cos(bs.yaw) * off));
      const ss = this.pose('PRO_Stool_Sparky', tablePos.clone().add(V(0, -0.75, -0.9)));
      const sud = this.m.PRO_Stool_Sparky?.userData ?? {};
      const f = V(Math.sin(ss.yaw), 0, Math.cos(ss.yaw)); // Sparky faces the table
      ss.pos.addScaledVector(f, -((sud.seat_centre_offset ?? 0.17) - 0.05));
      ss.pos.y += (sud.seat_height ?? 0.45) - 0.375;
      // Wide two-shot favouring Sparky: past Mr. Boon's shoulder, on the open side the set's wide
      // camera uses, ~35° off Sparky's facing so his face and the DSTA lettering read clearly.
      const side = V(f.z, 0, -f.x);
      const wideM = this.pose('PRO_Camera_Wide', tablePos.clone().add(V(2.4, 1.4, 3))).pos;
      const turn = side.dot(wideM.clone().sub(tablePos)) < 0 ? -1 : 1;
      side.multiplyScalar(turn);
      this.wide = tablePos.clone().addScaledVector(f, 1.5).addScaledVector(side, 2.7).setY(tablePos.y + 1);
      this.wideLook = tablePos.clone().addScaledVector(f, -0.15).add(V(0, 0.05, 0));
      ss.yaw += 0.35 * turn; // swivel a little toward that camera on the round stool
      // Soft warm fill on his face: the low sun is behind him from the wide camera.
      const fill = new THREE.PointLight('#ffe2c0', 1.6, 3.2, 2);
      fill.position.copy(ss.pos).addScaledVector(f, 0.95).addScaledVector(side, 0.9).setY(1.3);
      s.add(fill);
      this.boon = new Character('OldBoon', boon, { height: 1.55, placeholder: { shirt: '#f4f1ea', pants: '#6b6b6b', skin: '#d2a47c', hair: '#e8e6e0' } });
      this.boon.place(bs.pos, bs.yaw);
      this.boon.play('Sit');
      this.sparky = new Character('Sparky', sparky, { height: 1.0 });
      this.sparky.place(ss.pos, ss.yaw);
      this.sparky.play('Sit');
      s.add(this.boon.root, this.sparky.root);
      // Children playing in the playground behind them.
      this.playground = new Playground(s, this.m, kids);
    }
    this.hasSet = !!set;
    this.tablePos = tablePos;
  }

  pose(name, fallback) {
    const n = this.m?.[name];
    return n ? markerPose(n) : { pos: fallback.clone(), yaw: 0 };
  }

  buildFallback(s) {
    s.background = new THREE.Color('#0d0b09');
    s.fog = new THREE.Fog('#0d0b09', 4, 14);
    const terrazzo = new THREE.MeshStandardMaterial({ color: '#8f8a80', roughness: 0.45 });
    const table = new THREE.Mesh(new THREE.CylinderGeometry(0.75, 0.75, 0.06, 40), terrazzo);
    const leg = new THREE.Mesh(new THREE.CylinderGeometry(0.16, 0.22, 0.72, 20), terrazzo);
    leg.position.y = -0.36;
    table.add(leg);
    table.position.y = 0.72;
    s.add(table);
    const floor = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), new THREE.MeshStandardMaterial({ color: '#4a463f', roughness: 0.9 }));
    floor.rotation.x = -Math.PI / 2;
    s.add(floor);
    s.add(new THREE.HemisphereLight('#f4ead6', '#302820', 0.22));
    const key = new THREE.SpotLight('#ffd9a8', 9, 9, 0.55, 0.7, 1.5);
    key.position.set(1.4, 2.6, 1.2);
    key.castShadow = true;
    s.add(key, key.target);
  }

  update(dt) {
    this.boon?.update(dt);
    this.sparky?.update(dt);
    this.playground?.update(dt);
  }

  show() {
    const g = this.game;
    g.renderer.setScene(this.scene, g.camera);
    g.scene = this.scene;
    this.active = true;
  }

  wideShot(instant = false) {
    const g = this.game;
    const pos = this.wide ?? this.pose('PRO_Camera_Wide', this.tablePos.clone().add(V(2.4, 1.4, 3))).pos;
    const look = this.wideLook ?? this.tablePos.clone().add(V(0, 0.2, 0));
    g.rig.cut(pos, look, instant ? 1 : 0.5, instant);
  }

  closeShot() {
    const g = this.game;
    const c = this.pose('PRO_Camera_Close', this.tablePos.clone().add(V(0.7, 0.4, 0.8)));
    g.rig.cut(c.pos, this.tablePos.clone().add(V(0, 0.08, 0)), 0.35);
  }

  /**
   * Push into the Brownie's lens in one continuous move: swing onto the lens axis while closing in
   * on a log scale (so the lens grows at a steady rate), narrowing the field of view and bleeding to
   * sepia, until the dark glass fills the frame; then the iris closes on the lens. The next scene
   * opens the iris again (`ui.irisClosed`), so it reads as looking through the old camera.
   */
  async pushIn() {
    const g = this.game, cam = g.camera, rig = g.rig;
    const b = this.camera;
    b.updateMatrixWorld();
    const lens = b.localToWorld(V(0, -0.1, 0.5725)); // front of the taking lens's glass
    const axis = V(0, 0, 1).transformDirection(b.matrixWorld).add(V(0, 0.04, 0)).normalize();
    const from = cam.position.clone().sub(lens);
    const d0 = from.length(), d1 = 0.012;
    from.normalize();
    const look0 = rig.lookAt.clone(), fov0 = cam.fov, near0 = cam.near, far0 = cam.far;
    // Millimetres from the glass: a much closer near plane (and a nearer far one, for depth precision).
    cam.near = 0.004; cam.far = 200;
    rig.mode = 'scripted';
    const secs = 4.2, t0 = g.time;
    const smooth = (a, c, x) => { const t = Math.min(1, Math.max(0, (x - a) / (c - a))); return t * t * (3 - 2 * t); };
    const dir = V(), look = V();
    // Up close the glass would only mirror the synthetic environment: fade its reflections so the
    // last stretch looks into a dark lens.
    const glass = b.userData.lensGlass, boost0 = glass.userData.envBoost, coat0 = glass.clearcoat;
    g.tween(g.renderer.grade, { sepia: 0.85, saturation: 0.35, vignette: 0.95 }, secs);
    await new Promise((resolve) => {
      const stop = g.every(() => {
        const k = Math.min(1, (g.time - t0) / secs);
        const e = 0.5 - 0.5 * Math.cos(Math.PI * k);
        dir.lerpVectors(from, axis, smooth(0, 0.6, e)).normalize();
        cam.position.copy(lens).addScaledVector(dir, d0 * Math.pow(d1 / d0, e));
        look.lerpVectors(look0, lens, smooth(0, 0.35, e));
        rig.lookAt.copy(look);
        cam.lookAt(look);
        cam.fov = rig.targetFov = fov0 + (34 - fov0) * smooth(0.4, 1, e);
        cam.updateProjectionMatrix();
        const dark = smooth(0.5, 0.92, e);
        glass.userData.envBoost = boost0 * (1 - dark);
        glass.clearcoat = coat0 * (1 - 0.85 * dark);
        if (k >= 1) { stop(); resolve(); }
      });
    });
    await g.ui.iris(true, 0.45, { y: 50, soft: 3 });
    cam.near = near0; cam.far = far0; cam.fov = rig.targetFov = fov0;
    glass.userData.envBoost = boost0; glass.clearcoat = coat0;
    cam.updateProjectionMatrix();
    rig.shot.pos.copy(cam.position); rig.shot.look.copy(look);
    rig.mode = 'shot';
  }
}
