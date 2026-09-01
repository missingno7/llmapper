"""Sweep every exhibit through the conformance check for its construct.

Part A's catch list. The turnstile regression is the one the owner found by
walking; this asks what else has drifted from the template it was promoted
from, using the same relational miners that produced those templates.

A conformance check is a different question from the self-reading gate.
`selfread` asks whether the claimed mechanism EXISTS and is wired -- the type
is set, the channel is right, the trigger fires. Conformance asks whether it
still LOOKS like the thing it was mined from. The turnstile passed the first
question with its blades in a square.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from bloodmap.conformance import (                          # noqa: E402
    ConformanceError, measure_curtain, measure_planar_door,
    measure_sprite_payload, measure_turnstile, measure_wall_sprites,
)
from bloodmap.format import read_map                        # noqa: E402

#: Owner anchor 146: the curtain fabric. What a curtain wears is stable
#: across a change of topology, which is why the check is routed on it.
CURTAIN_TILE = 146

HERE = pathlib.Path(__file__).resolve().parent
MAP = HERE / "level" / "pattern-zoo.MAP"
MANIFEST = HERE / "reports" / "build-manifest.json"

#: Which check a sector's TYPE calls for. The construct is identified from
#: the built map rather than from the registry, so an exhibit cannot dodge a
#: check by describing itself differently.
BY_TYPE = {
    615: ("rotor", measure_turnstile),
    613: ("rotor", measure_turnstile),
}


def _for_sector(disk, sector_id, region_name):
    """The checks that apply to one built sector, by what it actually is."""
    from bloodmap.effects import payload

    type_id = int(disk.sectors[sector_id].fields["type"])
    if type_id in BY_TYPE:
        return [BY_TYPE[type_id][1]]
    if type_id in (614, 616):
        found = payload(disk, sector_id)
        shape = found["shape"]["shape"]
        checks = []
        #: A curtain is a FIN now, so its payload shape is "part of the
        #: sector travels" -- and routing the curtain check on the old
        #: "resizes itself" shape meant it stopped running the moment the
        #: constructor was corrected. The zoo reported 13/13 conforming
        #: because the curtain was never asked. It is identified by what it
        #: WEARS instead, which does not change when the topology does.
        sector = disk.sectors[sector_id]
        start = int(sector.fields["wall_ptr"])
        count = int(sector.fields["wall_count"])
        wears_fabric = any(
            int(disk.walls[i].fields["picnum"]) == CURTAIN_TILE
            for i in range(start, start + count))
        if wears_fabric or shape == "the sector resizes itself":
            checks.append(measure_curtain)
        if shape == "boundary re-partition":
            checks.append(measure_planar_door)
        if found["sprites_with"] or found["sprites_against"]:
            checks.append(measure_sprite_payload)
        return checks
    return []


def run(map_path: pathlib.Path = MAP,
        manifest_path: pathlib.Path = MANIFEST) -> dict:
    disk = read_map(map_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    results, deviations = [], []
    for name, sector_id in sorted(manifest["region_sectors"].items()):
        for check in _for_sector(disk, sector_id, name):
            try:
                found = check(disk, sector_id)
            except ConformanceError as exc:
                deviations.append(f"{name}: {exc}")
                continue
            row = {"region": name, "sector": sector_id,
                   "construct": found.construct,
                   "conforms": found.conforms,
                   "measured": found.measured,
                   "deviations": [str(d) for d in found.deviations]}
            results.append(row)
            for one in found.deviations:
                deviations.append(f"{name} (sector {sector_id}): {one}")
    #: One whole-map check, not per construct: every wall-aligned sprite
    #: should face out of the wall it is on. The campaign is 97.6%
    #: perpendicular over 1495 of them.
    across = measure_wall_sprites(disk)
    results.append({"region": "(whole map)", "sector": None,
                    "construct": across.construct,
                    "conforms": across.conforms,
                    "measured": across.measured,
                    "deviations": [str(d) for d in across.deviations]})
    deviations.extend(f"(whole map): {d}" for d in across.deviations)

    return {
        "$schema": "llmapper.pattern-zoo-conformance", "schema_version": 1,
        "map": str(map_path).replace("\\", "/"),
        "constructs_checked": len(results),
        "conforming": sum(1 for r in results if r["conforms"]),
        "results": results,
        "deviations": deviations,
        "passed": not deviations,
    }


def main() -> int:
    report = run()
    (HERE / "reports" / "conformance.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"constructs checked: {report['constructs_checked']}, "
          f"conforming: {report['conforming']}")
    for line in report["deviations"]:
        print(f"  !! {line}")
    print("PASS" if report["passed"]
          else f"FAIL: {len(report['deviations'])} deviation(s)")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
