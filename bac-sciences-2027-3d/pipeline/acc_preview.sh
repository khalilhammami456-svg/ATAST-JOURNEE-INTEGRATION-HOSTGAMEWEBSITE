#!/bin/bash
# quick previews of the accessories with their textures:  ./acc_preview.sh [ids]
cd "$(dirname "$0")"
source /home/user/venvs/bpyenv/bin/activate
declare -A CFG
CFG[A1]="nuit 1.72 1.3"; CFG[A2]="nuit 1.72 1.3"; CFG[S1]="nuit 1.30 2.6"; CFG[S2]="rose 1.30 2.6"
CFG[A3]="chalk 0.42 2.2"; CFG[A4]="nuit 1.2 0.5"; CFG[A5]="nuit 1.2 0.3"
for IT in ${@:-A1 A2 S1 S2 A3 A4 A5}; do
  set -- ${CFG[$IT]}
  HIDEP=""; case $IT in A1|A2) HIDEP="BaseTop,Trousers";; esac
  SRC=../3d/models/$IT/${IT}_scene.blend TEX=../3d/textures/$IT CW=$1 VIEWS=front,q,back W=520 H=520 SAMPLES=24 FOCUS=$2 DIST=$3 KEY=0.7 HIDE=$HIDEP OUTP=/home/user/work/prev/acc_${IT} python render_item.py 2>&1 | grep -E "Traceback|Error|done"
done
