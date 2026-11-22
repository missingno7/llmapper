"""Count sector motion sound profiles in the Blood campaign and tutorials."""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

from bloodmap.corpus import campaign_maps, list_corpus_maps
from bloodmap.format import read_map
from bloodmap.mechanism import SECTOR_SOUND_TYPE, TRIGGERED_MOTION_TYPES
from bloodmap.model import record_extra, record_fields


FIELDS = tuple(f"data_{n}" for n in range(1, 5))
MOTION_TYPES = TRIGGERED_MOTION_TYPES | {611, 612}


def _measure(maps):
    totals = Counter()
    marked = Counter()
    slots = defaultdict(lambda: [Counter() for _ in FIELDS])
    profiles = defaultdict(Counter)
    examples = {}
    forms = Counter()
    blast = Counter()
    path_slots = {"departure": Counter(), "arrival": Counter()}
    map_count = 0
    for path in maps:
        map_count += 1
        disk = read_map(path)
        markers = defaultdict(list)
        waypoints = {}
        for sprite_id, sprite in enumerate(disk.sprites):
            fields = record_fields(sprite)
            data = record_extra(sprite) or {}
            if fields["type"] == 15 and fields["status"] == 16 and data:
                waypoints[data["data_1"]] = data
            if fields["type"] != SECTOR_SOUND_TYPE:
                continue
            sounds = tuple(data.get(field, 0) for field in FIELDS)
            markers[fields["sector"]].append((sprite_id, sounds))
            forms[(fields["status"], fields["picnum"], fields["cstat"])] += 1

        for sector_id, sector in enumerate(disk.sectors):
            type_id = record_fields(sector)["type"]
            if type_id not in MOTION_TYPES:
                continue
            data = record_extra(sector) or {}
            group = str(type_id)
            if type_id in {600, 602}:
                planes = [surface for surface in ("floor", "ceiling")
                          if data.get(f"off_{surface}_z", 0) != data.get(f"on_{surface}_z", 0)]
                group += " " + (" and ".join(planes) if planes else "equal endpoints")
            totals[group] += 1
            sector_markers = markers.get(sector_id, [])
            if sector_markers:
                marked[group] += 1
            if type_id == 612 and sector_markers:
                # NBlood plays both sounds from the waypoint being departed.
                visited = set()
                waypoint_id = data.get("data")
                while waypoint_id in waypoints and waypoint_id not in visited:
                    waypoint = waypoints[waypoint_id]
                    if waypoint["data_2"] not in waypoints:
                        break
                    path_slots["departure"][waypoint["data_3"]] += 1
                    path_slots["arrival"][waypoint["data_4"]] += 1
                    visited.add(waypoint_id)
                    waypoint_id = waypoint["data_2"]
            if (type_id == 600 and data.get("trigger_once") and data.get("rx_id")
                    and data.get("busy_time_a", 0) <= 1
                    and data["off_ceiling_z"] == data["off_floor_z"]
                    and data["on_ceiling_z"] < data["off_ceiling_z"]):
                blast["sectors"] += 1
                blast["marked"] += bool(sector_markers)
            for sprite_id, sounds in sector_markers:
                profiles[group][sounds] += 1
                examples.setdefault((group, sounds), f"{path.stem}:{sector_id} sprite {sprite_id}")
                for slot, sound in zip(slots[group], sounds):
                    slot[sound] += 1

    groups = {}
    for group in sorted(totals, key=lambda group: (int(group.split()[0]), group)):
        groups[group] = {
            "sectors": totals[group], "with_709": marked[group],
            "profiles": [{"fields": sounds, "count": count, "first": examples[group, sounds]}
                         for sounds, count in profiles[group].most_common()],
            "by_slot": {field: dict(sorted(slot.items())) for field, slot in zip(FIELDS, slots[group])},
        }
    return {
        "maps": map_count,
        "groups": groups,
        "marker_forms": [{"stat": stat, "tile": tile, "cstat": cstat, "count": count}
                         for (stat, tile, cstat), count in forms.most_common()],
        "rapid_one_shot_closed_open": dict(blast),
        "path_waypoint_slots_with_709_source": {
            slot: dict(sorted(ids.items())) for slot, ids in path_slots.items()},
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", type=Path, required=True)
    args = parser.parse_args()
    tutorials = list_corpus_maps(population="mechanism-tutorial")
    report = {
        "field_order": FIELDS,
        "blood-campaign": _measure(campaign_maps()),
        "mechanism-tutorial": _measure(item.path for item in tutorials),
    }
    args.o.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    for population in ("blood-campaign", "mechanism-tutorial"):
        print(f"{population}: {report[population]['maps']} maps")


if __name__ == "__main__":
    main()
