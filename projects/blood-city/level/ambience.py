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

Sound ids are attested per context from the maps that are that context:
E3M3, Blood's sewer, runs sound **30** (21 of its 41 emitters); E3M1's
town runs **8** (22 of 35); E1M5's church runs **50** and **32**.
"""

from __future__ import annotations

AMBIENT_TYPE = 710
AMBIENT_STATNUM = 12
AMBIENT_CSTAT = 32896          # invisible | 128
AMBIENT_SHADE = -128
#: All 1,778 campaign ambient emitters carry this tile.
AMBIENT_TILE = 2521

#: (near, far, volume) -- the campaign's modal envelope.
NEAR, FAR, VOLUME = 100, 300, 50

#: sound id by context, each taken from the campaign map that IS that
#: context.  Named for what it is for, not for what it sounds like.
SOUNDS = {
    "street": 8,        # E3M1's town, 22 of its 35 emitters
    "interior": 32,     # common across E3M1, E1M1 and E1M5
    "sewer": 30,        # E3M3, 21 of its 41
    "church": 50,       # E1M5
    "works": 18,        # E3M1 and E1M5 both use it in machine spaces
    "mall": 65,         # E4M9, the campaign's shopping mall and the
                        # corpus's heaviest user of this sound (5 of 11)        # E3M1 and E1M5 both use it in machine spaces
}


def fields(context: str, *, near=NEAR, far=FAR, volume=VOLUME) -> dict:
    """The sprite and XSPRITE fields for one ambient emitter."""
    if near >= far:
        raise ValueError(
            f"ambient near {near} must be less than far {far}: ambInit "
            f"skips any emitter where data_1 >= data_2, silently")
    return {
        "type": AMBIENT_TYPE, "picnum": AMBIENT_TILE, "status": AMBIENT_STATNUM,
        "cstat": AMBIENT_CSTAT, "shade": AMBIENT_SHADE,
        "x_repeat": 64, "y_repeat": 64,
        "behavior": {"data_1": int(near), "data_2": int(far),
                     "data_3": int(SOUNDS[context]), "data_4": int(volume),
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
