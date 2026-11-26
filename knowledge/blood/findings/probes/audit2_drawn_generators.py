"""Count the generator and sound sprites (types 700-712) that carry no invisible bit, and so are drawn in play."""
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))

from bloodmap.corpus import campaign_maps  # noqa: E402
from bloodmap.format import read_map  # noqa: E402

INVISIBLE = 0x8000


def drawn(path) -> Counter:
    """(type, tile) of every sprite of type 700-712 in the map whose cstat lacks the invisible bit."""
    out: Counter = Counter()
    for sprite in read_map(path).sprites:
        kind = int(sprite.fields["type"])
        if 700 <= kind <= 712 and not int(sprite.fields["cstat"]) & INVISIBLE:
            out[(kind, int(sprite.fields["picnum"]))] += 1
    return out


if __name__ == "__main__":
    maps = [Path(arg) for arg in sys.argv[1:]] or list(campaign_maps())
    total: Counter = Counter()
    held = 0
    for path in maps:
        found = drawn(path)
        total.update(found)
        held += bool(found)
    by_type = Counter()
    for (kind, _tile), count in total.items():
        by_type[kind] += count
    print(f"{sum(total.values())} drawn sprites of types 700-712 in {held} of {len(maps)} maps")
    print("by type:", dict(sorted(by_type.items())))
    print("commonest (type, tile):", total.most_common(12))
