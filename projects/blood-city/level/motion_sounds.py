"""Score Gravesend's motion sectors and verify their sound records on disk."""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))

from bloodmap.blood_types import SECTOR_TYPES
from bloodmap.format import read_map
from bloodmap.mechanism import (
    SECTOR_SOUND_PROFILES, SECTOR_SOUND_STAT, SECTOR_SOUND_TILE, SECTOR_SOUND_TYPE,
    TRIGGERED_MOTION_TYPES, add_sector_sound,
)
from bloodmap.model import record_extra, record_fields
from bloodmap.sector_geom import sector_contains


WIRE_PROFILES = {
    "theatre:curtain": "curtain",
    "theatre:box-curtain": "curtain",
    "theatre:prize": "curtain",
    "church:breach": "blast",
    "arcade:cache": "blast",
    "pump:presses": "ceiling_press",
    "station:car-door": "metal_z_door",
    "station:gate": "chain_lift",
    "sewer:plague-pit": "blast",
    "foundry:loading-shutter": "heavy_slide",
    "theatre:fire-doors": "wood_swing",
    "lever:aldermack": "wood_swing",
    "lever:lobby": "wood_z_door",
    "sewer:settling-hall-lift": "winch_lift",
    "sewer:stockyard-trolley": "rail_shuttle",
    "ghost:hatch-open": "hydraulic_slide",
    "phantom:car": "phantom_train",
    "cabal:broken": "great_stone",
    "cabal:shut": "great_stone",
    "cabal:heart": "flesh_door",
    "station:fare-turnstile": "fare_ambient",
}
#: A door that rises (600), by the tile its leaf wears: what the campaign's
#: ceiling doors wearing it sound like. 22, the wooden door: 110/160 leads
#: (x4) and stone's 106 is never used. 495, panelled metal: 111 starts the
#: most, 165 its commonest stop. 110 and 1011, stone: 106.
#: (The owner, 2026-11-23: "These wooden zdoor sound 106 sounds like a moving
#: stone ... example 110 would be better".)
LEAF_PROFILES = {22: "wood_z_door", 495: "iron_z_door", 110: "stone_door", 1011: "stone_door"}
MOTION_TYPES = TRIGGERED_MOTION_TYPES | {611, 612}
FIELD_NAMES = tuple(f"data_{i}" for i in range(1, 5))
# E1M2 sprite 556 supplies the train motor. Death Wish s247 uses 277.
PHANTOM_TRAIN = (115, 277, 115, 277)
#: the member of the coach that speaks for the whole body (`mechanism.rigid_body`)
VOICE = "_coach:aisle"
SILENT = ("/settling_hall/rite:tooth_", "/settling_hall/rite:gate_side")
CARRIED_PROFILES = {"rail_shuttle", "phantom_train"}
FARE_AMBIENT = (250, 700, 21, 20)


def apply(disk, allocations, circuit):
    """Place audio on the built sector IDs and return their named expectations."""
    regions = {allocation.sector_id: name for name, allocation in allocations.items()}
    profiles = {wire.channel: WIRE_PROFILES[wire.name] for wire in circuit.wires
                if wire.name in WIRE_PROFILES}
    rows = {}
    for index, sector in enumerate(disk.sectors):
        type_id = record_fields(sector)["type"]
        if type_id not in MOTION_TYPES:
            continue
        region = regions[index]
        data = record_extra(sector) or {}
        profile = profiles.get(data.get("rx_id"))
        if profile is None and type_id == 600:
            profile = next((LEAF_PROFILES[tile] for tile in _leaf_faces(disk, index)
                            if tile in LEAF_PROFILES), None)
        if (profile == "phantom_train" and not region.endswith(VOICE)) or any(part in region for part in SILENT):
            # one body of many sectors has one voice, its aisle's; a ring of teeth has its well's
            rows[str(index)] = {"region": region, "profile": "silent member"}
            continue
        if profile is None:
            raise ValueError(f"{region} (sector {index}) needs a campaign sound profile")
        if profile == "phantom_train":
            add_sector_sound(disk, index, sounds=PHANTOM_TRAIN, carry=True)
        elif profile in SECTOR_SOUND_PROFILES:
            add_sector_sound(disk, index, profile, carry=profile in CARRIED_PROFILES)
        rows[str(index)] = {"region": region, "profile": profile}
    return rows


def _leaf_faces(disk, index):
    """The tiles a moving sector's neighbours show of it, commonest first."""
    fields = record_fields(disk.sectors[index])
    tiles = Counter()
    for wall in range(fields["wall_ptr"], fields["wall_ptr"] + fields["wall_count"]):
        other = record_fields(disk.walls[wall])["next_wall"]
        if other >= 0:
            tiles[record_fields(disk.walls[other])["picnum"]] += 1
    return [tile for tile, _ in sorted(tiles.items(), key=lambda row: (-row[1], row[0]))]


def check(disk, expected, wires):
    """List every moving sector and check its sound records against the build."""
    emitters = defaultdict(list)
    charges = defaultdict(list)
    lever_wires = {wire["channel"]: wire["name"] for wire in wires
                   if wire["name"].startswith("lever:")
                   or wire["name"] in {"station:car-door", "station:gate", "pump:belt"}}
    levers = defaultdict(list)
    for index, sprite in enumerate(disk.sprites):
        fields = record_fields(sprite)
        data = record_extra(sprite) or {}
        if fields["type"] in {SECTOR_SOUND_TYPE, 710}:
            emitters[fields["sector"]].append((index, fields, data))
        if fields["type"] == 459 and data.get("rx_id"):
            charges[data["rx_id"]].append(index)
        if fields["type"] == 20 and fields["picnum"] == 1070 and data.get("tx_id") in lever_wires:
            levers[data["tx_id"]].append((index, data))

    errors = []
    seen = set()
    count = 0
    for index, sector in enumerate(disk.sectors):
        type_id = record_fields(sector)["type"]
        if type_id not in MOTION_TYPES:
            continue
        key = str(index)
        seen.add(key)
        row = expected.get(key, {})
        profile = row.get("profile")
        name = row.get("region", "unscored")
        type_name = SECTOR_TYPES.get(type_id, {}).get("name", "unlisted motion")
        print(f"sector {index:4} {type_id} {type_name} {name}")
        markers = [item for item in emitters[index] if item[1]["type"] == SECTOR_SOUND_TYPE]
        for sprite_id, fields, data in emitters[index]:
            detail = " ".join(f"{field}={data.get(field, '?')}" for field in FIELD_NAMES)
            print(f"  sprite {sprite_id:4} type {fields['type']} {detail}")
        if profile == "blast":
            rx_id = (record_extra(sector) or {}).get("rx_id")
            print(f"  blast charges on the same wire: {charges.get(rx_id, [])}")
            if markers or not charges.get(rx_id):
                errors.append(f"sector {index}: expected wired blast charges and zero 709 markers")
            continue
        if profile == "fare_ambient":
            audible = [data for _, fields, data in emitters[index]
                       if fields["type"] == 710 and fields["status"] == 12
                       and fields["cstat"] & 32768 and data.get("state")
                       and tuple(data.get(field) for field in FIELD_NAMES) == FARE_AMBIENT]
            if len(audible) != 1 or markers:
                errors.append(f"sector {index}: expected one fare ambience and zero 709 markers")
            continue
        if profile == "silent member":
            if markers:
                errors.append(f"sector {index}: a second voice in one body")
            continue
        sounds = PHANTOM_TRAIN if profile == "phantom_train" else SECTOR_SOUND_PROFILES.get(profile)
        if sounds is None or len(markers) != 1:
            errors.append(f"sector {index}: expected one named sector sound")
            continue
        _, fields, data = markers[0]
        count += 1
        if (fields["status"] != SECTOR_SOUND_STAT or fields["picnum"] != SECTOR_SOUND_TILE
                or not fields["cstat"] & 32768 or data.get("tx_id") != 0 or data.get("rx_id") != 0
                or not sector_contains(disk, index, fields["x"], fields["y"])
                or tuple(data.get(field) for field in FIELD_NAMES) != sounds
                or bool(fields["cstat"] & 8192) != (profile in CARRIED_PROFILES)):
            errors.append(f"sector {index}: malformed {profile} marker")
    for key in sorted(expected.keys() - seen, key=int):
        errors.append(f"sector {key}: scored sector absent from the moving set")
    for index, items in sorted(emitters.items()):
        if str(index) not in seen and any(fields["type"] == SECTOR_SOUND_TYPE for _, fields, _ in items):
            errors.append(f"sector {index}: 709 marker outside a moving sector")
    belt_channels = {wire["channel"] for wire in wires if wire["name"] == "pump:belt"}
    for index, sector in enumerate(disk.sectors):
        data = record_extra(sector) or {}
        if (record_fields(sector)["type"] == 0 and data.get("rx_id") in belt_channels
                and data.get("pan_floor") and data.get("pan_velocity")):
            print(f"sector {index:4} pump belt pan, with machinery ambience in the hall")
    for channel, name in sorted(lever_wires.items()):
        rows = levers[channel]
        for sprite_id, data in rows:
            print(f"lever {name} sprite {sprite_id} data_1={data['data_1']} data_2={data['data_2']}")
        if len(rows) != 1 or (rows[0][1].get("data_1"), rows[0][1].get("data_2")) != (203, 203):
            errors.append(f"lever {name}: expected one lever with sound 203 in both positions")
    print(f"{len(seen)} moving sectors, {count} sector sound markers, {len(errors)} errors")
    for error in errors:
        print(f"ERROR {error}")
    return int(bool(errors))


if __name__ == "__main__":
    folder = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map", type=Path, nargs="?", default=folder / "blood-city-current.MAP")
    parser.add_argument("--manifest", type=Path,
                        default=folder.parent / "reports" / "build-manifest.json")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    raise SystemExit(check(read_map(args.map), manifest["motion_sounds"], manifest["wires"]["wires"]))
