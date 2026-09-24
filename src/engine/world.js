import * as THREE from 'three';
import { computeBoundsTree, disposeBoundsTree, acceleratedRaycast } from 'three-mesh-bvh';

THREE.BufferGeometry.prototype.computeBoundsTree = computeBoundsTree;
THREE.BufferGeometry.prototype.disposeBoundsTree = disposeBoundsTree;
THREE.Mesh.prototype.raycast = acceleratedRaycast;

const _v = new THREE.Vector3();
const _q = new THREE.Quaternion();
const _s = new THREE.Vector3();
const _e = new THREE.Euler();
const DOWN = new THREE.Vector3(0, -1, 0);
const _n = new THREE.Vector3();

/**
 * Static collision world:
 *  - `COL_*` meshes become yaw-rotated boxes (2D circle-vs-OBB push-out, with a y range).
 *  - visible static meshes get a BVH for ground-height and camera raycasts.
 */
export class World {
  constructor() {
    this.boxes = [];
    this.rayMeshes = [];
    this.dynamic = []; // { pos: Vector3, radius, enabled }
    this.raycaster = new THREE.Raycaster();
    this.raycaster.firstHitOnly = true;
    this.bounds = null; // optional { minX, maxX, minZ, maxZ }
  }

  addBoxFromMesh(mesh, enabled = true) {
    mesh.updateWorldMatrix(true, false);
    // Exported AABB extras (three.js space) are exact even when the mesh is quantized.
    const ex = mesh.userData;
    if (Array.isArray(ex?.aabb_min) && Array.isArray(ex?.aabb_max)) {
      const [x0, y0, z0] = ex.aabb_min, [x1, y1, z1] = ex.aabb_max;
      const box = { name: mesh.name, enabled, cx: (x0 + x1) / 2, cz: (z0 + z1) / 2, yaw: 0, cos: 1, sin: 0, hx: Math.abs(x1 - x0) / 2, hz: Math.abs(z1 - z0) / 2, minY: Math.min(y0, y1), maxY: Math.max(y0, y1) };
      this.boxes.push(box);
      return box;
    }
    const geo = mesh.geometry;
    if (!geo.boundingBox) geo.computeBoundingBox();
    const bb = geo.boundingBox;
    mesh.matrixWorld.decompose(_v, _q, _s);
    _e.setFromQuaternion(_q, 'YXZ');
    const localCenter = bb.getCenter(new THREE.Vector3());
    const center = localCenter.clone().applyMatrix4(mesh.matrixWorld);
    const size = bb.getSize(new THREE.Vector3()).multiply(_s);
    const box = {
      name: mesh.name, enabled,
      cx: center.x, cz: center.z, yaw: _e.y,
      hx: Math.abs(size.x) / 2, hz: Math.abs(size.z) / 2,
      minY: center.y - Math.abs(size.y) / 2, maxY: center.y + Math.abs(size.y) / 2,
    };
    box.cos = Math.cos(box.yaw); box.sin = Math.sin(box.yaw);
    this.boxes.push(box);
    return box;
  }

  addBox(cx, cz, hx, hz, minY = 0, maxY = 3, yaw = 0, name = 'box') {
    const box = { name, enabled: true, cx, cz, hx, hz, minY, maxY, yaw, cos: Math.cos(yaw), sin: Math.sin(yaw) };
    this.boxes.push(box);
    return box;
  }

  setEnabled(prefix, enabled) {
    for (const b of this.boxes) if (b.name.startsWith(prefix)) b.enabled = enabled;
  }

  /** Colliders tagged with a level `state` ('war' | 'now' | 'occ'): enable per era. */
  applyStates(active) {
    for (const b of this.boxes) if (b.state) b.enabled = active.includes(b.state) && !(b.name.startsWith('COL_DMG') && !active.includes('dmg'));
  }

  addRayMesh(mesh) {
    if (!mesh.geometry.boundsTree) mesh.geometry.computeBoundsTree();
    this.rayMeshes.push(mesh);
  }

  /** Push a circle at pos (feet at pos.y) out of all boxes. Mutates pos. */
  resolve(pos, radius, height = 1, step = 0.35, ignore = null) {
    for (const b of this.boxes) {
      if (!b.enabled || b.maxY <= pos.y + step || b.minY >= pos.y + height) continue;
      // To box-local 2D (box yaw rotates about +Y).
      const dx = pos.x - b.cx, dz = pos.z - b.cz;
      const lx = dx * b.cos - dz * b.sin;
      const lz = dx * b.sin + dz * b.cos;
      const px = Math.max(-b.hx, Math.min(b.hx, lx));
      const pz = Math.max(-b.hz, Math.min(b.hz, lz));
      let ox = lx - px, oz = lz - pz;
      const d2 = ox * ox + oz * oz;
      if (d2 >= radius * radius) continue;
      let nx, nz, push;
      if (d2 > 1e-8) {
        const d = Math.sqrt(d2);
        nx = ox / d; nz = oz / d; push = radius - d;
      } else {
        // Centre inside the box: exit via the nearest face.
        const ex = b.hx - Math.abs(lx), ez = b.hz - Math.abs(lz);
        if (ex < ez) { nx = Math.sign(lx) || 1; nz = 0; push = ex + radius; } else { nx = 0; nz = Math.sign(lz) || 1; push = ez + radius; }
      }
      // Back to world.
      const wx = nx * b.cos + nz * b.sin;
      const wz = -nx * b.sin + nz * b.cos;
      pos.x += wx * push; pos.z += wz * push;
    }
    for (const d of this.dynamic) {
      if (!d.enabled || d === ignore) continue;
      const dx = pos.x - d.pos.x, dz = pos.z - d.pos.z;
      const r = radius + d.radius;
      const dd = dx * dx + dz * dz;
      if (dd < r * r && dd > 1e-8) {
        const l = Math.sqrt(dd);
        pos.x += (dx / l) * (r - l); pos.z += (dz / l) * (r - l);
      }
    }
    if (this.bounds) {
      pos.x = Math.max(this.bounds.minX, Math.min(this.bounds.maxX, pos.x));
      pos.z = Math.max(this.bounds.minZ, Math.min(this.bounds.maxZ, pos.z));
    }
    return pos;
  }

  /** Walkable ground height under (x,z), searching down from y + reach. */
  groundHeight(x, y, z, reach = 0.55, maxDrop = 6) {
    if (!this.rayMeshes.length) return 0;
    this.raycaster.set(_v.set(x, y + reach, z), DOWN);
    this.raycaster.far = reach + maxDrop;
    const hits = this.raycaster.intersectObjects(this.rayMeshes, false);
    for (const h of hits) {
      if (!h.face) continue;
      const n = _n.copy(h.face.normal).transformDirection(h.object.matrixWorld);
      if (n.y > 0.55) return h.point.y;
    }
    return null;
  }

  /** Distance from `from` along `dir` (normalized) to the first surface, or `max`. */
  rayDistance(from, dir, max) {
    if (!this.rayMeshes.length) return max;
    this.raycaster.set(from, dir);
    this.raycaster.far = max;
    const hits = this.raycaster.intersectObjects(this.rayMeshes, false);
    return hits.length ? hits[0].distance : max;
  }
}

/** Collect named nodes from a level scene. */
export function collectMarkers(root) {
  const markers = {};
  root.traverse((o) => { if (o.name) markers[o.name] = o; });
  return markers;
}

/** World position + facing yaw (from the node's +Z axis in three space = Blender −Y). */
export function markerPose(node) {
  node.updateWorldMatrix(true, false);
  const pos = new THREE.Vector3().setFromMatrixPosition(node.matrixWorld);
  const fwd = new THREE.Vector3(0, 0, 1).transformDirection(node.matrixWorld);
  return { pos, yaw: Math.atan2(fwd.x, fwd.z) };
}
