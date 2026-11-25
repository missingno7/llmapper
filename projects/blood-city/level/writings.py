"""What has been written on the walls in blood, a hand's height over the floor and never twice in one place.

The owner, 2026-11-25: "On some places I think we can use decorative blood writings like
826, 1105,2345". Blood does it rarely: 826 (STAY OUT) seven times in six maps, 1105 (SLOTH)
and 2345 (ONE EYED MONKS RULE) once each, at 64 by 64, shade -8 or so, its middle about a
body up, and all but one of them indoors. So each stands by the thing it is about.
"""

from __future__ import annotations

PU = 1024
STAY_OUT, SLOTH, MONKS = 826, 1105, 2345
#: name, tile, the point its room is found by (plan units, floor), the wall as one faces it (left end, right end), where along
#: it, how high its middle is in bodies, what it is about
WRITINGS = (
    ("hangman", STAY_OUT, (9.0, 34.4, -32768), ((8.0, 34.95), (8.0, 33.85)), 0.5, 0.95, "beside the hangman's door, which somebody did not"),
    ("plague", STAY_OUT, (22.6, 20.42, 61440), ((24.38, 20.5), (21.02, 20.5)), 0.25, 0.9, "on the sewer walk, before the bricked-up pit"),
    ("saloon", SLOTH, (5.5, 7.0, 8192), ((4.0, 6.0), (7.0, 6.0)), 0.87, 0.95, "in the saloon's back room"),
    ("eye", MONKS, (51.4, 45.6, 8192), ((52.5, 46.5), (50.75, 46.5)), 0.5, 0.9, "in the passage behind the eye's door"),
)
#: the saloon's is squeezed in beside a picture
SIZE = {"saloon": 50}
#: along the gallows stair, over more than one step of it
STAIR = (8.0, 28.75, 4, 15200)


def build(layout) -> list[str]:
    """Write them, where the wall has room; returns what was written."""
    from shapely import Point, Polygon
    import gallows
    import wallplane
    done = []
    for name, tile, (x, y, floor), (a, b), t, high, _about in WRITINGS:
        at = Point(x * PU, y * PU)
        region = next((r for r in layout.regions.values() if int(r.floor_z) == floor and Polygon(r.outer, r.holes).contains(at)), None)
        if region is None:
            continue
        placed = wallplane.sprite(layout, f"writing:{name}", region.region_id, tuple(round(v * PU) for v in a), tuple(round(v * PU) for v in b),
                                  tile=tile, x_repeat=SIZE.get(name, 64), y_repeat=SIZE.get(name, 64), cstat=16 | 64 | 128, t=t, height_player_heights=high,
                                  offset_player_widths=0.03, shade=-8)
        if placed:
            done.append(name)
    x, y, step, up = STAIR
    region = layout.regions[f"{gallows.KEY}:step_{step}"]
    layout.add_sprite("writing:stair", region.region_id, x=round(x * PU) + 10, y=round(y * PU), z=region.floor_z - up, picnum=MONKS,
                      x_repeat=64, y_repeat=64, angle=0, cstat=16 | 64 | 128, shade=-4, type=0, status=0)
    return [*done, "stair"]
