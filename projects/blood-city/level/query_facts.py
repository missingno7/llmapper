"""The manifest, as queries over `projects/blood-city/facts/`.

Every number the build printed used to come out of the pass that made it,
which meant the manifest and the map could only ever agree. Read from the
store instead and the two can disagree -- which is the point of writing them
down separately.

It also closes the three read-back gaps slice 2i named, because all three were
gaps in the MAP and not in what the compiler knew: a surface's identity
survives a path, a piece's field depth survives being summed into a shade, and
a lamp's contribution survives being added to it. What stays open after this
is genuinely open, and is listed as such.
"""

from __future__ import annotations

import pathlib
import sys
from collections import Counter

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from bloodmap.facts import LEVEL_NAMES, FactStore                 # noqa: E402

FACTS = ROOT / "projects/blood-city/facts"

#: What a map alone still cannot say, after the store has said everything it
#: can. These are the honest remainder: not "the reader is weak" but "the
#: format does not carry it, and neither does any declaration we make".
OPEN_GAPS = (
    "playthrough: the store says which records realise which sentence, and "
    "nothing here says a body can reach them in that order -- that is the "
    "bot's evidence, not the compiler's",
    "intent: a fact records that a shadow fell here, never that the level "
    "wanted a dark corner here; taste is not a predicate",
)


def query(store: FactStore) -> dict:
    surfaces = store.of("surface")
    pieces = store.of("part_of")
    islands = store.of("island")
    depths = store.of("shade_depth")
    joins = store.of("join")
    lamps = store.of("lamp_delta")
    frames = store.of("frame")
    claims = store.of("claims")

    by_kind = Counter(f.attrs["kind"] for f in surfaces)
    piece_parents = Counter(f.attrs["parent"] for f in pieces
                            if f.predicate == "part_of"
                            and f.key[0] == "piece")
    depth_shade = Counter((int(f.attrs["depth"]), int(f.attrs["shade"]))
                          for f in depths)
    join_pairs = Counter((f.attrs["a"], f.attrs["b"]) for f in joins)
    contributors = Counter(f.attrs["owner"] if "owner" in f.fields
                           else f.source for f in claims)
    links = store.of("link")
    keys = store.of("key")
    return {
        "surfaces declared": len(surfaces),
        "openings (void)": len(store.of("void")),
        "inserts (fill)": Counter(f.attrs["kind"] for f in store.of("fill")),
        "sentences": Counter(f.attrs["construct"]
                             for f in store.of("sentence")),
        "realised by records": len(store.of("realises")),
        "links declared / realised":
            (len(links), sum(1 for f in links if f.attrs.get("realised"))),
        "keys declared / realised":
            (len(keys), sum(1 for f in keys if f.attrs.get("realised"))),
        "surfaces by kind": dict(sorted(by_kind.items())),
        "islands in the plan": Counter(f.attrs["kind"]
                                       for f in islands),
        "pieces": len(pieces),
        "pieces per surface (top 5)": piece_parents.most_common(5),
        "shade by depth": dict(sorted(depth_shade.items())),
        "join records": len(joins),
        "join pairs": dict(sorted(join_pairs.items())),
        "lamps": len(lamps),
        "lamp deltas": dict(Counter(int(f.attrs["delta"]) for f in lamps)),
        "texture runs": len(frames),
        "shade contributors": dict(sorted(contributors.items())),
        "facts by level": {LEVEL_NAMES[k]: v
                           for k, v in sorted(store.by_level().items())},
        "facts by predicate": store.count(),
    }


def closed_gaps(store: FactStore) -> list:
    """The three of slice 2i, answered from the store rather than the map."""
    surfaces = [f for f in store.of("surface")]
    pavements = [f for f in surfaces if f.attrs["kind"] == "pavement"]
    depths = store.of("shade_depth")
    lamps = store.of("lamp_delta")
    levels = sorted({int(f.attrs["depth"]) for f in depths})
    unrealised = [f for f in store.of("link") + store.of("key")
                  if not f.attrs.get("realised")]
    return [
        f"mission wiring: {len(unrealised)} declaration(s) carry "
        f"realised: false with their reason, so an unrealised link is a ROW "
        f"and not an absence",
        f"surface identity: {len(pavements)} pavement surfaces were declared "
        f"and each keeps its own row; the built map merges any two of them "
        f"that a pavement-only path connects into one component, and a path "
        f"cannot merge a fact",
        f"field depth: every sector carries its k -- levels {levels} -- "
        f"beside the shade it was summed into",
        f"lamp authorship: {len(lamps)} lamp contributions survive as their "
        f"own rows after LightBomb summed them into floor_shade",
    ]


def main() -> int:
    if not FACTS.exists():
        print(f"no fact store at {FACTS}; build the city first")
        return 1
    store = FactStore.read(FACTS)
    for key, value in query(store).items():
        print(f"{key}: {value}")
    print("\nread-back gaps closed by the store:")
    for line in closed_gaps(store):
        print(f"  - {line}")
    print("\nstill open, and about the world rather than the format:")
    for line in OPEN_GAPS:
        print(f"  - {line}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
