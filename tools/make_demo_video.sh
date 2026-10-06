#!/bin/zsh
# Record ../linger-demo.mp4 end to end:
# start the app, record the UI, fetch the processed audio, measure sync, mux, stop the app.
#
#   ./make_demo_video.sh            (uses ./venv, see README.md)
#   PORT=5057 ./make_demo_video.sh  (if the app is already running on 5056)
#   OUT=/tmp/test.mp4 ./make_demo_video.sh
set -euo pipefail

TOOLS=${0:A:h}
ROOT=${TOOLS:h}
PY=${PYTHON:-$TOOLS/venv/bin/python}
PORT=${PORT:-5056}
URL=http://127.0.0.1:$PORT
BUILD=$TOOLS/build
OUT=${OUT:-$ROOT/linger-demo.mp4}

if lsof -nP -iTCP:$PORT -sTCP:LISTEN >/dev/null; then
  echo "port $PORT is already in use; stop that server or run with PORT=<other>" >&2
  exit 1
fi

rm -rf "$BUILD" && mkdir -p "$BUILD" && cd "$BUILD"
cp "$TOOLS/assets/podcast-clip.m4a" .

(cd "$ROOT" && exec "$PY" -m flask --app linger_play run --host 127.0.0.1 --port "$PORT") > server.log 2>&1 &
SERVER=$!
{
for _ in {1..20}; do curl -s -o /dev/null "$URL/" && break; sleep 0.5; done

echo "== recording"
"$PY" "$TOOLS/record_demo.py" podcast-clip.m4a "$URL/"
VIDEO=$(ls video/*.webm)

echo "== fetching processed audio"
for s in 75 130; do
  curl -sf -F file=@podcast-clip.m4a -F speed=$s -o out$s.m4a "$URL/process"
done

echo "== measuring sync"
"$PY" "$TOOLS/measure_sync.py" "$VIDEO"
D75=$("$PY" -c 'import json;print(int(json.load(open("sync.json"))["play75"]*1000))')
D130=$("$PY" -c 'import json;print(int(json.load(open("sync.json"))["play130"]*1000))')
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$VIDEO")
FO=$(echo "$D - 0.8" | bc)

echo "== muxing -> $OUT"
ffmpeg -loglevel error -y -i "$VIDEO" -i out75.m4a -i out130.m4a -filter_complex "\
[0:v]fps=30,fade=t=out:st=${FO}:d=0.8,format=yuv420p[v];\
[1:a]adelay=${D75}|${D75}[a1];[2:a]adelay=${D130}|${D130}[a2];\
[a1][a2]amix=inputs=2:normalize=0:duration=longest,apad,atrim=0:${D},afade=t=out:st=${FO}:d=0.8[a]" \
  -map "[v]" -map "[a]" -c:v libx264 -preset slow -crf 18 -movflags +faststart \
  -c:a aac -b:a 160k -t "$D" "$OUT"

ffprobe -v error -show_entries format=duration,size -of compact "$OUT"
} always {
  # always-block runs even on fatal shell errors, unlike an EXIT trap
  kill $SERVER 2>/dev/null || true
}
