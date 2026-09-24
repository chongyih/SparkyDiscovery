#!/usr/bin/env bash
# Rebuild the optimised Sparky GLBs (desktop + mobile tiers) into public/assets/models/.
#
#   tools/optimize_sparky.sh                 # all outfits (ww2, ns, original), both tiers
#   OUTFITS=ww2 TIERS=mobile tools/optimize_sparky.sh
#   PREVIEWS=1 tools/optimize_sparky.sh      # also render EEVEE checks to docs/previews/sparky/
#
# Pipeline per file:
#   1. Blender 5.2 (tools/optimize_sparky.py): new clips, merge by material, decimate, 1 m scale,
#      JPEG textures -> raw GLB in $WORK/raw
#   2. gltf-transform (installed into $SPARKY_NODE_TOOLS, NOT the game's package.json):
#        dedup -> prune -> resample (lossless keyframe reduction) -> meshopt --level medium
#      meshopt = EXT_meshopt_compression + KHR_mesh_quantization; three.js needs
#      gltfLoader.setMeshoptDecoder(MeshoptDecoder) from three/examples/jsm/libs/meshopt_decoder.module.js
#   3. node tools/inspect_sparky.mjs: parse the final GLBs, print tris / draw calls / clips / size.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
OUTFITS="${OUTFITS:-ww2,ns,original}"
TIERS="${TIERS:-desktop,mobile}"
WORK="${WORK:-${TMPDIR:-/tmp}/sparky-optimize}"
export SPARKY_NODE_TOOLS="${SPARKY_NODE_TOOLS:-${TMPDIR:-/tmp}/sparky-gltf-tools}"
DEST="$ROOT/public/assets/models"
mkdir -p "$WORK/raw" "$WORK/pp" "$DEST"
rm -f "$WORK"/raw/*.glb "$WORK"/pp/*.glb

if [ ! -x "$SPARKY_NODE_TOOLS/node_modules/.bin/gltf-transform" ]; then
  mkdir -p "$SPARKY_NODE_TOOLS"
  [ -f "$SPARKY_NODE_TOOLS/package.json" ] || echo '{"private":true}' > "$SPARKY_NODE_TOOLS/package.json"
  # private npm cache: avoids a root-owned ~/.npm breaking the install
  npm_config_cache="$SPARKY_NODE_TOOLS/.npm-cache" npm install --prefix "$SPARKY_NODE_TOOLS" --no-audit --no-fund \
    @gltf-transform/cli@4.5.0 @gltf-transform/core@4.5.0 @gltf-transform/extensions@4.5.0 \
    @gltf-transform/functions@4.5.0 meshoptimizer@1.2.0 >/dev/null
fi
GT="$SPARKY_NODE_TOOLS/node_modules/.bin/gltf-transform"

"$BLENDER" --background --factory-startup --python "$HERE/optimize_sparky.py" -- \
  --out "$WORK/raw" --outfits "$OUTFITS" --tiers "$TIERS" 2>&1 | grep -E '\[optimize_sparky\]|Error|Traceback' || true

finals=()
for raw in "$WORK"/raw/*.glb; do
  name="$(basename "$raw" .glb)"
  "$GT" dedup    "$raw"                "$WORK/pp/$name.1.glb" >/dev/null
  "$GT" prune    "$WORK/pp/$name.1.glb" "$WORK/pp/$name.2.glb" >/dev/null
  "$GT" resample "$WORK/pp/$name.2.glb" "$WORK/pp/$name.3.glb" >/dev/null
  "$GT" meshopt  "$WORK/pp/$name.3.glb" "$DEST/$name.glb" --level medium >/dev/null
  finals+=("$DEST/$name.glb")
done
node "$HERE/inspect_sparky.mjs" "${finals[@]}"

if [ "${PREVIEWS:-0}" = "1" ]; then
  for f in "${finals[@]}"; do
    "$BLENDER" --background --factory-startup --python "$HERE/render_sparky_previews.py" -- \
      --glb "$f" --out "$ROOT/docs/previews/sparky" 2>&1 | grep -E 'SUMMARY total|Error|Traceback' || true
  done
fi
