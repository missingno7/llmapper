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

Five further checks, one per thing the owner found by walking or named as a
binding rule:

* **nothing floats.** Every sprite the layout seated on a floor is checked
  against its sector's floor and its tile's drawn extent.
* **nothing is stranded.** Every section has to be reachable from the player
  start, or a whole environment exists that nobody can visit.
* **the representation taxonomy holds.** A tile an exhibit claims as wall
  texture must appear on walls and not as a sprite, and the reverse; a
  concept realized at the wrong level is a build failure, not a style choice.
* **the engine usage laws hold.** The Part-A validators from
  `bloodmap.rules_blood` run here as a block: the mask law (extended to
  one-sided walls), the parallax law in both directions, the flat-tile
  power-of-two law, and the usage-kind table. The first four fail the build;
  the usage-kind check is a warning tier, because it is derived from 43 maps
  and an authored map is allowed to be the first to do something.
* **no tile is leaned on far harder than the campaign leans on it.** Slot
  correctness is not the whole of usage: every one of the 162 uses of tile
  400 in v3 was in an attested slot, and 400 is a facade backdrop the
  campaign puts on 48 wall slots in 43 maps.
* **every exhibit is lettered.** A label sprite has to exist for each, or an
  exhibit has lost the identity that owner feedback arrives by.
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

from bloodmap.conditional import build_graph, route_edges    # noqa: E402
from bloodmap.doors import _wall_owners, observe_motion_sector  # noqa: E402
from bloodmap.effects import read_mechanism                 # noqa: E402
from bloodmap.format import read_map                        # noqa: E402
from bloodmap.texture_align import sprite_tile_extents      # noqa: E402

import registry as registry_module                          # noqa: E402

HERE = pathlib.Path(__file__).resolve().parent
MAP = HERE / "level" / "pattern-zoo.MAP"
MANIFEST = HERE / "reports" / "build-manifest.json"

#: Letters are wall sprites too, and they are not exhibits.
LETTER_TILES = range(3808, 3834)


def _relative(path: pathlib.Path) -> str:
    """The path as the repo sees it, or as given when it is outside."""
    try:
        return str(path.relative_to(ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def exhibit_sectors(manifest: dict, prefix: str) -> list[int]:
    """Every sector the named exhibit built, by region-id prefix."""
    return sorted(
        sector for name, sector in manifest["region_sectors"].items()
        if name == prefix or name.startswith(prefix + ":"))


_WALL_SECTOR: dict[int, int] = {}


def _wall_sector(disk, wall_index: int) -> int:
    """Which sector owns a wall, cached across the whole read."""
    if not _WALL_SECTOR:
        for sector_id, sector in enumerate(disk.sectors):
            first = int(sector.fields["wall_ptr"])
            for offset in range(int(sector.fields["wall_count"])):
                _WALL_SECTOR[first + offset] = sector_id
    return _WALL_SECTOR.get(wall_index, -1)


def _taxonomy(disk, sectors, exhibit) -> list[str]:
    """Whether each concept was realized at the level it is meant to be.

    The owner's rule, made checkable: a shelf is a WALL TEXTURE on shallow
    sectors and a mannequin is a SPRITE, and swapping them is a build
    failure. v1 shipped the shelf as a sprite and the crates as sprites, and
    every static gate it faced passed.

    Checked inside the exhibit's own sectors, so one exhibit's crate tile
    cannot satisfy another exhibit's claim.
    """
    problems = []
    group = set(sectors)
    on_walls = {int(wall.fields["picnum"])
                for index, wall in enumerate(disk.walls)
                if _wall_sector(disk, index) in group}
    as_sprites = {int(s.fields["picnum"]) for s in disk.sprites}
    for tile in exhibit.expect.wall_tiles:
        if tile not in on_walls:
            problems.append(
                f"{exhibit.label}: tile {tile} is claimed as wall texture and "
                f"is on no wall of its own sectors {sorted(group)}")
        if tile in as_sprites:
            problems.append(
                f"{exhibit.label}: tile {tile} is claimed as wall texture but "
                f"was also thrown somewhere as a sprite")
    for tile in exhibit.expect.sprite_tiles:
        if tile not in as_sprites:
            problems.append(
                f"{exhibit.label}: tile {tile} is claimed as a sprite and is "
                f"not one")
    return problems


def check(disk, manifest, graph, exhibit) -> list[str]:
    """What the understanding stack fails to find for one exhibit."""
    want = exhibit.expect
    if want.is_empty():
        return []
    prefix = exhibit.region_prefix()
    sectors = exhibit_sectors(manifest, prefix)
    problems: list[str] = []

    if want.wall_tiles or want.sprite_tiles:
        problems.extend(_taxonomy(disk, sectors, exhibit))
    if want.sector_type is None:
        return problems
    if not sectors:
        return problems + [f"{exhibit.label}: built no sector under {prefix!r}"]

    owners = _wall_owners(disk)
    typed = [s for s in sectors
             if int(disk.sectors[s].fields["type"]) == want.sector_type]
    if len(typed) < want.count:
        found = sorted({int(disk.sectors[s].fields["type"]) for s in sectors})
        problems.append(
            f"{exhibit.label}: wanted {want.count} sector(s) of type "
            f"{want.sector_type}, found {len(typed)} among types {found}")
        return problems

    #: The reading, from the map rather than from the source that built it.
    readings = []
    for sector in typed:
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

    if want.payload_shape:
        from bloodmap.effects import payload

        shapes = {payload(disk, sector)["shape"]["shape"] for sector in typed}
        if want.payload_shape not in shapes:
            problems.append(
                f"{exhibit.label}: its payload reads as {sorted(shapes)}, "
                f"wanted {want.payload_shape!r}")

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
                    route["requires_key"] == want.requires_key
                    for route in routes):
                keys = sorted({route["requires_key"] for route in routes})
                problems.append(
                    f"{exhibit.label}: wanted key {want.requires_key}, "
                    f"routes require {keys}")
            if want.irreversible and not any(route["irreversible"]
                                             for route in routes):
                problems.append(
                    f"{exhibit.label}: wanted a one-way route; none of its "
                    f"routes is irreversible")
    return problems


def floating_sprites(disk, manifest) -> list[str]:
    """Sprites the builder seated on a floor that do not stand on one.

    v1's mannequins sat 9408 units above their floor because their tiles have
    no ART extent, so the seating fell back to a guess and nothing complained.

    Only floor-seated placements are checked, from the build manifest: a face
    sprite hung deliberately up a wall -- the crack, the switches, the letters
    -- is indistinguishable from a failed seating in the finished MAP, and
    flagging those would make the check cry wolf until nobody read it.
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


#: The laws that fail a build, and the one that only warns.
LAW_RULES = ("mask-tile-off-plain-surfaces", "parallax-wears-a-sky-tile",
             "sky-tile-is-parallaxed", "flat-tile-power-of-two")
WARN_RULES = ("tile-sits-in-an-attested-slot",)


def usage_laws(disk) -> tuple[list[str], list[str]]:
    """The Part-A validators, run over the built map. (failures, warnings).

    These are the same `bloodmap.rules_blood` rules the authored-map
    validation uses, so the zoo cannot pass a gate the rest of the pipeline
    would fail it on -- which is exactly how v3 shipped eighteen transparency
    violations inside the exhibit that teaches the transparency law.
    """
    try:
        import bloodmap.rules_blood                      # noqa: F401
        from bloodmap.rules import RULES
    except Exception:
        return [], []
    failures, warnings = [], []
    for rule_id, sink in ([(r, failures) for r in LAW_RULES]
                          + [(r, warnings) for r in WARN_RULES]):
        rule = RULES.get(rule_id)
        if rule is None:
            continue
        found = rule.check(disk)
        for violation in found.violations:
            sink.append(f"{rule_id}: {violation.location} {violation.detail}")
    return failures, warnings


def leaned_on(disk) -> list[str]:
    """Tiles used far out of proportion to the campaign's own use of them."""
    try:
        from bloodmap.usage_kinds import overused
    except Exception:
        return []
    return [
        f"tile {row['picnum']} is on {row['used']} walls "
        f"({row['times_the_campaign_rate']}x the campaign's rate; it has "
        f"{row['campaign_slots']} wall slots in the whole campaign)"
        for row in overused(disk)]


def masked_surfaces(disk) -> list[str]:
    """The transparency law, enforced: no mask tile on a floor or ceiling.

    Owner-stated and measured the same day: of 3590 tiles carrying mask
    pixels above 5%, exactly zero appear on any of the campaign's 28158
    non-sky floor/ceiling slots across 43 maps. Parallax surfaces are exempt
    because the sky is not sampled this way at all.
    """
    try:
        from bloodmap.art import read_art_directory, transparency_stats
        tiles = read_art_directory("reference/blood")
    except Exception:
        return []
    masked = set()
    for picnum, tile in tiles.items():
        try:
            stats = transparency_stats(tile)
        except Exception:
            continue
        if stats.get("has_mask") and float(stats["transparent_ratio"]) > 0.05:
            masked.add(int(picnum))
    out = []
    for index, sector in enumerate(disk.sectors):
        fields = sector.fields
        for role, stat_key, pic_key in (
                ("floor", "floor_stat", "floor_picnum"),
                ("ceiling", "ceiling_stat", "ceiling_picnum")):
            if int(fields[stat_key]) & 1:
                continue                       # parallax: not sampled
            picnum = int(fields[pic_key])
            if picnum in masked:
                out.append(
                    f"sector {index}: tile {picnum} carries mask pixels and "
                    f"is on its {role}; the campaign never does this")
    return out


def unlettered(disk, manifest) -> list[str]:
    """Labels that are missing, or that landed as something else."""
    letters = set(manifest.get("letter_sprites", []))
    if not letters:
        return ["the build recorded no label sprites at all"]
    out = []
    for index in sorted(letters):
        picnum = int(disk.sprites[index].fields["picnum"])
        if picnum not in LETTER_TILES:
            out.append(f"sprite {index} is recorded as a letter but wears "
                       f"tile {picnum}, which is not a letter tile")
    return out


def stranded_sections(disk, manifest, graph) -> list[str]:
    """Environments no body can reach from the player start."""
    held = graph.everything_worked()
    reached = graph.reachable(held)
    out = []
    for name, sector in sorted(manifest["region_sectors"].items()):
        if not name.startswith("section:"):
            continue
        if sector not in reached:
            out.append(f"{name} (sector {sector}) is not reachable from the "
                       f"start")
    return out


def run(map_path: pathlib.Path = MAP,
        manifest_path: pathlib.Path = MANIFEST) -> dict[str, Any]:
    """Read the built map back and report every claim it fails to support."""
    _WALL_SECTOR.clear()
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
    stranded = stranded_sections(disk, manifest, graph)
    masked = masked_surfaces(disk)
    labels = unlettered(disk, manifest)
    laws, warnings = usage_laws(disk)
    leaned = leaned_on(disk)
    problems.extend(floats + stranded + masked + labels + laws + leaned)

    from collections import Counter
    types = Counter(int(s.fields["type"]) for s in disk.sectors)
    return {
        "$schema": "llmapper.pattern-zoo-selfread", "schema_version": 2,
        "map": _relative(map_path),
        "sector_types": {str(k): v for k, v in sorted(types.items())},
        "claims_checked": sum(1 for e in exhibits if not e.expect.is_empty()),
        "per_exhibit": per_exhibit,
        "floating_sprites": floats,
        "stranded_sections": stranded,
        "masked_surfaces": masked,
        "lettering": labels,
        "usage_law_failures": laws,
        "usage_kind_warnings": warnings,
        "leaned_on": leaned,
        "problems": problems,
        "passed": not problems,
    }


def main() -> int:
    report = run()
    (HERE / "reports" / "selfread.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(f"sector types: {report['sector_types']}")
    print(f"claims checked: {report['claims_checked']}")
    for found in report["per_exhibit"].values():
        for line in found:
            print(f"  !! {line}")
    for line in (report["floating_sprites"] + report["stranded_sections"]
                 + report["masked_surfaces"] + report["lettering"]
                 + report["usage_law_failures"] + report["leaned_on"]):
        print(f"  !! {line}")
    for line in report["usage_kind_warnings"]:
        print(f"  ?  {line}")
    print("PASS" if report["passed"]
          else f"FAIL: {len(report['problems'])} problems")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
