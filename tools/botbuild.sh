#!/usr/bin/env bash
# Build NBlood with the playtest bot and stage it next to the game data.
#
# The tree's dependency tracking does not rebuild a bot object when one of the
# bot's own headers changes, and a stale object there is a silent struct-layout
# mismatch that crashes at run time rather than a link error, so drop the whole
# bot object tree every time. blood.o and view.o go too: they hold the bot's
# command-line switches and its draw call, and a stale one of those looks
# like the flag was never added.
set -e
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT/NBlood"
# A bot run left running holds nblood.exe open and the link fails.
taskkill //F //IM nblood.exe >/dev/null 2>&1 || true
rm -rf obj/blood/llmapper obj/blood/blood.o obj/blood/view.o
mingw32-make -j8 "$@" blood 2>&1 | grep -iE '\berror\b|\bError\b' && exit 1
cp -f nblood.exe "$ROOT/reference/blood/nblood.exe"
echo "build ok: $(ls -la nblood.exe | awk '{print $5}') bytes"
