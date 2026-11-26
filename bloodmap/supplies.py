"""Supplies: what a map gives the player, how far along the way it gives it, and what keys, gates and secrets stand between.

Four readings of one map, all from its own records and the engine's tables:

* **what is there**: every weapon, ammo, health, armour, powerup and key the
  engine keeps in a single-player game at one difficulty (`launched`);
* **how far along**: an event-driven walk (`Walk`) from the player's start.
  It keeps the gates `bloodmap.conditional` reads and adds three things that
  reader leaves out and a key gate needs: the pose a sliding or turning leaf
  really has when the level loads, a floor too high to jump to, and a portal
  with no opening. Every place gets a distance walked, the set of keys its
  way needs, and what opened it;
* **the budget**: the health of everything that fights against the damage in
  the ammo, and the health lying about;
* **keys and secrets**: where a key stands, what its lock works, whether the
  lock was met first, how the way back differs from the way there; what a
  secret holds, what opened it and who guards it.

The distance is a critical path, not a play-through: what a body must walk at
least to have done everything the place needs, with no detour and no error. A
`way` is that distance over the distance of the exit, so the exit is 1.0 and
a place off past it reads over 1. Where the walk does not reach the exit, its
far end stands in for it, and `way_is` says so.

Engine facts, NBlood `source/blood/src`:

* `launch_skill`, `launch_single`, ... are LOCKOUT bits: a sprite with the
  bit of the difficulty set is deleted (`blood.cpp:699`). Difficulty 2 is
  "Lightly Broiled", where `DudeDifficulty` is 256: no scaling of what a dude
  takes (`actor.cpp:2455`).
* A slide or rotate sector is SAVED IN ITS ON POSE. `trInit` moves it by
  -65536 to get the OFF pose and then forward by `busy`
  (`triggers.cpp:2231`). A leaf drawn open along its wall, state 0, is shut
  when the level loads: E1M1's skull gate is drawn so.
* A dude's `key` is the key it drops, its `drop_item` what it drops; a tommy
  cultist drops a tommy gun one time in ten and 15 rounds four in ten, a
  shotgun cultist a shotgun or 4 shells (`actKillDude`, `actor.cpp:3053`).
* ammo counts, health and armour: `gAmmoItemData`, `gWeaponItemData`
  (`actor.cpp:1148`, `:1382`), `gPowerUpInfo`, `armorData` (`player.cpp`).
* a standing jump is `0xbaaaa` up against 58254 a frame: its apex is about
  15,050-15,370 z when gravity is applied tick by tick as the engine does
  (15,052 by the bot's replay); 19,600 is the continuous formula v^2/2g,
  which the engine does not follow. `MAX_RISE` is 22,000 because shipped ways
  rise 22,528 and more; a way that is too high is still taken when nothing
  else is left, and counted as taken on trust.

`damage` is a convention where the engine has none: what one round does to
ONE target fired the ordinary way (`DAMAGE_PER_ROUND`). Explosives hit more
than one and miss more often.
"""

from __future__ import annotations

import heapq
from collections import Counter, defaultdict
from copy import copy
from dataclasses import replace
from math import cos, hypot, pi, sin
from typing import Any, Iterable, Mapping, Sequence

from . import conditional, wiring
from .blood_types import classify
from .doors import KEY_NAMES, KEY_TYPES
from .model import DiskObject, record_extra, record_fields
from .player_space import PLAYER_PROFILES
from .sector_geom import sector_walls, wall_owners

SCHEMA = "llmapper.supplies"
SCHEMA_VERSION = 1

DEFAULT_SKILL = 2
BODY = PLAYER_PROFILES["blood"].standing_height
EYE = PLAYER_PROFILES["blood"].eye_height
#: Not a jump's apex (that is about 15,050-15,370 per tick; 19,600 is the
#: continuous formula): the rise shipped ways ask (22,528 and more), the jump
#: plus the step a landing body still climbs, taken generously.
MAX_RISE = 22000
#: How wide a pit a running jump clears: "about three thousand units", flown by
#: the bot (its leaping notes); a fall on the way lengthens it.
LEAP = 3000
#: A rise a body cannot simply walk up (`conditional`'s step_up).
WALK_RISE = 6656
#: Under this a portal is shut to a crouched body (a generous reading).
MIN_OPENING = 8192
#: What counts as at the fight, and beside it, by walking distance.
AT_FIGHT, BESIDE_FIGHT = 3072, 8192
#: Guards and groups are counted within these.
GUARD_REACH, GROUP_REACH = 4096, 1024
#: A secret whose loss takes more of the map than this is on the way, not off it.
SECRET_SHARE = 0.05

#: type -> (short name, ammo kind, rounds it brings, tier). Tiers are ours:
#: 1 what every level hands out, 2 the working guns, 3 what a player is glad
#: of, 4 what changes the fight.
WEAPONS: dict[int, tuple[str, str, int, int]] = {
    41: ("sawed-off", "shells", 8, 2), 42: ("tommy gun", "bullets", 50, 2),
    43: ("flare pistol", "flares", 9, 1), 44: ("voodoo doll", "voodoo", 100, 3),
    45: ("tesla cannon", "tesla", 64, 4), 46: ("napalm launcher", "napalm", 6, 4),
    48: ("spray can", "spray", 480, 1), 49: ("TNT", "tnt", 1, 1),
    50: ("life leech", "souls", 35, 4),
}
AMMO: dict[int, tuple[str, str, int, int]] = {
    60: ("spray can", "spray", 480, 1), 62: ("TNT bundle", "tnt", 1, 1),
    63: ("TNT box", "tnt", 5, 2), 64: ("proximity TNT", "prox", 1, 2),
    65: ("remote TNT", "remote", 1, 2), 66: ("trapped soul", "souls", 10, 4),
    67: ("4 shells", "shells", 4, 1), 68: ("box of shells", "shells", 15, 2),
    69: ("15 bullets", "bullets", 15, 1), 70: ("voodoo doll", "voodoo", 100, 3),
    72: ("drum of bullets", "bullets", 100, 2), 73: ("tesla charge", "tesla", 32, 3),
    76: ("box of flares", "flares", 8, 1), 79: ("gasoline can", "napalm", 6, 3),
}
#: type -> (name, health it gives, tier)
HEALTH: dict[int, tuple[str, int, int]] = {
    107: ("doctor's bag", 100, 3), 108: ("medicine pouch", 50, 2),
    109: ("life essence", 20, 1), 110: ("life seed", 100, 4),
    111: ("red potion", 2, 1),
}
#: type -> (name, armour points over the three kinds, tier)
ARMOR: dict[int, tuple[str, int, int]] = {
    140: ("basic armor", 150, 2), 141: ("body armor", 100, 3),
    142: ("fire armor", 100, 2), 143: ("spirit armor", 100, 2),
    144: ("super armor", 600, 4),
}
POWERUPS: dict[int, tuple[str, int]] = {
    112: ("feather fall", 2), 113: ("cloak of invisibility", 4),
    114: ("death mask", 4), 115: ("jump boots", 3), 117: ("guns akimbo", 4),
    118: ("diving suit", 2), 119: ("gas mask", 2), 121: ("crystal ball", 2),
    124: ("reflective shots", 4), 125: ("beast vision", 2),
    128: ("delirium shroom", 1), 139: ("asbestos suit", 2),
}
#: What one round does to one target. Vectors from `gVectorData` (a shell is
#: 16 pellets of 4, a bullet 12); a flare is 25 and 60 of burning; a tesla
#: bolt 20; a soul 10; a voodoo unit is spent at a quarter of the damage it
#: did; a spray can's 4 units are 3.5 with the burn. The explosives are at
#: about 1,000 units, one target: TNT 150, napalm 75 for the hit and a blast.
DAMAGE_PER_ROUND = {
    "shells": 64.0, "bullets": 12.0, "flares": 85.0, "tnt": 150.0, "prox": 150.0,
    "remote": 150.0, "tesla": 20.0, "souls": 10.0, "voodoo": 4.0,
    "napalm": 150.0, "spray": 0.875,
}
#: What a cultist leaves, in expectation (`actKillDude`).
DROPS = {201: ("bullets", 0.10 * 50 + 0.40 * 15), 202: ("shells", 0.11 * 8 + 0.40 * 4)}

#: `dudeInfo[].startHealth`, `dude.cpp`, by type. Innocents and the player's
#: own types are not fought and are left out.
DUDE_HEALTH: dict[int, int] = {
    201: 40, 202: 40, 203: 60, 204: 80, 205: 60, 206: 110, 207: 200, 208: 100,
    209: 100, 210: 100, 211: 70, 212: 10, 213: 10, 214: 25, 215: 75, 216: 100,
    217: 50, 218: 25, 219: 10, 220: 10, 221: 50, 222: 10, 223: 100, 224: 20,
    225: 200, 226: 50, 227: 200, 228: 100, 229: 32, 230: 25, 240: 30, 241: 12,
    242: 25, 244: 60, 246: 25, 247: 40, 248: 40, 249: 40, 250: 10, 251: 120,
}
DUDE_NAMES: dict[int, str] = {
    201: "tommy cultist", 202: "shotgun cultist", 203: "axe zombie", 204: "butcher",
    205: "buried zombie", 206: "gargoyle", 207: "stone gargoyle", 208: "gargoyle statue",
    209: "stone gargoyle statue", 210: "phantasm", 211: "hell hound", 212: "hand",
    213: "brown spider", 214: "red spider", 215: "black spider", 216: "mother spider",
    217: "gill beast", 218: "bone eel", 219: "bat", 220: "rat", 221: "green pod",
    222: "green tentacle", 223: "fire pod", 224: "fire tentacle", 225: "mother pod",
    226: "mother tentacle", 227: "cerberus", 228: "one-headed cerberus",
    229: "Tchernobog", 230: "prone tommy cultist", 240: "burning cultist",
    241: "burning zombie", 242: "burning butcher", 244: "lying zombie",
    246: "prone shotgun cultist", 247: "tesla cultist", 248: "TNT cultist",
    249: "beast cultist", 250: "tiny Caleb", 251: "beast",
}
SPAWN_MARKER = 18
#: Pictures of the dead, by what `catalog show` says the tile is.
CORPSE_TILES = frozenset({
    370, 648, 680, 681, 682, 688, 689, 690, 691, 696, 697, 698, 895, 906, 924,
    975, 976, 1040, 1059, 1223, 1455, 1569, 1727, 1728, 2324, 2333, 2334, 2914,
    2937, 2954, 3661, 3791, 3792})
Z_MOVERS = frozenset({600, 602, 613})
SWEPT = frozenset({614, 615, 616, 617})
SECRET_CHANNEL, EXIT_NORMAL, EXIT_SECRET = 2, 4, 5
WALL_BLOCK = 1
KINDS = ("weapon", "ammo", "health", "armor", "powerup", "key")

Point = tuple[float, float]
Node = tuple[int, int]


# ---------------------------------------------------------------------------
# What is in the game at all
# ---------------------------------------------------------------------------

def launched(sprite: Any, skill: int = DEFAULT_SKILL) -> bool:
    """Whether a single-player game at this difficulty keeps the sprite (`blood.cpp:699`)."""
    extra = record_extra(sprite)
    if not extra:
        return True
    return not (int(extra.get("launch_skill") or 0) & (1 << skill)
                or int(extra.get("launch_single") or 0))


def as_launched(disk: Any, skill: int = DEFAULT_SKILL) -> Any:
    """A copy of the map in which every sprite the game deletes is a plain, inert one.

    Indices are kept: a marker is found by its number.
    """
    out = []
    for sprite in disk.sprites:
        if launched(sprite, skill):
            out.append(sprite)
        else:
            fields = dict(record_fields(sprite))
            fields["type"], fields["status"], fields["extra"] = 0, 1024, -1
            out.append(DiskObject(fields=fields))
    return replace(disk, sprites=out)


#: How a pickup lies in the world: type -> (tile, repeat). The repeats are the campaign's own for each (the owner,
#: 2026-11-25: "pickups keep Blood's sizes"); a type missing here has not been set down by a level of ours yet.
ITEM_ART: dict[int, tuple[int, int]] = {
    41: (559, 48), 42: (558, 48), 43: (524, 48), 45: (539, 48), 46: (526, 48), 50: (800, 48), 60: (618, 40),
    62: (589, 48), 63: (809, 48), 64: (811, 40), 65: (810, 40), 66: (820, 24), 67: (619, 48), 68: (812, 48),
    69: (813, 48), 70: (525, 48), 72: (817, 48), 73: (548, 24), 76: (816, 48), 79: (801, 48), 107: (519, 48),
    108: (822, 40), 109: (2169, 40), 110: (2433, 40), 113: (896, 40), 114: (825, 40), 117: (829, 40), 118: (830, 64),
    121: (760, 40), 124: (2428, 40), 140: (2628, 64), 141: (2586, 64), 143: (2602, 64), 144: (2594, 64),
}
#: ... and the few that are not square: type -> the fields that differ
ITEM_ART_FIELDS: dict[int, dict[str, int]] = {118: {'x_repeat': 80}}
#: How an enemy stands in the world: type -> (tile, repeat, palette). The palette is what tells two cultists apart.
DUDE_ART: dict[int, tuple[int, int, int]] = {
    201: (2820, 40, 3), 202: (2825, 40, 0), 203: (1170, 40, 0), 204: (1370, 48, 0), 205: (3054, 40, 0),
    206: (1470, 40, 0), 210: (3060, 40, 0), 211: (1270, 40, 0), 217: (1570, 48, 0), 248: (2820, 40, 13),
    212: (1980, 32, 0), 218: (1870, 32, 0), 220: (1745, 24, 0),
}


def item(kind: int, **overrides: int) -> dict[str, int]:
    """The sprite record of a pickup as Blood sets it down: type, tile and size derived together, on the item list."""
    if kind not in ITEM_ART:
        raise KeyError(f"item type {kind} has no art on file in bloodmap.supplies.ITEM_ART: look one up in the campaign "
                       f"(python -m tools.catalog show sprite:{kind}) and add it")
    tile, size = ITEM_ART[kind]
    return {"type": kind, "picnum": tile, "x_repeat": size, "y_repeat": size, "status": 3, "shade": -8,
            **ITEM_ART_FIELDS.get(kind, {}), **overrides}


def dude(kind: int, **overrides: int) -> dict[str, int]:
    """The sprite record of an enemy as Blood sets it down: type, tile, size and palette, blocking, on the dude list."""
    if kind not in DUDE_ART:
        raise KeyError(f"dude type {kind} has no art on file in bloodmap.supplies.DUDE_ART: look one up in the campaign "
                       f"(python -m tools.catalog show sprite:{kind}) and add it")
    tile, size, pal = DUDE_ART[kind]
    return {"type": kind, "picnum": tile, "x_repeat": size, "y_repeat": size, "pal": pal, "cstat": 384, "status": 6,
            "shade": -8, **overrides}


def item_type(kind: int) -> dict[str, Any] | None:
    """What an item type gives when it is walked over, or None."""
    for label, table in (("weapon", WEAPONS), ("ammo", AMMO)):
        if kind in table:
            name, ammo, rounds, tier = table[kind]
            return {"kind": label, "name": name, "ammo": ammo, "rounds": rounds, "tier": tier}
    for label, table in (("health", HEALTH), ("armor", ARMOR)):
        if kind in table:
            name, points, tier = table[kind]
            return {"kind": label, "name": name, "points": points, "tier": tier}
    if kind in POWERUPS:
        name, tier = POWERUPS[kind]
        return {"kind": "powerup", "name": name, "tier": tier}
    if kind in KEY_TYPES:
        return {"kind": "key", "name": f"{KEY_NAMES[KEY_TYPES[kind]]} key",
                "key": KEY_TYPES[kind], "tier": 0}
    return None


def damage_of(item: Mapping[str, Any]) -> float:
    """The damage a weapon's or ammo pickup's rounds carry, by the convention above."""
    return item.get("rounds", 0) * DAMAGE_PER_ROUND.get(item.get("ammo", ""), 0.0)


# ---------------------------------------------------------------------------
# The map as it stands when the level loads
# ---------------------------------------------------------------------------

def _turned(x: float, y: float, angle: float, px: float, py: float) -> Point:
    """Blood's `RotatePoint`: a Build angle about a pivot."""
    a = angle * pi / 1024.0
    dx, dy = x - px, y - py
    return (dx * cos(a) - dy * sin(a) + px, dx * sin(a) + dy * cos(a) + py)


def swept_off_pose(disk: Any, sector_id: int) -> dict[int, Point]:
    """Wall -> where its point stands in the OFF pose, for one slide or rotate sector.

    The saved pose is the ON pose, so this is the saved point moved back by
    the whole of the motion (`trInit`, `TranslateSector`). Walls elsewhere
    that share the point are dragged with it, which `Geometry` does.
    """
    kind = int(record_fields(disk.sectors[sector_id])["type"])
    extra = record_extra(disk.sectors[sector_id]) or {}
    if kind not in SWEPT:
        return {}
    marks = []
    for name in ("marker_0", "marker_1"):
        raw = extra.get(name)
        index = -1 if raw is None else int(raw)
        marks.append(record_fields(disk.sprites[index]) if 0 <= index < len(disk.sprites) else None)
    off, on = marks
    if off is None or (kind in (614, 616) and on is None):
        return {}
    px, py = float(off["x"]), float(off["y"])
    if kind in (614, 616):
        vx, vy = px - float(on["x"]), py - float(on["y"])
        turn = 2 * int(off["angle"]) - int(on["angle"])
    else:
        vx, vy, turn = 0.0, 0.0, -int(off["angle"])
    out: dict[int, Point] = {}

    def place(wall: int, sign: int) -> None:
        f = record_fields(disk.walls[wall])
        x, y = float(f["x"]), float(f["y"])
        if turn:
            x, y = _turned(x, y, sign * turn, px, py)
        out[wall] = (x + sign * vx, y + sign * vy)

    for wall in sector_walls(disk, sector_id):
        f = record_fields(disk.walls[wall])
        if kind in (616, 617):
            place(wall, 1)
            continue
        cstat = int(f["cstat"])
        sign = 1 if cstat & 16384 else -1 if cstat & 32768 else 0
        if not sign:
            continue
        place(wall, sign)
        other = int(f["point2"])
        if not int(record_fields(disk.walls[other])["cstat"]) & 49152:
            place(other, sign)
    return out


class Geometry:
    """Wall ends, heights and openings of one map, in the pose it loads in."""

    def __init__(self, disk: Any):
        self.disk = disk
        self.owner = wall_owners(disk)
        rows = [record_fields(w) for w in disk.walls]
        self.saved = [(float(w["x"]), float(w["y"])) for w in rows]
        self.next = [int(w["next_sector"]) for w in rows]
        self.point2 = [int(w["point2"]) for w in rows]
        self.cstat = [int(w["cstat"]) for w in rows]
        self.partner = [int(w["next_wall"]) for w in rows]
        self.walls = [list(sector_walls(disk, s)) for s in range(len(disk.sectors))]
        self.fields = [record_fields(s) for s in disk.sectors]
        self.extra = [record_extra(s) or {} for s in disk.sectors]
        # the heights the level loads with, not the ones it was drawn with
        for s, e in enumerate(self.extra):
            if int(self.fields[s]["type"]) in Z_MOVERS | SWEPT and e:
                side = "on" if int(e.get("state") or 0) else "off"
                for name in ("floor_z", "ceiling_z"):
                    if int(e.get(f"on_{name}") or 0) != int(e.get(f"off_{name}") or 0):
                        self.fields[s] = {**self.fields[s], name: int(e[f"{side}_{name}"])}
        by_point: dict[Point, list[int]] = defaultdict(list)
        for wall, point in enumerate(self.saved):
            by_point[point].append(wall)
        #: mechanism -> wall -> its point when that one mechanism is in its OFF pose
        self.off_pose: dict[int, dict[int, Point]] = {}
        for s, f in enumerate(self.fields):
            if int(f["type"]) not in SWEPT:
                continue
            spread = {}
            for wall, point in swept_off_pose(disk, s).items():
                if hypot(point[0] - self.saved[wall][0], point[1] - self.saved[wall][1]) < 2:
                    continue
                for twin in by_point[self.saved[wall]]:
                    spread[twin] = point
            if spread:
                self.off_pose[s] = spread
        self.at = self.pose()
        self._segs = [[(w, self.at[w], self.at[self.point2[w]]) for w in walls] for walls in self.walls]

    def pose(self, toggled: Iterable[int] = ()) -> list[Point]:
        """Every wall's point at load, with these mechanisms in their other state."""
        out, other = list(self.saved), set(toggled)
        for s, spread in self.off_pose.items():
            on = bool(int(self.extra[s].get("state") or 0)) ^ (s in other)
            if not on:
                for wall, point in spread.items():
                    out[wall] = point
        return out

    def height(self, sector: int, x: float, y: float, floor: bool = True) -> float:
        """A floor's or ceiling's z at a point, slope read (`getflorzofslope`)."""
        f = self.fields[sector]
        side = "floor" if floor else "ceiling"
        z = float(f[f"{side}_z"])
        if not int(f[f"{side}_stat"]) & 2 or not self.walls[sector]:
            return z
        first = self.walls[sector][0]
        ax, ay = self.saved[first]
        bx, by = self.saved[self.point2[first]]
        dx, dy = bx - ax, by - ay
        length = hypot(dx, dy)
        if length < 1:
            return z
        return z + int(f[f"{side}_heinum"]) * (dx * (y - ay) - dy * (x - ax)) / length / 256.0

    def z_mover(self, sector: int) -> bool:
        f, e = self.fields[sector], self.extra[sector]
        if int(f["type"]) not in Z_MOVERS | SWEPT or not e:
            return False
        return (int(e.get("off_floor_z") or 0) != int(e.get("on_floor_z") or 0)
                or int(e.get("off_ceiling_z") or 0) != int(e.get("on_ceiling_z") or 0))

    def underwater(self, sector: int) -> bool:
        return bool(self.extra[sector].get("underwater"))

    def segments(self, sector: int, at: Sequence[Point] | None = None):
        if at is None:
            return self._segs[sector]
        return [(w, at[w], at[self.point2[w]]) for w in self.walls[sector]]

    def area(self, sector: int) -> float:
        total = 0.0
        for _wall, (ax, ay), (bx, by) in self.segments(sector):
            total += ax * by - bx * ay
        return abs(total) / 2

    def contains(self, sector: int, x: float, y: float) -> bool:
        inside = False
        for _wall, (ax, ay), (bx, by) in self.segments(sector):
            if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
                inside = not inside
        return inside

    def sees(self, sector: int, eye: tuple[float, float, float],
             at: tuple[float, float, float], limit: int = 96) -> bool:
        """Whether the line is clear, walked through the portals with its height.

        Slopes are read flat, masked walls seen through, sprites hide nothing;
        the pose is the load pose.
        """
        ex, ey, ez = eye
        dx, dy, dz = at[0] - ex, at[1] - ey, at[2] - ez
        here, reached = sector, 0.0
        for _step in range(limit):
            best = None
            for wall, (ax, ay), (bx, by) in self.segments(here):
                wx, wy = bx - ax, by - ay
                cross = dx * wy - dy * wx
                if abs(cross) < 1e-9:
                    continue
                t = ((ax - ex) * wy - (ay - ey) * wx) / cross
                u = ((ax - ex) * dy - (ay - ey) * dx) / cross
                if reached + 1e-7 < t <= 1.0 and -1e-6 <= u <= 1 + 1e-6 and (best is None or t < best[0]):
                    best = (t, wall)
            if best is None:
                return self.contains(here, at[0], at[1])
            t, wall = best
            beyond = self.next[wall]
            if beyond < 0:
                return False
            z = ez + dz * t
            for side in (here, beyond):
                f = self.fields[side]
                if not int(f["ceiling_z"]) <= z <= int(f["floor_z"]):
                    return False
            here, reached = beyond, t
        return False


def _components(geo: Geometry, sector: int, at: Sequence[Point]):
    """The parts of one sector's floor a body can walk between, on a grid.

    Returns a function from a point to the part it is in (None where the grid
    has nothing near). Every wall of the sector bounds it, portals too, so
    this is movement inside the one sector.
    """
    segs = [(a, b) for _w, a, b in geo.segments(sector, at)]
    xs, ys = [p[0] for s in segs for p in s], [p[1] for s in segs for p in s]
    x0, y0, x1, y1 = min(xs), min(ys), max(xs), max(ys)
    extent = max(x1 - x0, y1 - y0)
    cell = max(64.0, min(160.0, extent / 110.0), extent / 220.0)
    nx, ny = int((x1 - x0) / cell) + 1, int((y1 - y0) / cell) + 1
    cx = [x0 + (i + 0.437) * cell for i in range(nx)]
    cy = [y0 + (j + 0.563) * cell for j in range(ny)]

    def column(x: float) -> int:          # the last grid column left of x
        return int((x - x0) / cell - 0.437) if x >= cx[0] else -1

    def line(y: float) -> int:
        return int((y - y0) / cell - 0.563) if y >= cy[0] else -1

    inside: set[tuple[int, int]] = set()
    for i, x in enumerate(cx):
        cuts = sorted(a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])
                      for a, b in segs if (a[0] > x) != (b[0] > x))
        for low, high in zip(cuts[::2], cuts[1::2]):
            inside.update((i, j) for j in range(line(low) + 1, min(ny, line(high) + 1)))
    up: set[tuple[int, int]] = set()      # the link (i,j)-(i,j+1) is cut
    right: set[tuple[int, int]] = set()   # the link (i,j)-(i+1,j) is cut
    for (ax, ay), (bx, by) in segs:
        length = hypot(bx - ax, by - ay)
        if length < 1:
            continue
        # a turned corner is rounded to whole units; close the hair it leaves
        ux, uy = (bx - ax) / length * 48, (by - ay) / length * 48
        ax, ay, bx, by = ax - ux, ay - uy, bx + ux, by + uy
        if abs(bx - ax) > 1e-9:
            for i in range(max(0, column(min(ax, bx))), min(nx, column(max(ax, bx)) + 1)):
                if (ax > cx[i]) != (bx > cx[i]):
                    up.add((i, line(ay + (by - ay) * (cx[i] - ax) / (bx - ax))))
        if abs(by - ay) > 1e-9:
            for j in range(max(0, line(min(ay, by))), min(ny, line(max(ay, by)) + 1)):
                if (ay > cy[j]) != (by > cy[j]):
                    right.add((column(ax + (bx - ax) * (cy[j] - ay) / (by - ay)), j))
    part: dict[tuple[int, int], int] = {}
    sizes: list[int] = []
    for seed in sorted(inside):
        if seed in part:
            continue
        number, pending, count = len(sizes), [seed], 0
        part[seed] = number
        while pending:
            i, j = pending.pop()
            count += 1
            for there, cut in (((i, j + 1), (i, j) in up), ((i, j - 1), (i, j - 1) in up),
                               ((i + 1, j), (i, j) in right), ((i - 1, j), (i - 1, j) in right)):
                if not cut and there in inside and there not in part:
                    part[there] = number
                    pending.append(there)
        sizes.append(count)

    def where(x: float, y: float) -> int | None:
        i, j = int((x - x0) / cell), int((y - y0) / cell)
        best = None
        for di in range(-2, 3):
            for dj in range(-2, 3):
                got = part.get((i + di, j + dj))
                # a sliver of cells between a leaf and its frame is no place
                if got is None or sizes[got] < 6:
                    continue
                d = hypot(cx[i + di] - x, cy[j + dj] - y)
                if best is None or d < best[0]:
                    best = (d, got)
        return best[1] if best else None
    return where


# ---------------------------------------------------------------------------
# The walk
# ---------------------------------------------------------------------------

class Walk:
    """One map walked from its start: what opens what, how far it is, which keys it takes.

    A node is (sector, part): a sector a shut leaf cuts in two is two nodes.
    After `run`, `nodes[node]` holds `entries` (distance walked, point) for
    the ways in, `needs` (the keys the way takes), `opener` (the event that
    let a body in, None where the way was open) and `rescued` (the way is a
    jump or an opening this reader does not believe in). `events` are the
    acts that opened anything, in the order they were done.
    """

    def __init__(self, disk: Any):
        self.disk = disk
        self.geo = Geometry(disk)
        self.graph = conditional.build_graph(disk)
        start = self.graph.reach.start
        self.start_sector = int(start["sector"])
        if start["sprite"] is not None:
            f = record_fields(disk.sprites[start["sprite"]])
            self.start_point = (float(f["x"]), float(f["y"]))
        else:
            self.start_point = (float(disk.header["start_x"]), float(disk.header["start_y"]))
        self._parts()
        self._crossings()
        #: walls a body breaks with no wire: `conditional` calls that "operate" too
        hand = {(e.mechanism_kind, e.mechanism) for e in self.graph.edges
                if any(not cause.channel for cause in e.causes)}
        self._hand_walls = {index for kind, index in hand
                            if kind == "wall" and ("sector", index) not in hand}
        self._avoid: set[int] = set()
        self._believed: set[int] = set()
        self.nodes: dict[Node, dict[str, Any]] = {}
        self.events: list[dict[str, Any]] = []

    # -- building -----------------------------------------------------------

    def _parts(self) -> None:
        """Sectors a shut leaf divides, and what joins their parts again."""
        geo = self.geo
        touched: dict[int, set[int]] = defaultdict(set)
        for mover, spread in geo.off_pose.items():
            for wall in spread:
                if wall in geo.owner:
                    touched[geo.owner[wall]].add(mover)
        self.part_of: dict[int, Any] = {}
        #: (sector, part, part) -> the movers any one of which joins them
        self.joins: dict[tuple[int, int, int], set[int]] = {}
        for sector, movers in sorted(touched.items()):
            f = geo.fields[sector]
            if not geo.walls[sector] or (int(f["floor_z"]) - int(f["ceiling_z"]) < MIN_OPENING
                                         and not geo.z_mover(sector)):
                continue
            ways = [((geo.at[w][0] + geo.at[geo.point2[w]][0]) / 2,
                     (geo.at[w][1] + geo.at[geo.point2[w]][1]) / 2)
                    for w in geo.walls[sector] if geo.next[w] >= 0]
            where = _components(geo, sector, geo.at)
            first: dict[int, Point] = {}
            for point in ways:
                mark = where(*point)
                if mark is not None:
                    first.setdefault(mark, point)
            if len(first) < 2:
                continue
            workable = sorted(movers)
            trials: list[tuple[int, ...]] = [(m,) for m in workable]
            if len(workable) > 1:
                trials.append(tuple(workable))
            found: dict[tuple[int, int], set[int]] = defaultdict(set)
            for trial in trials:
                then = _components(geo, sector, geo.pose(trial))
                marks = {m: then(*p) for m, p in first.items()}
                for a in first:
                    for b in first:
                        if a < b and marks[a] is not None and marks[a] == marks[b] and (
                                len(trial) == 1 or not found.get((a, b))):
                            found[(a, b)].update(trial)
            if not found:
                continue              # nothing here ever joins them: our grid's error, not a gate
            self.part_of[sector] = where
            joined = {m for pair in found for m in pair}
            for pair, who in found.items():
                self.joins[(sector, *pair)] = who
            for part in first:
                if part not in joined:
                    self.joins[(sector, min(first), part)] = set()

    def node(self, sector: int, x: float, y: float) -> Node:
        where = self.part_of.get(sector)
        if where is None:
            return (sector, 0)
        got = where(x, y)
        return (sector, 0 if got is None else got)

    def middle(self, sector: int) -> Point:
        points = [self.geo.at[w] for w in self.geo.walls[sector]] or [(0.0, 0.0)]
        return (sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points))

    def _crossings(self) -> None:
        """Every way from one node to another, with what stands in it."""
        geo, graph = self.geo, self.graph
        self.cross: list[dict[str, Any]] = []
        self.out: dict[Node, list[int]] = defaultdict(list)

        def add(a: Node, b: Node, pa, pb, kind: str, **more) -> None:
            row = {"a": a, "b": b, "pa": pa, "pb": pb, "kind": kind, "high": False,
                   "shut": False, "blocked": False, "rise": 0.0, **more}
            self.out[a].append(len(self.cross))
            self.cross.append(row)

        # a floor sprite that blocks is a deck: a rope bridge over a pit is nothing else
        decks: dict[int, set[float]] = defaultdict(set)
        for sprite in self.disk.sprites:
            f = record_fields(sprite)
            if int(f["cstat"]) & 49 == 33 and int(f["status"]) < 1024:
                decks[int(f["sector"])].add(float(f["z"]))
        for sector, walls in enumerate(geo.walls):
            for wall in walls:
                there = geo.next[wall]
                if not 0 <= there < len(geo.walls):
                    continue
                (ax, ay), (bx, by) = geo.at[wall], geo.at[geo.point2[wall]]
                x, y = (ax + bx) / 2, (ay + by) / 2
                partner = geo.partner[wall]
                stop = bool(geo.cstat[wall] & WALL_BLOCK
                            or (0 <= partner < len(geo.cstat) and geo.cstat[partner] & WALL_BLOCK))
                here_floor, there_floor = geo.height(sector, x, y), geo.height(there, x, y)
                opening = (min(here_floor, there_floor)
                           - max(geo.height(sector, x, y, False), geo.height(there, x, y, False)))
                free = geo.z_mover(sector) or geo.z_mover(there)
                rise = here_floor - there_floor
                if rise > MAX_RISE and sector in decks:
                    rise = min((r for r in (z - there_floor for z in decks[sector])
                                if abs(r) <= MAX_RISE), default=here_floor - there_floor, key=abs)
                add(self.node(sector, x, y), self.node(there, x, y), (x, y), (x, y), "portal",
                    wall=wall, blocked=stop, rise=rise,
                    high=not free and not geo.underwater(sector) and rise > MAX_RISE,
                    shut=not free and opening < MIN_OPENING)
        self._leaps(add)
        for record in graph.reach.links:
            (a, b), (sa, sb) = record["sectors"], record["sprites"]
            fa, fb = record_fields(self.disk.sprites[sa]), record_fields(self.disk.sprites[sb])
            pa, pb = (float(fa["x"]), float(fa["y"])), (float(fb["x"]), float(fb["y"]))
            add(self.node(a, *pa), self.node(b, *pb), pa, pb, "link")
            add(self.node(b, *pb), self.node(a, *pa), pb, pa, "link")
        for record in graph.reach.teleports:
            a, b = record["sectors"]
            f = record_fields(self.disk.sprites[record["marker_sprite"]])
            pa, pb = self.middle(a), (float(f["x"]), float(f["y"]))
            add(self.node(a, *pa), self.node(b, *pb), pa, pb, "teleport")
        for (sector, a, b), movers in self.joins.items():
            add((sector, a), (sector, b), None, None, "leaf", movers=movers)
            add((sector, b), (sector, a), None, None, "leaf", movers=movers)

    def _leaps(self, add) -> None:
        """A running jump over a pit: from one edge to another across a floor too deep to climb from."""
        geo = self.geo

        def edges(at, only: set[int] | None = None) -> dict[int, list]:
            into: dict[int, list] = defaultdict(list)
            for sector, walls in enumerate(geo.walls):
                for wall in walls:
                    there = geo.next[wall]
                    if not 0 <= there < len(geo.walls) or geo.underwater(there) or (
                            only is not None and there not in only):
                        continue
                    a, b = at[wall], at[geo.point2[wall]]
                    x, y = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                    partner = geo.partner[wall]
                    if geo.cstat[wall] & WALL_BLOCK or (
                            0 <= partner < len(geo.cstat) and geo.cstat[partner] & WALL_BLOCK):
                        continue
                    floor = geo.height(sector, x, y)
                    roof = max(geo.height(sector, x, y, False), geo.height(there, x, y, False))
                    if geo.height(there, x, y) - floor > MAX_RISE and floor - roof >= BODY * 0.8:
                        into[there].append((sector, a, b, (x, y), geo.height(sector, x, y)))
            return into

        def clear(pit: int, p: Point, q: Point, za: float, zb: float) -> bool:
            """Nothing solid and no low roof of the pit's between the two edges."""
            length = hypot(q[0] - p[0], q[1] - p[1])
            if length < 8:
                return True
            ux, uy = (q[0] - p[0]) / length * 3, (q[1] - p[1]) / length * 3
            return geo.sees(pit, (p[0] + ux, p[1] + uy, za - BODY * 1.2),
                            (q[0] - ux, q[1] - uy, zb - BODY * 1.2))

        def pairs(into, must: int | None, movers: set[int]) -> None:
            for pit, rows in into.items():
                for s, a, b, pa, za in rows:
                    for t, c, d, pb, zb in rows:
                        if s == t or za - zb > MAX_RISE * 0.75 or (must is not None and must not in (s, t)):
                            continue
                        if hypot(pa[0] - pb[0], pa[1] - pb[1]) > LEAP + hypot(b[0] - a[0], b[1] - a[1]) + hypot(
                                d[0] - c[0], d[1] - c[1]):
                            continue
                        gap, here, there = _closest(a, b, c, d)
                        if gap <= LEAP and (clear(pit, here, there, za, zb) or clear(pit, pa, pb, za, zb)):
                            add(self.node(s, *pa), self.node(t, *pb), pa, pb, "leap", pit=pit, movers=movers)

        standing = edges(geo.at)
        pairs(standing, None, set())
        # a bridge that turns or slides over a pit: its edges in its other pose
        for mover in geo.off_pose:
            pits = {pit for pit, rows in standing.items() if any(row[0] == mover for row in rows)}
            if pits:
                pairs(edges(geo.pose((mover,)), pits), mover, {mover})

    # -- what is open -------------------------------------------------------

    def _edge_open(self, edge, held) -> bool:
        """`conditional`'s rule for a gate, with the state the engine loads.

        `conditional.rest_state` reads a door drawn open and saved in state 0
        as open at rest. `trInit` moves every motion sector to its state
        (`ZTranslateSector(i, busy)`, triggers.cpp:2250), so it is shut: E6M1's
        three key doors are drawn open. Only a sector whose ON and OFF heights
        are the same keeps the pose it was drawn in.
        """
        if edge.verdict != "conditional":
            return False
        if edge.mechanism_kind == "sector" and edge.delta.get("rest_state"):
            extra = self.geo.extra[edge.mechanism]
            rest = "on" if int(extra.get("state") or 0) else "off"
            if rest == edge.enabling_state:
                return True
            if edge.delta.get("rest_state") == edge.enabling_state and not self.geo.z_mover(edge.mechanism):
                return True
        if edge.requires_key and edge.requires_key not in held.keys:
            return False
        for cause in edge.causes:
            if cause.channel and cause.channel in held.channels:
                return True
            if not cause.channel and (edge.mechanism in held.operated or (
                    # a door worked by hand AND by wire is never offered as an
                    # act by `available_actions`; a body in front of it opens it
                    edge.mechanism_kind == "sector" and any(c.channel for c in edge.causes)
                    and not self.geo.extra[edge.mechanism].get("locked"))):
                return True
        return False

    def _open(self, held) -> tuple[frozenset[tuple[int, int]], frozenset[int]]:
        """Sector pairs a gate now lets through, and the movers that have been worked."""
        graph = self.graph
        full = conditional.Held(graph.fired(held.channels | graph.fired_at_start),
                                held.keys, held.operated)
        pairs = {edge.sectors for edge in graph.edges if self._edge_open(edge, full)}
        worked = set()
        for mover in self.geo.off_pose:
            extra = self.geo.extra[mover]
            key = int(extra.get("key") or 0)
            if key and key not in full.keys:
                continue
            rx = int(extra.get("rx_id") or 0)
            # pushed by hand with no wire: it opens in front of whoever comes
            by_hand = (extra.get("trigger_push") or extra.get("trigger_wall_push")
                       or extra.get("trigger_enter")) and not extra.get("locked")
            if mover in full.operated or (rx and rx in full.channels) or by_hand:
                worked.add(mover)
        for pair, mover in graph.swept_blocked.items():
            if graph._mover_worked(mover, full, full.channels) or mover in worked:
                pairs.add(pair)
        return frozenset(pairs), frozenset(worked)

    def _allowed(self, row: Mapping[str, Any], gates, rescued: bool) -> bool:
        pairs, worked = gates
        a, b = row["a"][0], row["b"][0]
        if self._avoid and (a in self._avoid or b in self._avoid):
            return False
        if row["kind"] == "leaf":
            return not row["movers"] or bool(row["movers"] & worked)
        base = self.graph.base
        if row["kind"] == "leap":
            pit = row["pit"]
            if row["movers"] and not row["movers"] & worked:
                return False
            return (((a, pit) in pairs or pit in base.get(a, ()))
                    and ((pit, b) in pairs or b in base.get(pit, ())) and pit not in self._avoid)
        pair = (a, b)
        if pair in pairs:
            return rescued or not row["high"]
        if b not in base.get(a, ()):
            return False
        if row["kind"] != "portal":
            return True
        if row["blocked"]:
            return False
        return rescued or not (row["shut"] or row["high"])

    @staticmethod
    def _disbelief(row: Mapping[str, Any]) -> float:
        """How far past a body a crossing is: what it must be raised, or squeezed."""
        return max(0.0, row["rise"] - MAX_RISE) + (4 * BODY if row["shut"] else 0.0)

    # -- distances ----------------------------------------------------------

    def spread(self, sources, gates, *, rescued: bool = False, limit: float | None = None,
               skip: Mapping[Node, Any] | None = None, first_only: bool = False):
        """Distances over the crossings: node -> entries, and node -> the crossing that got there first.

        `skip` is nodes not to go into; `first_only` keeps one way into each
        node, which is enough to know what is reached.
        """
        entries: dict[Node, list[tuple[float, Point]]] = {}
        first: dict[Node, int] = {}
        done: set[int] = set()
        heap: list[tuple[float, int, int, Node, Point]] = []
        tick = 0
        for at, node, point in sources:
            heap.append((at, tick, -1, node, point))
            tick += 1
        heapq.heapify(heap)
        marks: set[tuple[Node, int, int]] = set()
        while heap:
            at, _tick, via, node, point = heapq.heappop(heap)
            if limit is not None and at > limit:
                break
            if via >= 0:
                if via in done:
                    continue
                done.add(via)
            mark = (node, round(point[0]), round(point[1]))
            if mark in marks:
                continue
            marks.add(mark)
            got = entries.get(node)
            if got is None:
                got = entries[node] = []
                if via >= 0:
                    first[node] = via
            elif first_only or len(got) >= 24:
                continue
            got.append((at, point))
            for c in self.out.get(node, ()):
                if c in done:
                    continue
                row = self.cross[c]
                if (skip is not None and row["b"] in skip) or (first_only and row["b"] in entries):
                    continue
                if not self._allowed(row, gates, rescued or c in self._believed):
                    continue
                pa = point if row["pa"] is None else row["pa"]
                pb = point if row["pb"] is None else row["pb"]
                tick += 1
                heapq.heappush(heap, (at + hypot(pa[0] - point[0], pa[1] - point[1]),
                                      tick, c, row["b"], pb))
        return entries, first

    @staticmethod
    def nearest(entries, x: float, y: float) -> float:
        return min(at + hypot(p[0] - x, p[1] - y) for at, p in entries)

    def info(self, sector: int, x: float, y: float) -> dict[str, Any] | None:
        """The node a point stands in, or any reached part of its sector."""
        got = self.nodes.get(self.node(sector, x, y))
        if got is None:
            for node in self._sector_nodes.get(sector, ()):
                return self.nodes[node]
        return got

    def distance(self, sector: int, x: float, y: float) -> float | None:
        """How far a body has walked, at least, to stand here; None where the walk never came."""
        got = self.info(sector, x, y)
        return None if got is None else self.nearest(got["entries"], x, y)

    def reached(self) -> set[int]:
        return set(self._sectors)

    # -- the run ------------------------------------------------------------

    def act_place(self, action) -> tuple[int, float, float, int]:
        """Where an act is done, and the key its object wants."""
        if action.kind in ("obtain_key", "use_switch") or action.what == "sprite" or (
                action.kind == "destroy" and not action.what):
            sprite = self.disk.sprites[action.index]
            f = record_fields(sprite)
            key = 0
            if classify("sprite", int(f["type"])).get("category") != "dude":
                key = int((record_extra(sprite) or {}).get("key", 0) or 0)
            return int(f["sector"]), float(f["x"]), float(f["y"]), key
        if action.kind == "use_wall" or action.what == "wall" or (
                action.kind == "operate" and action.index in self._hand_walls):
            (ax, ay), (bx, by) = self.geo.at[action.index], self.geo.at[self.geo.point2[action.index]]
            key = int((record_extra(self.disk.walls[action.index]) or {}).get("key", 0) or 0)
            return self.geo.owner.get(action.index, action.where), (ax + bx) / 2, (ay + by) / 2, key
        sector = action.index if action.index >= 0 else action.where
        key = int((record_extra(self.disk.sectors[sector]) or {}).get("key", 0) or 0)
        return (sector, *self.middle(sector), key)

    def _is_crack(self, action) -> bool:
        return (action.kind in ("destroy", "shoot") and action.what in ("", "sprite")
                and int(record_fields(self.disk.sprites[action.index])["type"]) == conditional.CRACK_TYPE)

    def _act_time(self, action) -> tuple[float, Node, Point, frozenset]:
        sector, x, y, key = self.act_place(action)
        here = [sector] if sector in self._sectors else sorted(
            s for s in self.graph.reach.graph.get(sector, ()) if s in self._sectors)
        if not here and action.where in self._sectors:
            here = [action.where]
        seen, edge = {sector}, {sector}
        while not here and edge and len(seen) < 400:      # shot from some rooms off
            edge = {t for s in edge for t in self.graph.reach.graph.get(s, ())} - seen
            seen |= edge
            here = sorted(edge & self._sectors)
        best = None
        for s in here:
            for node in self._sector_nodes[s]:
                at = self.nearest(self.nodes[node]["entries"], x, y)
                if best is None or at < best[0]:
                    best = (at, node, self.nodes[node]["needs"])
        if best is None:
            return 0.0, self.node(self.start_sector, *self.start_point), self.start_point, frozenset()
        at, node, needs = best
        if key and key in self.key_spread:
            entries = self.key_spread[key].get(node)
            if entries:
                at = max(at, self.nearest(entries, x, y))
            needs = needs | {key} | self.key_needs[key]
        return at, node, (x, y), needs

    def run(self, *, avoid_sectors: Iterable[int] = (), avoid_acts: Iterable[str] = (),
            distances: bool = True, keys: bool = True) -> "Walk":
        """Walk the whole map. `avoid_*` leave sectors or acts ("wall 12") undone."""
        self._avoid = set(avoid_sectors)
        banned = set(avoid_acts)
        self.nodes, self.events = {}, []
        self._sectors: set[int] = set()
        self._sector_nodes: dict[int, list[Node]] = defaultdict(list)
        #: key -> node -> entries: how far everything is once the key is held
        self.key_spread: dict[int, dict] = {}
        self.key_needs: dict[int, frozenset] = {}
        self.key_sprite: dict[int, int] = {}
        self.key_gates: dict[int, Any] = {}
        graph, held = self.graph, self.graph.at_rest()
        self.rescued_sectors: set[int] = set()
        #: the jumps and squeezes taken on trust, in order, and what each gave
        self.believed: list[dict[str, Any]] = []
        self._believed: set[int] = set()

        def enter(entries, first, opener, base: frozenset, jump: bool = False) -> list[Node]:
            fresh = [n for n in entries if n not in self.nodes]
            needs: dict[Node, frozenset] = {}
            for node in fresh:
                trail, walk = [], node
                while walk not in needs and walk not in self.nodes:
                    trail.append(walk)
                    via = first.get(walk)
                    if via is None or len(trail) > 9000:
                        break
                    walk = self.cross[via]["a"]
                known = (self.nodes[walk]["needs"] if walk in self.nodes
                         else needs.get(walk, frozenset())) | base
                for back in reversed(trail):
                    known = needs[back] = known | needs.get(back, frozenset())
            for node in fresh:
                self.nodes[node] = {"entries": entries[node], "needs": needs[node],
                                    "opener": opener, "rescued": jump, "via": first.get(node)}
                self._sectors.add(node[0])
                self._sector_nodes[node[0]].append(node)
            return fresh

        def frontier(gates) -> list[int]:
            return [c for c, row in enumerate(self.cross)
                    if row["b"] not in self.nodes and row["a"] in self.nodes
                    and self._allowed(row, gates, c in self._believed)]

        def from_frontier(ways, gates):
            sources, lead = [], {}
            for c in ways:
                row = self.cross[c]
                known = self.nodes[row["a"]]["entries"]
                pa = known[0][1] if row["pa"] is None else row["pa"]
                sources.append((self.nearest(known, *pa), row["b"], pa if row["pb"] is None else row["pb"]))
                lead.setdefault(row["b"], c)
            entries, first = self.spread(sources, gates, skip=self.nodes, first_only=not distances)
            for node, c in lead.items():
                first.setdefault(node, c)
                if self.cross[first[node]]["a"] in lead and self.cross[first[node]]["a"] not in self.nodes:
                    first[node] = c
            return entries, first

        gates = self._open(held)
        begin = self.node(self.start_sector, *self.start_point)
        enter(*self.spread([(0.0, begin, self.start_point)], gates, first_only=not distances),
              None, frozenset())
        done: set[tuple[str, str, int]] = set()
        nouns = {"obtain_key": "sprite", "destroy": "sprite", "use_switch": "sprite",
                 "use_wall": "wall", "operate": "sector"}
        for _round in range(4000):
            acts = []
            for action in graph.available_actions(held, self._sectors):
                name = (action.kind, action.what, action.index)
                if name in done or (action.kind == "obtain_key"
                                    and (action.key in held.keys or not keys)):
                    continue
                if f"{action.what or nouns.get(action.kind, '')} {action.index}" in banned:
                    continue
                if action.where in self._avoid:
                    continue
                acts.append(action)
            # the ordinary way first, then a key, and a crack that wants TNT last:
            # E1M1's way round its skull gate is a blast, and the gate is still the gate
            ranks = {a: (2 if self._is_crack(a) else 1 if a.kind == "obtain_key" else 0) for a in acts}
            least = min(ranks.values(), default=0)
            chosen = [a for a in acts if ranks[a] == least]
            if not chosen:
                # stuck: believe in one more jump or squeeze, the easiest there is
                ways = []
                for c, row in enumerate(self.cross):
                    if (row["a"] in self.nodes and row["b"] not in self.nodes
                            and c not in self._believed and (row["high"] or row["shut"])
                            and self._allowed(row, gates, True)):
                        ways.append((self._disbelief(row), c))
                if not ways:
                    break
                cost, c = min(ways)
                # the same jump is the whole sill, not one wall of it
                pair = (self.cross[c]["a"], self.cross[c]["b"])
                opened = [n for n in self.out[pair[0]] if self.cross[n]["b"] == pair[1]
                          and self._disbelief(self.cross[n]) <= cost + 1024]
                self._believed.update(opened)
                before = len(self._sectors)
                source = self.nodes[pair[0]]
                for node in enter(*from_frontier(opened, gates), source["opener"], source["needs"],
                                  jump=True):
                    self.rescued_sectors.add(node[0])
                self.believed.append({"from": pair[0][0], "to": pair[1][0], "rise": round(self.cross[c]["rise"]),
                                      "shut": self.cross[c]["shut"], "gave": len(self._sectors) - before})
                continue
            timed = sorted(((self._act_time(a), a) for a in chosen),
                           key=lambda item: (item[0][0], item[1].kind, item[1].index))
            for (at, node, point, needs), action in timed:
                done.add((action.kind, action.what, action.index))
                held = held.with_action(action)
                after = self._open(held)
                ways = frontier(after) if after != gates else []
                gates = after
                got_key = action.kind == "obtain_key"
                if got_key:
                    needs = needs | {action.key}
                    self.key_needs[action.key] = needs
                    self.key_sprite[action.key] = action.index
                    self.key_gates[action.key] = gates
                if distances and (got_key or ways):
                    entries, first = self.spread([(at, node, point)], gates)
                else:
                    entries, first = {}, {}
                if got_key:
                    self.key_spread[action.key] = entries
                if ways:
                    fresh: list[Node] = []
                    event = {"act": action, "at": at, "needs": needs, "point": point,
                             "held": sorted(held.keys)}
                    fresh += enter(entries, first, event, needs)
                    left = frontier(gates)
                    if left:
                        fresh += enter(*from_frontier(left, gates), event, needs)
                    if fresh:
                        event["sectors"] = sorted({n[0] for n in fresh})
                        self.events.append(event)
                if got_key or ways:
                    break
        self.held, self.gates = held, gates
        return self


# ---------------------------------------------------------------------------
# One map, read
# ---------------------------------------------------------------------------

def _round(value: float | None, places: int = 3) -> float | None:
    return None if value is None else round(value, places)


def fighters(disk: Any) -> list[dict[str, Any]]:
    """Every dude that fights (and every spawn marker), with its health."""
    out = []
    for index, sprite in enumerate(disk.sprites):
        f = record_fields(sprite)
        kind = int(f["type"])
        extra = record_extra(sprite) or {}
        if kind in DUDE_HEALTH and int(f["status"]) == 6:
            out.append({"sprite": index, "type": kind, "name": DUDE_NAMES[kind],
                        "health": DUDE_HEALTH[kind], "sector": int(f["sector"]),
                        "x": float(f["x"]), "y": float(f["y"]), "spawned": False,
                        "key": int(extra.get("key") or 0), "drop": int(extra.get("drop_item") or 0)})
        elif kind == SPAWN_MARKER and int(extra.get("data_1") or 0) in DUDE_HEALTH:
            made = int(extra["data_1"])
            out.append({"sprite": index, "type": made, "name": DUDE_NAMES[made],
                        "health": DUDE_HEALTH[made], "sector": int(f["sector"]),
                        "x": float(f["x"]), "y": float(f["y"]), "spawned": True,
                        "key": 0, "drop": 0})
    return out


def pickups(disk: Any, foes: Sequence[Mapping[str, Any]] = ()) -> list[dict[str, Any]]:
    """Every item in the map, and what dudes carry on purpose (`key`, `drop_item`)."""
    out = []
    for index, sprite in enumerate(disk.sprites):
        f = record_fields(sprite)
        item = item_type(int(f["type"]))
        if item is None or int(f["status"]) not in (0, 3):
            continue
        out.append({"sprite": index, **item, "sector": int(f["sector"]), "x": float(f["x"]),
                    "y": float(f["y"]), "z": float(f["z"]), "carried_by": None})
    for foe in foes:
        for kind in ([99 + foe["key"]] if foe["key"] else []) + ([foe["drop"]] if foe["drop"] else []):
            item = item_type(kind)
            if item:
                f = record_fields(disk.sprites[foe["sprite"]])
                out.append({"sprite": foe["sprite"], **item, "sector": foe["sector"], "x": foe["x"],
                            "y": foe["y"], "z": float(f["z"]), "carried_by": foe["name"]})
    return out


def stands_on(geo: Geometry, disk: Any, item: Mapping[str, Any]) -> dict[str, Any]:
    """What a pickup stands on, how far from a wall, and whether one of the dead lies by it."""
    sector, x, y = item["sector"], item["x"], item["y"]
    if item["carried_by"]:
        return {"on": "carried by a dude", "raised": 0, "wall": None, "corpse": False,
                "room": round(geo.area(sector))}
    floor = geo.height(sector, x, y)
    gap = floor - item["z"]
    around = {geo.next[w] for w in geo.walls[sector] if geo.next[w] >= 0}
    rises = [geo.height(o, x, y) - floor for o in around]      # + : this floor is higher
    area = geo.area(sector)
    wall = min((_to_segment(x, y, a, b) for w, a, b in geo.segments(sector)
                if geo.next[w] < 0 or abs(geo.height(geo.next[w], x, y) - floor) > WALK_RISE),
               default=None)
    if gap > 6144:
        on = "a sprite, above the floor"
    elif rises and area < 1.6e6 and max(rises) >= 3072 and (
            sum(1 for r in rises if r >= 3072) * 2 >= len(rises)):
        on = ("a ledge or shelf" if len(around) == 1 and any(geo.next[w] < 0 for w in geo.walls[sector])
              else "furniture (a raised sector)")
    elif len(around) == 1 and area < 1.6e6:
        on = "a niche"
    else:
        on = "the floor"
    corpse = min((hypot(float(record_fields(s)["x"]) - x, float(record_fields(s)["y"]) - y)
                  for s in disk.sprites if int(record_fields(s)["picnum"]) in CORPSE_TILES
                  and abs(float(record_fields(s)["z"]) - item["z"]) < 2 * BODY), default=None)
    return {"on": on, "raised": round(max(rises, default=0)), "wall": None if wall is None else round(wall),
            "corpse": bool(corpse is not None and corpse < 1024), "room": round(area)}


def _closest(a: Point, b: Point, c: Point, d: Point) -> tuple[float, Point, Point]:
    """The shortest gap between two segments, and the point on each."""
    best = None
    for p, (s, t), swap in ((a, (c, d), False), (b, (c, d), False), (c, (a, b), True), (d, (a, b), True)):
        dx, dy = t[0] - s[0], t[1] - s[1]
        span = dx * dx + dy * dy
        u = 0.0 if not span else max(0.0, min(1.0, ((p[0] - s[0]) * dx + (p[1] - s[1]) * dy) / span))
        q = (s[0] + u * dx, s[1] + u * dy)
        gap = hypot(p[0] - q[0], p[1] - q[1])
        if best is None or gap < best[0]:
            best = (gap, q, p) if swap else (gap, p, q)
    return best


def _to_segment(x: float, y: float, a: Point, b: Point) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    span = dx * dx + dy * dy
    t = 0.0 if not span else max(0.0, min(1.0, ((x - a[0]) * dx + (y - a[1]) * dy) / span))
    return hypot(x - a[0] - t * dx, y - a[1] - t * dy)


def groups(items: Sequence[Mapping[str, Any]]) -> list[list[int]]:
    """Pickups standing within `GROUP_REACH` of one another, as lists of positions in `items`."""
    parent = list(range(len(items)))

    def root(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i, a in enumerate(items):
        for j in range(i):
            b = items[j]
            if (abs(a["x"] - b["x"]) <= GROUP_REACH and abs(a["z"] - b["z"]) < BODY
                    and hypot(a["x"] - b["x"], a["y"] - b["y"]) <= GROUP_REACH):
                parent[root(i)] = root(j)
    found: dict[int, list[int]] = defaultdict(list)
    for i in range(len(items)):
        found[root(i)].append(i)
    return sorted(found.values())


def _act_words(disk: Any, action, hand_walls: frozenset | set = frozenset()) -> str:
    """How an act opens a thing, in the words a secret is asked about in."""
    if action is None:
        return "open"
    kind = action.kind
    if kind in ("destroy", "shoot") and (action.what in ("", "sprite")):
        what = int(record_fields(disk.sprites[action.index])["type"])
        return {408: "blast a crack", 406: "break glass", 400: "blast a barrel",
                411: "break a grate"}.get(what, "shoot or break an object")
    if kind == "shoot" or (kind == "operate" and action.index in hand_walls):
        return "break a wall or glass"
    return {"use_switch": "a switch", "use_wall": "push a wall", "push": "push it",
            "operate": "push the door itself", "enter": "walk into a trigger", "kill": "a kill",
            "pick_up": "pick something up", "touch": "touch it", "destroy": "break it",
            "obtain_key": "a key"}.get(kind, kind)


def _secret_roots(disk: Any, chains: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Every chain that credits a secret: where it starts and what starts it."""
    command = {node["id"]: node["command"] for node in wiring.nodes(disk)}
    out = []
    for chain in chains:
        ends = [s for s in chain["steps"] if s["to"] == "engine" and s["channel"] == SECRET_CHANNEL
                and command.get(s["from"], 0) >= 64]
        if not ends or chain["silent"]:
            continue
        out.append({"root": chain["root"], "kind": chain["root_kind"], "sector": chain["sector"],
                    "cause": chain["cause"], "steps": chain["steps"], "super": command[ends[0]["from"]] > 64})
    return sorted(out, key=lambda row: row["root"])


def read(disk: Any, name: str = "", skill: int = DEFAULT_SKILL) -> dict[str, Any]:
    """Everything above, for one map at one difficulty."""
    live = as_launched(disk, skill)
    walk = Walk(live).run()
    geo = walk.geo
    chains = wiring.chains(live)
    foes = fighters(live)
    items = pickups(live, foes)

    # -- the length of the way
    exits = []
    for chain in chains:
        if chain["silent"] or chain["sector"] < 0:
            continue
        ends = {s["channel"] for s in chain["steps"] if s["to"] == "engine"} & {EXIT_NORMAL, EXIT_SECRET}
        if not ends:
            continue
        if chain["root_kind"] == "sprite":
            f = record_fields(live.sprites[int(chain["root"].split()[1])])
            at = walk.distance(chain["sector"], float(f["x"]), float(f["y"]))
        else:
            at = walk.distance(chain["sector"], *walk.middle(chain["sector"]))
            if at is None:
                at = min((d for d in (walk.distance(s, *walk.middle(chain["sector"]))
                                      for s in walk.graph.reach.graph.get(chain["sector"], ()))
                          if d is not None), default=None)
        info = walk.info(chain["sector"], *walk.middle(chain["sector"]))
        exits.append({"root": chain["root"], "sector": chain["sector"], "normal": EXIT_NORMAL in ends,
                      "at": at, "needs": sorted(info["needs"]) if info else None})
    ended = [e for e in exits if e["at"] is not None and e["normal"]] or [
        e for e in exits if e["at"] is not None]
    farthest = max((row["entries"][0][0] for row in walk.nodes.values() if not row["rescued"]), default=1.0)
    if ended:
        length, way_is = min(e["at"] for e in ended), "the exit"
        if length < 0.25 * farthest:
            length, way_is = farthest, "the far end (the exit reads too near: %d)" % round(length)
    else:
        length, way_is = farthest, "the far end (no exit reached)"
    length = max(length, 1.0)

    # -- distances of things
    for thing in foes + items:
        at = walk.distance(thing["sector"], thing["x"], thing["y"])
        info = walk.info(thing["sector"], thing["x"], thing["y"])
        thing["at"] = at
        thing["way"] = None if at is None else at / length
        thing["area"] = None if info is None else len(info["needs"])
        thing["needs"] = None if info is None else sorted(info["needs"])
    foes_by_sector: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for foe in foes:
        foes_by_sector[foe["sector"]].append(foe)
    total_health = sum(f["health"] for f in foes) or 1

    # -- secrets
    secrets = _secrets(live, walk, _secret_roots(live, chains), items, foes)
    hidden_sectors: set[int] = set()
    hidden_sprites: set[int] = set()
    for row in secrets:
        hidden_sectors.update(row["region"])
        hidden_sprites.update(row["picked"])
    for item in items:
        item["secret"] = item["sector"] in hidden_sectors or item["sprite"] in hidden_sprites

    # -- the fight a supply stands at
    for item in items:
        item["foe"], item["foe_first"] = None, None
        got = walk.node(item["sector"], item["x"], item["y"])
        near, _f = walk.spread([(0.0, got, (item["x"], item["y"]))], walk.gates, rescued=True,
                               limit=BESIDE_FIGHT * 2)
        best = None
        count = 0
        for node, entries in near.items():
            for foe in foes_by_sector.get(node[0], ()):
                d = walk.nearest(entries, foe["x"], foe["y"])
                if d <= GUARD_REACH:
                    count += 1
                if best is None or d < best[0]:
                    best = (d, foe)
        item["guards"] = count
        if best and best[0] <= BESIDE_FIGHT * 2:
            item["foe"] = round(best[0])
            if item["at"] is not None and best[1]["at"] is not None:
                item["foe_first"] = best[1]["at"] <= item["at"]
        item["fight"] = ("at" if item["foe"] is not None and item["foe"] <= AT_FIGHT else
                         "beside" if item["foe"] is not None and item["foe"] <= BESIDE_FIGHT else "between")
        item["foes_before"] = None if item["at"] is None else round(
            sum(f["health"] for f in foes if f["at"] is not None and f["at"] < item["at"]) / total_health, 3)
        item["stands"] = stands_on(geo, live, item)
    for number, members in enumerate(groups(items)):
        same = Counter(items[i]["name"] for i in members)
        for i in members:
            items[i]["group"] = len(members)
            items[i]["same"] = same[items[i]["name"]]
            items[i]["group_id"] = number

    keys, locks = _keys(live, walk, chains, items, foes, length)
    return {
        "map": name, "skill": skill,
        "sectors": len(live.sectors), "reached": len(walk.reached()),
        "rescued": len(walk.rescued_sectors),
        "length": round(length), "way_is": way_is,
        "exits": [{**e, "at": _round(e["at"], 0)} for e in exits],
        "areas": _areas(walk, length, foes, items),
        "items": items, "foes": foes, "keys": keys, "locks": locks, "secrets": secrets,
        "budget": budget(items, foes),
    }


def _areas(walk: Walk, length: float, foes, items) -> list[dict[str, Any]]:
    """The map by how many keys a place needs: 0 is open from the start."""
    out: dict[int, dict[str, Any]] = {}
    for node, row in walk.nodes.items():
        area = out.setdefault(len(row["needs"]), {"sectors": set(), "first": None, "last": None})
        area["sectors"].add(node[0])
        at = row["entries"][0][0] / length
        area["first"] = at if area["first"] is None else min(area["first"], at)
        area["last"] = at if area["last"] is None else max(area["last"], at)
    return [{"area": number, "sectors": len(row["sectors"]), "from": round(row["first"], 3),
             "to": round(row["last"], 3),
             "foes": sum(1 for f in foes if f["area"] == number),
             "foe_health": sum(f["health"] for f in foes if f["area"] == number),
             "items": sum(1 for i in items if i["area"] == number)}
            for number, row in sorted(out.items())]


def budget(items: Sequence[Mapping[str, Any]], foes: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Ammo damage and health against the health of what fights."""
    health = sum(f["health"] for f in foes)
    placed = [f for f in foes if not f["spawned"]]
    by_ammo: Counter = Counter()
    hidden = 0.0
    for item in items:
        if item["kind"] in ("weapon", "ammo"):
            by_ammo[item["ammo"]] += damage_of(item)
            if item.get("secret"):
                hidden += damage_of(item)
    dropped = sum(DROPS[f["type"]][1] * DAMAGE_PER_ROUND[DROPS[f["type"]][0]]
                  for f in foes if f["type"] in DROPS)
    damage = sum(by_ammo.values())
    heal = sum(i["points"] for i in items if i["kind"] == "health")
    heal_hidden = sum(i["points"] for i in items if i["kind"] == "health" and i.get("secret"))
    armor = sum(i["points"] for i in items if i["kind"] == "armor")
    per = max(health, 1)
    return {
        "foes": len(foes), "placed": len(placed), "spawn_markers": len(foes) - len(placed),
        "foe_health": health, "by_foe": dict(sorted(Counter(f["name"] for f in foes).items())),
        "ammo_damage": round(damage), "ammo_damage_in_secrets": round(hidden),
        "ammo_damage_by_kind": {k: round(v) for k, v in sorted(by_ammo.items())},
        "expected_drops": round(dropped),
        "damage_per_health": _round(damage / per), "damage_outside_secrets_per_health": _round((damage - hidden) / per),
        "damage_with_drops_per_health": _round((damage + dropped) / per),
        "health": heal, "health_in_secrets": heal_hidden, "armor": armor,
        "health_per_100": _round(100 * heal / per, 1), "armor_per_100": _round(100 * armor / per, 1),
    }


def _secrets(disk: Any, walk: Walk, roots, items, foes) -> list[dict[str, Any]]:
    """Each secret: what it holds, what opened it, who is in it."""
    everything = walk.reached()
    main = {node: row for node, row in walk.nodes.items()}
    sector_nodes = {s: list(n) for s, n in walk._sector_nodes.items()}
    out = []
    other = copy(walk)                    # the same map, walked again with something left undone
    for root in roots:
        region: set[int] = set()
        picked: set[int] = set()
        sector = root["sector"]
        causes = root["cause"]
        pickup = root["kind"] == "sprite" and "pickup" in causes
        if pickup:
            picked.add(int(root["root"].split()[1]))
            event = next((main[n]["opener"] for n in sector_nodes.get(sector, ())), None)
            if event is not None and len(event.get("sectors", ())) <= 8:
                region = set(event["sectors"])
            elif len(disk.sectors) and walk.geo.area(sector) < 1.6e6:
                region = {sector}
        else:
            walked = root["kind"] == "sector" and ("enter" in causes or "exit" in causes)
            if walked:
                other.run(avoid_sectors={sector}, distances=False)
            else:
                other.run(avoid_acts={root["root"]}, distances=False)
            region = everything - other.reached()
            if len(region) > max(6, SECRET_SHARE * len(everything)):
                region = {sector} if walked else set()
            if walked:
                region.add(sector)
        if sector not in everything:
            # the walk never came here: what hangs together with it and was not walked either
            region, edge = {sector}, {sector}
            while edge and len(region) <= 12:
                edge = {t for s in edge for t in walk.graph.reach.graph.get(s, ())
                        if t not in everything} - region
                region |= edge
        row = next((main[n] for n in sector_nodes.get(sector, ())), None)
        if not region and not pickup:
            region = {sector} if walk.geo.area(sector) < 6e6 else set()
        # what let a body in: the event that opened the secret's own sector, else its way in
        action = None if row is None or row["opener"] is None else row["opener"]["act"]
        if not pickup and root["kind"] != "sector" and "pickup" not in causes:
            opened = {"push": "push it", "vector": "shoot it", "destroyed": "break it"}.get(causes[0], causes[0])
            opened = {"sprite": "a switch or object", "wall": "push a wall"}.get(root["kind"], opened)
        elif action is not None and len(row["opener"].get("sectors", ())) <= max(
                10, 0.08 * len(everything)):
            opened = _act_words(disk, action, walk._hand_walls)
        else:
            opened = _open_way(walk, sector, main, sector_nodes)
        mine = [i for i in items if i["sector"] in region or i["sprite"] in picked]
        if not mine:
            # the credit is given at the door of it: look at what the act moves, and next door
            about = {sector} | {int(step["to"].split()[1]) for step in root["steps"]
                                if step["to_kind"] == "sector"}
            small = {t for s in about for t in walk.graph.reach.graph.get(s, ()) if walk.geo.area(t) < 3e6}
            near_by = {i["sector"] for i in items if i["sector"] in (about | small)
                       and walk.geo.area(i["sector"]) < 6e6}
            region |= near_by
            mine = [i for i in items if i["sector"] in near_by]
        point = ((mine[0]["x"], mine[0]["y"]) if mine else walk.middle(sector))
        near, _f = walk.spread([(0.0, walk.node(sector, *point), point)], walk.gates, rescued=True,
                               limit=GUARD_REACH)
        guards = [f for f in foes if f["sector"] in region or any(
            n[0] == f["sector"] and walk.nearest(e, f["x"], f["y"]) <= GUARD_REACH
            for n, e in near.items())]
        at = None if row is None else row["entries"][0][0]
        out.append({
            "root": root["root"], "sector": sector, "super": root["super"], "by": "/".join(causes),
            "opened": opened, "act": (None if action is None else action.describes()),
            "region": sorted(region), "picked": sorted(picked), "at": at,
            "needs": None if row is None else sorted(row["needs"]),
            "reward": sorted((i["name"] for i in mine)), "tier": max((i["tier"] for i in mine), default=0),
            "guards": len(guards), "guards_inside": sum(1 for f in guards if f["sector"] in region)})
    return out


def _open_way(walk: Walk, sector: int, main, sector_nodes) -> str:
    """How a secret nobody opens is kept out of the way: climb, water, drop, or a look round a corner."""
    for node in sector_nodes.get(sector, ()):
        if walk.geo.underwater(sector):
            return "under water"
        if main[node]["rescued"]:
            return "a jump or climb our reader does not see"
        via = main[node]["via"]
        hops = 0
        while via is not None and hops < 4:
            row = walk.cross[via]
            if row["kind"] == "link":
                return "through water or a stacked link"
            if row["rise"] > WALK_RISE:
                return "a jump up"
            if row["rise"] < -2 * BODY:
                return "a drop"
            via, hops = main[row["a"]]["via"] if row["a"] in main else None, hops + 1
    return "open: out of the way"


def _lock_reading(disk: Any, walk: Walk, chain, kind: str, index: int) -> tuple[str, list[int]]:
    """What a lock works: a door, a lift, a switch; and the sectors that move."""
    sectors = []
    others: Counter = Counter()
    if kind == "sector":
        sectors.append(index)
    if chain is not None:
        for step in chain["steps"]:
            if step["to_kind"] == "sector":
                sectors.append(int(step["to"].split()[1]))
            elif step["to"] == "engine":
                others[step["to_type"]] += 1
            else:
                others[step["to_type"]] += 1
    moving = sorted({s for s in sectors if int(walk.geo.fields[s]["type"]) in Z_MOVERS | SWEPT | {612}})
    if moving:
        kinds = {int(walk.geo.fields[s]["type"]) for s in moving}
        if kinds & {615, 617, 613}:
            return "a swinging door", moving
        if kinds & {614, 616}:
            return "a sliding door", moving
        if 612 in kinds:
            return "a ride", moving
        for s in moving:
            e = walk.geo.extra[s]
            floor = abs(int(e.get("off_floor_z") or 0) - int(e.get("on_floor_z") or 0))
            roof = abs(int(e.get("off_ceiling_z") or 0) - int(e.get("on_ceiling_z") or 0))
            if roof and roof >= floor:
                return "a rising door", moving
        return "a lift or floor", moving
    if any("Exit" in name for name in others):
        return "the exit", []
    if others:
        return "wiring (" + ", ".join(sorted(others)[:3]) + ")", []
    return "nothing we can read", []


def _keys(disk: Any, walk: Walk, chains, items, foes, length: float):
    """Every key in the order it is come to, and every lock."""
    roots = {chain["root"]: chain for chain in chains}
    owners = walk.geo.owner
    locks: list[dict[str, Any]] = []
    for kind, group in (("sector", disk.sectors), ("wall", disk.walls), ("sprite", disk.sprites)):
        for index, record in enumerate(group):
            wants = int((record_extra(record) or {}).get("key", 0) or 0)
            if not wants:
                continue
            f = record_fields(record)
            if kind == "sprite":
                category = classify("sprite", int(f["type"])).get("category")
                if category in ("dude", "key", "weapon", "ammo", "health", "armor", "powerup"):
                    continue
                sector, x, y = int(f["sector"]), float(f["x"]), float(f["y"])
            elif kind == "sector":
                sector, (x, y) = index, walk.middle(index)
            else:
                sector = owners.get(index, -1)
                (ax, ay), (bx, by) = walk.geo.at[index], walk.geo.at[walk.geo.point2[index]]
                x, y = (ax + bx) / 2, (ay + by) / 2
            if sector < 0:
                continue
            what, moving = _lock_reading(disk, walk, roots.get(f"{kind} {index}"), kind, index)
            # the front: the nearest reached place that needs the fewest keys
            near = {sector} | set(walk.graph.reach.graph.get(sector, ()))
            if kind == "wall" and walk.geo.next[index] >= 0:
                near.add(walk.geo.next[index])
            fronts = []
            for s in near:
                for node in walk._sector_nodes.get(s, ()):
                    row = walk.nodes[node]
                    fronts.append((wants in row["needs"], walk.nearest(row["entries"], x, y), node))
            fronts.sort(key=lambda t: (t[0], t[1], t[2]))
            front = fronts[0] if fronts and not fronts[0][0] else None
            locks.append({"object": f"{kind} {index}", "key": wants, "key_name": KEY_NAMES.get(wants),
                          "sector": sector, "x": x, "y": y, "works": what, "moves": moving,
                          "front_at": None if front is None else front[1],
                          "front_node": None if front is None else front[2]})
    # one lock is many faces: gather by key and by what moves
    gathered: dict[Any, dict[str, Any]] = {}
    for lock in locks:
        mark = (lock["key"], tuple(lock["moves"]) or (lock["works"], lock["sector"]))
        old = gathered.get(mark)
        if old is None:
            gathered[mark] = {**lock, "faces": 1}
        else:
            old["faces"] += 1
            if lock["front_at"] is not None and (old["front_at"] is None or lock["front_at"] < old["front_at"]):
                old.update({k: lock[k] for k in ("front_at", "front_node", "x", "y", "object", "sector")})
    locks = sorted(gathered.values(), key=lambda l: (l["key"], l["front_at"] is None, l["front_at"] or 0))
    for lock in locks:
        mine = [e for e in walk.events if lock["key"] in e["needs"]]
        lock["opens_sectors"] = len({s for node, row in walk.nodes.items() if lock["key"] in row["needs"]
                                     for s in [node[0]]})
        lock["gates_anything"] = bool(mine)
        lock["front_way"] = None if lock["front_at"] is None else round(lock["front_at"] / length, 3)
        lock["front_at"] = _round(lock["front_at"], 0)

    out = []
    for item in items:
        if item["kind"] != "key":
            continue
        key = item["key"]
        mine = [l for l in locks if l["key"] == key and l["works"] != "nothing we can read"] or [
            l for l in locks if l["key"] == key]
        spread = walk.key_spread.get(key) if walk.key_sprite.get(key) == item["sprite"] else None
        back = []
        for lock in mine:
            if lock["front_at"] is None:
                continue
            there = None
            if spread is not None and item["at"] is not None:
                got = spread.get(lock["front_node"])
                if got:
                    there = walk.nearest(got, lock["x"], lock["y"]) - item["at"]
            back.append((lock["front_at"], there, lock))
        first = min(back, key=lambda t: t[0], default=None)
        walked = min((t[1] for t in back if t[1] is not None), default=None)
        chain = roots.get(f"sprite {item['sprite']}") if not item["carried_by"] else None
        woken: Counter = Counter()
        for c in ([chain] if chain else []) + [
                c for c in chains if c["root"] == f"sector {item['sector']}" and "enter" in c["cause"]
                and walk.geo.area(item["sector"]) < 12e6]:
            for step in c["steps"]:
                if step["to_kind"] == "sprite" and (200 <= step["to_type_id"] < 255
                                                    or step["to_type_id"] == SPAWN_MARKER):
                    woken["dudes"] += 1
                elif step["to_kind"] == "sector":
                    s = int(step["to"].split()[1])
                    woken["sectors"] += 1
                    woken["dudes"] += sum(1 for f in foes if f["sector"] == s or (
                        int(walk.geo.fields[s]["type"]) in Z_MOVERS | SWEPT
                        and f["sector"] in walk.graph.reach.graph.get(s, ()) and
                        f["sector"] not in walk.reached()))
                elif step["to"] == "engine":
                    woken["engine"] += 1
                else:
                    woken["sprites"] += 1
        opened = [e for e in walk.events if e["act"].kind == "pick_up" and e["act"].index == item["sprite"]]
        met_first = None
        if first is not None and item["at"] is not None:
            met_first = first[0] < item["at"]
        out.append({
            "sprite": item["sprite"], "key": key, "name": KEY_NAMES[key], "sector": item["sector"],
            "carried_by": item["carried_by"], "at": _round(item["at"], 0), "way": _round(item["way"]),
            "needs": item["needs"], "secret": item.get("secret", False),
            "stands": item["stands"]["on"], "raised": item["stands"]["raised"],
            "corpse": item["stands"]["corpse"], "guards": item["guards"],
            "taken_first": walk.key_sprite.get(key) == item["sprite"],
            "locks": len(mine), "opens": sorted({l["works"] for l in mine}),
            "gates": any(key in row["needs"] for row in walk.nodes.values()),
            "unlocks_sectors": len({n[0] for n, r in walk.nodes.items() if key in r["needs"]}),
            "lock_way": None if first is None else round(first[0] / length, 3),
            "lock_met_first": met_first,
            "to_lock": _round(walked, 0), "to_lock_way": None if walked is None else round(walked / length, 3),
            "out_from_lock": (None if first is None or item["at"] is None else round(item["at"] - first[0])),
            "glimpsed": _glimpse(walk, item),
            "on_pickup": dict(sorted(woken.items())),
            "opens_on_pickup": sum(len(e["sectors"]) for e in opened),
        })
    out.sort(key=lambda row: (row["at"] is None, row["at"] or 0, row["sprite"]))
    for lock in locks:
        lock.pop("front_node", None)
    return out, locks


def _glimpse(walk: Walk, item: Mapping[str, Any], reach: float = 12288) -> dict[str, Any] | None:
    """Whether a key is seen from well before it can be had, and from where.

    From the points a body has passed, with at least 6,144 of walking and
    twice the plain distance still to go. The line is clear of walls in the
    load pose; a masked window is seen through.
    """
    if item["at"] is None:
        return None
    geo = walk.geo
    target = (item["x"], item["y"], item["z"] - 1024)
    tried = 0
    points = []
    for node, row in walk.nodes.items():
        for at, p in row["entries"][:3]:
            plain = hypot(p[0] - item["x"], p[1] - item["y"])
            if plain <= reach and item["at"] - at >= max(6144, 2 * plain):
                points.append((at, node[0], p))
    for at, sector, p in sorted(points):
        tried += 1
        if tried > 240:
            break
        # a step off the portal, so the line does not run along it
        mx, my = walk.middle(sector)
        x, y = p[0] + (mx - p[0]) * 0.05, p[1] + (my - p[1]) * 0.05
        if not geo.contains(sector, x, y):
            x, y = p
        eye = (x, y, geo.height(sector, x, y) - EYE)
        if geo.sees(sector, eye, target):
            return {"from_sector": sector, "walked": round(at), "still_to_go": round(item["at"] - at),
                    "plain": round(hypot(p[0] - item["x"], p[1] - item["y"]))}
    return None
