#!/usr/bin/env bash
# Build NBlood with the playtest bot and stage it next to the game data.
#
# The tree's dependency tracking does not rebuild nav_kernel.o when
# nav_kernel.h changes, and a stale object there is a silent struct-layout
# mismatch rather than a link error, so force those two objects every time.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/NBlood"
rm -f obj/blood/llmapper/bot/nav_kernel.o obj/blood/llmapper/bot/bot.o
mingw32-make -j8 "$@" blood 2>&1 | grep -iE '\berror\b|\bError\b' && exit 1
cp -f nblood.exe "$ROOT/reference/blood/nblood.exe"
echo "build ok: $(ls -la nblood.exe | awk '{print $5}') bytes"
