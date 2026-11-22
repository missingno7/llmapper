"""List mapper-authored sound references in a compiled Blood map."""

from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path

from bloodmap.blood_types import SPRITE_TYPES
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from tools.sound_catalog import SPRITE_SLOTS, facts

CITY = Path(__file__).resolve().parents[1] / "projects/blood-city/level/blood-city-current.MAP"


def sound_references(disk):
    """Yield object, index, type, sector, slot, role and SFX id in map order."""
    for index, sprite in enumerate(disk.sprites):
        fields, extra = record_fields(sprite), record_extra(sprite)
        if extra is None:
            continue
        type_id, sector = fields["type"], fields["sector"]
        name, slots = SPRITE_SLOTS.get(type_id, ("", {}))
        if type_id == 710 or fields["status"] == 12:
            name, slots = "Ambient SFX", {"data_3": "loop"}
        elif type_id == 15:
            name, slots = "kMarkerPath", {"data_3": "departure", "data_4": "arrival"}
        elif SPRITE_TYPES.get(type_id, {}).get("name") in {
            "kThingObjectGib", "kThingObjectExplode", "kThingBloodBits",
            "kThingBloodChunks", "kThingZombieHead",
        }:
            name = SPRITE_TYPES[type_id]["name"]
            slots = {"data_4": "gib activation"}
        for slot, role in slots.items():
            if extra[slot] > 0:
                yield "sprite", index, name, sector, slot, role, extra[slot]

    # XSECTOR has no direct sound slot. Its moving-sector sounds are on
    # sprites 709 in that sector, and ambient radii and IDs are on stat 12.
    for index, wall in enumerate(disk.walls):
        extra = record_extra(wall)
        if record_fields(wall)["type"] == 511 and extra and extra["data"] in (1, 12, 13):
            yield "wall", index, "kWallGib", None, "data", "glass break (implicit)", 300


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map", type=Path, nargs="?", default=CITY)
    args = parser.parse_args()
    disk, catalogue = read_map(args.map), facts()
    counts = Counter()
    unknown = set()
    for obj, index, kind, sector, slot, role, sound_id in sound_references(disk):
        counts[kind] += 1
        row = catalogue.get(str(sound_id))
        if row is not None:
            descriptions = [item["text"] for item in row["descriptions"]]
            if row.get("transcript"):
                descriptions.insert(0, row["transcript"]["text"])
            details = f"{row['name']}.SFX | {' / '.join(dict.fromkeys(descriptions))}"
        else:
            unknown.add(sound_id)
            details = "unresolved"
        location = f" in sector {sector}" if sector is not None else ""
        print(f"{obj} {index}{location} {kind} {slot} ({role}): {sound_id} {details}")
    print("Sound slots:", dict(sorted(counts.items())), "total", sum(counts.values()))
    print("Direct XSECTOR sound slots: 0")
    print("Unresolved sound IDs:", sorted(unknown))
    return int(bool(unknown))


if __name__ == "__main__":
    raise SystemExit(main())
