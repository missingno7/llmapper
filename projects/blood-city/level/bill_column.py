"""The bill column in the Aldermack's square: the playhouse's own, a plastered drum on a step, pasted with what is on.

The plan has had a "kiosk" there since it was drawn, a free-standing mass a unit
and a half wide, and nobody built it: the street's hole stood as a tower of
brick to the sky. A theatre's square keeps a column for its bills. Two steps, a
drum two and a half bodies tall with a smaller crown on it, seen over; the
bills are the house's, one a face and no two beside each other alike.
"""

from __future__ import annotations

import math

from bloodmap import arrangement as A

PU = 1024
KEY = "region:gravesend/theatre_row/bill_column"
AT = (29.0, 13.0)
GRADE, SKY_Z, SKY = 8192, -188416, 3491
STEP, DRUM, CROWN = 2048, 40960, 47104                   # over the street: the kerb, the drum, the crown on it
DRUM_R, CROWN_R = 0.55, 0.4
STONE, ROOF, PLASTER, TIMBER = 253, 67, 379, 28
#: round the drum from the south, a face an eighth of a turn, two bills a face: (tile, repeat, how far up the drum in bodies)
BILLS = (((440, 32, 0.75), (453, 38, 1.4)), ((981, 19, 0.7), (356, 32, 1.35)), ((453, 38, 0.8), (932, 19, 1.4)),
         ((356, 32, 0.75), (440, 32, 1.4)), ((932, 19, 0.7), (453, 38, 1.3)), ((440, 32, 0.8), (981, 19, 1.4)),
         ((453, 38, 0.75), (356, 32, 1.45)), ((981, 19, 0.75), (440, 32, 1.35)))


def _q(v: float) -> int:
    return round(v * PU)


def build(layout) -> dict[str, str]:
    """Stand the column in the square's hole and join its step to the street."""
    from shapely import Point, Polygon
    centre = (_q(AT[0]), _q(AT[1]))
    street, hole = next((r, h) for r in layout.regions.values() if r.parallax_ceiling and r.floor_z == GRADE for h in r.holes
                        if Polygon(h).contains(Point(centre)) and Polygon(h).area < (2 * PU) ** 2)
    place = A.Arrangement()
    place.add("step", [tuple(int(v) for v in p) for p in hole])
    place.add("drum", A.circle(centre, _q(DRUM_R), 8, 1 / 16))
    place.add("crown", A.circle(centre, _q(CROWN_R), 8, 1 / 16))
    cells = place.resolve()
    rise = {"step": STEP, "drum": DRUM, "crown": CROWN}

    def surface(name):
        return dict(floor_z=GRADE - rise[name], ceiling_z=SKY_Z, floor_picnum=STONE if name == "step" else ROOF,
                    wall_picnum=STONE if name == "step" else PLASTER, ceiling_picnum=SKY, parallax_ceiling=True, layer="street",
                    floor_shade=12, wall_shade=14, ceiling_shade=0, role="detail", declared_zero_exit=True,
                    intent={"kind": "furnished"})

    def face(_seen, beyond, _a, _b):
        return {"picnum": {"drum": PLASTER, "crown": TIMBER}[beyond]} if beyond in ("drum", "crown") else {}

    regions = A.lay(layout, KEY, cells, surface, face)
    for name, a, b in A.rim(cells):
        if name == "step":
            layout.add_connection(f"connection:bill_column:{a[0]}:{a[1]}", street.region_id, regions[name], a1=b, a2=a,
                                  min_width=1, min_opening=0)
    flat = DRUM_R * math.cos(math.pi / 8) * PU + 3
    for k, pair in enumerate(BILLS):
        turn = math.pi / 2 + k * math.pi / 4
        for n, (tile, size, up) in enumerate(pair):
            layout.add_sprite(f"bill_column:bill_{k}_{n}", regions["step"], x=round(centre[0] + flat * math.cos(turn)),
                              y=round(centre[1] + flat * math.sin(turn)), z=GRADE - STEP - round(up * 16960), picnum=tile,
                              x_repeat=size, y_repeat=size, angle=round(turn * 1024 / math.pi) & 2047, cstat=16 | 64 | 128, shade=6)
    return regions
