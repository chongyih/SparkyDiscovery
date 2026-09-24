import * as THREE from 'three';

// Minimal stand-in for ww2-street.glb so the chapter is playable before the Blender level exists.
// Uses the same node-name contract as docs/design.md (three.js coordinates).

const mat = (c, r = 0.9) => new THREE.MeshStandardMaterial({ color: c, roughness: r });

function box(w, h, d, m, x, y, z, name) {
  const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), m);
  mesh.position.set(x, y + h / 2, z);
  if (name) mesh.name = name;
  return mesh;
}

function marker(root, name, x, y, z, yaw = 0) {
  const o = new THREE.Object3D();
  o.name = name;
  o.position.set(x, y, z);
  o.rotation.y = yaw;
  root.add(o);
  return o;
}

export function buildFallbackStreet() {
  const root = new THREE.Group();
  root.name = 'ww2-fallback';
  const road = mat('#6f665a');
  const walk = mat('#9c8c74');
  const colors = ['#d8cdb4', '#c9b79a', '#bfc7b6', '#d6c0a0', '#c4b8a8', '#cdbd9f'];
  root.add(box(90, 0.1, 40, mat('#5d574d'), 0, -0.1, 0));
  root.add(box(90, 0.02, 7, road, 0, 0, 0));
  const FW = 0.2; // five-foot way height
  for (const side of [-1, 1]) {
    root.add(box(90, FW, 2.6, walk, 0, 0, side * 4.8));
    let x = -34;
    let i = 0;
    while (x < 34) {
      const w = 4.8 + ((i * 37) % 17) / 10;
      const h = 8 + ((i * 53) % 5);
      const m = mat(colors[(i + (side > 0 ? 2 : 0)) % colors.length]);
      const cx = x + w / 2;
      // Upper floors overhang the five-foot way; ground floor set back.
      root.add(box(w - 0.1, h - 3.2, 9, m, cx, 3.2, side * (4.8 + 3.2)));
      root.add(box(w - 0.1, 3.2, 8, mat('#8a7a64'), cx, 0, side * (6.1 + 4)));
      root.add(box(0.35, 3.2, 0.35, m, x + 0.2, FW, side * 3.7));
      root.add(box(w + 0.2, 0.5, 2.8, mat('#8b4a32'), cx, h, side * 3.8)); // eave
      const col = box(0.35, 3.2, 0.35, m, x + 0.2, 0, side * 3.7, `COL_pillar_${side}_${i}`);
      root.add(col);
      x += w;
      i++;
    }
    root.add(box(90, 4, 1, mat('#000'), 0, 0, side * 6.3, `COL_facade_${side}`));
  }
  // Street ends + shelter.
  root.add(box(1, 4, 14, mat('#000'), -36, 0, 0, 'COL_end_w'));
  root.add(box(1, 4, 14, mat('#000'), 36, 0, 0, 'COL_end_e'));
  const sand = mat('#a89572');
  const shelter = new THREE.Group();
  shelter.add(box(5, 2.4, 3.2, sand, 0, 0, 0));
  shelter.add(box(1.2, 1.9, 0.3, mat('#2a2018'), 0, 0, -1.7));
  shelter.position.set(30, 0, 1.5);
  root.add(shelter);
  root.add(box(5, 2.4, 3.2, mat('#000'), 30, 0, 1.5, 'COL_shelter'));
  // Posters, bicycle, rickshaw stand-ins.
  root.add(box(1.4, 1.8, 0.05, mat('#d9c7a0'), -12, 1.0, -6.2, 'PRE_Poster'));
  root.add(box(1.4, 1.6, 0.05, mat('#e8e2d6'), -12, 1.0, -6.18, 'OCC_Notice'));
  root.add(box(1.6, 1.0, 0.5, mat('#3b3a36'), 4, FW, 3.9, 'BicycleStandIn'));
  const dmg = box(5, 3, 5, mat('#4a3f35'), 14, 0, -6.5, 'DMG_House'); root.add(dmg);
  root.add(box(3, 1, 2, mat('#000'), 14, 0, -3.8, 'COL_DMG_rubble'));
  // Shelter interior (away from the street).
  const I = new THREE.Group();
  I.add(box(6, 0.1, 4, mat('#5a5046'), 0, -0.1, 0));
  I.add(box(6, 2.6, 0.2, mat('#8a6a50'), 0, 0, -2));
  I.add(box(6, 2.6, 0.2, mat('#8a6a50'), 0, 0, 2));
  I.add(box(0.2, 2.6, 4, mat('#8a6a50'), -3, 0, 0));
  I.add(box(0.2, 2.6, 4, mat('#8a6a50'), 3, 0, 0));
  I.add(box(5, 0.45, 0.6, mat('#6b4f36'), 0, 0, -1.5));
  I.add(box(0.6, 0.6, 0.6, mat('#6b4f36'), 2.2, 0, 1.2));
  I.position.set(200, 0, 0);
  root.add(I);

  root.traverse((o) => { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });

  marker(root, 'SPAWN_Sparky', -24, FW, 4.6, Math.PI / 2);
  marker(root, 'NPC_Siti', -21, FW, 4.3, -Math.PI / 2);
  marker(root, 'NPC_Rajan', -4, 0, 1.6, 0);
  marker(root, 'NPC_AhMa', 0, FW, -5.2, 0);
  marker(root, 'NPC_Boon', 1.2, FW, -5.6, 0);
  marker(root, 'NPC_Hassan', 18, 0, 2.5, -Math.PI / 2);
  marker(root, 'DROP_1', -16, FW, -5.9, 0);
  marker(root, 'DROP_2', 8, FW, 5.9, Math.PI);
  marker(root, 'DROP_3', 22, FW, -5.9, 0);
  marker(root, 'SNAP_Poster', -12, FW, -4.4, Math.PI);
  marker(root, 'SNAP_Bicycle', 4, FW, 2.2, 0);
  marker(root, 'SNAP_Smoke', -30, 0, 0, -Math.PI / 2);
  marker(root, 'SHELTER_Entrance', 30, 0, -1.2, Math.PI);
  marker(root, 'INT_Spawn', 200, 0, 0.8, Math.PI);
  marker(root, 'INT_Radio', 202.2, 0.6, 1.2, Math.PI);
  marker(root, 'INT_Camera', 200, 1.1, 1.6, Math.PI);
  for (let i = 1; i <= 5; i++) marker(root, `INT_Seat_${i}`, 198 + i * 0.8 - 0.4, 0.45, -1.45, 0);
  marker(root, 'EPI_Spawn', -8, FW, 4.6, Math.PI / 2);
  for (let i = 1; i <= 4; i++) marker(root, `EPI_Queue_${i}`, 20 + i * 1.1, FW, -4.6, -Math.PI / 2);
  marker(root, 'SMOKE_1', -260, 0, -140);
  marker(root, 'SMOKE_2', -120, 0, -260);
  marker(root, 'SMOKE_3', 180, 0, -230);
  marker(root, 'DMG_Fire_1', 13, 1, -6);
  marker(root, 'DMG_Fire_2', 15.5, 2.5, -7);
  return { scene: root, animations: [] };
}
