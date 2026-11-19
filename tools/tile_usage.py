"""What a tile LOOKS like, and every way Blood uses it.

The owner, 2026-11-18, after naming tile 346 for a coffin's top and adding
that it "can be used for multiple things, it can even be a door texture":
"If you want to check on textures, you should be able yourself to obtain
it how it is used in other levels in which context to be able to build
that database of usages yourself. But still you should understand what it
looks like to be able to use as you want in different contexts that were
never seen before if it makes sense."

Two halves, and neither is enough alone:

* **the picture** -- the tile drawn from the ART at four times its size,
  with its pixel size and what that is in the world at Blood's scale (16
  units a texel across, 256 z a texel up). A tile is a pattern, a picture
  of one thing, or a mask with see-through pixels; only looking says
  which. (144, "wooden lattice, used as windows", is a mask: on a solid
  wall it drew magenta.)
* **the usage** -- over the campaign and the curated maps, every role the
  tile plays and the CONTEXT of each: on a solid wall (how tall, how
  long), on the face of a raised thing, on a moving sector's leaf (a
  door), as glass or bars over an opening, as a floor (of a room, or of
  the top of something standing in one, and how big that top is), as a
  ceiling, as a sprite (which alignment, what size, how high).

.. code-block:: bash

    python -m tools.tile_usage 346 128            # print, and write PNGs
    python -m tools.tile_usage 346 -o some/dir
    python -m tools.tile_usage --build            # the whole database

The picture goes to ``reports/tiles/tile-N.png``; READ it. The owner's
name for the tile, when he has given one, heads the report: a use this
database has never seen is allowed when the picture supports it, and is
then something to tell him.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import statistics
import sys
from collections import Counter
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SCHEMA = "llmapper.tile-usage"
DATABASE = ROOT / "knowledge" / "blood" / "design" / "tile-usage-v1.json"
PICTURES = ROOT / "reports" / "tiles"
ART_DIR = ROOT / "reference" / "blood"
PALETTE = ART_DIR / "xmapedit" / "palettes" / "import" / "BLOOD.PAL"
BODY = 16960
#: sector types that MOVE: a wall of one, or facing one, is a leaf
MOVERS = set(range(600, 620))
POPULATIONS = ("blood-campaign", "community-curated")
ROLES = ("wall", "step_face", "leaf", "mask", "floor", "top", "ceiling",
         "sprite_face", "sprite_wall", "sprite_flat")


def corpus() -> list[pathlib.Path]:
    from bloodmap.patterns import list_corpus_maps

    out = []
    for population in POPULATIONS:
        out += [m.path for m in list_corpus_maps(population=population)]
    return out


def _median(values, digits=2):
    return round(statistics.median(values), digits) if values else None


class Usage:
    """Everything seen of one tile."""

    def __init__(self, tile: int):
        self.tile = tile
        self.count: Counter = Counter()
        self.maps: dict[str, set] = {role: set() for role in ROLES}
        self.numbers: dict[str, list] = {}
        self.with_: dict[str, Counter] = {}
        self.examples: dict[str, list] = {role: [] for role in ROLES}

    def see(self, role: str, where: tuple, **numbers: Any) -> None:
        self.count[role] += 1
        self.maps[role].add(where[0])
        if len(self.examples[role]) < 3 and all(
                e[0] != where[0] for e in self.examples[role]):
            self.examples[role].append(where)
        for key, value in numbers.items():
            if key.startswith("with_"):
                self.with_.setdefault(f"{role}.{key[5:]}", Counter())[value] += 1
            elif value is not None:
                self.numbers.setdefault(f"{role}.{key}", []).append(value)

    def summary(self) -> dict[str, Any]:
        roles = {}
        for role in ROLES:
            if not self.count[role]:
                continue
            row: dict[str, Any] = {"count": self.count[role],
                                   "maps": len(self.maps[role]),
                                   "examples": [list(e) for e in
                                                self.examples[role]]}
            for key, values in self.numbers.items():
                if key.startswith(role + "."):
                    name = key.split(".", 1)[1]
                    if name.endswith("_mode"):
                        row[name] = Counter(values).most_common(1)[0][0]
                    else:
                        row[name] = _median(values)
            for key, counter in self.with_.items():
                if key.startswith(role + "."):
                    row["with_" + key.split(".", 1)[1]] = [
                        list(pair) for pair in counter.most_common(4)]
            roles[role] = row
        return {"tile": self.tile, "total": sum(self.count.values()),
                "roles": roles}


def scan(paths, only: set[int] | None = None) -> dict[int, Usage]:
    from bloodmap.format import read_map

    seen: dict[int, Usage] = {}

    def use(tile: int) -> Usage | None:
        if only is not None and tile not in only:
            return None
        return seen.setdefault(tile, Usage(tile))

    for path in paths:
        try:
            disk = read_map(path)
        except Exception:                                   # noqa: BLE001
            continue
        name = pathlib.Path(path).stem
        S = [s.fields for s in disk.sectors]
        W = [w.fields for w in disk.walls]
        owner = {}
        spans = {}
        for i, s in enumerate(S):
            xs, ys = [], []
            for w in range(int(s["wall_ptr"]),
                           int(s["wall_ptr"]) + int(s["wall_count"])):
                owner[w] = i
                xs.append(int(W[w]["x"]))
                ys.append(int(W[w]["y"]))
            spans[i] = (max(xs) - min(xs), max(ys) - min(ys)) if xs else (0, 0)
        for w, wall in enumerate(W):
            i = owner.get(w)
            if i is None:
                continue
            s = S[i]
            nxt = W[int(wall["point2"])]
            length = round(math.hypot(int(nxt["x"]) - int(wall["x"]),
                                      int(nxt["y"]) - int(wall["y"])))
            other = int(wall["next_sector"])
            clear = (int(s["floor_z"]) - int(s["ceiling_z"])) / BODY
            tile = int(wall["picnum"])
            common = {"length": length, "x_repeat_mode": int(wall["x_repeat"]),
                      "y_repeat_mode": int(wall["y_repeat"]),
                      "shade": int(wall["shade"]),
                      "with_floor": int(s["floor_picnum"])}
            if other < 0:
                u = use(tile)
                if u:
                    role = "leaf" if int(s["type"]) in MOVERS else "wall"
                    u.see(role, (name, "wall", w), height_bodies=round(clear, 2),
                          **common)
            else:
                o = S[other]
                rise = (int(s["floor_z"]) - int(o["floor_z"])) / BODY
                drop = (int(o["ceiling_z"]) - int(s["ceiling_z"])) / BODY
                if int(o["type"]) in MOVERS or int(s["type"]) in MOVERS:
                    u = use(tile)
                    if u:
                        u.see("leaf", (name, "wall", w), **common)
                elif rise > 0.1 or drop > 0.1:
                    u = use(tile)
                    if u:
                        u.see("step_face", (name, "wall", w),
                              rise_bodies=round(max(rise, drop), 2), **common)
                if int(wall["cstat"]) & (16 | 32) and int(wall["over_picnum"]):
                    u = use(int(wall["over_picnum"]))
                    if u:
                        u.see("mask", (name, "wall", w), length=length,
                              blocks_mode=int(wall["cstat"]) & 1,
                              breaks_mode=int(wall["type"]) == 511,
                              height_bodies=round(min(
                                  int(s["floor_z"]), int(o["floor_z"]))
                                  / BODY - max(int(s["ceiling_z"]),
                                               int(o["ceiling_z"])) / BODY, 2))
        for i, s in enumerate(S):
            around = [int(W[w]["next_sector"]) for w in range(
                int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"]))]
            lower = [S[n] for n in around if n >= 0]
            rise = (min((int(n["floor_z"]) - int(s["floor_z"]) for n in lower),
                        default=0) / BODY)
            short, long_ = sorted(spans[i])
            u = use(int(s["floor_picnum"]))
            if u:
                #: the top of a thing: higher than everything round it,
                #: and no bigger than a table
                top = bool(lower) and rise >= 0.1 and long_ <= 4096
                u.see("top" if top else "floor", (name, "sector", i),
                      short_side=short, long_side=long_,
                      rise_bodies=round(rise, 2) if top else None,
                      relative_mode=bool(int(s["floor_stat"]) & 64),
                      moves_mode=int(s["type"]) in MOVERS,
                      with_host_floor=(int(lower[0]["floor_picnum"])
                                       if top else int(s["ceiling_picnum"])))
            if not int(s["ceiling_stat"]) & 1:
                u = use(int(s["ceiling_picnum"]))
                if u:
                    u.see("ceiling", (name, "sector", i), short_side=short,
                          long_side=long_,
                          height_bodies=round((int(s["floor_z"])
                                               - int(s["ceiling_z"])) / BODY, 2))
        for index, sprite in enumerate(disk.sprites):
            f = sprite.fields
            if int(f["cstat"]) & 32768 or not 0 <= int(f["sector"]) < len(S):
                continue
            u = use(int(f["picnum"]))
            if not u:
                continue
            align = int(f["cstat"]) & 48
            role = ("sprite_wall" if align == 16 else
                    "sprite_flat" if align == 32 else "sprite_face")
            s = S[int(f["sector"])]
            u.see(role, (name, "sprite", index),
                  x_repeat_mode=int(f["x_repeat"]),
                  y_repeat_mode=int(f["y_repeat"]),
                  over_floor_bodies=round((int(s["floor_z"]) - int(f["z"]))
                                          / BODY, 2),
                  type_mode=int(f["type"]), pal_mode=int(f["pal"]),
                  with_floor=int(s["floor_picnum"]))
    return seen


def picture(tile: int, out_dir: pathlib.Path = PICTURES) -> dict[str, Any]:
    """Draw the tile at 4x and say what it is made of."""
    from bloodmap.art import read_art_directory, read_palette, tile_to_rgb

    tiles = read_art_directory(ART_DIR)
    art = tiles.get(tile)
    if art is None or not art.width or not art.height:
        return {"tile": tile, "missing": True}
    palette = read_palette(PALETTE)
    see_through = sum(1 for p in art.pixels if p == 255)
    info = {"tile": tile, "pixels": [art.width, art.height],
            #: what one repeat covers in the world at Blood's usual scale
            "world_at_repeat_8": [art.width * 16, art.height * 256],
            "see_through_share": round(see_through / len(art.pixels), 3),
            "is_mask": see_through / len(art.pixels) > 0.02}
    try:
        from PIL import Image
    except ImportError:
        return info
    #: `tile_to_rgb` returns rows; the ART itself is stored in columns
    rgb = bytearray(tile_to_rgb(art, palette))
    #: see-through pixels in magenta, so a mask cannot be taken for a wall
    for x in range(art.width):
        for y in range(art.height):
            if art.pixels[x * art.height + y] == 255:
                k = (y * art.width + x) * 3
                rgb[k:k + 3] = bytes((255, 0, 255))
    image = Image.frombytes("RGB", (art.width, art.height), bytes(rgb))
    scale = max(1, min(8, 512 // max(art.width, art.height)))
    image = image.resize((art.width * scale, art.height * scale),
                         Image.Resampling.NEAREST)
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / f"tile-{tile}.png"
    image.save(path)
    info["picture"] = str(path)
    return info


def owner_name(tile: int) -> str | None:
    path = ROOT / "knowledge" / "blood" / "design" / "owner-anchors-v1.json"
    try:
        for anchor in json.loads(path.read_text("utf-8"))["anchors"]:
            if int(anchor["picnum"]) == tile:
                note = anchor.get("notes") or ""
                return anchor.get("label_en", "") + (f" [{note}]" if note else "")
    except OSError:
        pass
    return None


def report(tile: int, usage: Usage | None, out_dir: pathlib.Path) -> str:
    info = picture(tile, out_dir)
    lines = [f"TILE {tile}: owner says: {owner_name(tile) or '(not named)'}"]
    if info.get("missing"):
        lines.append("  no such tile in the ART")
    else:
        w, h = info["pixels"]
        lines.append(
            f"  {w} x {h} px; one repeat is {w * 16} wide by {h * 256} z "
            f"({h * 256 / BODY:.2f} bodies) on a wall, {w * 16} by {h * 16} "
            f"on a floor; {'A MASK: ' if info['is_mask'] else ''}"
            f"{info['see_through_share']:.0%} see-through")
        lines.append(f"  picture: {info.get('picture', '(PIL missing)')}")
    if usage is None:
        lines.append("  never used in the campaign or the curated maps")
        return "\n".join(lines)
    summary = usage.summary()
    for role, row in summary["roles"].items():
        facts = ", ".join(
            f"{k} {v}" for k, v in row.items()
            if k not in ("count", "maps", "examples")
            and not k.startswith("with_") and v is not None)
        lines.append(f"  {role:<12} {row['count']:>5} in {row['maps']:>2} maps"
                     f"  {facts}")
        for key, pairs in row.items():
            if key.startswith("with_"):
                lines.append(f"      {key[5:]}: " + ", ".join(
                    f"{t} x{n}" for t, n in pairs))
        lines.append("      e.g. " + "; ".join(
            f"{m} {kind} {i}" for m, kind, i in row["examples"]))
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("tiles", nargs="*", type=int)
    parser.add_argument("--build", action="store_true")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)
    if args.build:
        seen = scan(corpus())
        data = {"$schema": SCHEMA, "schema_version": 1,
                "populations": list(POPULATIONS),
                "tiles": {str(t): u.summary() for t, u in sorted(seen.items())}}
        out = pathlib.Path(args.output or DATABASE)
        out.write_text(json.dumps(data, indent=1), "utf-8")
        print(f"{len(seen)} tiles -> {out}")
        return 0
    wanted = set(args.tiles)
    seen = scan(corpus(), only=wanted)
    out_dir = pathlib.Path(args.output) if args.output else PICTURES
    for tile in args.tiles:
        print(report(tile, seen.get(tile), out_dir))
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
