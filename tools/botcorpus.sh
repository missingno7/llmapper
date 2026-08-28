#!/usr/bin/env bash
# Run the validation corpus and print one scorecard line per map.
#
# Five maps, and only these five. AGTST1, AGTST6 and AGTST7 are the
# behavioural gate for the walking-and-interaction phase: they need ordinary
# walking, exploration, a generic Use and a generic Collect, and all three
# complete, so any other result on them is a regression. AGTST17 and AGTST18
# are the harder ones the model is being pushed against; they are expected to
# expose problems rather than to pass, and what matters about them is which
# problem they expose this time.
#
# Everything runs without monsters. This phase has no combat at all, so an
# enemy is not a test of anything the bot does -- it just decides how long the
# run lasts.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TAG="${1:-corpus}"
TIMEOUT="${2:-300}"
cd "$ROOT"
for MAP in AGTST1 AGTST6 AGTST7 AGTST17 AGTST18; do
  SRC="reference/blood/$MAP.map"
  [ -f "$SRC" ] || { printf "%-8s (map not present)\n" "$MAP"; continue; }
  bash tools/botrun.sh "$SRC" "$TAG-$MAP" -bot_timeout "$TIMEOUT" -nodudes \
    >/dev/null 2>&1
  printf "%-8s " "$MAP"
  python tools/bot_scorecard.py "work/botlab/$TAG-$MAP/telemetry.ndjson" \
                                "work/botlab/$TAG-$MAP/trajectory.ndjson" --brief \
    --output "work/botlab/$TAG-$MAP/scorecard.json"
  # The scorecard says how the run went; the invariants say whether the bot's
  # own account of it can be trusted.  A run may fail its objective and still
  # be honest, but a violation here means the world model is corrupted.
  python tools/bot_invariants.py "work/botlab/$TAG-$MAP/telemetry.ndjson" \
      --trajectory "work/botlab/$TAG-$MAP/trajectory.ndjson" \
      --map "$SRC" --quiet || true
done
