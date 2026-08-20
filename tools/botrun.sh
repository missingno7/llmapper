#!/usr/bin/env bash
# Run the NBlood playtest bot on one map and collect telemetry.
#
# usage: botrun.sh <MAPNAME|path/to/map.map> <tag> [extra nblood args...]
#
# A bare MAPNAME is looked up in maps/blood.  Output lands in work/botlab/<tag>.
set -u
MAP="$1"; TAG="$2"; shift 2
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GAME="$ROOT/reference/blood"
OUT="$ROOT/work/botlab/$TAG"
mkdir -p "$OUT"
cp -f "$ROOT/NBlood/nblood.exe" "$GAME/nblood.exe" 2>/dev/null || true
if [ -f "$MAP" ]; then
  SRC="$MAP"; NAME="BOT$(basename "${MAP%.*}").MAP"
elif [ -f "$ROOT/maps/blood/$MAP.MAP" ]; then
  SRC="$ROOT/maps/blood/$MAP.MAP"; NAME="BOT$MAP.MAP"
else
  echo "no such map: $MAP" >&2; exit 2
fi
cp -f "$SRC" "$GAME/$NAME"
cd "$GAME"
./nblood.exe -usecwd -nosetup -map "$NAME" -bot \
  -bot_telemetry "$OUT/telemetry.ndjson" \
  -bot_trajectory "$OUT/trajectory.ndjson" \
  -bot_demo "$OUT/run.dem" "$@" >"$OUT/stdout.txt" 2>&1
echo "exit=$?"
