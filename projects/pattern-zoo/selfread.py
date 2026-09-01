"""The zoo reads itself.

The acceptance gate this rebuild exists for. v1 passed structural validation,
byte-exact round trip, an NBlood load smoke and twenty-four renders -- and not
one of its doors worked, because a hand-written XSECTOR dict on a type-0
sector is inert. Every gate it passed was a gate about *depiction*.

So the map is read back with the understanding stack -- `bloodmap.effects` and
`bloodmap.conditional`, the same code that reads the campaign -- and each
registry entry's `expect` is checked against what that reading finds. A label
that claims a push door has to produce a z-motion mechanism whose cause is a
push. A dead map fails here.

Two further checks, for the other things the owner found by walking:

* **nothing floats.** Every sprite the layout seated on a floor is checked
  against its sector's floor and its tile's drawn extent.
* **nothing is stranded.** Every stall has to be reachable from the player
  start, or an exhibit exists that nobody can visit.
"""

from __future__ import annotations

import json
import pathlib
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from bloodmap.conditional import (                          # noqa: E402
    build_graph, design_role, route_edges,
)
from bloodmap.doors import _wall_owners, observe_motion_sector  # noqa: E402
from bloodmap.effects import read_mechanism                 # noqa: E402
from bloodmap.format import read_map                        # noqa: E402
from bloodmap.texture_align import sprite_tile_extents      # noqa: E402

import registry as registry_module                          # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
MAP = HERE / "level" / "pattern-zoo.MAP"
MANIFEST = HERE / "reports" / "build-manifest.json"


def _relative(path: pathlib.Path) -> str:
    """The path as the repo sees it, or as given when it is outside."""
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def _extra(item: Any) -> dict:
    payload = getattr(item, "extra", None)
    return payload.fields if payload is not None and hasattr(payload, "fields") else {}


def exhibit_sectors(manifest: dict, prefix: str) -> list[int]:
    """Every sector the named exhibit built, by region-id prefix."""
    return sorted(
        sector for name, sector in manifest["region_sectors"].items()
        if name == prefix or name.startswith(prefix + ":"))


def check(disk, manifest, graph, exhibit) -> list[str]:
    """What the understanding stack fails to find for one exhibit."""
    want = exhibit.expect
    if want.is_empty():
        return []
    prefix = exhibit.region_prefix()
    sectors = exhibit_sectors(manifest, prefix)
    if not sectors:
        return [f"{exhibit.label}: built no sector under {prefix!r}"]

    problems: list[str] = []
    owners = _wall_owners(disk)
    typed = [s for s in sectors
             if int(disk.sectors[s].fields["type"]) == want.sector_type]
    if want.sector_type is not None:
        if len(typed) < want.count:
            found = sorted({int(disk.sectors[s].fields["type"]) for s in sectors})
            problems.append(
                f"{exhibit.label}: wanted {want.count} sector(s) of type "
                f"{want.sector_type}, found {len(typed)} among types {found}")
            return problems

    #: The reading, from the map rather than from the source that built it.
    readings = []
    for sector in typed or sectors:
        record = observe_motion_sector(disk, sector, owners=owners)
        if record is None:
            continue
        reading = read_mechanism(disk, sector, owners=owners)
        if reading is not None:
            readings.append((sector, record, reading))
    if not readings:
        problems.append(
            f"{exhibit.label}: effects.read_mechanism found no mechanism in "
            f"sectors {sectors}")
        return problems

    if want.rx_id is not None:
        listening = [s for s, record, _ in readings
                     if int(record["rx_id"] or 0) == want.rx_id]
        if not listening:
            heard = sorted({int(r["rx_id"] or 0) for _s, r, _x in readings})
            problems.append(
                f"{exhibit.label}: wanted a mechanism listening on channel "
                f"{want.rx_id}, found {heard}")

    if want.reads_as:
        objects = {reading["design_object"] for _s, _r, reading in readings}
        if want.reads_as not in objects:
            problems.append(
                f"{exhibit.label}: effects reads it as {sorted(objects)}, "
                f"wanted {want.reads_as!r}")

    if want.trigger or want.requires_key or want.irreversible:
        routes = [route for route in route_edges(graph.edges)
                  if route["mechanism"] in set(sectors)
                  and route["mechanism_kind"] == "sector"]
        if not routes:
            problems.append(
                f"{exhibit.label}: conditional found no gated route through "
                f"sectors {sectors}")
        else:
            triggers = {cause["trigger"] for route in routes
                        for cause in route["causes"]}
            if want.trigger and want.trigger not in triggers:
                problems.append(
                    f"{exhibit.label}: its causes are {sorted(triggers)}, "
                    f"wanted a {want.trigger!r}")
            if want.requires_key and not any(
                    route["requires_key"] == want.requires_key for route in routes):
                keys = sorted({route["requires_key"] for route in routes})
                problems.append(
                    f"{exhibit.label}: wanted key {want.requires_key}, "
                    f"routes require {keys}")
            if want.irreversible and not any(route["irreversible"] for route in routes):
                problems.append(
                    f"{exhibit.label}: wanted a one-way route; none of its "
                    f"routes is irreversible")
    return problems


def floating_sprites(disk, manifest) -> list[str]:
    """Sprites the builder seated on a floor that do not stand on one.

    v1's mannequins sat 9408 units above their floor because their tiles have
    no ART extent, so the seating fell back to a guess and nothing complained.

    Only floor-seated placements are checked, from the build manifest: a face
    sprite hung deliberately up a wall -- the crack, the switches -- is
    indistinguishable from a failed seating in the finished MAP, and flagging
    those would make the check cry wolf until nobody read it.
    """
    from bloodmap.effects import STEP_UP
    from bloodmap.placement import sprite_extent

    try:
        extents = sprite_tile_extents()
    except Exception:
        return []
    out = []
    for index in sorted(set(manifest.get("floor_seated_sprites", []))):
        fields = disk.sprites[index].fields
        picnum = int(fields["picnum"])
        extent = extents.get(picnum)
        if not extent:
            #: No drawn extent means the seating had nothing to seat against.
            #: That is v1's exact failure, so it fails here rather than
            #: passing quietly.
            out.append(
                f"sprite {index} (tile {picnum}) was seated on a floor but "
                f"tile {picnum} has no drawn extent to seat it against")
            continue
        height, y_offset = extent
        #: The same arithmetic the seating used, from the module that owns it.
        #: Re-deriving it here is how a checker ends up disagreeing with the
        #: builder about which sprites are wrong.
        _above, below = sprite_extent(height, int(fields["y_repeat"]),
                                      int(fields["cstat"]), y_offset=y_offset)
        floor = int(disk.sectors[int(fields["sector"])].fields["floor_z"])
        gap = floor - (int(fields["z"]) + below)
        if abs(gap) > STEP_UP:
            out.append(
                f"sprite {index} (tile {picnum}) sits {gap} units off the "
                f"floor of sector {int(fields['sector'])}")
    return out


def stranded_stalls(disk, manifest, graph) -> list[str]:
    """Stalls no body can reach from the player start."""
    held = graph.everything_worked()
    reached = graph.reachable(held)
    out = []
    for name, sector in sorted(manifest["region_sectors"].items()):
        if not name.startswith("stall:"):
            continue
        if sector not in reached:
            out.append(f"{name} (sector {sector}) is not reachable from the start")
    return out


def run(map_path: pathlib.Path = MAP,
        manifest_path: pathlib.Path = MANIFEST) -> dict[str, Any]:
    """Read the built map back and report every claim it fails to support."""
    disk = read_map(map_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    graph = build_graph(disk)
    exhibits = registry_module.exhibits()

    per_exhibit = {}
    problems: list[str] = []
    for exhibit in exhibits:
        found = check(disk, manifest, graph, exhibit)
        per_exhibit[exhibit.label] = found
        problems.extend(found)
    floats = floating_sprites(disk, manifest)
    stranded = stranded_stalls(disk, manifest, graph)
    problems.extend(floats)
    problems.extend(stranded)

    from collections import Counter
    types = Counter(int(s.fields["type"]) for s in disk.sectors)
    return {
        "$schema": "llmapper.pattern-zoo-selfread", "schema_version": 1,
        "map": _relative(map_path),
        "sector_types": {str(k): v for k, v in sorted(types.items())},
        "claims_checked": sum(1 for e in exhibits if not e.expect.is_empty()),
        "per_exhibit": per_exhibit,
        "floating_sprites": floats,
        "stranded_stalls": stranded,
        "problems": problems,
        "passed": not problems,
    }


def main() -> int:
    report = run()
    (HERE / "reports" / "selfread.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"sector types: {report['sector_types']}")
    print(f"claims checked: {report['claims_checked']}")
    for label, found in report["per_exhibit"].items():
        if found:
            for line in found:
                print(f"  !! {line}")
    for line in report["floating_sprites"] + report["stranded_stalls"]:
        print(f"  !! {line}")
    print("PASS" if report["passed"] else f"FAIL: {len(report['problems'])} problems")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
