"""The city's sound, which it did not have.

Found by studying Duke: DukCity carries 22 to 52 MUSICANDSFX emitters per
map, which prompted the same count on the Blood side.  The Blood campaign
runs a **median of 78 ambient sound sprites per map -- 23.6 per hundred
sectors**.  Gravesend had one.  It is the largest single dimension the city
was missing, and nothing in a rendered frame would ever have shown it.

The mechanism, read out of `NBlood/source/blood/src/asound.cpp` rather
than inferred:

* type **710**, "Ambient SFX", goes on **statnum 12** -- `mapedit.cpp`
  moves it there, and `ambProcess` walks `headspritestat[kStatAmbience]`;
* it is invisible (cstat 32896) and shade -128;
* the **sound id is `XSPRITE.data_3`**, not the sprite's `owner` -- `owner`
  is the runtime channel index and is -1 in all 1,778 campaign instances;
* `data_1` and `data_2` are the near and far radius, and `ambInit` skips
  any sprite where **data_1 >= data_2**, so getting them the wrong way
  round silently produces no sound at all;
* `data_4` is the volume: 50 in 1,177 of 1,778;
* `state` must be 1 (1,582 of 1,778).

Sound ids are attested per context from the campaign rooms that are that
context, and checked against what each id IS (`python -m tools.catalog show
sound:<id>`; the counts are in knowledge/blood/studies/ambient-sounds/):
the street keeps E3M1's distant machinery (8), the sewer E3M3's drips (30).
Two were wrong until the sound catalogue named them: "interior" was 32, a
torch's fire, now E1M2's enclosed-room hum (2); "church" was 50, steam, now
E3M4's chapel wind (1). Works moved from wind (18) to E3M6's conveyor hum
(20), and the crypt has E1M1's crypt wind (17).
"""

from __future__ import annotations

AMBIENT_TYPE = 710
AMBIENT_STATNUM = 12
AMBIENT_CSTAT = 32896          # invisible | 128
AMBIENT_SHADE = -128
#: All 1,778 campaign ambient emitters carry this tile.
AMBIENT_TILE = 2521

# See knowledge/blood/studies/ambient-sounds/notes.md for the counts and rooms.
SOUNDS = {
    "street": 8,
    "interior": 2,
    "sewer": 30,
    "church": 1,
    "crypt": 17,
    "fare_turnstile": 21,
    "works": 20,
    "mall": 65,
    "drowned": 37,        # E1M8's swimming: the diver's breath
    "lapping": 40,        # E6M4's, on 24 surfaces: water at a wall
    "wheel": 20,          # the works' machine, heard through water
    "tubes": 25,          # a fluorescent's hum: the underpass
}

# Near radius, far radius and volume from comparable campaign placements.
ENVELOPES = {
    "street": (150, 350, 50),
    "interior": (300, 600, 50),
    "sewer": (100, 300, 50),
    "church": (400, 800, 40),
    "crypt": (200, 500, 50),
    "fare_turnstile": (250, 700, 20),
    "works": (200, 400, 50),
    # the campaign's is (900, 1500), over E4M9's whole mall; the owner,
    # 2026-11-23: "you can hear that shop music from arcades too broad ...
    # it should be enough to have just 150/350"
    "mall": (150, 350, 50),
    "tubes": (75, 150, 50),
    "drowned": (75, 300, 60),
    "lapping": (75, 150, 50),
    "wheel": (150, 350, 40),
}


def fields(context: str, *, near=None, far=None, volume=None) -> dict:
    """The sprite and XSPRITE fields for one ambient emitter."""
    default_near, default_far, default_volume = ENVELOPES[context]
    near = default_near if near is None else int(near)
    far = default_far if far is None else int(far)
    volume = default_volume if volume is None else int(volume)
    if near >= far:
        raise ValueError(
            f"ambient near {near} must be less than far {far}: ambInit "
            f"skips any emitter where data_1 >= data_2, silently")
    return {
        "type": AMBIENT_TYPE, "picnum": AMBIENT_TILE, "status": AMBIENT_STATNUM,
        "cstat": AMBIENT_CSTAT, "shade": AMBIENT_SHADE,
        "x_repeat": 64, "y_repeat": 64,
        "behavior": {"data_1": near, "data_2": far,
                     "data_3": SOUNDS[context], "data_4": volume,
                     "state": 1},
    }


def fill(layout, regions, *, target_per_100_sectors: float = 23.6) -> dict:
    """Put ambience through the city at the campaign's own rate.

    `regions` is a list of (region_id, context, local) -- the caller knows
    which spaces are which, and this does not guess.
    """
    from dressing import _free_point

    report = {"placed": 0, "skipped": 0, "by_context": {}}
    for index, (region_id, context, local) in enumerate(regions):
        region = layout.regions.get(region_id)
        if region is not None and int(region.ceiling_z) >= int(region.floor_z):
            # shut at rest (a blown hole's pieces): no room for a sprite
            report["shut"] = report.get("shut", 0) + 1
            continue
        # A street region is a rectangle with the building masses cut out of
        # it, so a local can land inside a mass.  The same containment test
        # the dressing pass needs.
        if region is not None and _free_point(region, *local) is None:
            found = None
            for u, v in ((0.5, 0.5), (0.15, 0.15), (0.85, 0.15),
                         (0.15, 0.85), (0.85, 0.85), (0.35, 0.5)):
                if _free_point(region, u, v) is not None:
                    found = (u, v)
                    break
            if found is None:
                report["skipped"] += 1
                continue
            local = found
        layout.place_on_floor(
            f"ambience:{context}_{index}", region_id, local=local,
            height_player_heights=0.5, **fields(context))
        report["placed"] += 1
        report["by_context"][context] = report["by_context"].get(context, 0) + 1
    return report
