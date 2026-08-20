#!/usr/bin/env bash
# Run the validation corpus and print one scorecard line per map.
#
# The AGTST maps are the fast exploration gate: they isolate concave rooms,
# occluded interactions, crouch traversal, auto-closing doors, breakable
# walls, gaps too narrow for the body, solid and pushable sprites, a sprite
# bridge over a damage pit, and a run of pillars that has to be jumped, from
# the size of the campaign maps.  All of them complete, so any result other
# than COMPLETED is a regression.  Run them before the campaign corpus.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAG="${1:-corpus}"
TIMEOUT="${2:-420}"
cd "$ROOT"
for MAP in AGTST1 AGTST2 AGTST3 AGTST4 AGTST5 AGTST6 AGTST7 E1M1 E3M1 E3M3 E4M1; do
  case "$MAP" in
    AGTST*) SRC="reference/blood/$MAP.map"; T=180 ;;
    *)      SRC="$MAP";                     T="$TIMEOUT" ;;
  esac
  [ -f "$SRC" ] || [ -f "maps/blood/$MAP.MAP" ] || { printf "%-7s (map not present)\n" "$MAP"; continue; }
  bash tools/botrun.sh "$SRC" "$TAG-$MAP" -bot_timeout "$T" -bot_stall 90 >/dev/null 2>&1
  printf "%-7s " "$MAP"
  python tools/bot_scorecard.py "work/botlab/$TAG-$MAP/telemetry.ndjson" \
                                "work/botlab/$TAG-$MAP/trajectory.ndjson" --brief \
    --output "work/botlab/$TAG-$MAP/scorecard.json"
  # The scorecard says how the run went; the invariants say whether the bot's
  # own account of it can be trusted.  A run may fail its objective and still
  # be honest, but a violation here means the world model is corrupted.
  MAPARG=""
  [ -f "$SRC" ] && MAPARG="--map $SRC"
  python tools/bot_invariants.py "work/botlab/$TAG-$MAP/telemetry.ndjson"                                  $MAPARG --quiet || true
done
