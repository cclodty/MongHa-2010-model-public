#!/usr/bin/env bash
# Linux / Claude Code cloud sessions: fetch Blender (official Linux build) into /opt/blender and put it on the PATH as
# `blender`, so build_estate.py and tools/preview.py run here. Headless use only; no GPU needed for the preview.
# usage: bash tools/get_blender.sh [version]   (default 5.2.3)
set -euo pipefail
V="${1:-5.2.3}"
DIR=/opt/blender
if [ ! -x "$DIR/blender-$V-linux-x64/blender" ]; then
  mkdir -p "$DIR"
  curl -fsSL "https://download.blender.org/release/Blender${V%.*}/blender-$V-linux-x64.tar.xz" | tar -xJ -C "$DIR"
fi
ln -sf "$DIR/blender-$V-linux-x64/blender" /usr/local/bin/blender
blender -b --version | head -1
