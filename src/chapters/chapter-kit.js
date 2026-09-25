import * as THREE from 'three';
import { markerPose } from '../engine/world.js';

// Shared chapter helpers (dialogue with framing, Sparky's reactions, photos, one-shot interactions,
// free "Look closer" camera). Chapter 1 predates this and keeps its own copies in ww2.js; new
// chapters extend ChapterKit and provide: game, cast, player, world, m (markers), brownie,
// T (text with .snaps), id ('ind'), names ({ key: display name }).

const V = (x, y, z) => new THREE.Vector3(x, y, z);

export class ChapterKit {
  constructor(game, { id, T, names }) {
    this.game = game;
    this.id = id;
    this.T = T;
    this.names = names;
    this.cast = {};
    this.extras = [];
    this.fx = [];
    this.gltf = {};
    this.aborted = false;
    this.barkIndex = {};
  }

  marker(name, fallback = V(0, 0, 0), yaw = 0) {
    const n = this.m?.[name];
    if (!n) { console.warn(`[${this.id}] missing marker`, name); return { pos: fallback.clone(), yaw }; }
    return markerPose(n);
  }

  markersWith(prefix) {
    return Object.keys(this.m).filter((k) => k.startsWith(prefix)).sort((a, b) => a.localeCompare(b, 'en', { numeric: true })).map((k) => ({ name: k, ...markerPose(this.m[k]) }));
  }

  nameOf(who) { return this.names[who] ?? who; }

  // ------------------------------------------------------------------ dialogue
  frameSpeaker(who) {
    const ch = this.cast[who];
    if (!ch || !this.framing) return;
    this.game.rig.frameTwo(this.player, ch, { lambda: 2.5 });
  }

  /** Play text lines (handles Card, Sparky reactions, Radio / Narrator styles). Never overlaps. */
  lines(list, opts = {}) {
    const run = () => this._lines(list, opts);
    this._linesQueue = (this._linesQueue || Promise.resolve()).then(run, run);
    return this._linesQueue;
  }

  async _lines(list, { frame = true } = {}) {
    const g = this.game;
    this.framing = frame;
    let framedFor = null;
    for (const line of list) {
      if (this.aborted) throw new Error('aborted');
      if (line.fact) { g.ui.toast(line.fact.title, line.fact.text, 11); continue; }
      if (line.who === 'Card') { g.ui.endDialogue(); await this.cardLine(line.text); continue; }
      if (line.who === 'Sparky') { await this.react(line.react); continue; }
      const style = line.who === 'Radio' ? 'radio' : (line.who === 'Narrator' ? 'narrator' : '');
      const ch = this.cast[line.who];
      if (ch) this.lastSpeaker = line.who;
      if (frame && ch && framedFor !== line.who) { this.frameSpeaker(line.who); framedFor = line.who; }
      const posed = ['Sit', 'Cower', 'Attention'].includes(ch?.currentName); // on parade, recruits keep facing front
      if (ch && !posed) { ch.faceTowards(this.player.root.position); if (ch.has('Talk')) ch.play('Talk'); }
      g.input.moveEnabled = false;
      await g.ui.say(line.who === 'Narrator' ? '' : this.nameOf(line.who), line.text, { style });
      if (ch && ch.currentName === 'Talk') ch.play(ch.idleClip);
    }
    g.ui.endDialogue();
    g.input.moveEnabled = true;
  }

  async cardLine(text) {
    const [kicker, ...rest] = text.split('. ');
    if (rest.length) await this.game.ui.card(kicker, rest.join('. ').replace(/\.$/, ''), '', 3.2);
    else await this.game.ui.card('', text, '', 3);
  }

  async react(kind) {
    const p = this.player;
    if (kind === 'hug') {
      const who = this.cast[this.lastSpeaker];
      if (who) p.faceTowards(who.root.position, true);
      await this.game.wait(1.4);
      p.play('Idle');
      return;
    }
    const clip = { nod: 'Cheer', startle: 'Crouch', peer: 'Snap' }[kind];
    if (clip && p.clips[clip]) {
      if (clip === 'Crouch') { p.play('Crouch'); await this.game.wait(0.8); p.play('Idle'); } else await p.play(clip, { loop: false });
    } else await this.game.wait(0.4);
  }

  /** Short non-blocking line as a toast. */
  bark(line) { if (line) this.game.ui.toast(this.nameOf(line.who), line.text, 4); }

  /** Resolve when the player uses an interactable on a character (or at a position). */
  interactOnce(target, label, { radius = 1.9, priority = 10 } = {}) {
    const g = this.game;
    const pos = target.isVector3 ? target : () => target.root.position;
    return new Promise((resolve) => {
      const it = g.addInteract({ pos, radius, label, priority, onUse: () => { g.removeInteract(it); g.mode = 'cutscene'; g.ui.prompt(null); resolve(); } });
    });
  }

  /** Back to free play after a cutscene bit. */
  resume() {
    const g = this.game;
    if (g.ui.irisClosed && g.mode !== 'viewfinder') g.ui.iris(false, 0.4);   // never hand back control through a closed iris
    g.rig.follow();
    // Right next to someone (just served or talked)? Put the camera behind Sparky, looking past him
    // towards them, so their body doesn't block the view and push the camera overhead.
    const p = this.player?.root.position;
    let near = null, best = 1.8;
    if (p) for (const ch of Object.values(this.cast)) {
      if (!ch.root.visible) continue;
      const d = Math.hypot(ch.root.position.x - p.x, ch.root.position.z - p.z);
      if (d < best) { best = d; near = ch; }
    }
    if (near && g.world) {
      // Try angles around "looking past Sparky towards them"; keep the first with room behind him
      // (no counter or wall) and nobody between the camera and Sparky.
      const base = Math.atan2(near.root.position.x - p.x, near.root.position.z - p.z);
      const head = this.player.headPosition(new THREE.Vector3());
      const dir = new THREE.Vector3(), cam = new THREE.Vector3();
      const pitch = 0.3, dist = g.rig.distance;
      for (const off of [0, 0.6, -0.6, 1.1, -1.1, 1.6, -1.6, Math.PI]) {
        const yaw = base + off;
        dir.set(-Math.sin(yaw) * Math.cos(pitch), Math.sin(pitch), -Math.cos(yaw) * Math.cos(pitch));
        if (g.world.rayDistance(head, dir, dist + 0.3) < dist) continue;
        cam.copy(head).addScaledVector(dir, dist);
        if (g.rig.blocked?.(cam, head, [this.player]) || g.rig.crowded?.(cam, [this.player])) continue;
        // ...and Sparky's body (not just his head) is visible, e.g. not hidden behind the counter
        const body = p.clone().setY(p.y + 0.5), toBody = body.sub(cam), len = toBody.length();
        if (g.world.rayDistance(cam, toBody.normalize(), len) < len - 0.15) continue;
        g.rig.yaw = yaw;
        g.rig.pitch = pitch;
        g.rig.placeFollow(true, g.world);
        break;
      }
    }
    g.mode = 'play';
    g.input.requestLock();
  }

  /** Optional chats: one line per talk, cycling. Returns a teardown function. */
  setupBarks(map) {
    const g = this.game;
    const its = [];
    for (const [key, list] of Object.entries(map)) {
      const ch = this.cast[key];
      if (!ch || !list?.length) continue;
      this.barkIndex[key] ??= 0;
      if (!ch.indicatorKind) ch.indicator('chat');
      const it = g.addInteract({
        pos: () => ch.root.position, radius: 1.8, label: `Talk to ${this.nameOf(key)}`,
        onUse: async () => {
          g.ui.prompt(null);
          const line = list[this.barkIndex[key] % list.length];
          this.barkIndex[key]++;
          this.chats = (this.chats || 0) + 1;
          if (ch.indicatorKind === 'chat') ch.indicator(null);
          g.mode = 'cutscene';
          await this.lines([line]);
          this.resume();
        },
      });
      its.push(it);
    }
    return () => { its.forEach((it) => g.removeInteract(it)); for (const key of Object.keys(map)) if (this.cast[key]?.indicatorKind === 'chat') this.cast[key].indicator(null); };
  }

  // ------------------------------------------------------------------ photos
  /** Sparky raises the Brownie, then the viewfinder; develops the photo into the album. */
  async takePhoto(key, eye, aim, { allowCancel = true, custom = null } = {}) {
    const g = this.game;
    const info = custom || this.T.snaps[key];
    const p = this.player;
    const prevMode = g.mode;
    g.mode = 'cutscene';
    p.faceTowards(aim, true);
    // Side-on, on whichever side has room — never between Sparky and what he's photographing (as Chapter 1).
    const head = p.headPosition();
    const sideDir = (s) => V(Math.sin(p.yaw + s * 1.25), 0, Math.cos(p.yaw + s * 1.25));
    // (Unlike Chapter 1's street, the kopitiam is full of people: also skip a side with someone in the way.)
    const side = (s) => {
      const room = this.world.rayDistance(head, sideDir(s), 2.5);
      const pos = head.clone().addScaledVector(sideDir(s), Math.min(1.9, room - 0.3)).add(V(0, -0.05, 0));
      const near = (g.rig.blockers?.() || []).some((c) => c !== p && c.root.visible && Math.hypot(c.root.position.x - pos.x, c.root.position.z - pos.z) < 1.2);
      const people = near || g.rig.blocked?.(pos, head, [p]);
      return { pos, score: room - (people ? 3 : 0) };
    };
    const L = side(1), R = side(-1);
    g.rig.cut((L.score >= R.score ? L : R).pos, head.clone().add(V(0, -0.15, 0)), 5, true);
    p.play('Snap', { loop: false });
    await g.wait(0.38);
    this.brownie.visible = true;
    await g.wait(0.4);
    g.mode = prevMode;
    const img = await g.snap({ eye, aim, label: info.title, allowCancel, onCovered: () => { this.brownie.visible = false; } });
    this.brownie.visible = false;
    if (!img) return false;
    await this.developPhoto(key, img, custom);
    return true;
  }

  async developPhoto(key, img, custom = null) {
    const g = this.game;
    const info = custom || this.T.snaps[key];
    g.audio.play('pickup-chime');
    const photo = { id: custom?.id || `${this.id}-${key}`, chapter: this.id, title: info.title, year: info.year, text: info.text, image: img, free: !!custom?.free };
    g.mode = 'cutscene';
    g.input.releaseLock();
    await g.ui.develop(photo);
    g.album.add(photo);
    g.input.requestLock();
    g.mode = 'play';
  }

  /** Hotspots for the free camera: SNAP_<Key> markers not yet photographed. */
  hotspots() {
    const out = [];
    for (const key of Object.keys(this.T.lookCloser || {})) {
      const mk = this.m[`SNAP_${key}`];
      if (!mk || this.game.album.has(`${this.id}-${key}`)) continue;
      out.push({ id: key, pos: markerPose(mk).pos, note: this.T.lookCloser[key], label: this.T.snaps[key].title });
    }
    return out;
  }

  /** Raise the camera anywhere (C / right mouse / camera button). */
  async freeCamera() {
    const g = this.game;
    if (g.mode !== 'play' || this.inFreeCamera || this.carrying) return;
    this.inFreeCamera = true;
    const p = this.player;
    const eye = p.headPosition().add(V(0, -0.05, 0));
    const f = g.camera.getWorldDirection(new THREE.Vector3()).setY(0).normalize();
    p.faceTowards(p.root.position.clone().add(f), true);
    g.mode = 'cutscene';
    p.play('Snap', { loop: false });
    this.brownie.visible = true;
    await g.wait(0.35);
    g.mode = 'play';
    const img = await g.snap({ eye, aim: eye.clone().addScaledVector(f, 5), label: 'Look closer', hotspots: this.hotspots(), limit: 1.6, onCovered: () => { this.brownie.visible = false; } });
    this.brownie.visible = false;
    const id = g.snapHotspot;
    this.inFreeCamera = false;
    if (!img) return;
    if (id) await this.developPhoto(id, img);
    else await this.developPhoto(null, img, { id: `${this.id}-free-${Date.now()}`, title: 'Sparky’s own photo', year: this.T.meta.dates.match(/\d{4}/)?.[0] || '', text: `A moment from ${this.T.meta.dates}, just as Sparky saw it.`, free: true });
  }
}
