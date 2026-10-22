#!/usr/bin/env bash
# usage: shots.sh view1 view2 ...   -> export/ue_<view>.png
T="G:/Claude/mongha-ue/tools"; SS="G:/Claude/mongha-ue/MongHa2010/Saved/Screenshots/WindowsEditor"; OUT="G:/Claude/mongha-ue/export"
mkdir -p "$SS"
for v in "$@"; do
  py -3 -I "$T/ue_bridge.py" file "$T/ue_04_view.py" "VIEW=$v" | tail -2
  sleep 10
  before=$(ls -t "$SS"/*.png 2>/dev/null | head -1)
  py -3 -I "$T/ue_bridge.py" cmd "unreal.SystemLibrary.execute_console_command(None, 'HighResShot 1920x1080')" | tail -1
  for i in $(seq 1 30); do sleep 1; now=$(ls -t "$SS"/*.png 2>/dev/null | head -1); [ -n "$now" ] && [ "$now" != "$before" ] && break; done
  sleep 1
  now=$(ls -t "$SS"/*.png 2>/dev/null | head -1)
  if [ -n "$now" ] && [ "$now" != "$before" ]; then cp "$now" "$OUT/ue_$v.png"; echo "SHOT $v -> $OUT/ue_$v.png"; else echo "NO_SHOT $v"; fi
done
echo SHOTS_DONE
