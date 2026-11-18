"""Look at a Duke Nukem 3D map with the Blood observer.

The observer (`xmapedit-observe`) reads Blood's MAP format and takes its
palette from BLOOD.RFF. It cannot open a Duke map and it cannot be changed
here (it lives in a submodule). So this builds the two things it needs to be
pointed at a Duke level instead:

* **a viewing copy of the map** in Blood's file format: every sector, wall and
  visible sprite with its geometry, tile number, cstat, repeats and pannings
  exactly as Duke wrote them. Nothing is scaled, so a coordinate read off a
  frame is a coordinate in the Duke map. Shades are doubled, because Blood's
  shade table has twice Duke's steps (`conversion.convert_shade`, measured on
  the E3L1 pair). Effector and marker sprites are dropped: they are invisible
  in the game and the observer would draw their editor icons.
* **a resource directory** holding Duke's own ART, untouched, and a small
  archive in the one format the observer reads a palette from (Blood's RFF)
  carrying **Duke's own palette, shade table, translucency table and
  palette swaps** out of `duke3d.grp`.

**What a frame from this is evidence of, and what it is not.** Geometry,
proportion, where a thing stands, colour and light as authored are Duke's.
Parallax skies are drawn by the observer's rule, not Duke's multi-tile one,
so the sky is wrong or black. Nothing moves, nothing is lit by a sector
effector, and no mechanism has run. It is a way to SEE a Duke level, never a
conversion of one.

(The first version of this moved every pixel of Duke's ART to the nearest
colour in Blood's palette, because the observer takes its palette from
BLOOD.RFF. Blood's palette has almost no blue or green and the owner said,
of the first frames, "Duke palette is off". The observer was never the
limit: it reads three kinds of entry from an archive, and an archive can be
written.)

.. code-block:: bash

    python -m tools.duke_view maps/duke3d/DukCity1.map -o work/dukcity1
    python -m tools.duke_view maps/duke3d/DukCity1.map -o work/dukcity1 \\
        --pose street:-60000,62000,-58000,62000 --pose up:-60000,62000,-58000,62000,160
    python -m tools.duke_view maps/duke3d/DukCity1.map -o work/dukcity1 --sectors 12,40
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import shutil
import struct
import sys
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DUKE_DIR = ROOT / "reference" / "duke3d"
BLOOD_DIR = ROOT / "reference" / "blood"

#: Duke's eye stands 38 "units" (<<8) over the floor: EDuke32 player.h PHEIGHT.
DUKE_EYE = 38 << 8
#: The first tiles of Duke's ART are its editor-only markers (DEFS.CON):
#: SECTOREFFECTOR 1, ACTIVATOR 2, TOUCHPLATE 3, ACTIVATORLOCKED 4,
#: MUSICANDSFX 5, LOCATORS 6, CYCLER 7, MASTERSWITCH 8, RESPAWN 9, GPSPEED 10.
DUKE_MARKER_TILES = frozenset(range(1, 11))
#: Blood sprite cstat 0x8000 is "invisible"; Duke's is the same bit.
INVISIBLE = 0x8000


class DukeViewError(ValueError):
    pass


# ---------------------------------------------------------------------------
# resources: Duke's art, palette and shade table, in an archive the observer reads
# ---------------------------------------------------------------------------

def read_grp(path: pathlib.Path) -> dict[str, bytes]:
    """A Build GRP archive: "KenSilverman", a count, then 16-byte entries."""
    data = path.read_bytes()
    if data[:12] != b"KenSilverman":
        raise DukeViewError(f"{path} is not a GRP archive")
    count = struct.unpack_from("<i", data, 12)[0]
    offset = 16 + 16 * count
    out = {}
    for index in range(count):
        name, size = struct.unpack_from("<12si", data, 16 + 16 * index)
        out[name.split(b"\0")[0].decode("ascii", "replace").upper()] = \
            data[offset:offset + size]
        offset += size
    return out


def duke_palette(grp: dict[str, bytes]) -> list[tuple[int, int, int]]:
    """PALETTE.DAT's first 768 bytes: six-bit VGA, so times four."""
    raw = grp.get("PALETTE.DAT")
    if raw is None or len(raw) < 768:
        raise DukeViewError("the GRP holds no PALETTE.DAT")
    return [(raw[i * 3] << 2, raw[i * 3 + 1] << 2, raw[i * 3 + 2] << 2)
            for i in range(256)]


#: The observer asks an RFF archive for three kinds of entry and nothing
#: else (`xmapedit/src_blood/observe/obs_main.c: obs_load_palette`): "PAL",
#: an eight-bit palette; "PLU" by id, a shade table of SIXTY-FOUR levels of
#: 256; and "TLU" named TRANS, a 65536-byte translucency table.
RFF_SHADES = 64
RESOURCE_VERSION = 3


def duke_tables(grp: dict[str, bytes]) -> dict[str, Any]:
    """PALETTE.DAT and LOOKUP.DAT, as the game reads them.

    PALETTE.DAT: 768 bytes of six-bit colour, a 16-bit count of shade levels,
    that many 256-byte rows, then the translucency table. LOOKUP.DAT: a count,
    then for each swap one byte of palette number and 256 bytes of remap.
    """
    raw = grp.get("PALETTE.DAT")
    if raw is None or len(raw) < 770:
        raise DukeViewError("the GRP holds no PALETTE.DAT")
    shades = struct.unpack_from("<H", raw, 768)[0]
    table = raw[770:770 + shades * 256]
    if len(table) != shades * 256:
        raise DukeViewError("PALETTE.DAT's shade table is truncated")
    transluc = raw[770 + shades * 256:770 + shades * 256 + 65536]
    swaps: dict[int, bytes] = {}
    lookup = grp.get("LOOKUP.DAT")
    if lookup:
        count = lookup[0]
        for index in range(count):
            at = 1 + index * 257
            if at + 257 > len(lookup):
                break
            swaps[lookup[at]] = lookup[at + 1:at + 257]
    return {"palette": bytes(c for rgb in duke_palette(grp) for c in rgb),
            "shades": shades, "shade_table": table,
            "transluc": transluc if len(transluc) == 65536 else None,
            "swaps": swaps}


def shade_table_64(table: bytes, shades: int, remap: bytes | None = None) -> bytes:
    """Duke's shade rows stretched to the sixty-four the observer wants.

    Blood's table has twice Duke's steps and the viewing copy doubles every
    shade to match (`conversion.convert_shade`), so level `n` here is Duke's
    level `n // 2`: a wall at Duke shade 7 is drawn from Duke's own row 7. A
    palette swap is applied first, as the engine does: colour `i` is looked
    up as `remap[i]`.
    """
    out = bytearray()
    for level in range(RFF_SHADES):
        row = table[min(shades - 1, level // 2) * 256:][:256]
        if remap is not None:
            row = bytes(row[remap[i]] for i in range(256))
        out += row
    return bytes(out)


def write_rff(path: pathlib.Path, entries: list[tuple[str, int, str, bytes]]) -> None:
    """A version-2 RFF: header, payloads, then a plain 48-byte directory.

    Only the fields the observer reads are set: offset and size at 16 and 20,
    flags at 32 (zero: nothing encrypted), type at 33, name at 36, id at 44.
    """
    blob = bytearray()
    directory = bytearray()
    offset = 32
    for kind, ident, name, data in entries:
        entry = bytearray(48)
        struct.pack_into("<ii", entry, 16, offset, len(data))
        entry[33:36] = kind.encode("ascii")[:3].ljust(3, b"\0")
        entry[36:44] = name.encode("ascii")[:8].ljust(8, b"\0")
        struct.pack_into("<i", entry, 44, ident)
        directory += entry
        blob += data
        offset += len(data)
    header = bytearray(32)
    header[0:4] = b"RFF\x1a"
    struct.pack_into("<H", header, 4, 0x0200)
    struct.pack_into("<ii", header, 8, 32 + len(blob), len(entries))
    path.write_bytes(bytes(header) + bytes(blob) + bytes(directory))


def build_resources(out_dir: pathlib.Path, *, duke_dir: pathlib.Path = DUKE_DIR,
                    blood_dir: pathlib.Path = BLOOD_DIR) -> dict[str, Any]:
    """Write the resource directory the observer is pointed at. Idempotent.

    Duke's ART is copied as it is. The palette, the shade table, the
    translucency table and the palette swaps are Duke's own, packed into the
    one archive the observer knows how to read.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = out_dir / "duke-view-resources.json"
    if stamp.exists():
        found = json.loads(stamp.read_text("utf-8"))
        if found.get("version") == RESOURCE_VERSION:
            return found
    grp = read_grp(duke_dir / "duke3d.grp")
    tables = duke_tables(grp)
    files = 0
    for source in sorted(duke_dir.glob("TILES*.ART")):
        shutil.copyfile(source, out_dir / source.name)
        files += 1
    entries = [("PAL", 0, "DUKE", tables["palette"]),
               ("PLU", 0, "NORMAL", shade_table_64(tables["shade_table"],
                                                   tables["shades"]))]
    for number, remap in sorted(tables["swaps"].items()):
        if number == 0:
            continue
        entries.append(("PLU", number, f"SWAP{number}",
                        shade_table_64(tables["shade_table"], tables["shades"],
                                       remap)))
    if tables["transluc"] is not None:
        entries.append(("TLU", 0, "TRANS", tables["transluc"]))
    write_rff(out_dir / "BLOOD.RFF", entries)
    report = {"version": RESOURCE_VERSION, "art_files": files,
              "palette": "Duke's PALETTE.DAT, eight-bit, unchanged",
              "shade_levels": tables["shades"],
              "palette_swaps": sorted(n for n in tables["swaps"] if n),
              "translucency": tables["transluc"] is not None,
              "limits": ["parallax skies are drawn by the observer's rule, "
                         "not Duke's multi-tile one",
                         "sector-effector lighting has not run"]}
    stamp.write_text(json.dumps(report, indent=2), "utf-8")
    return report


# ---------------------------------------------------------------------------
# the viewing copy of the map
# ---------------------------------------------------------------------------

def viewing_copy(duke: Any) -> Any:
    """A Blood-format DiskMap with Duke's geometry and tile numbers, unscaled."""
    from bloodmap.conversion import convert_shade
    from bloodmap.construction import new_level

    level = new_level()
    header = duke.header
    level.player_start = {"x": int(header["start_x"]), "y": int(header["start_y"]),
                          "z": int(header["start_z"]),
                          "angle": int(header["start_angle"]) & 2047,
                          "sector": int(header["start_sector"])}

    def shade(value: int) -> int:
        return convert_shade(int(value), "duke3d", "blood")

    template_sector = dict(level_template("sector"))
    template_wall = dict(level_template("wall"))
    for index, sector in enumerate(duke.sectors):
        s = sector.fields
        fields = dict(template_sector)
        fields.update(
            wall_ptr=s["wall_ptr"], wall_count=s["wall_count"],
            ceiling_z=s["ceiling_z"], floor_z=s["floor_z"],
            ceiling_stat=s["ceiling_stat"] & 0x03FF,
            floor_stat=s["floor_stat"] & 0x03FF,
            ceiling_picnum=s["ceiling_picnum"], floor_picnum=s["floor_picnum"],
            ceiling_heinum=s["ceiling_heinum"], floor_heinum=s["floor_heinum"],
            ceiling_shade=shade(s["ceiling_shade"]),
            floor_shade=shade(s["floor_shade"]),
            ceiling_x_panning=s["ceiling_x_panning"],
            ceiling_y_panning=s["ceiling_y_panning"],
            floor_x_panning=s["floor_x_panning"],
            floor_y_panning=s["floor_y_panning"],
            ceiling_pal=s["ceiling_pal"], floor_pal=s["floor_pal"],
            visibility=s["visibility"])
        level.sectors.append({"id": index, "fields": fields, "blood": None})
    for index, wall in enumerate(duke.walls):
        w = wall.fields
        fields = dict(template_wall)
        fields.update(
            x=w["x"], y=w["y"], point2=w["point2"], next_wall=w["next_wall"],
            next_sector=w["next_sector"], cstat=w["cstat"] & 0x03FF,
            picnum=w["picnum"], over_picnum=max(0, w["over_picnum"]),
            shade=shade(w["shade"]), pal=w["pal"], x_repeat=w["x_repeat"],
            y_repeat=w["y_repeat"], x_panning=w["x_panning"],
            y_panning=w["y_panning"])
        level.walls.append({"id": index, "fields": fields, "blood": None})
    from bloodmap.conversion import _empty
    from bloodmap.format import SPRITE_FIELDS

    #: appended directly: `LevelBuilder.add_sprite` checks that a sprite lies
    #: between its sector's floor and ceiling, and Duke's own maps hold
    #: sprites that do not (a sign hung past a sloped ceiling, a prop sunk in
    #: a floor). They are Duke's and they are shown.
    kept = dropped = 0
    for sprite in duke.sprites:
        s = sprite.fields
        if (int(s["picnum"]) in DUKE_MARKER_TILES or int(s["cstat"]) & INVISIBLE
                or not 0 <= int(s["sector"]) < len(duke.sectors)):
            dropped += 1
            continue
        fields = _empty(SPRITE_FIELDS)
        fields.update(
            x=s["x"], y=s["y"], z=s["z"], cstat=int(s["cstat"]) & 0x03FF,
            picnum=s["picnum"], shade=shade(s["shade"]), pal=s["pal"],
            x_repeat=s["x_repeat"], y_repeat=s["y_repeat"],
            sector=s["sector"], angle=s["angle"], extra=-1)
        for key, value in (("status", 0), ("statnum", 0), ("type", 0),
                           ("owner", -1), ("clipdist", 32)):
            if key in fields:
                fields[key] = value
        level.sprites.append({"id": kept, "fields": fields, "blood": None})
        kept += 1
    disk = level.to_disk_map()
    return disk, {"sprites_kept": kept, "sprites_dropped": dropped}


def level_template(kind: str) -> dict[str, int]:
    from bloodmap.conversion import BLOOD_SECTOR_FIELDS, BLOOD_WALL_FIELDS, _empty

    fields = _empty(BLOOD_SECTOR_FIELDS if kind == "sector" else BLOOD_WALL_FIELDS)
    fields["extra"] = -1
    return fields


# ---------------------------------------------------------------------------
# poses
# ---------------------------------------------------------------------------

def _loop(duke: Any, sector_id: int) -> list[tuple[int, int]]:
    f = duke.sectors[sector_id].fields
    return [(int(duke.walls[w].fields["x"]), int(duke.walls[w].fields["y"]))
            for w in range(int(f["wall_ptr"]),
                           int(f["wall_ptr"]) + int(f["wall_count"]))]


def _inside(point, loop) -> bool:
    x, y = point
    inside = False
    for (ax, ay), (bx, by) in zip(loop, loop[1:] + loop[:1]):
        if (ay > y) != (by > y) and x < (bx - ax) * (y - ay) / (by - ay) + ax:
            inside = not inside
    return inside


def sector_at(duke: Any, x: int, y: int) -> int | None:
    """The sector holding a point; where several do, the one with open sky,
    then the largest."""
    found = []
    for index in range(len(duke.sectors)):
        f = duke.sectors[index].fields
        start, count = int(f["wall_ptr"]), int(f["wall_count"])
        #: a sector's walls are one or more loops; even-odd over all of them
        hit = False
        loop: list[tuple[int, int]] = []
        first = start
        for w in range(start, start + count):
            wall = duke.walls[w].fields
            loop.append((int(wall["x"]), int(wall["y"])))
            if int(wall["point2"]) == first:
                hit ^= _inside((x, y), loop)
                loop = []
                first = w + 1
        if hit:
            found.append((bool(int(f["ceiling_stat"]) & 1), count, index))
    if not found:
        return None
    return max(found)[2]


def pose(duke: Any, name: str, x: int, y: int, tx: int, ty: int,
         horiz: int = 100):
    from bloodmap.visual import Viewpoint

    sector = sector_at(duke, x, y)
    if sector is None:
        raise DukeViewError(f"{name}: no sector at ({x}, {y})")
    floor = int(duke.sectors[sector].fields["floor_z"])
    angle = int(round(math.atan2(ty - y, tx - x) * 1024 / math.pi)) & 2047
    return Viewpoint(view_id=name, x=int(x), y=int(y), z=floor - DUKE_EYE,
                     angle=angle, horiz=int(horiz), sector=sector,
                     node=f"pose:{name}", purpose="loop", screenshot=True,
                     note=f"({x}, {y}) toward ({tx}, {ty})")


def sector_pose(duke: Any, sector_id: int, horiz: int = 100):
    """Stand in a sector's middle and look at its farthest corner."""
    loop = _loop(duke, sector_id)
    cx = sum(p[0] for p in loop) // len(loop)
    cy = sum(p[1] for p in loop) // len(loop)
    if sector_at(duke, cx, cy) != sector_id:
        ax, ay = loop[0]
        bx, by = loop[1]
        nx, ny = -(by - ay), (bx - ax)
        length = max(1.0, math.hypot(nx, ny))
        for sign in (1, -1):
            px = int((ax + bx) / 2 + sign * nx / length * 96)
            py = int((ay + by) / 2 + sign * ny / length * 96)
            if sector_at(duke, px, py) == sector_id:
                cx, cy = px, py
                break
    far = max(loop, key=lambda p: (p[0] - cx) ** 2 + (p[1] - cy) ** 2)
    made = pose(duke, f"sector_{sector_id}", cx, cy, far[0], far[1], horiz)
    return made


def look(map_path: pathlib.Path, out_dir: pathlib.Path, views, *,
         resources: pathlib.Path | None = None) -> dict[str, Any]:
    from bloodmap.duke import read_duke_map
    from bloodmap.format import write_map
    from bloodmap.visual import ObservationRequest, run_observation

    duke = read_duke_map(map_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    resources = resources or (ROOT / "work" / "duke-view-resources")
    report = build_resources(resources)
    disk, counts = viewing_copy(duke)
    copy = out_dir / "viewing-copy.MAP"
    write_map(disk, copy)
    made = [v(duke) if callable(v) else v for v in views]
    run_observation(ObservationRequest(
        map_path=copy, output_dir=out_dir, resource_dir=resources,
        viewpoints=made, width=640, height=480,
        screenshots=[v.view_id for v in made], brightness=0, rff=None))
    frames = sorted(p.stem for p in (out_dir / "frames").glob("*.png"))
    missing = [v.view_id for v in made if v.view_id not in frames]
    result = {"map": str(map_path), "views": [v.view_id for v in made],
              "frames_missing": missing, "resources": report, **counts,
              "claims": {"geometry_is_dukes": True,
                         "palette_and_shading_are_dukes": True,
                         "sky_is_dukes": False,
                         "mechanisms_ran": False, "is_a_conversion": False}}
    (out_dir / "duke-view.json").write_text(json.dumps(result, indent=2), "utf-8")
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("map")
    parser.add_argument("-o", "--out", required=True)
    parser.add_argument("--pose", action="append", default=[],
                        help="name:x,y,tx,ty[,horiz] in the Duke map's units")
    parser.add_argument("--sectors", default="",
                        help="sector ids to stand in the middle of")
    args = parser.parse_args(argv)
    from bloodmap.duke import read_duke_map

    duke = read_duke_map(args.map)
    views = []
    for text in args.pose:
        name, numbers = text.split(":", 1)
        values = [int(v) for v in numbers.split(",")]
        views.append(pose(duke, name, *values))
    for text in (s for s in args.sectors.split(",") if s):
        views.append(sector_pose(duke, int(text)))
    if not views:
        h = duke.header
        for name, turn in (("start", 0), ("start_left", 1536),
                           ("start_right", 512), ("start_back", 1024)):
            a = (int(h["start_angle"]) + turn) & 2047
            views.append(pose(
                duke, name, h["start_x"], h["start_y"],
                int(h["start_x"] + 4096 * math.cos(a * math.pi / 1024)),
                int(h["start_y"] + 4096 * math.sin(a * math.pi / 1024))))
    result = look(pathlib.Path(args.map), pathlib.Path(args.out), views)
    print(json.dumps({k: result[k] for k in
                      ("views", "frames_missing", "sprites_kept",
                       "sprites_dropped")}, indent=2))
    return 1 if result["frames_missing"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
