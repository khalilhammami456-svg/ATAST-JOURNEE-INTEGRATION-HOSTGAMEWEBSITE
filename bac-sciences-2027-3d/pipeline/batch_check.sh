#!/bin/bash
# produce + textures + quick render for a list of "ITEM:colorway"
cd "$(dirname "$0")"
source /home/user/venvs/bpyenv/bin/activate
for spec in "$@"; do
  IT=${spec%%:*}; CW=${spec##*:}
  echo "=== $IT $CW"
  ITEM=$IT python produce.py 2>&1 | grep -E "saved|Traceback|Error:|File \"" | head -5
  /usr/bin/python3 build_textures.py $IT $CW 2>&1 | tail -2 | cut -c1-120
  SRC=../3d/models/$IT/${IT}_scene.blend TEX=../3d/textures/$IT CW=$CW VIEWS=front,back W=480 H=720 SAMPLES=16 FOCUS=1.05 DIST=5.0 KEY=0.5 OUTP=/home/user/work/prev/chk_${IT} python render_item.py 2>&1 | grep -E "Traceback|Error:|done"
done
