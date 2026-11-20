"""One sun over a map's open sky: outdoor walls shaded by which way they face, and the measure of it.

The owner, 2026-11-20: "Overall it feels like there is no real direction of
natural light and shadows in the city exterior ... Looks like this might be
a systematic problem." It was. The city's outdoor walls took a flat shade
from their district's style and whatever the street lamps' rays
(`bloodmap.lightbomb`) added; nothing gave the outside one light. Measured
(`measure`, `tools/light_profile.py`):

==========  ====================  =============================
map         outdoor wall shade    wall shade by facing N/E/S/W
            spread (sd)           (median; lower is brighter)
==========  ====================  =============================
E3M1        15.8                  24 / 24 / 34 / 27
E3M2        16.0                  31 / 36 / 35 / 30
E1M1        11.7                  20 / 28 / 24 / 24
E2M1        14.0                  17 / 28 / 28 / 27
E6M1        10.7                   8 / 24 / 12 / 24
the city     5.0                  14 /  9 / 10 /  9 (ground 30)
==========  ====================  =============================

The campaign gives its streets a direction: one or two facings a step of 8
to 16 darker than the rest, and its facades about as dark as its ground. The
city's facades were flat and brighter than the ground it stands on.

`apply` gives a map one sun. Every wall drawn on the street side of an
open-sky sector -- a facade, or the face of a step seen from the street --
first has the outdoor walls' median brought to the ground's (what the lamps
added stays, as an offset), then is shaded by the angle between the way it
faces and the sun: turned to it, up to `LIT` brighter; turned away, up to
`SHADOWED` darker; side on, as it was. Interiors are not touched.
"""

from __future__ import annotations

import math
import statistics
from typing import Any

from .model import record_fields as _fields

#: Where the light comes from, as a map direction (degrees: 0 is +x, east;
#: 90 is +y, south, Build's y running down). South-east: the campaign's
#: darkest facing is most often north (E1M1, E2M1, E6M1).
SUN_AZIMUTH = 45.0
#: shades a wall turned squarely to the sun is brightened, and one turned
#: squarely away is darkened: the campaign's step between its lit and its
#: dark facings is 8 to 16
LIT, SHADOWED = 6, 12
#: where the facades' median sits against the ground's: a little brighter,
#: so a face turned away from the sun is dark, not black (the campaign's
#: darkest facings are about 34; the first build put the city's at 39)
BASE_UNDER_GROUND = 4
#: walls shorter than this are corners and chamfers, not faces
MIN_FACE = 256
SHADE_RANGE = (-128, 63)


def _owners(disk: Any) -> dict[int, int]:
    out = {}
    for index, sector in enumerate(disk.sectors):
        f = _fields(sector)
        for wall in range(int(f["wall_ptr"]), int(f["wall_ptr"]) + int(f["wall_count"])):
            out[wall] = index
    return out


def _open(disk: Any, sector: int) -> bool:
    return bool(int(_fields(disk.sectors[sector])["ceiling_stat"]) & 1)


def outdoor_faces(disk: Any) -> list[tuple[int, float]]:
    """(wall, facing in degrees) for every wall seen from an open-sky sector.

    Build winds a sector's outer loop so its inside is on the right of each
    wall, so the wall faces (-dy, dx) of its run: into the sector it is seen
    from. A two-sided wall counts when the neighbour stands up as a step or
    hangs down as a lintel, i.e. when the street sees some of it.
    """
    owners = _owners(disk)
    out = []
    for index, wall in enumerate(disk.walls):
        f = _fields(wall)
        here = owners.get(index)
        if here is None or not _open(disk, here):
            continue
        other = int(f["next_sector"])
        if other >= 0:
            mine, theirs = _fields(disk.sectors[here]), _fields(disk.sectors[other])
            step = int(theirs["floor_z"]) < int(mine["floor_z"])
            lintel = (not int(theirs["ceiling_stat"]) & 1
                      and int(theirs["ceiling_z"]) > int(mine["ceiling_z"]))
            if not (step or lintel):
                continue
        n = _fields(disk.walls[int(f["point2"])])
        dx, dy = int(n["x"]) - int(f["x"]), int(n["y"]) - int(f["y"])
        if math.hypot(dx, dy) < MIN_FACE:
            continue
        out.append((index, math.degrees(math.atan2(dx, -dy)) % 360))
    return out


def _quarter(angle: float) -> str:
    return "ESWN"[int(((angle + 45) % 360) // 90)]


def measure(disk: Any) -> dict[str, Any]:
    """The outdoor light of a map, in the campaign's terms."""
    faces = outdoor_faces(disk)
    shades = {index: int(_fields(disk.walls[index])["shade"]) for index, _ in faces}
    by = {q: [] for q in "NESW"}
    for index, angle in faces:
        by[_quarter(angle)].append(shades[index])
    grounds = [int(_fields(s)["floor_shade"]) for i, s in enumerate(disk.sectors)
               if _open(disk, i)]
    medians = {q: (statistics.median(v) if v else None) for q, v in by.items()}
    known = [m for m in medians.values() if m is not None]
    values = list(shades.values())
    return {
        "walls": len(values),
        "wall_sd": round(statistics.pstdev(values), 1) if len(values) > 1 else 0.0,
        "wall_median": statistics.median(values) if values else None,
        "by_facing": medians,
        "facing_step": (max(known) - min(known)) if known else 0,
        "ground_median": statistics.median(grounds) if grounds else None,
        "ground_sd": round(statistics.pstdev(grounds), 1) if len(grounds) > 1 else 0.0,
    }


def apply(disk: Any, *, azimuth: float = SUN_AZIMUTH, lit: int = LIT,
          shadowed: int = SHADOWED, base: int | None = None) -> dict[str, Any]:
    """Shade every outdoor wall by one sun. Returns the light before and after.

    `base` is where the outdoor walls' median goes before the sun is applied;
    by default a little brighter than the map's own outdoor ground median
    (`BASE_UNDER_GROUND`), so a facade stands about as dark as the street it
    stands on, as the campaign's do.
    """
    before = measure(disk)
    faces = outdoor_faces(disk)
    if not faces:
        return {"before": before, "after": before, "walls": 0}
    target = (before["ground_median"] - BASE_UNDER_GROUND
              if base is None and before["ground_median"] is not None else base)
    shift = 0 if target is None else int(round(target - before["wall_median"]))
    sun = math.radians(azimuth)
    for index, angle in faces:
        f = _fields(disk.walls[index])
        facing = math.cos(math.radians(angle) - sun)
        offset = -lit * max(0.0, facing) + shadowed * max(0.0, -facing)
        value = int(f["shade"]) + shift + int(round(offset))
        f["shade"] = max(SHADE_RANGE[0], min(SHADE_RANGE[1], value))
    return {"before": before, "after": measure(disk), "walls": len(faces),
            "azimuth": azimuth, "shift": shift}
