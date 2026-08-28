#!/usr/bin/env bash
# Check that the bot's authorities are separated by something the compiler
# and a grep can both see, not only by intent.
#
#   Blood -> blood/ -> semantic/ + terrain/ -> traversal/ -> planner/ -> exec/
#                       debug/ reads both, feeds neither
#
# The last check is the one that matters: the spatial layers are compiled
# with no engine include path at all, and the spatial invariants are run.
#
# usage: bot_layering.sh
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BOT="$ROOT/NBlood/source/blood/src/llmapper/bot"
FAIL=0

note() { printf '%-52s %s\n' "$1" "$2"; }

ABOVE=$(find "$BOT/semantic" "$BOT/terrain" "$BOT/traversal" "$BOT/nav" "$BOT/planner" \
             "$BOT/exec" -name '*.h' -o -name '*.cpp')
ABOVE="$ABOVE $BOT/bot.cpp $BOT/bot.h"

# 1. The engine's own vocabulary must not appear above the mapper. Comments
#    are excluded: the rule is about code, and the headers explain the rule.
LEAKS=$(grep -nEw 'sector|wall|sprite|nextsector|XSECTOR|XWALL|XSPRITE|xsector|xwall|xsprite|ClipMove|GetZRange|ActionScan|cansee|supportHit|florhit|ROR|gMe|spritetype|walltype|sectortype' $ABOVE \
        | grep -vE '^[^:]+:[0-9]+: *(//|\*)' || true)
if [ -n "$LEAKS" ]; then
  note "no Blood vocabulary above the mapper" "FAIL"
  echo "$LEAKS"
  FAIL=1
else
  note "no Blood vocabulary above the mapper" "ok"
fi

# 2. Planning must not depend on provenance. If it ever includes the debug
#    module, removing that module could change behaviour.
if grep -rn 'bot_debug' "$BOT/semantic" "$BOT/terrain" "$BOT/traversal" \
        "$BOT/planner" "$BOT/exec" >/dev/null 2>&1; then
  note "planning cannot reach provenance" "FAIL"
  FAIL=1
else
  note "planning cannot reach provenance" "ok"
fi

# 3. The world must not be able to ask about the actor, and the planner must
#    not be able to ask about physics numbers.
if grep -rnEw 'radius|hull|jumpImpulse|crouchHeight|stepUp' \
        "$BOT/semantic" "$BOT/terrain" >/dev/null 2>&1; then
  note "world geometry is free of actor configuration" "FAIL"
  FAIL=1
else
  note "world geometry is free of actor configuration" "ok"
fi

# 4. Sampling constants must not exist above the mapper at all.
if grep -rnE 'kSurvey|kConnect|kQuant|gridCell|placeCell' $ABOVE \
        >/dev/null 2>&1; then
  note "no sampling constants define topology" "FAIL"
  FAIL=1
else
  note "no sampling constants define topology" "ok"
fi

# 5. The decisive one: compile the spatial layers with no engine include path
#    whatsoever, and run the spatial invariants.
OUT="$ROOT/work/botlab/layering"
mkdir -p "$OUT"
if g++ -std=c++17 -Wall -Wextra -Werror -O1 -o "$OUT/spatial_test.exe" \
      "$BOT/semantic_layer_test.cpp" "$BOT/semantic/semantic_world.cpp" \
      "$BOT/semantic/geometry.cpp" "$BOT/terrain/terrain_model.cpp" \
      "$BOT/traversal/traversal_model.cpp" "$BOT/planner/bot_planner.cpp" \
      "$BOT/nav/local_path.cpp" \
      "$BOT/exec/bot_executor.cpp" 2>"$OUT/compile.log"; then
  note "spatial layers compile without Blood" "ok"
  if "$OUT/spatial_test.exe" > "$OUT/spatial.log" 2>&1; then
    note "spatial invariants hold" "ok"
    sed 's/^/    /' "$OUT/spatial.log"
  else
    note "spatial invariants hold" "FAIL"
    sed 's/^/    /' "$OUT/spatial.log"
    FAIL=1
  fi
else
  note "spatial layers compile without Blood" "FAIL"
  sed -n '1,30p' "$OUT/compile.log"
  FAIL=1
fi

# 6. Report the dependency direction that actually exists in the includes.
echo
echo "includes crossing module boundaries:"
for DIR in semantic terrain traversal planner exec blood debug; do
  DEPS=$(grep -ho '#include "\.\./[a-z_]*/' "$BOT/$DIR"/* 2>/dev/null \
         | sed 's|#include "../||; s|/$||' | sort -u | tr '\n' ' ')
  printf '  %-10s -> %s\n' "$DIR" "${DEPS:-(none)}"
done

exit $FAIL
