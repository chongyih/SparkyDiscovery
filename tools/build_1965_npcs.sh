#!/usr/bin/env bash
# Build the Chapter 2 (1965) NPC GLBs, desktop + mobile tiers, into public/assets/models/.
#
#   tools/build_1965_npcs.sh                    # all NPCs, both tiers
#   ONLY=boon65,siti65 TIERS=desktop tools/build_1965_npcs.sh
#
# Pipeline (same as tools/optimize_sparky.sh):
#   1. Blender 5.2 (tools/build_1965_npcs.py): procedural model + rig + clips -> raw GLB in $WORK/raw
#   2. gltf-transform (in $SPARKY_NODE_TOOLS, NOT the game's package.json):
#        dedup -> prune -> resample (lossless keyframe reduction) -> meshopt --level medium
#      (EXT_meshopt_compression + KHR_mesh_quantization; the game's loader already sets MeshoptDecoder)
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
BLENDER="${BLENDER:-/Applications/Blender.app/Contents/MacOS/Blender}"
TIERS="${TIERS:-both}"
WORK="${WORK:-${TMPDIR:-/tmp}/npc-build-1965}"
export SPARKY_NODE_TOOLS="${SPARKY_NODE_TOOLS:-${TMPDIR:-/tmp}/sparky-gltf-tools}"
DEST="$ROOT/public/assets/models"
mkdir -p "$WORK/raw" "$DEST"
rm -f "$WORK"/raw/*.glb

if [ ! -x "$SPARKY_NODE_TOOLS/node_modules/.bin/gltf-transform" ]; then
  mkdir -p "$SPARKY_NODE_TOOLS"
  [ -f "$SPARKY_NODE_TOOLS/package.json" ] || echo '{"private":true}' > "$SPARKY_NODE_TOOLS/package.json"
  npm_config_cache="$SPARKY_NODE_TOOLS/.npm-cache" npm install --prefix "$SPARKY_NODE_TOOLS" --no-audit --no-fund \
    @gltf-transform/cli@4.5.0 @gltf-transform/core@4.5.0 @gltf-transform/extensions@4.5.0 \
    @gltf-transform/functions@4.5.0 meshoptimizer@1.2.0 >/dev/null
fi
GT="$SPARKY_NODE_TOOLS/node_modules/.bin/gltf-transform"

ARGS=(--out "$WORK/raw" --tier "$TIERS")
[ -n "${ONLY:-}" ] && ARGS+=(--only "$ONLY")
"$BLENDER" --background --factory-startup --python "$HERE/build_1965_npcs.py" -- "${ARGS[@]}" 2>&1 \
  | grep -E '\[NPC\]|Error|Traceback|line [0-9]+' || true

for f in "$WORK"/raw/npc-*.glb; do
  b="$(basename "$f")"
  "$GT" dedup "$f" "$WORK/$b.1.glb" >/dev/null
  "$GT" prune "$WORK/$b.1.glb" "$WORK/$b.2.glb" >/dev/null
  "$GT" resample "$WORK/$b.2.glb" "$WORK/$b.3.glb" >/dev/null
  "$GT" meshopt "$WORK/$b.3.glb" "$DEST/$b" --level medium >/dev/null
  rm -f "$WORK/$b".[123].glb
  printf '[NPC] %-24s raw %4d KB -> %4d KB\n' "$b" $(( $(stat -f%z "$f") / 1024 )) $(( $(stat -f%z "$DEST/$b") / 1024 ))
done
cp "$WORK/raw/npc_build_report.json" "$WORK/npc_build_report.json" 2>/dev/null || true

