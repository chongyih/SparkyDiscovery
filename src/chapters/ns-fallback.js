import * as THREE from 'three';

// Stand-in for camp.glb (tools/build_camp.py) so Chapter 3 always runs: flat ground, grey boxes and every
// marker the chapter reads (docs/design.md, "Chapter 3 set contract"), at the contract's positions.

const V = (x, y, z) => new THREE.Vector3(x, y, z);

export function buildCampFallback() {
  const root = new THREE.Group();
  root.name = 'camp_fallback';
  const grey = new THREE.MeshStandardMaterial({ color: '#9a9488', roughness: 0.9 });
  const ground = (area, color, w, d, at) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, d), new THREE.MeshStandardMaterial({ color, roughness: 0.95 }));
    m.rotation.x = -Math.PI / 2;
    m.position.copy(at);
    m.name = `${area.name}_Ground`;
    area.add(m);
    return m;
  };
  const box = (area, name, at, size, color = null) => {
    const m = new THREE.Mesh(new THREE.BoxGeometry(...size), color ? new THREE.MeshStandardMaterial({ color, roughness: 0.85 }) : grey);
    m.position.copy(at).add(V(0, size[1] / 2, 0));
    m.name = name;
    area.add(m);
    return m;
  };
  const mark = (area, name, at, yaw = 0) => {
    const o = new THREE.Object3D();
    o.name = name;
    o.position.copy(at);
    o.rotation.y = yaw;
    area.add(o);
  };
  const quad = (area, name, at, w, h, yaw = 0) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshStandardMaterial({ color: '#ffffff' }));
    m.position.copy(at); m.rotation.y = yaw; m.name = name;
    area.add(m);
  };
  const N = Math.PI; // facing north (−z)

  // ---------------------------------------------------------------- parade square
  const P = new THREE.Group(); P.name = 'AREA_Parade'; root.add(P);
  const then = new THREE.Group(); then.name = 'THEN_Camp'; P.add(then);
  const now = new THREE.Group(); now.name = 'NOW_Park'; P.add(now);
  ground(P, '#8f8a6e', 160, 160, V(0, -0.01, 0));
  ground(then, '#7d7466', 60, 40, V(0, 0, 0));
  ground(now, '#6f9a52', 64, 44, V(0, 0.005, 0));
  for (const x of [-30, 0, 30]) box(then, `THEN_Block_${x}`, V(x, 0, -38), [26, 15, 10], '#d8d2c2');
  // One real flight of stairs up to the first landing.
  for (let i = 0; i < 9; i++) box(then, `THEN_Step_${i}`, V(22, 0, -28.6 - i * 0.25), [1.4, 0.165 * (i + 1), 0.25], '#b8b2a4');
  box(then, 'THEN_Landing', V(22, 0, -31.6), [1.6, 1.49, 1.4], '#b8b2a4');
  box(then, 'THEN_Dais', V(8, 0, 24.5), [6, 0.6, 3], '#a0896a');
  box(then, 'THEN_StandsE', V(15, 0, 26.5), [8, 1.2, 4], '#8c8374');
  box(then, 'THEN_StandsW', V(2, 0, 26.5), [8, 1.2, 4], '#8c8374');
  box(then, 'THEN_BedPile', V(24.2, 0, -27.2), [1.0, 0.5, 2.0], '#3f4a3f');
  box(now, 'NOW_Marker', V(4, 0, 16), [1.0, 0.6, 0.35], '#5b5f58');
  quad(now, 'DECAL_Marker', V(4, 0.85, 16.18), 0.9, 0.6, 0);
  for (const x of [-40, -10, 25]) box(now, `NOW_HDB_${x}`, V(x, 0, -60), [16, 36, 12], '#e8e1d6');

  mark(P, 'SPAWN_Sparky', V(22, 0, -26.2), N);
  mark(P, 'STAIR_Bottom', V(22, 0, -28.4), N);
  mark(P, 'STAIR_Landing', V(22, 1.49, -31.2), N);
  mark(P, 'STAIR_Top', V(22, 1.49, -31.6), N);
  mark(P, 'BED_Start', V(22, 0.45, -27.4), N);
  mark(P, 'BED_Landing', V(22, 1.94, -31.0), N);
  mark(P, 'NPC_Osman_Stair', V(19.6, 0, -26.4), Math.PI / 2);
  mark(P, 'NPC_Leo_Stair', V(22.5, 0.75, -29.6), 0);
  mark(P, 'NPC_Ravi_Stair', V(24.4, 0, -25.8), N);
  mark(P, 'NPC_Farid_Landing', V(22, 1.49, -31.4), 0);
  [-2, -1, 0, 1, 2].forEach((x, i) => mark(P, `DRILL_${i + 1}`, V(x, 0, 0), N));
  mark(P, 'NPC_Osman_Drill', V(0, 0, -4), 0);
  mark(P, 'NPC_Adviser_1', V(-14, 0, -6), Math.PI / 2);
  mark(P, 'NPC_Adviser_2', V(-15, 0, -4.6), Math.PI / 2);
  mark(P, 'SNAP_Mexicans', V(-14.5, 1.6, -5.3));
  [-14, -13, -12, -11, -10].forEach((x, i) => mark(P, `PARADE_${i + 1}`, V(x, 0, 12), N));
  mark(P, 'PARADE_Halt', V(22, 0, 12), Math.PI / 2);
  mark(P, 'NPC_Minister', V(8, 0.6, 24), N);
  mark(P, 'STAND_X', V(12, 0, 19.5), N);
  for (let i = 0; i < 16; i++) {
    const side = i < 8 ? 15 : 2, k = i % 8;
    mark(P, `STAND_Seat_${i + 1}`, V(side - 3 + (k % 4) * 2, 0.6 + Math.floor(k / 4) * 0.4, 25.5 + Math.floor(k / 4) * 1.2), N);
  }
  const standNpc = { Siti: [13.6, 20.6], Rajan: [14.6, 20.6], Rohani: [16.0, 21.0], AhPek: [17.0, 21.0], Letchumi: [0.6, 21.0], Neighbour: [1.6, 21.0], AhMa: [2.8, 21.0] };
  for (const [k, [x, z]] of Object.entries(standNpc)) mark(P, `NPC_${k}_Stand`, V(x, 0, z), N);
  mark(P, 'CAM_Title', V(-26, 6, 26), 2.6);
  mark(P, 'CAM_DrillDay', V(-3.6, 2.3, 4.6), 2.5);
  mark(P, 'CAM_Parade', V(-8, 1.8, 5), 2.2);
  mark(P, 'THEN_NOW_Camera', V(-26, 1.45, 26), 2.63);
  mark(P, 'SNAP_Marker', V(4, 1.0, 16.2));

  // ---------------------------------------------------------------- barracks (x = 200)
  const B = new THREE.Group(); B.name = 'AREA_Barracks'; root.add(B);
  ground(B, '#8a8174', 24, 12, V(200, 0, -2));
  box(B, 'BAR_WallBack', V(200, 0, -6.2), [20, 3, 0.2], '#c9c2b0');
  [191, 197, 203, 209].forEach((x) => box(B, `BAR_Wall_${x}`, V(x, 0, -4), [0.2, 3, 4.4], '#c9c2b0'));
  [[194, -4.4], [200, -4.4], [206, -4.4], [207.6, -3.4]].forEach(([x, z], i) => box(B, `BAR_Bed_${i}`, V(x, 0, z), [0.8, 0.42, 1.9], '#3f4a3f'));
  mark(B, 'BAR_Spawn', V(192, 0, 1.4), Math.PI / 2);
  mark(B, 'BAR_Farid', V(194, 0, -3.1), 0);
  mark(B, 'BAR_AhHock', V(200, 0, -3.1), 0);
  mark(B, 'BAR_Ravi', V(206, 0, -3.1), 0);
  mark(B, 'BAR_Leo', V(207.6, 0, -2.2), 0);
  mark(B, 'BAR_Uniform', V(198.8, 0, -2.6), 0);
  mark(B, 'SNAP_Uniform', V(198.8, 1.0, -2.6));
  [194, 200, 206].forEach((x, i) => mark(B, `LAMP_Bar_${i + 1}`, V(x, 2.6, -4)));
  mark(B, 'CAM_Barracks', V(190, 1.6, 2), Math.PI / 2);

  // ---------------------------------------------------------------- night scrub (x = −200)
  const Nt = new THREE.Group(); Nt.name = 'AREA_Night'; root.add(Nt);
  ground(Nt, '#2f3a26', 40, 40, V(-200, 0, 0));
  const stream = ground(Nt, '#27404a', 30, 2.4, V(-200, 0.01, -9.5));
  stream.name = 'NIGHT_Water';
  box(Nt, 'NIGHT_Tree', V(-200, 0, -1.5), [1.2, 6, 1.2], '#3b2e22');
  mark(Nt, 'NIGHT_Spawn', V(-200, 0, 4.5), N);
  [-2, -1, 0, 1, 2].forEach((x, i) => mark(Nt, `NIGHT_Group_${i + 1}`, V(-200 + x * 0.9, 0, 0.6 + Math.abs(x) * 0.3), N));
  mark(Nt, 'NIGHT_Stream', V(-200, 0, -8), N);
  [-2, -1, 0, 1, 2].forEach((x, i) => mark(Nt, `NIGHT_Rest_${i + 1}`, V(-200 + x * 0.9, 0, -7.2 + Math.abs(x) * 0.4), 0));
  mark(Nt, 'CAM_Night', V(-203.5, 1.7, 5), 2.7);

  // ---------------------------------------------------------------- community centre (z = 200)
  const C = new THREE.Group(); C.name = 'AREA_CC'; root.add(C);
  ground(C, '#8a8579', 40, 40, V(0, 0, 200));
  box(C, 'CC_Building', V(0, 0, 190), [18, 4.5, 8], '#e7dfc9');
  quad(C, 'DECAL_CCSign', V(0, 3.6, 194.02), 5, 1.25, 0);
  box(C, 'PROP_Truck', V(7, 0, 204), [2.4, 2.8, 6], '#56603f');
  quad(C, 'DECAL_Banner', V(-4, 2.6, 196), 6, 1, 0);
  mark(C, 'CC_Spawn', V(-3, 0, 206), N);
  mark(C, 'CC_Truck_Tail', V(3.4, 0, 204), Math.PI / 2);
  mark(C, 'CC_Gate', V(0, 0, 197), N);
  mark(C, 'CC_Boon_Spot', V(-1.2, 0, 197.4), 0);
  [-8, -7, -6, -5].forEach((x, i) => mark(C, `CC_Band_${i + 1}`, V(x, 0, 196.2), 0));
  for (let i = 0; i < 10; i++) mark(C, `CC_Family_${i + 1}`, V(-6 + (i % 5) * 2.2, 0, 199.5 + Math.floor(i / 5) * 1.6 + (i % 2) * 0.4), (i % 3) - 1);
  const ccNpc = { Rajan: [1.2, 201.2], Ravi: [1.9, 201.8], Siti: [-1.6, 202.2], Farid: [-0.8, 202.9], AhMa: [-7.2, 203.4], Neighbour: [-3.2, 200.6], MP: [0.2, 198.6] };
  for (const [k, [x, z]] of Object.entries(ccNpc)) mark(C, `NPC_${k}_CC`, V(x, 0, z), 0);
  mark(C, 'CAM_CC', V(-8, 2.2, 211), 2.6);

  return root;
}
