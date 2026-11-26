"""Split the campaign's keyed things (tools.mine_keys.keyed_things) into locks and the foes that only carry a key."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from bloodmap.corpus import campaign_maps  # noqa: E402
from bloodmap.format import read_map  # noqa: E402
from tools.mine_keys import keyed_things  # noqa: E402

if __name__ == "__main__":
    kinds: Counter = Counter()
    for path in campaign_maps():
        disk = read_map(path)
        for thing in keyed_things(disk):
            if thing["kind"] != "sprite":
                kinds[thing["kind"]] += 1
                continue
            kind = int(disk.sprites[thing["index"]].fields["type"])
            # a dude's key field is the key it drops (actor.cpp, actKillDude: actDropObject of kItemKeyBase + key)
            kinds["foe carrying a key" if 200 <= kind <= 254 else "plain sprite, type 0" if kind == 0 else f"sprite type {kind}"] += 1
    print(sum(kinds.values()), "keyed things:", dict(kinds.most_common()))
