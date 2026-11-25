"""How shipped maps hide a secret: what stands before it, what opens that, what gives it away, and what is inside.

`bloodmap.supplies` finds a map's secrets (every chain that ends at the
engine's secret counter) and the region each one holds. This takes the walk
it made, follows the way back out of the region, and reads what is in it:

* **the gate**: a sector that moves (600/602 up or down, 614/616 aside,
  613/615/617 round), a wall or thing that breaks, a crack, or no gate at all
  and then how the place is kept (a climb, a jump, a drop, a crawl, water, a
  teleport, or only a corner);
* **the trigger**: the panel itself, another wall, a sprite (a switch tile, or
  a prop that answers a push), a shot, a blast, a step, a pickup, a kill; how
  far it is from the gate and whether the gate is in sight of it;
* **the face**: what the panel wears against the wall it stands in: the same
  tile running through, the same tile with its pattern broken or its shade
  changed, another tile, or a sprite hung on it. That is the tell;
* **the window**: whether the thing inside is seen from ordinary ground in
  the pose the level loads with, and through what (bars, glass, a hole).

.. code-block:: bash

    python -m tools.mine_secrets                       # write the study's json and print the counts
    python -m tools.mine_secrets show E3M3             # one map's secrets, one by one
    python -m tools.mine_secrets show projects/blood-city/level/blood-city-current.MAP
    python -m tools.mine_secrets buttons               # sectors that go in a little when pressed
    python -m tools.mine_secrets bars                  # bars that a moving sector carries, and who moves them
    python -m tools.mine_secrets record E1M2 s:261 ch:160    # every set field of a sector, wall (w:), sprite (p:), channel

The reading is in ``knowledge/blood/studies/secrets/notes.md``.

What it cannot see: a tell that is not in the records (a room shown in a
mirror, a book that stands out by its drawing), how hard a jump is, and which
of two ways in a player takes. The way is the walk's shortest. Stacked rooms
are not looked through, so a thing seen across one counts as not seen.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter, defaultdict
from math import hypot
from typing import Any, Iterable

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bloodmap import supplies, wiring
from bloodmap.corpus import campaign_maps, corpus_map_path, named_maps
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.sector_geom import sector_walls, wall_owners

OUTPUT = ROOT / "knowledge" / "blood" / "studies" / "secrets" / "secrets.json"
SCHEMA = "llmapper.secrets"
BODY, EYE = PLAYER_PROFILES["blood"].standing_height, PLAYER_PROFILES["blood"].eye_height
#: Sector types that move, and what they do.
MOTION = {600: "rises or sinks", 602: "carries sprites up or down", 612: "travels a path",
          613: "turns by steps", 614: "slides", 615: "turns", 616: "slides", 617: "turns"}
GIB_WALL = 511
THING_WORDS = {406: "glass", 408: "crack", 411: "metal grate"}
#: How far from the outside an item is looked for, and how many rays a secret is given.
SIGHT, RAYS = 12288, 700
#: Tiles that are bars, grates and gates, by the library's names for them.
BARS = frozenset({58, 59, 104, 116, 155, 218, 330, 331, 332, 376, 403, 428, 439, 463, 464, 465, 466, 502, 699,
                  1044, 1055, 1056, 1060, 1064, 1065})


def said(fields: dict[str, Any]) -> dict[str, Any]:
    """The fields of a record that are set."""
    return {k: v for k, v in fields.items() if v not in (0, -1, None) and k not in ("extra", "index", "reference")}


def find(name: str) -> pathlib.Path:
    path = pathlib.Path(name)
    return path if path.suffix.upper() == ".MAP" and path.exists() else corpus_map_path(name)


class Art:
    """Widths and see-through shares of tiles; empty where the game's art is not there."""

    def __init__(self) -> None:
        self.width: dict[int, int] = {}
        self.holes: dict[int, float] = {}
        try:
            from bloodmap.art import read_art_directory
            from tools.tile_usage import ART_DIR
            for number, tile in read_art_directory(ART_DIR).items():
                if tile.width and tile.height:
                    self.width[number] = tile.width
                    self.holes[number] = tile.pixels.count(255) / len(tile.pixels)
        except (OSError, ImportError, ValueError):
            pass


_ART: Art | None = None


def art() -> Art:
    global _ART
    if _ART is None:
        _ART = Art()
    return _ART


# ---------------------------------------------------------------------------
# One map
# ---------------------------------------------------------------------------

class Reading:
    """One map's secrets, gate by gate."""

    def __init__(self, disk: Any, name: str = ""):
        self.name = name
        self.disk = supplies.as_launched(disk)
        self.walk = supplies.Walk(self.disk).run()
        self.geo = self.walk.geo
        self.owner = self.geo.owner
        self.chains = wiring.chains(self.disk)
        self.by_root = {c["root"]: c for c in self.chains}
        foes = supplies.fighters(self.disk)
        self.items = supplies.pickups(self.disk, foes)
        roots = supplies._secret_roots(self.disk, self.chains)
        self.secrets = supplies._secrets(self.disk, self.walk, roots, self.items, foes)
        self.walls = [record_fields(w) for w in self.disk.walls]
        self.wall_x = [record_extra(w) or {} for w in self.disk.walls]
        self.sprites = [record_fields(s) for s in self.disk.sprites]
        self.sprite_x = [record_extra(s) or {} for s in self.disk.sprites]
        self.before = {int(self.walls[w]["point2"]): w for s in range(len(self.disk.sectors)) for w in self.geo.walls[s]}
        self.standing: dict[int, list[int]] = defaultdict(list)
        for i, f in enumerate(self.sprites):
            self.standing[int(f["sector"])].append(i)
        #: moving sector -> the chains that work it
        self.works: dict[int, list[dict]] = defaultdict(list)
        for chain in self.chains:
            if not chain["silent"]:
                for target in {int(s["to"].split()[1]) for s in chain["steps"] if s["to_kind"] == "sector"}:
                    self.works[target].append(chain)

    # -- places -----------------------------------------------------------------

    def moves(self, sector: int) -> bool:
        kind = int(self.geo.fields[sector]["type"])
        if kind in (600, 602):
            return self.geo.z_mover(sector)
        return kind in MOTION and bool(self.geo.extra[sector])

    def carries_a_body(self, sector: int) -> bool:
        """A lift: what moves is the floor, and it starts level with nothing it shuts."""
        e = self.geo.extra[sector]
        floor = int(e.get("on_floor_z") or 0) - int(e.get("off_floor_z") or 0)
        roof = int(e.get("on_ceiling_z") or 0) - int(e.get("off_ceiling_z") or 0)
        f = self.geo.fields[sector]
        return bool(floor and not roof and int(f["floor_z"]) - int(f["ceiling_z"]) > BODY)

    def middle(self, sector: int) -> tuple[float, float, float]:
        x, y = self.walk.middle(sector)
        return x, y, float(self.geo.fields[sector]["floor_z"]) - EYE

    def trigger_place(self, kind: str, index: int) -> tuple[int, float, float, float]:
        if kind == "sprite":
            f = self.sprites[index]
            return int(f["sector"]), float(f["x"]), float(f["y"]), float(f["z"])
        if kind == "wall":
            a, b = self.geo.at[index], self.geo.at[self.geo.point2[index]]
            sector = self.owner.get(index, -1)
            f = self.geo.fields[sector]
            return sector, (a[0] + b[0]) / 2, (a[1] + b[1]) / 2, float(f["floor_z"]) - EYE
        return (index, *self.middle(index))

    def distance(self, at: tuple[float, float], sector: int) -> float:
        return min((supplies._to_segment(at[0], at[1], a, b) for _w, a, b in self.geo.segments(sector)), default=0.0)

    # -- what stands before it ----------------------------------------------------

    def trail(self, secret: dict[str, Any]) -> list[dict[str, Any]]:
        """The crossings from the secret's sector back to ordinary ground."""
        walk, region = self.walk, set(secret["region"]) | {secret["sector"]}
        node = next(iter(walk._sector_nodes.get(secret["sector"], ())), None)
        out: list[dict[str, Any]] = []
        outside = 0
        while node is not None and len(out) < 24 and outside < 2:
            via = walk.nodes[node]["via"]
            if via is None:
                break
            row = walk.cross[via]
            out.append(row)
            node = row["a"]
            if node[0] not in region:
                outside += 1
                if not self.moves(node[0]):
                    break
        return out

    def gates(self, secret: dict[str, Any], trail: list[dict[str, Any]]) -> list[int]:
        """The moving sectors between a secret and ordinary ground: on its way in, or moved by what credits it."""
        found: list[int] = []

        def add(s):
            if s is not None and s not in found and self.moves(s):
                found.append(s)
        if secret["by"] not in ("enter", "exit", "pickup", "itself"):
            kind, index = secret["root"].split()
            if kind == "sector":
                add(int(index))
            for step in secret_steps(self, secret):
                if step["to_kind"] == "sector":
                    add(int(step["to"].split()[1]))
        for row in trail:
            add(row["b"][0])
            for s in row.get("movers", ()) or ():
                add(s)
            add(self.walk.graph.swept_blocked.get((row["a"][0], row["b"][0])))
            add(row["a"][0])
        node = next(iter(self.walk._sector_nodes.get(secret["sector"], ())), None)
        event = None if node is None else self.walk.nodes[node]["opener"]
        if event and len(event.get("sectors", ())) <= 10:
            act = event["act"]
            name = f"{act.what or {'use_switch': 'sprite', 'use_wall': 'wall', 'destroy': 'sprite'}.get(act.kind, 'sector')} {act.index}"
            near = set(secret["region"]) | {secret["sector"]}
            if act.kind == "operate" and act.index not in self.walk._hand_walls and act.index < len(self.disk.sectors):
                add(act.index)
            answer = [int(step["to"].split()[1]) for step in (self.by_root.get(name) or {"steps": ()})["steps"]
                      if step["to_kind"] == "sector"]
            for s in answer:
                if s in near or near & set(self.walk.graph.reach.graph.get(s, ())):
                    add(s)
            if not found:
                for s in answer:
                    add(s)
        # a panel that bounds the region and which the way did not need to cross
        if not found:
            for s in sorted(set(secret["region"]) | {secret["sector"]}):
                for w in self.geo.walls[s]:
                    there = self.geo.next[w]
                    if there >= 0 and (self.works.get(there) or self.geo.extra[there].get("trigger_wall_push")):
                        add(there)
        # a leaf before a lift: what shuts a place comes before what carries a body to it
        found.sort(key=self.carries_a_body)
        return found[:4]

    def openers(self, gate: int, inside: set[int]) -> list[dict[str, Any]]:
        """What works a moving sector: itself, a wall, a sprite, a step, a shot."""
        out = []
        extra = self.geo.extra[gate]
        for flag, cause in (("trigger_wall_push", "wall_push"), ("trigger_push", "push"), ("trigger_enter", "enter")):
            if extra.get(flag):
                out.append({"kind": "sector", "index": gate, "cause": cause, "tile": None, "panel": True, "depth": 0,
                            "type": int(self.geo.fields[gate]["type"]), "key": int(extra.get("key") or 0)})
        for chain in self.works.get(gate, ()):
            kind, index = chain["root"].split()
            index = int(index)
            if kind == "sector" and index == gate:
                continue
            depth = 0 if any(s["to"] == f"sector {gate}" and s["from"] == chain["root"] for s in chain["steps"]) else 1
            record = {"sprite": self.disk.sprites, "wall": self.disk.walls, "sector": self.disk.sectors}[kind][index]
            f = record_fields(record)
            sector = chain["sector"]
            facing = kind == "wall" and (self.owner.get(index) == gate or self.geo.next[index] == gate)
            if facing and self.faces_in(gate, index, inside):
                facing, sector = False, next(iter(inside), sector)
            carried = kind == "sprite" and sector == gate
            out.append({"kind": kind, "index": index, "cause": "/".join(chain["cause"]), "type": int(f["type"]),
                        "tile": int(f.get("picnum", -1)) if kind != "sector" else None,
                        "panel": facing or carried, "depth": depth, "sector": sector, "key": chain["key"],
                        "inside": sector in inside and not (facing or carried),
                        "unseen": kind == "sprite" and bool(int(f["cstat"]) & 0x8000)})
        out.sort(key=lambda o: (o.get("inside", False), not o["panel"], o["depth"]))
        return out

    def faces_in(self, gate: int, wall: int, inside: set[int]) -> bool:
        """Whether a wall of a gate is on the secret's side of it: pushed to get out, not in."""
        inner = inside - {gate}
        if self.owner.get(wall) in inner:
            return True
        if self.owner.get(wall) != gate:
            return False
        there = self.geo.next[wall]
        if there >= 0:
            return there in inner

        def to(side):
            ways = [w for w in self.geo.walls[gate] if self.geo.next[w] >= 0 and (self.geo.next[w] in inner) == side]
            (ax, ay), (bx, by) = self.geo.at[wall], self.geo.at[self.geo.point2[wall]]
            return min((supplies._to_segment((ax + bx) / 2, (ay + by) / 2, self.geo.at[w], self.geo.at[self.geo.point2[w]])
                        for w in ways), default=None)
        near, far = to(True), to(False)
        return near is not None and far is not None and near < far * 0.8

    def trigger(self, gate: int, opener: dict[str, Any]) -> dict[str, Any]:
        """Where an opener is from its gate, and whether the gate is seen from it."""
        if opener["panel"]:
            return {"away": 0, "gate_in_sight": None}
        sector, x, y, _z = self.trigger_place(opener["kind"], opener["index"])
        seen = False
        if sector >= 0:
            stand = self.stand(sector, x, y)
            for w in self.geo.walls[gate]:
                there = self.geo.next[w]
                if there < 0:
                    continue
                a, b = self.geo.at[w], self.geo.at[self.geo.point2[w]]
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                tx, ty = mx + (stand[0] - mx) * 0.02, my + (stand[1] - my) * 0.02
                if self.sight(sector, stand, (tx, ty, float(self.geo.fields[there]["floor_z"]) - EYE))[0]:
                    seen = True
                    break
        return {"away": round(self.distance((x, y), gate)), "gate_in_sight": seen}

    def stand(self, sector: int, x: float, y: float) -> tuple[float, float, float]:
        cx, cy = self.walk.middle(sector)
        d = hypot(cx - x, cy - y) or 1.0
        step = min(384.0, d / 2)
        px, py = x + (cx - x) / d * step, y + (cy - y) / d * step
        if not self.geo.contains(sector, px, py):
            px, py = x, y
        return px, py, self.geo.height(sector, px, py) - EYE

    def sight(self, sector: int, eye, at, limit: int = 64) -> tuple[bool, list[int]]:
        """`Geometry.sees` with masked walls read: what a line goes through, and an opaque one stops it."""
        geo, holes = self.geo, art().holes
        ex, ey, ez = eye
        dx, dy, dz = at[0] - ex, at[1] - ey, at[2] - ez
        here, reached = sector, 0.0
        through: list[int] = []
        passed = {sector}
        for _ in range(limit):
            best = None
            for wall, (ax, ay), (bx, by) in geo.segments(here):
                wx, wy = bx - ax, by - ay
                cross = dx * wy - dy * wx
                if abs(cross) < 1e-9:
                    continue
                t = ((ax - ex) * wy - (ay - ey) * wx) / cross
                u = ((ax - ex) * dy - (ay - ey) * dx) / cross
                if reached + 1e-7 < t <= 1.0 and -1e-6 <= u <= 1 + 1e-6 and (best is None or t < best[0]):
                    best = (t, wall)
            if best is None:
                if not geo.contains(here, at[0], at[1]):
                    return False, through
                return True, through + self.bars_between(passed, eye, at)
            t, wall = best
            beyond = geo.next[wall]
            if beyond < 0:
                return False, through
            z = ez + dz * t
            for side in (here, beyond):
                f = geo.fields[side]
                if not int(f["ceiling_z"]) <= z <= int(f["floor_z"]):
                    return False, through
            cstat = geo.cstat[wall]
            if cstat & 32:
                return False, through
            if cstat & 16:
                tile = int(self.walls[wall]["over_picnum"])
                if holes and holes.get(tile, 0.0) < 0.02 and not cstat & 128:
                    return False, through
                through.append(tile)
            here, reached = beyond, t
            passed.add(here)
            # a shut leaf stands exactly in its doorway: the portal and the leaf are one line
            for wall, (ax, ay), (bx, by) in geo.segments(here):
                cross = dx * (by - ay) - dy * (bx - ax)
                if geo.next[wall] >= 0 or abs(cross) < 1e-9:
                    continue
                if abs(((ax - ex) * (by - ay) - (ay - ey) * (bx - ax)) / cross - t) < 1e-6 and (
                        0.002 < ((ax - ex) * dy - (ay - ey) * dx) / cross < 0.998):
                    return False, through
        return False, through

    def bars_between(self, sectors: set[int], eye, at) -> list[int]:
        """Blocking wall sprites a line goes through."""
        out = []
        d = hypot(at[0] - eye[0], at[1] - eye[1]) or 1.0
        for s in sectors:
            for i in self.standing.get(s, ()):
                f = self.sprites[i]
                if int(f["cstat"]) & 48 != 16 or not int(f["cstat"]) & 1:
                    continue
                t = ((f["x"] - eye[0]) * (at[0] - eye[0]) + (f["y"] - eye[1]) * (at[1] - eye[1])) / d / d
                if not 0.02 < t < 0.98:
                    continue
                px, py = eye[0] + t * (at[0] - eye[0]), eye[1] + t * (at[1] - eye[1])
                if hypot(px - f["x"], py - f["y"]) < art().width.get(int(f["picnum"]), 64) * int(f["x_repeat"]) / 8:
                    out.append(int(f["picnum"]))
        return out

    # -- the face ----------------------------------------------------------------

    def face(self, gate: int, inside: set[int]) -> dict[str, Any] | None:
        """What the panel wears, against the wall it stands in."""
        geo = self.geo
        kind = int(geo.fields[gate]["type"])

        def length(w):
            (ax, ay), (bx, by) = geo.at[w], geo.at[geo.point2[w]]
            return hypot(bx - ax, by - ay)
        faces = [w for s in sorted(self.walk._sectors) if s != gate and s not in inside
                 for w in geo.walls[s] if geo.next[w] == gate]
        if kind in (613, 614, 615, 616, 617):
            own = [w for w in geo.walls[gate] if geo.cstat[w] & 49152 or kind in (613, 616, 617)]
            own = [w for w in own if not self.faces_in(gate, w, inside | {gate})] or own
            faces = [w for w in own if geo.next[w] < 0 or geo.cstat[w] & 16] or own or faces
        if not faces:
            return None
        wall = max(faces, key=length)
        f = self.walls[wall]
        home = self.owner[wall]
        lower = (kind in (600, 602) and geo.next[wall] == gate
                 and int(geo.fields[gate]["floor_z"]) < int(geo.fields[home]["floor_z"]) - 1024)
        shown = self.walls[geo.partner[wall]] if lower and int(f["cstat"]) & 2 and geo.partner[wall] >= 0 else f
        tile = int(shown["over_picnum"]) if int(shown["cstat"]) & 48 else int(shown["picnum"])
        beside = []
        (ax, ay), (bx, by) = geo.at[wall], geo.at[geo.point2[wall]]
        for w in (self.before.get(wall), int(f["point2"])):
            if w is None or self.owner.get(w) != home or length(w) < 64:
                continue
            (cx, cy), (dx, dy) = geo.at[w], geo.at[geo.point2[w]]
            turn = abs((bx - ax) * (dy - cy) - (by - ay) * (dx - cx)) / max(1.0, length(wall) * length(w))
            beside.append((turn, w, self.walls[w]))
        beside.sort(key=lambda b: b[0])
        decals = [int(s["picnum"]) for i, s in enumerate(self.sprites)
                  if int(s["cstat"]) & 48 == 16 and int(s["sector"]) in (home, gate) and not int(s["cstat"]) & 0x8000
                  and min(supplies._to_segment(float(s["x"]), float(s["y"]), at[wall], at[geo.point2[wall]])
                          for at in (geo.saved, geo.at)) < 48]
        out = {"wall": wall, "tile": tile, "shade": int(shown["shade"]), "pal": int(shown["pal"]),
               "wide": round(length(wall)), "decals": sorted(decals)}
        out["in_line"] = bool(beside) and beside[0][0] < 0.3
        if not beside:
            out["tell"] = "nothing beside it"
            return out
        g = beside[0][2]
        out["beside_tile"] = int(g["picnum"])
        out["shade_step"] = int(shown["shade"]) - int(g["shade"])
        width = art().width.get(tile, 64)
        first, second = (g, f) if int(g["point2"]) == wall else (f, g)
        runs_on = ((int(first["x_panning"]) + int(first["x_repeat"]) * 8 - int(second["x_panning"])) % width) in (
            0, 1, width - 1) and int(f["y_repeat"]) == int(g["y_repeat"])
        if out["beside_tile"] != tile:
            out["tell"] = "another tile"
        elif int(shown["pal"]) != int(g["pal"]):
            out["tell"] = "same tile, another colour"
        elif out["in_line"] and abs(out["shade_step"]) > 3:
            out["tell"] = "same tile, another shade"
        elif out["in_line"] and not runs_on:
            out["tell"] = "same tile, pattern broken"
        else:
            out["tell"] = "identical" if out["in_line"] else "same tile, in a bay or standing free"
        return out

    # -- the window -----------------------------------------------------------------

    def seen(self, secret: dict[str, Any], gates: set[int]) -> dict[str, Any]:
        """Whether what is in it shows from ordinary ground as the level loads."""
        geo, region = self.geo, set(secret["region"]) | {secret["sector"]} | gates
        things = [i for i in self.items if i["sector"] in region or i["sprite"] in secret["picked"]]
        spots = [(i["x"], i["y"], i["z"] - 2048) for i in things[:4]]
        if not spots:
            return {"seen": None, "through": [], "nearest": None}
        about: set[int] = set()
        edge = set(region)
        for _hop in range(5):
            edge = {t for s in edge for t in self.walk.graph.reach.graph.get(s, ())} - about - region
            about |= edge
        eyes = []
        for s in sorted(s for s in about if s in self.walk._sectors and not self.moves(s)):
            centre = self.walk.middle(s)
            points = [centre]
            for w in geo.walls[s][:24]:
                a, b = geo.at[w], geo.at[geo.point2[w]]
                mx, my = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
                points.append((mx + (centre[0] - mx) * 0.15, my + (centre[1] - my) * 0.15))
            eyes += [(s, x, y, geo.height(s, x, y) - EYE) for x, y in points if geo.contains(s, x, y)]
        best: tuple[list[int], float] | None = None
        rays = 0
        for x, y, z in spots:
            for s, ex, ey, ez in sorted(eyes, key=lambda e: hypot(e[1] - x, e[2] - y)):
                d = hypot(ex - x, ey - y)
                if d > SIGHT or rays > RAYS:
                    break
                if d < 256:
                    continue
                rays += 1
                ok, through = self.sight(s, (ex, ey, ez), (x, y, z))
                if ok and (best is None or (not through, -d) > (not best[0], -best[1])):
                    best = (through, d)
                    if not through:
                        break
        if best is None:
            return {"seen": False, "through": [], "nearest": None}
        return {"seen": True, "through": sorted(set(best[0])), "nearest": round(best[1])}

    # -- one secret --------------------------------------------------------------------

    def read(self, secret: dict[str, Any]) -> dict[str, Any]:
        inside = set(secret["region"]) | {secret["sector"]}
        trail = self.trail(secret)
        gates = self.gates(secret, trail)
        rows = []
        for gate in gates:
            kind = int(self.geo.fields[gate]["type"])
            extra = self.geo.extra[gate]
            rows.append({"sector": gate, "type": kind, "does": MOTION.get(kind, "?"), "lift": self.carries_a_body(gate),
                         "travel_z": [int(extra.get("on_floor_z") or 0) - int(extra.get("off_floor_z") or 0),
                                      int(extra.get("on_ceiling_z") or 0) - int(extra.get("off_ceiling_z") or 0)],
                         "travel_xy": travel(self.disk, gate),
                         "openers": [{**o, **self.trigger(gate, o)} for o in self.openers(gate, inside | set(gates))[:6]],
                         "face": self.face(gate, inside - {gate})})
        # a gate counts when something a body does works it from outside
        real = [g for g in rows if any(not o.get("inside") for o in g["openers"])]
        out = {"map": self.name, "root": secret["root"], "sector": secret["sector"], "credit": secret["by"],
               "super": secret["super"], "region": secret["region"], "reward": secret["reward"], "tier": secret["tier"],
               "guards": secret["guards"], "opened_by_the_walk": secret["opened"], "act": secret["act"],
               "gates": real, "breaks": self.breaks(secret, trail), "kept_by": self.keeps(secret, trail),
               "window": self.seen(secret, {g["sector"] for g in real})}
        out["gate"], out["opened"], out["tile"] = self.kinds(out, secret)
        return out

    def breaks(self, secret, trail) -> list[dict[str, Any]]:
        """Walls, cracks and things on the way that are broken rather than worked."""
        out, seen = [], set()
        for row in trail:
            w = row.get("wall")
            if w is None:
                continue
            for wall in (w, self.geo.partner[w]):
                if 0 <= wall < len(self.walls) and int(self.walls[wall]["type"]) == GIB_WALL and wall not in seen:
                    seen.add(wall)
                    out.append({"what": "wall", "index": wall, "tile": int(self.walls[wall]["over_picnum"]),
                                "by": [c for c in ("vector", "impact", "push", "touch")
                                       if self.wall_x[wall].get(f"trigger_{c}")]})
            for s in sorted({row["a"][0], row["b"][0]}):
                for i in self.standing.get(s, ()):
                    if int(self.sprites[i]["type"]) == 411 and i not in seen:
                        seen.add(i)
                        out.append({"what": "metal grate", "index": i, "tile": int(self.sprites[i]["picnum"]),
                                    "by": ["impact"]})
        node = next(iter(self.walk._sector_nodes.get(secret["sector"], ())), None)
        event = None if node is None else self.walk.nodes[node]["opener"]
        if event and len(event.get("sectors", ())) <= max(10, 0.08 * len(self.walk._sectors)):
            act = event["act"]
            if act.kind in ("operate", "shoot") and act.what in ("", "wall") and (
                    act.what == "wall" or act.index in self.walk._hand_walls) and act.index not in seen and (
                        act.index < len(self.walls)):
                out.insert(0, {"what": "wall", "index": act.index, "tile": int(self.walls[act.index]["over_picnum"]),
                               "by": [c for c in ("vector", "impact", "push", "touch")
                                      if self.wall_x[act.index].get(f"trigger_{c}")]})
            elif act.kind in ("destroy", "shoot") and act.index not in seen and act.what in ("", "sprite"):
                f = self.sprites[act.index]
                out.insert(0, {"what": THING_WORDS.get(int(f["type"]), "object"), "index": act.index,
                               "tile": int(f["picnum"]),
                               "by": [c for c in ("vector", "impact") if self.sprite_x[act.index].get(f"trigger_{c}")]
                               or ["destroyed"]})
        return out

    def keeps(self, secret, trail) -> list[str]:
        out = []
        for row in trail:
            if row["kind"] in ("link", "teleport"):
                out.append("water or a stacked link" if row["kind"] == "link" else "a teleporter")
            elif row["kind"] == "leap":
                out.append("a running jump")
            elif row["kind"] == "portal":
                a, b = row["a"][0], row["b"][0]
                floor = min(self.geo.fields[a]["floor_z"], self.geo.fields[b]["floor_z"])
                roof = max(self.geo.fields[a]["ceiling_z"], self.geo.fields[b]["ceiling_z"])
                moving = self.moves(a) or self.moves(b)
                if row["rise"] > supplies.WALK_RISE and not moving and not self.geo.underwater(a):
                    out.append("a climb past a jump" if row["rise"] > supplies.MAX_RISE else "a jump up")
                elif row["rise"] < -2 * BODY:
                    out.append("a drop")
                if not moving and 0 < floor - roof < BODY * 0.8:
                    out.append("a crawl")
        if self.geo.underwater(secret["sector"]):
            out.append("under water")
        return sorted(set(out))

    def kinds(self, out, secret) -> tuple[str, str, int | None]:
        """The gate in a word, what opens it in a word, and the tile that is worked."""
        broken = out["breaks"][0] if out["breaks"] else None
        if out["gates"] and not (broken and broken["what"] == "crack"):
            g = next((g for g in out["gates"] if not g["lift"]), out["gates"][0])
            z = g["travel_z"]
            if g["lift"]:
                gate = "a lift or floor that moves"
            elif g["type"] == 600:
                gate = ("a wall that rises" if z[1] < 0 else "a block that sinks" if z[0] > 0
                        else "a floor that rises" if z[0] < 0 else "a ceiling that comes down")
            else:
                gate = {602: "bars or sprites carried up or down", 614: "a panel that slides", 616: "a panel that slides",
                        612: "a thing on a path"}.get(g["type"], "a panel that turns")
            for o in g["openers"]:
                if o.get("inside"):
                    continue
                cause = o["cause"]
                if o["panel"]:
                    word = ("push the panel itself" if "push" in cause else "walk onto it" if "enter" in cause
                            else "shoot the panel" if "vector" in cause or "impact" in cause else cause)
                elif o["kind"] == "sprite" and "push" in cause:
                    word = "a switch" if o["type"] in (20, 21, 22, 23) else "push a prop"
                elif o["kind"] == "wall" and "push" in cause:
                    word = "push another wall"
                elif "vector" in cause or "impact" in cause:
                    word = "shoot something"
                elif "destroyed" in cause:
                    word = "blow or break something"
                elif "enter" in cause or "exit" in cause:
                    word = "walk over something"
                elif "pickup" in cause:
                    word = "take something"
                elif "killed" in cause:
                    word = "kill something"
                elif "push" in cause:
                    word = "push a sector elsewhere"
                else:
                    word = cause
                return gate, word, o["tile"]
        if broken:
            return {"crack": "a crack, blown open", "wall": "a wall or pane that breaks"}.get(
                broken["what"], "a grate, pane or object that breaks"), "break it (%s)" % "/".join(broken["by"]), broken["tile"]
        kind, index = secret["root"].split()
        if secret["by"] not in ("enter", "exit", "pickup", "itself"):
            tile = {"sprite": lambda: int(self.sprites[int(index)]["picnum"]),
                    "wall": lambda: int(self.walls[int(index)]["picnum"])}.get(kind, lambda: None)()
            return ("nothing we read moves", {"sprite": "a sprite", "wall": "a wall"}.get(kind, kind)
                    + ", " + secret["by"], tile)
        for word in ("under water", "water or a stacked link", "a teleporter", "a climb past a jump", "a running jump",
                     "a jump up", "a drop", "a crawl"):
            if word in out["kept_by"]:
                return "no gate: " + word, "nothing", None
        return "no gate: out of the way", "nothing", None


def secret_steps(reading: Reading, secret: dict[str, Any]) -> list[dict[str, Any]]:
    chain = reading.by_root.get(secret["root"])
    return [] if chain is None else chain["steps"]


def travel(disk: Any, sector: int) -> float | None:
    """How far a slide goes in the plan."""
    extra = record_extra(disk.sectors[sector]) or {}
    if int(record_fields(disk.sectors[sector])["type"]) not in (614, 616):
        return None
    try:
        a, b = (record_fields(disk.sprites[int(extra[k])]) for k in ("marker_0", "marker_1"))
    except (KeyError, IndexError):
        return None
    return round(hypot(a["x"] - b["x"], a["y"] - b["y"]))


# ---------------------------------------------------------------------------
# Buttons and bars
# ---------------------------------------------------------------------------

def buttons(paths: Iterable[pathlib.Path], most: int = 520) -> list[dict[str, Any]]:
    """Sectors that go in a little when pressed: a short slide with a push on it, its walls or a sprite it carries."""
    out = []
    for path in paths:
        disk = read_map(path)
        for s, sector in enumerate(disk.sectors):
            go = travel(disk, s)
            extra = record_extra(sector) or {}
            if go is None or not 0 < go <= most:
                continue
            walls = list(sector_walls(disk, s))
            faces = {w for w in walls} | {int(record_fields(disk.walls[w])["next_wall"]) for w in walls}
            pushed = [{"wall": w, "tile": int(record_fields(disk.walls[w])["picnum"]),
                       "tx": record_extra(disk.walls[w])["tx_id"]}
                      for w in sorted(faces) if w >= 0 and (record_extra(disk.walls[w]) or {}).get("trigger_push")]
            carried = [{"sprite": i, "tile": int(record_fields(p)["picnum"]), "tx": record_extra(p)["tx_id"]}
                       for i, p in enumerate(disk.sprites) if int(record_fields(p)["sector"]) == s
                       and (record_extra(p) or {}).get("trigger_push")]
            own = [k for k in ("trigger_push", "trigger_wall_push") if extra.get(k)]
            if not (pushed or carried or own):
                continue
            channels = ({int(p["tx"] or 0) for p in pushed + carried} | {int(extra.get("tx_id") or 0)}) - {0}
            answers = [f"sector {i} type {record_fields(o)['type']}" for i, o in enumerate(disk.sectors)
                       if i != s and int((record_extra(o) or {}).get("rx_id") or 0) in channels]
            xs = [int(record_fields(disk.walls[w])["x"]) for w in walls]
            ys = [int(record_fields(disk.walls[w])["y"]) for w in walls]
            out.append({"map": path.stem, "sector": s, "type": int(record_fields(sector)["type"]), "travel": go,
                        "size": [max(xs) - min(xs), max(ys) - min(ys)],
                        "busy": [extra.get("busy_time_a"), extra.get("busy_time_b")],
                        "comes_back_after": extra.get("wait_time_a") if extra.get("retrigger_a") else None,
                        "pushed_walls": pushed, "pushed_sprites": carried, "own": own, "answers": answers})
    return out


def bars(paths: Iterable[pathlib.Path]) -> list[dict[str, Any]]:
    """Bars a moving sector carries: sprites or masked walls of a bars tile, and who moves them."""
    out = []
    for path in paths:
        disk = read_map(path)
        owners = wall_owners(disk)
        hits: dict[int, list] = defaultdict(list)

        def moving(s):
            return 0 <= s < len(disk.sectors) and int(record_fields(disk.sectors[s])["type"]) in MOTION
        for i, sprite in enumerate(disk.sprites):
            f = record_fields(sprite)
            if int(f["picnum"]) in BARS and moving(int(f["sector"])):
                hits[int(f["sector"])].append({"sprite": i, "tile": int(f["picnum"]), "cstat": int(f["cstat"])})
        for w, wall in enumerate(disk.walls):
            f = record_fields(wall)
            if int(f["cstat"]) & 48 and int(f["over_picnum"]) in BARS:
                for s in sorted({owners[w], int(f["next_sector"])}):
                    if moving(s):
                        hits[s].append({"wall": w, "tile": int(f["over_picnum"]), "cstat": int(f["cstat"])})
        chains = wiring.chains(disk) if hits else []
        for s, found in sorted(hits.items()):
            extra = record_extra(disk.sectors[s]) or {}
            roots = [c["root"] + " (%s, tile %s)" % ("/".join(c["cause"]), c["tile"]) for c in chains
                     if any(step["to"] == f"sector {s}" for step in c["steps"])]
            out.append({"map": path.stem, "sector": s, "type": int(record_fields(disk.sectors[s])["type"]),
                        "bars": found, "worked_by": sorted(roots)[:6], "key": extra.get("key"),
                        "lift_z": int(extra.get("on_floor_z") or 0) - int(extra.get("off_floor_z") or 0),
                        "slide": travel(disk, s)})
    return out


# ---------------------------------------------------------------------------
# The counts
# ---------------------------------------------------------------------------

def counts(rows: list[dict[str, Any]]) -> dict[str, Any]:
    def main_gate(r):
        return next((g for g in r["gates"] if not g["lift"]), r["gates"][0])
    first = [main_gate(r) for r in rows if r["gates"]]
    worked = [next((o for o in g["openers"] if not o.get("inside")), None) for g in first]
    remote = [o for o in worked if o and not o["panel"]]
    faces = [g["face"] for g, o in zip(first, worked) if g["face"] and o and o["panel"]]
    # the rule of the tell: a wall that is its own button shows it, a wall worked from elsewhere does not
    remote_faces = [g["face"] for g, o in zip(first, worked) if g["face"] and o and not o["panel"]]
    tiles = Counter(r["tile"] for r in rows if r["opened"] in ("a switch", "push a prop") and r["tile"] is not None)
    windows = [r["window"] for r in rows if r["window"]["seen"] is not None]

    def spread(values):
        got = sorted(values)
        return [got[len(got) // 4], got[len(got) // 2], got[3 * len(got) // 4]] if got else None
    return {
        "secrets": len(rows), "super": sum(r["super"] for r in rows),
        "gate": dict(Counter(r["gate"] for r in rows).most_common()),
        "opened_by": dict(Counter(r["opened"] for r in rows).most_common()),
        "credit": dict(Counter(r["credit"] for r in rows).most_common()),
        "switch_or_prop_tiles": dict(tiles.most_common()),
        "remote_triggers": {"count": len(remote), "away_quartiles": spread([o["away"] for o in remote]),
                            "gate_in_sight": sum(1 for o in remote if o["gate_in_sight"])},
        "faces_worked_from_elsewhere": {"count": len(remote_faces),
                                        "tell": dict(Counter(f["tell"] for f in remote_faces).most_common())},
        "panel_faces": {"count": len(faces), "tell": dict(Counter(f["tell"] for f in faces).most_common()),
                        "with_a_sprite_hung_on_it": sum(1 for f in faces if f["decals"]),
                        "decal_tiles": dict(Counter(t for f in faces for t in f["decals"]).most_common(12))},
        "seen_before_it_is_opened": {
            "read": len(windows), "seen": sum(1 for w in windows if w["seen"]),
            "through_bars_or_glass": sum(1 for w in windows if w["seen"] and w["through"]),
            "seen_by_gate": dict(Counter(r["gate"] for r in rows if r["window"]["seen"]).most_common()),
            "through_tiles": dict(Counter(t for w in windows if w["seen"] for t in w["through"]).most_common())},
        "tier_by_gate": {g: [sum(1 for r in rows if r["gate"] == g and r["tier"] == t) for t in range(5)]
                         for g in sorted({r["gate"] for r in rows})}}


def mine(paths: Iterable[pathlib.Path]) -> list[dict[str, Any]]:
    out = []
    for path in paths:
        reading = Reading(read_map(path), path.stem)
        out += [reading.read(s) for s in reading.secrets]
    return out


def compact(row: dict[str, Any]) -> str:
    bits = ["%s %s (sector %d)%s: %s; %s%s" % (
        row["map"], row["root"], row["sector"], " SUPER" if row["super"] else "", row["gate"], row["opened"],
        "" if row["tile"] is None else " [tile %d]" % row["tile"])]
    for g in row["gates"]:
        o = next((o for o in g["openers"] if not o.get("inside")), None)
        bits.append("    gate sector %d type %d%s, travel z %s xy %s; worked by %s" % (
            g["sector"], g["type"], " lift" if g["lift"] else "", g["travel_z"], g["travel_xy"],
            "nothing" if o is None else "%s %d (%s, tile %s) %s" % (
                o["kind"], o["index"], o["cause"], o["tile"],
                "on it" if o["panel"] else "%d away, gate %s" % (
                    o["away"], "in sight" if o["gate_in_sight"] else "not in sight"))))
        if g["face"]:
            f = g["face"]
            bits.append("      face wall %d tile %d beside %s: %s%s" % (
                f["wall"], f["tile"], f.get("beside_tile"), f["tell"], ", sprites %s" % f["decals"] if f["decals"] else ""))
    for b in row["breaks"]:
        bits.append("    breaks: %s %d tile %d by %s" % (b["what"], b["index"], b["tile"], "/".join(b["by"])))
    w = row["window"]
    bits.append("    kept by %s; %s; holds %s" % (
        row["kept_by"] or "nothing", "seen from %s%s" % (
            w["nearest"], " through %s" % w["through"] if w["through"] else "") if w["seen"] else "not seen", row["reward"]))
    return "\n".join(bits)


def show_record(name: str, what: list[str]) -> None:
    """Every set field of the records asked for: what an idiom is copied from."""
    disk = read_map(find(name))
    owners = wall_owners(disk)
    groups = {"s": disk.sectors, "w": disk.walls, "p": disk.sprites}
    for word in what:
        kind, index = word.split(":")[0], int(word.split(":")[1])
        if kind == "ch":
            for label, group in (("sector", disk.sectors), ("wall", disk.walls), ("sprite", disk.sprites)):
                for i, o in enumerate(group):
                    e = record_extra(o) or {}
                    for side in ("tx", "rx"):
                        if int(e.get(side + "_id") or 0) == index:
                            print("  channel", index, side.upper(), label, i, "in",
                                  owners.get(i) if label == "wall" else record_fields(o).get("sector", i),
                                  "type", record_fields(o)["type"], "tile", record_fields(o).get("picnum"), said(e))
            continue
        print(name, word, said(record_fields(groups[kind][index])), "X", said(record_extra(groups[kind][index]) or {}))
        if kind == "s":
            for w in sector_walls(disk, index):
                print("   wall", w, said(record_fields(disk.walls[w])), "X", said(record_extra(disk.walls[w]) or {}))
            for i, p in enumerate(disk.sprites):
                f = record_fields(p)
                if int(f["sector"]) == index or (int(f["type"]) in (3, 4, 5) and int(f["owner"]) == index):
                    print("   sprite", i, said(f), "X", said(record_extra(p) or {}))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("what", nargs="?", default="mine", choices=["mine", "show", "buttons", "bars", "record"])
    parser.add_argument("rest", nargs="*")
    args = parser.parse_args(argv)
    if args.what == "record":
        show_record(args.rest[0], args.rest[1:])
        return 0
    if args.what == "show":
        path = find(args.rest[0])
        reading = Reading(read_map(path), path.stem)
        for secret in reading.secrets:
            print(compact(reading.read(secret)))
        return 0
    campaign = campaign_maps(required=True)
    names = {p.stem for p in campaign}
    curated = [p for p in named_maps() if p.stem not in names]
    if args.what in ("buttons", "bars"):
        for row in (buttons if args.what == "buttons" else bars)(campaign + curated):
            print(json.dumps(row))
        return 0
    ours = mine(campaign)
    theirs = mine([p for p in curated if p.stem.upper().startswith("DWE")])
    result = {"$schema": SCHEMA, "schema_version": 1,
              "says": "how each secret is gated, opened, given away and filled; written by tools/mine_secrets.py",
              "counts": {"campaign": counts(ours), "death_wish": counts(theirs)},
              "buttons": buttons(campaign + curated), "bars": bars(campaign + curated),
              "campaign": ours, "death_wish": theirs}
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(result["counts"], indent=1)
    OUTPUT.write_text("{\n" + ",\n".join(
        '"%s": %s' % (k, text if k == "counts" else json.dumps(v) if not isinstance(v, list)
                      else "[\n" + ",\n".join(json.dumps(r) for r in v) + "\n]")
        for k, v in result.items()) + "\n}\n", encoding="utf-8", newline="\n")
    print(text)
    print(OUTPUT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
