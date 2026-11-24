"""What stands on the counters, hangs on the walls and is posted in the street.

The owner, 2026-11-18: "try using more variety of assets, check other blood
city maps like DWE3M1, E3M1, etc. what they are using for decorations. Looks
like you have quite limited set now."

It was: 38 distinct decoration tiles against E3M1's 61, E1M4's 104 and
DWE3M1's 142 (`tools/mine_city_assets.py`). And two blind reviewers had said
the same thing from the other side: "the pawn's goods say 'boutique', not
'pawn'", "the mall units sell nothing".

Every tile here is used by at least two of Blood's own town maps, and is set
down the way they set it down: `references/city-assets.json` holds, for each
tile, the repeats, cstat, shade, palette, type and status the mappers gave
it and how far over the floor it sits. What a tile IS was read off its
picture (`references/city-assets.png`); the owner's sheet is still the
authority, and the tiles used here that the owner has not named are listed
by `unnamed()` for the next one.

The plan is by PLACE, because a thing means something only where it is: a
bottle on a bar, a jar in a grocer's window, a show bill beside a theatre
door. Nothing is scattered.
"""

from __future__ import annotations

import json
import pathlib

_REF = pathlib.Path(__file__).resolve().parents[1] / "references"
with (_REF / "city-assets.json").open(encoding="utf-8") as _handle:
    ASSETS = {int(k): v for k, v in json.load(_handle)["tiles"].items()}

#: The owner's "wall clock" (1165). The census leaves it out because in the
#: town maps it is never plain decoration: all five are SWITCHES (type 20 or
#: 21) wearing a clock face, wall-aligned at cstat 464, repeats 32 to 80.
#: Hung here untyped, at the commonest size.
ASSETS[1165] = {"count": 5, "maps": {"E3M2": 1, "E1M2": 1, "E6M1": 1, "DWE3M1": 2},
                "where": {"in": 5}, "align": "wall", "x_repeat": 40,
                "y_repeat": 40, "cstat": 464, "shade": 0, "pal": 0, "type": 0,
                "status": 0, "over_floor_bodies": 1.5}

#: What each tile is, read off its picture. A reading, not a measurement,
#: and held to the owner's name and the library's reading by
#: `tests/test_goods_names.py`: 2937 stood here as "roast" and is the owner's
#: "dead cultist"; two of them lay in the grocer's windows.
NAMES = {
    759: "bottle", 605: "brown bottle", 606: "blue bottle", 574: "drinking glass",
    521: "wine glass", 758: "chair", 649: "round table", 1009: "potted plant",
    1010: "plant in a barrel planter", 1013: "vase of dried flowers", 616: "jug",
    834: "glass jar", 938: "candle", 536: "small statue", 739: "clay vase",
    712: "clay jug", 520: "skull goblet", 2304: "pan",
    2305: "frying pan, turned", 604: "keg", 802: "jar with a green label", 517: "red flask",
    741: "sign: Cask of Amontillado Pub & Grille",
    740: "sign: Pickman's Rare Books and Maps", 943: "sign: TICKETS",
    751: "sign: MANAGER", 440: "bill: Tonight, monkey wrestling",
    453: "bill: Possum Gallo", 356: "bill: Jo-Jo book signing",
    981: "bill: Jo-Jo the idiot circus boy", 932: "bill: Sloth",
    742: "notice", 744: "warning plate", 743: "newspaper",
    613: "still life", 163: "painting", 621: "portrait of a ghoul",
    268: "snake panel", 614: "tapestry", 644: "painted map",
    1712: "shovel", 1710: "broom", 2139: "cleaver", 1708: "pliers",
    658: "fire extinguisher", 540: "dead tree", 543: "dead tree",
    545: "dead tree", 608: "dry bush", 3540: "metal can",
    579: "iron bowl", 845: "banner, lion", 848: "banner, ram",
    1165: "wall clock", 73: "hanging clothes",
}

#: The pub sign hangs at repeat 136 in the town maps, 4,352 units wide: a
#: frontage of its own. The saloon has 2,816 beside its door.
_REPEATS = {741: (80, 80),
            #: the chair: DWE3M1 draws it as a voxel at 24; the campaign's
            #: four (E3M1, E3M2, E6M1) at 40 to 48
            758: (40, 40)}

#: How a thing may be set down, from how the town maps set it down and from
#: what the renderer draws (`bloodmap.placement.drawn_extent`). The owner,
#: walking the build of 2026-11-17: "sometimes you are placing sprites
#: partially under ground or into space where they don't fit, also
#: sometimes you are using statues on weird places."
BODY = 16960
#: a thing whose z in the town maps is this far over where it would STAND
#: does not stand: it hangs (a pan on a rack, 1.0 body up)
HANGS = 0.3
#: the room a face sprite needs each side, as a share of its half width;
#: `tools/sprite_fit.py`: under it are 1% to 6% of a town map's sprites
ROOM = 0.5
#: A statue (536) stands on a floor by a wall, or in a niche with a body of
#: air over its head: E3M1 twice, E1M2 once, and nowhere on a counter or a
#: shop shelf. Things that only go on a room's own floor:
FLOOR_ONLY = {536, 758, 649, 1009, 1010}

#: A few tiles whose commonest cstat in the census is an oddity of one map.
_CSTAT = {834: 385, 517: 385}


def fields(tile: int) -> dict:
    """The fields Blood's town maps give this tile."""
    row = ASSETS[int(tile)]
    return {"picnum": int(tile), "cstat": _CSTAT.get(int(tile), int(row["cstat"])),
            "x_repeat": _REPEATS.get(int(tile), (int(row["x_repeat"]),))[0],
            "y_repeat": _REPEATS.get(int(tile), (0, int(row["y_repeat"])))[1],
            "shade": int(row["shade"]), "pal": int(row["pal"]),
            "type": int(row["type"]), "status": int(row["status"])}


# ---------------------------------------------------------------------------
# the plan
# ---------------------------------------------------------------------------

#: Things standing ON something that is already geometry: (path suffix of
#: the region, [(tile, u, v)]). u and v are fractions of the region's box.
ON_TOP = [
    # the saloon: a bar is bottles and glasses
    # (one bar now, end to end: clusters along it, as E3M1's bars carry
    # theirs -- two or three things, then bare wood)
    ("saloon/main/fittings/main_bar/main_bar_0", [
        (759, 0.06, 0.5), (574, 0.11, 0.45), (605, 0.30, 0.5), (521, 0.35, 0.55),
        (606, 0.55, 0.5), (759, 0.60, 0.45), (574, 0.81, 0.5), (616, 0.92, 0.5)]),
    ("saloon/main/fittings/main_table_0", [(759, 0.4, 0.45), (574, 0.65, 0.6)]),
    ("saloon/main/fittings/main_table_1", [(605, 0.55, 0.4), (521, 0.4, 0.65)]),
    # the pawnbroker's window: what people pledge
    ("pawn_shop/pawn_display", [(739, 0.08, 0.5), (616, 0.22, 0.5),
                                (520, 0.36, 0.5), (574, 0.50, 0.5),
                                (938, 0.64, 0.5), (712, 0.78, 0.5),
                                (604, 0.92, 0.5)]),
    ("pawn_shop/vault", [(712, 0.25, 0.3), (938, 0.75, 0.3)]),
    # PROVISIONS: a grocer's windows
    ("market_hall/display_n", [(616, 0.5, 0.12), (834, 0.5, 0.30), (759, 0.5, 0.45),
                               (802, 0.5, 0.62), (616, 0.5, 0.78), (604, 0.5, 0.92)]),
    ("market_hall/display_s", [(834, 0.5, 0.3), (802, 0.5, 0.7)]),
    ("market_hall/display_side", [(604, 0.08, 0.5), (759, 0.22, 0.5), (605, 0.40, 0.5),
                                  (834, 0.60, 0.5), (616, 0.76, 0.5), (802, 0.92, 0.5)]),
    # the market hall's counter: what is sold with the meat (the meat itself
    # is `meat_market.dress`'s)
    ("meat_fittings/meat_counter", [(802, 0.2, 0.75), (604, 0.5, 0.3), (834, 0.78, 0.75)]),
    # the canteen, and the altar
    # (RAT DOGS' counter is a bar run now; the rats and the cleaver hold its
    # middle, so the stock stands at its ends)
    ("canteen/main/canteen_counter/canteen_counter_0", [(802, 0.5, 0.12), (604, 0.5, 0.9)]),
    ("st_gallows/altar_mensa", [(938, 0.25, 0.5), (938, 0.75, 0.5)]),
]

#: A ROW of stock along a shelf let into a wall (`fixtures.shelf_niche`):
#: (path suffix, the tiles in order, repeated to fill it). The town maps'
#: stocked shelves hold a thing every third of a player width: E1M2 213 five
#: in 1.25, E3M2 87 five in 1.5, E1M4 298 nine in 3.0 (`tools/
#: mine_stands.py`, `references/town-fixtures.png`).
ROW_PITCH = 340
ROWS = [
    ("saloon/main/shelf", [759, 605, 606, 759, 574, 605]),
    #: RAT DOGS' kitchen shelf: the cook's jars and jugs
    ("canteen/main/shelf", [834, 616, 802, 712]),
    #: and its freezer's: kegs and jars kept cold
    ("canteen/back/shelf", [604, 802, 604, 834]),
    #: the pawnbroker: what people pledged, out of reach behind the counter
    ("pawn_shop/shop/shelf", [739, 616, 520, 574, 938]),
]
#: a shelf with one tile in its list holds one thing at each end, not a row

#: Things standing on a room's own floor, hard by a wall or a corner:
#: (path suffix, [(tile, u, v)]).
ON_FLOOR = [
    #: a plant in the corner, and a chair at each card table: E3M1's and
    #: E6M1's rooms have them and a reviewer said so ("no chairs or stools
    #: anywhere")
    #: (one at each table, on its open side. Two more stood in the gap
    #: between the tables and read as "chairs clipping into tables".)
    ("saloon/main", [(1009, 0.95, 0.06), (758, 0.333, 0.47), (758, 0.667, 0.47)]),
    ("st_gallows/chancel", [(536, 0.1, 0.5)]),
]

#: Things hung on a room's wall: (path suffix, face, tile, t, height in
#: bodies or None for the census height).
ON_WALL = [
    ("saloon/main", "west", 613, 0.5, None),
    ("saloon/back", "north", 163, 0.5, None),
    ("saloon/back", "east", 621, 0.5, None),
    ("pawn_shop/shop", "west", 268, 0.5, None),
    ("gravesend_arcade/service", "south", 1710, 0.3, None),
    #: (the arcade's service extinguisher is wired now: `l3_mall`)
    ("st_gallows/narthex", "north", 845, 0.5, 1.7),
    ("st_gallows/chancel", "west", 848, 0.82, 1.9),
    ("st_gallows/west_aisle", "west", 614, 0.5, None),
]

#: On a street's wall: (district, world segment, tile, t, height or None).
#: A segment is ordered so the street lies on the side `wallplane` hangs a
#: sprite on. Positions are stated in world units because a facade is where
#: it is; each is beside the door or the front it belongs to.
ON_STREET = [
    # over the saloon's door, and a bill beside it
    ("theatre_row", ((7424, 15360), (10240, 15360)), 741, 0.5, 2.0),
    ("theatre_row", ((3584, 15360), (5888, 15360)), 981, 0.5, None),
    # the Aldermack: tonight's bills either side of its forecourt
    ("theatre_row", ((19456, 15360), (26112, 15360)), 440, 0.25, None),
    ("theatre_row", ((19456, 15360), (26112, 15360)), 453, 0.60, None),
    ("theatre_row", ((14592, 15360), (19200, 15360)), 932, 0.5, 1.6),
    # notices and papers where people pass
    ("theatre_row", ((11264, 15360), (16384, 15360)), 742, 0.75, None),
    ("old_crossing", ((14336, 21504), (4096, 21504)), 743, 0.3, None),
    ("old_crossing", ((14336, 21504), (4096, 21504)), 742, 0.6, None),
    ("market_slip", ((15360, 51200), (15360, 49152)), 744, 0.5, None),
    ("foundry_ward", ((39936, 22528), (39936, 30720)), 356, 0.4, None),
    ("foundry_ward", ((39936, 22528), (39936, 30720)), 743, 0.7, None),
]

#: Standing in a street or a yard: (region key, world x, world y, tile).
#: Keys are a district name (its street) or a path suffix.
ON_GROUND = [
    # (A bin stood by each door that sells something: tile 505, which I
    # read off its picture as a waste bin. In place it is a blood-spattered
    # bucket, and a blind reviewer met it at three doors: "says 'danger',
    # not 'hall' ... the most obvious repeat". Gone. A picture is not a
    # reading of a thing in a street.)
    # the churchyard: what grows there is dead
    ("cemetery", 22016, 24576, 540),
    ("cemetery", 24576, 31232, 543),
    ("cemetery", 21504, 33792, 545),
    ("cemetery", 27136, 34304, 540),
    ("cemetery", 23552, 26624, 608),
    ("cemetery", 25600, 30208, 608),
    ("cemetery", 21760, 30720, 608),
]


# ---------------------------------------------------------------------------
# setting things down
# ---------------------------------------------------------------------------

def _find(layout, suffix: str):
    hits = [rid for rid in layout.regions if rid.endswith("/" + suffix)
            or rid.endswith(":" + suffix)]
    return hits[0] if len(hits) == 1 else None


def _box(region):
    xs = [p[0] for p in region.outer]
    ys = [p[1] for p in region.outer]
    return min(xs), min(ys), max(xs), max(ys)


def _inside(region, x: float, y: float, clear: float = 96.0) -> bool:
    from shapely.geometry import Point, Polygon

    here = Point(x, y)
    outer = Polygon(region.outer)
    if not outer.contains(here) or outer.exterior.distance(here) < clear:
        return False
    return all(Polygon(hole).distance(here) >= clear for hole in region.holes)


def dress(layout, street_regions: dict, district_bounds: dict) -> dict:
    """Set everything in the plan down. Returns what was placed and what was
    refused, by reason: a prop with nowhere to stand is left out, and said."""
    import wallplane

    placed: list[int] = []
    refused: list[str] = []
    street_of = {district: rid for rid, district in street_regions.items()}

    from bloodmap.placement import drawn_extent

    def put_floor(region_id, tile, x, y, tag, *, raised=False, pitch=None):
        region = layout.regions[region_id]
        x0, y0, x1, y1 = _box(region)
        row = fields(tile)
        name = NAMES.get(tile, tile)
        size = wallplane.art().get(tile)
        lift, half = 0, 0.0
        if size is not None and row["cstat"] & 48 == 0:
            width, height, _xofs, yofs = size
            top, lift = drawn_extent(height, yofs, row["y_repeat"],
                                     row["cstat"], 0)
            half = width * row["x_repeat"] / 8.0
            over = ASSETS[tile]["over_floor_bodies"]
            if over is not None and over - lift / BODY > HANGS:
                refused.append(f"{tag}: a {name} hangs in the town maps, "
                               f"{over:.2f} body up; it does not stand")
                return
            if raised and tile in FLOOR_ONLY:
                refused.append(f"{tag}: a {name} stands on a room's floor, "
                               "not on a counter or a shelf")
                return
            clear = int(region.floor_z) - int(region.ceiling_z)
            if not region.parallax_ceiling and lift - top > clear:
                refused.append(f"{tag}: a {name} is {lift - top} tall and "
                               f"this place is {clear}")
                return
            if pitch is not None and 2 * half > 1.2 * pitch:
                refused.append(f"{tag}: a {name} is {int(2 * half)} wide, "
                               f"too wide for a row at {pitch}")
                return
        if not _inside(region, x, y, clear=max(96.0, ROOM * half)):
            refused.append(f"{tag}: no room for a {name} at "
                           f"({int(x)}, {int(y)})")
            return
        layout.place_on_floor(
            f"goods:{tag}", region_id,
            local=((x - x0) / max(1, x1 - x0), (y - y0) / max(1, y1 - y0)),
            height_player_heights=lift / BODY,
            **row)
        placed.append(tile)

    for raised, plan in ((True, ON_TOP), (False, ON_FLOOR)):
        for suffix, items in plan:
            region_id = _find(layout, suffix)
            if region_id is None:
                refused.append(f"{suffix}: no such place")
                continue
            x0, y0, x1, y1 = _box(layout.regions[region_id])
            for index, (tile, u, v) in enumerate(items):
                put_floor(region_id, tile, x0 + u * (x1 - x0),
                          y0 + v * (y1 - y0),
                          f"{suffix.replace('/', '_')}_{index}_{tile}",
                          raised=raised)

    for suffix, tiles in ROWS:
        region_id = _find(layout, suffix)
        if region_id is None:
            refused.append(f"{suffix}: no such shelf")
            continue
        x0, y0, x1, y1 = _box(layout.regions[region_id])
        along_x = (x1 - x0) >= (y1 - y0)
        count = max(1, int((x1 - x0 if along_x else y1 - y0) // ROW_PITCH))
        for index in range(count):
            if len(tiles) == 1 and 0 < index < count - 1:
                continue
            t = (index + 0.5) / count
            tile = tiles[index % len(tiles)]
            put_floor(region_id, tile,
                      x0 + (t if along_x else 0.5) * (x1 - x0),
                      y0 + (0.5 if along_x else t) * (y1 - y0),
                      f"row_{suffix.replace('/', '_')}_{index}_{tile}",
                      raised=True, pitch=ROW_PITCH)

    for suffix, face, tile, t, height in ON_WALL:
        region_id = _find(layout, suffix)
        if region_id is None:
            refused.append(f"{suffix}: no such place")
            continue
        x0, y0, x1, y1 = _box(layout.regions[region_id])
        #: ordered so the room lies on the side a sprite is offset to
        a1, a2 = {"north": ((x0, y0), (x1, y0)), "south": ((x1, y1), (x0, y1)),
                  "west": ((x0, y1), (x0, y0)), "east": ((x1, y0), (x1, y1))}[face]
        row = fields(tile)
        over = ASSETS[tile]["over_floor_bodies"] if height is None else height
        got = wallplane.sprite(
            layout, f"goods:{suffix.replace('/', '_')}_{face}_{tile}",
            region_id, a1, a2, tile=tile, x_repeat=row["x_repeat"],
            y_repeat=row["y_repeat"], cstat=row["cstat"], t=t,
            height_player_heights=float(over), shade=row["shade"],
            pal=row["pal"])
        if got is None:
            refused.append(f"{suffix} {face}: no room for {NAMES.get(tile, tile)}")
        else:
            placed.append(tile)

    for district, (a1, a2), tile, t, height in ON_STREET:
        region_id = street_of.get(district)
        if region_id is None:
            refused.append(f"{district}: no street")
            continue
        row = fields(tile)
        over = ASSETS[tile]["over_floor_bodies"] if height is None else height
        try:
            got = wallplane.sprite(
                layout, f"goods:street_{district}_{a1[0]}_{a1[1]}_{tile}",
                region_id, a1, a2, tile=tile, x_repeat=row["x_repeat"],
                y_repeat=row["y_repeat"], cstat=row["cstat"], t=t,
                height_player_heights=float(over), shade=row["shade"],
                pal=row["pal"])
        except Exception as error:                       # not a wall of this street
            refused.append(f"{district} {a1}-{a2}: {type(error).__name__}")
            continue
        if got is None:
            refused.append(f"{district} {a1}-{a2}: no room for "
                           f"{NAMES.get(tile, tile)}")
        else:
            placed.append(tile)

    for key, x, y, tile in ON_GROUND:
        region_id = street_of.get(key) or next(
            (rid for rid in layout.regions if rid.split("/")[-1].startswith(key)
             or f"/{key}/" in rid and rid.endswith("ground")), None)
        if region_id is None:
            refused.append(f"{key}: no such ground")
            continue
        put_floor(region_id, tile, x, y, f"ground_{key}_{x}_{y}_{tile}")

    return {"placed": len(placed), "tiles": len(set(placed)),
            "refused": refused}


def unnamed() -> list[int]:
    """Tiles this plan uses that the owner has not named: for the next sheet."""
    root = pathlib.Path(__file__).resolve().parents[3]
    anchors = json.loads((root / "knowledge" / "blood" / "design"
                          / "owner-anchors-v1.json").read_text("utf-8"))
    named = {a["picnum"] for a in anchors["anchors"] if "picnum" in a}
    used = {tile for _s, items in ON_TOP + ON_FLOOR for tile, _u, _v in items}
    used |= {tile for _s, tiles in ROWS for tile in tiles}
    used |= {row[2] for row in ON_WALL} | {row[2] for row in ON_STREET}
    used |= {row[3] for row in ON_GROUND}
    return sorted(used - named)
