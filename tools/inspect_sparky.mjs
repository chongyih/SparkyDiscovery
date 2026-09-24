// Parse optimised Sparky GLBs (meshopt-decoding them like three.js would) and print a summary.
//   SPARKY_NODE_TOOLS=<dir with @gltf-transform/* + meshoptimizer> node tools/inspect_sparky.mjs a.glb [b.glb ...]
// (tools/optimize_sparky.sh installs those packages into a scratch dir and sets the variable.)
import { createRequire } from 'node:module';
import { statSync } from 'node:fs';
import { basename } from 'node:path';

const toolsDir = process.env.SPARKY_NODE_TOOLS;
if (!toolsDir) throw new Error('set SPARKY_NODE_TOOLS');
const require = createRequire(toolsDir.replace(/\/?$/, '/') + 'package.json');
const { NodeIO } = require('@gltf-transform/core');
const { ALL_EXTENSIONS } = require('@gltf-transform/extensions');
const { MeshoptDecoder } = require('meshoptimizer');

await MeshoptDecoder.ready;
const io = new NodeIO().registerExtensions(ALL_EXTENSIONS).registerDependencies({ 'meshopt.decoder': MeshoptDecoder });

let failed = false;
for (const file of process.argv.slice(2)) {
  const doc = await io.read(file);
  const root = doc.getRoot();
  let tris = 0;
  let drawCalls = 0;
  const meshNodes = [];
  for (const node of root.listNodes()) {
    const mesh = node.getMesh();
    if (!mesh) continue;
    let t = 0;
    for (const prim of mesh.listPrimitives()) {
      drawCalls++;
      const idx = prim.getIndices();
      t += (idx ? idx.getCount() : prim.getAttribute('POSITION').getCount()) / 3;
      for (const a of ['POSITION', 'NORMAL', 'JOINTS_0', 'WEIGHTS_0']) {
        if (!prim.getAttribute(a)) { console.error(`  !! ${node.getName()} missing ${a}`); failed = true; }
      }
    }
    tris += t;
    meshNodes.push(`${node.getName()}(${t} tris, mat ${mesh.listPrimitives().map((p) => p.getMaterial()?.getName()).join('+')}, skin ${node.getSkin() ? 'yes' : 'NO'})`);
  }
  const skin = root.listSkins()[0];
  const bones = skin ? skin.listJoints().map((j) => j.getName()) : [];
  const clips = root.listAnimations().map((a) => {
    let dur = 0;
    for (const s of a.listSamplers()) dur = Math.max(dur, s.getInput().getMax([])[0]);
    const targets = new Set(a.listChannels().map((c) => c.getTargetNode()?.getName()));
    if (targets.size !== bones.length) { console.error(`  !! clip ${a.getName()} animates ${targets.size}/${bones.length} bones`); failed = true; }
    return `${a.getName()} ${dur.toFixed(3)}s`;
  });
  const textures = root.listTextures().map((t) => `${t.getName()} ${t.getSize()?.join('x')} ${t.getMimeType()} ${(t.getImage().byteLength / 1024).toFixed(0)}KB`);
  const kb = statSync(file).size / 1024;
  console.log(`\n${basename(file)}  ${(kb / 1024).toFixed(2)} MB (${kb.toFixed(0)} KB)`);
  console.log(`  extensions: ${root.listExtensionsUsed().map((e) => e.extensionName).join(', ') || 'none'}`);
  console.log(`  triangles: ${tris}   draw calls (primitives): ${drawCalls}   materials: ${root.listMaterials().map((m) => m.getName()).join(', ')}`);
  console.log(`  mesh nodes: ${meshNodes.join('; ')}`);
  console.log(`  bones (${bones.length}): ${bones.join(', ')}`);
  console.log(`  clips (${clips.length}): ${clips.join(', ')}`);
  console.log(`  textures: ${textures.join('; ')}`);
}
if (failed) process.exit(1);
