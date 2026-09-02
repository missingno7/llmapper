"""The sleep phase: what three decompilations needed, and what a macro is.

Research section 2.5 says to refactor the programs after a second map, name
what both needed, and promote it. This runs over the three decompiled maps --
E3M1, E1M2 and E4M8 -- and answers three questions with queries rather than
opinions:

1. what does each layer leave as residue, per map;
2. which residue REASONS appear on more than one map (a reason on one map is
   that map's, a reason on three is the model's);
3. for each proposed macro, how many residue facts it would lower on each
   map -- and a macro that lowers residue on fewer than two maps is dropped
   here rather than proposed.

The classification a macro proposal turns on is not the size of the residue
but its CAUSE, and there are three:

* a CONSTRUCT gap -- the map authors something our language cannot say. A
  macro fixes this.
* a ROW gap -- the join grammar has no row for a pair the campaign makes.
  A row fixes this; a macro does not.
* a READER gap -- our reader cannot attest what the map did. Neither fixes
  this; a better measurement does.

Only the first becomes a macro. The other two are reported next to it so the
count is not mistaken for a mandate.

Nothing here writes to bloodmap: the macro list is a proposal for P14b, who
owns the constructors.
"""

from __future__ import annotations

import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
PROJECT = pathlib.Path(__file__).resolve().parents[1]
MAPS = ("e3m1", "e1m2", "e4m8")

#: A reason has to hold on this many maps before it is the model's problem.
SHARED = 2

CONSTRUCT, ROW, READER = "construct", "row", "reader"


def facts(name: str, predicate: str) -> list[dict]:
    path = ROOT / f"projects/{name}-decompiled/facts/{predicate}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def ledger(name: str) -> dict:
    path = ROOT / f"projects/{name}-decompiled/residue-ledger.json"
    return json.loads(path.read_text(encoding="utf-8"))


def reason(row: dict) -> str:
    """The residue's reason, cut before the colon that carries its detail."""
    why = str(row.get("why", ""))
    head = why.split(":")[0] if ":" in why else why
    return head[:70]


def _subject(row: dict) -> tuple[str, str]:
    about = str(row.get("about", ""))
    kind, _, index = about.partition(":")
    return kind, index


def stair_walls(name: str) -> set[str]:
    """Every wall of every sector in a recovered stepped run.

    A tread is its own sector, so its side walls have no same-material
    neighbour to continue onto -- which is exactly what layer 2 reports as
    residue. A `stair` construct owns the whole run and projects across it.
    """
    sectors: set[int] = set()
    for run in facts(name, "stepped_run"):
        for source in run.get("_from", ()):
            kind, _, index = str(source).partition(":")
            if kind == "sector":
                sectors.add(int(index))
    #: A wall fact carries no sector; a sector fact carries the run of walls
    #: that closes it. Following `wall_ptr`/`wall_count` is the map's own way
    #: of saying which walls a sector owns.
    walls: set[str] = set()
    for record in facts(name, "sector"):
        index = int(str(record["id"]).split(":")[-1])
        if index not in sectors:
            continue
        first = int(record["wall_ptr"])
        walls.update(str(one) for one in
                     range(first, first + int(record["wall_count"])))
    return walls


def macros(name: str) -> dict[str, dict]:
    """Each candidate macro, and the residue facts it would take ownership of.

    Ownership is decided by the residue's own subject, never by a count typed
    here: a macro lowers a residue fact when the fact is about a record the
    macro would author.
    """
    residue = facts(name, "residue")
    walls = stair_walls(name)
    out: dict[str, list[str]] = collections.defaultdict(list)
    for row in residue:
        kind, index = _subject(row)
        why = str(row.get("why", ""))
        head = reason(row)
        if head == "an XSPRITE with no wiring this reader reads":
            out["dressing"].append(row["id"])
        elif (head == "wired, and no sentence realises it"
              or "but no sentence names it" in why):
            out["channel"].append(row["id"])
        elif head == "carries a light wave and nothing else":
            out["self_lit"].append(row["id"])
        elif head == "the course teaches no lesson of type 511":
            out["breakable"].append(row["id"])
        elif row["aspect"] == "surface" and kind == "wall" and index in walls:
            out["stair"].append(row["id"])
    return {key: {"lowers": len(value), "facts": sorted(value)}
            for key, value in out.items()}


#: What each candidate says, and which of the three gaps it is. The `lowers`
#: numbers are never here; they are computed above.
PROPOSALS = {
    "dressing": {
        "cause": CONSTRUCT,
        "signature": "dressing(anchor, [prop...], *, spread=, facing=)",
        "says": ("a bundle of unwired sprites placed against an anchor -- a "
                 "table with its bottles, a shelf with its books. The reader "
                 "that names them already exists (read_intent.named_props "
                 "and anchors.find_bundles); nothing authors them"),
        "why_a_macro": ("the residue is one fact per sprite and every sprite "
                        "is decoration our language cannot place except by "
                        "absolute coordinate"),
    },
    "channel": {
        "cause": CONSTRUCT,
        "signature": "channel(number, tx=[...], rx=[...], *, on=, wave=)",
        "says": ("one channel with its transmitters and its receivers as a "
                 "single construct. The campaign fans a channel out to as "
                 "many records as it likes; our writer wires one pair"),
        "why_a_macro": ("the residue is records that transmit or listen on a "
                        "channel no sentence reaches, which is what a "
                        "one-pair writer produces"),
    },
    "self_lit": {
        "cause": CONSTRUCT,
        "signature": "self_lit(space, amplitude=, phase=, wave=)",
        "says": ("a sector that lights itself: an XSECTOR carrying a light "
                 "wave and no motion, no key and no channel"),
        "why_a_macro": ("the reader can read it and calls it residue only "
                        "because it is not a mechanism; it is a lighting "
                        "construct with no home in the language"),
    },
    "stair": {
        "cause": CONSTRUCT,
        "signature": "stair(from_, to, *, treads=, width=, clear_height=)",
        "says": ("a stepped run as one construct owning every tread and the "
                 "projection across them, rather than N sectors each fitted "
                 "its own frame"),
        "why_a_macro": ("a tread is its own sector, so its side walls have "
                        "no same-material neighbour and layer 2 cannot "
                        "attest a frame on any of them"),
    },
    "breakable": {
        "cause": CONSTRUCT,
        "signature": "breakable(surface, *, on=, reveals=)",
        "says": ("a wall of type 511 (kWallGib) with the channel it fires "
                 "and what it opens onto"),
        "why_a_macro": ("layer 8 refuses to name these because the taught "
                        "course has no lesson of type 511 at all -- the "
                        "campaign uses a mechanism its own course omits"),
    },
}

#: Reported next to the macros, never as macros. Each is a real gap with a
#: real owner, and none of them is fixed by a constructor.
NOT_MACROS = {
    "interior|interior rows": {
        "cause": ROW,
        "owner": "queue item 37e -- 11 proposed rows, none added",
        "says": ("the join grammar has no row for two interiors meeting, in "
                 "any of the three height relations. It is the campaign's "
                 "commonest join and the table is silent on it"),
    },
    "a surface's own projection": {
        "cause": READER,
        "owner": "the Surface/Frame representation item",
        "says": ("layer 2 cannot attest a frame on a wall with no "
                 "same-material neighbour, or on one whose neighbour breaks "
                 "the projection. This is the single largest residue on all "
                 "three maps and no macro touches it: it is what the tree "
                 "modelling spaces instead of surfaces costs"),
    },
    "spaces nothing groups": {
        "cause": READER,
        "owner": "bloodmap.decompiler.decompile_level",
        "says": ("a sector in the tree only so the partition closes. The "
                 "reader has no perceptual evidence that groups it, and a "
                 "constructor cannot supply evidence"),
    },
}


def main() -> int:
    rows = []
    per_map_reasons: dict[str, collections.Counter] = {}
    per_map_macros: dict[str, dict] = {}
    for name in MAPS:
        residue = facts(name, "residue")
        per_map_macros[name] = macros(name)
        per_map_reasons[name] = collections.Counter(
            (row["aspect"], reason(row)) for row in residue)
        book = ledger(name)
        rows.append({"map": name.upper(), "residue_facts": len(residue),
                     "layers": book.get("layers", book.get("summary", {})),
                     "macros": {key: value["lowers"]
                                for key, value in per_map_macros[name].items()}})

    shared = {}
    for key in set().union(*(set(counter) for counter in
                             per_map_reasons.values())):
        counts = {name: per_map_reasons[name].get(key, 0) for name in MAPS}
        maps_with = sum(1 for value in counts.values() if value)
        if maps_with >= SHARED:
            shared[f"{key[0]}: {key[1]}"] = {
                "maps": maps_with, "total": sum(counts.values()),
                **{name.upper(): value for name, value in counts.items()}}

    proposed, dropped = {}, {}
    for key, body in PROPOSALS.items():
        lowers = {name.upper(): per_map_macros[name].get(key, {}).get("lowers", 0)
                  for name in MAPS}
        maps_with = sum(1 for value in lowers.values() if value)
        entry = {**body, "lowers": lowers, "maps_it_lowers": maps_with,
                 "total": sum(lowers.values())}
        (proposed if maps_with >= SHARED else dropped)[key] = entry

    out = {
        "population": [name.upper() for name in MAPS],
        "rule": (f"a macro that lowers residue on fewer than {SHARED} maps is "
                 f"not proposed"),
        "per_map": rows,
        "shared_reasons": dict(sorted(shared.items(),
                                      key=lambda kv: -kv[1]["total"])),
        "macros_proposed": proposed,
        "macros_dropped": dropped,
        "not_macros": NOT_MACROS,
    }
    target = PROJECT / "references" / "sleep-phase.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(out, indent=1, sort_keys=True),
                      encoding="utf-8")

    print(f"three decompilations, "
          f"{sum(row['residue_facts'] for row in rows)} residue facts")
    for row in rows:
        print(f"  {row['map']}: {row['residue_facts']}")
    print("")
    print(f"reasons on {SHARED}+ maps: {len(shared)}")
    for key, value in list(out["shared_reasons"].items())[:12]:
        print(f"  {value['total']:5d}  on {value['maps']} maps  {key}")
    print("")
    print("MACROS PROPOSED")
    for key, value in sorted(proposed.items(), key=lambda kv: -kv[1]["total"]):
        print(f"  {key:12s} lowers {value['total']:5d} on "
              f"{value['maps_it_lowers']} maps  {value['lowers']}")
        print(f"               {value['signature']}")
    if dropped:
        print("DROPPED (fewer than two maps)")
        for key, value in dropped.items():
            print(f"  {key:12s} {value['lowers']}")
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
