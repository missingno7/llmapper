"""Cut a sector set out of a map into a small playable map, with one question.

    PYTHONPATH=. python -m tools.fragment_map MAP -s 3 7 8 45 \
        -o projects/e3m1-decompiled/fragments/street.MAP \
        --question "Is this one step of shadow or two?"

The owner's review channel is the walk and the FRAGMENT
(`10_AGENT_EXECUTION_PROTOCOL.md`, "The owner's review channel is the walk").
A fragment is for the questions a census cannot answer because they are about
what something LOOKS like: whether a shade step reads as one shadow or two,
whether a width reads as a street or an avenue, whether a room reads as
anything at all. Those cannot be settled by counting, and they do not deserve
a whole map to walk.

What it does:

* keeps the chosen sectors, their walls and the sprites standing in them;
* SEALS every wall that used to lead somewhere else -- `next_sector` and
  `next_wall` to -1, blocking bit set, and a visible texture chosen from the
  fragment's own one-sided walls rather than invented, so the cut edge looks
  like the map it came from;
* rebases the start position into the first chosen sector, at its floor;
* writes a `.MAP` and a one-line `.md` beside it with the question and the
  ORIGINAL sector ids, so an answer comes back with ids that mean something
  in the whole map.

Indices necessarily move -- the fragment is a smaller map -- so the sidecar
carries the mapping both ways. The question is what the owner reads; the
mapping is what turns an answer into a test.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter
from typing import Any

BLOCKING = 1
#: A wall that used to be two-sided has no `picnum` worth showing -- Blood
#: draws the masked band from `over_picnum` there. Sealing it needs a real
#: tile, and the honest source is the fragment's own one-sided walls: the
#: material this piece of the map is already made of.
FALLBACK_TILE = 0


def _floor_centre(disk: Any, sector: int) -> tuple[int, int]:
    fields = disk.sectors[sector].fields
    first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    xs = [int(disk.walls[i].fields["x"]) for i in range(first, first + count)]
    ys = [int(disk.walls[i].fields["y"]) for i in range(first, first + count)]
    return sum(xs) // len(xs), sum(ys) // len(ys)


def cut(disk: Any, sectors: list[int]) -> dict[str, Any]:
    """Build the fragment in place on `disk`. Returns what moved."""
    chosen = sorted(set(int(one) for one in sectors))
    for one in chosen:
        if not 0 <= one < len(disk.sectors):
            raise SystemExit(f"sector {one} is not in 0..{len(disk.sectors) - 1}")

    wall_ids: list[int] = []
    for sector in chosen:
        fields = disk.sectors[sector].fields
        first, count = int(fields["wall_ptr"]), int(fields["wall_count"])
        wall_ids.extend(range(first, first + count))
    if len(wall_ids) != len(set(wall_ids)):
        raise SystemExit("the chosen sectors share wall ownership")

    sector_of = {source: index for index, source in enumerate(chosen)}
    wall_of = {source: index for index, source in enumerate(wall_ids)}

    #: The tile the cut edges will wear: whatever this piece of the map
    #: already shows on a wall that faces nothing.
    solid = Counter(int(disk.walls[i].fields["picnum"]) for i in wall_ids
                    if int(disk.walls[i].fields["next_sector"]) < 0)
    fill = solid.most_common(1)[0][0] if solid else FALLBACK_TILE

    walls = [disk.walls[i] for i in wall_ids]
    sealed = 0
    for source, wall in zip(wall_ids, walls):
        fields = wall.fields
        fields["point2"] = wall_of[int(fields["point2"])]
        there = int(fields["next_sector"])
        if there in sector_of:
            fields["next_sector"] = sector_of[there]
            fields["next_wall"] = wall_of[int(fields["next_wall"])]
            continue
        fields["next_sector"] = -1
        fields["next_wall"] = -1
        fields["cstat"] = int(fields["cstat"]) | BLOCKING
        if not int(fields["picnum"]):
            fields["picnum"] = (int(fields["over_picnum"])
                                or fill)
        sealed += 1

    sprites = [item for item in disk.sprites
               if int(item.fields["sector"]) in sector_of]
    for item in sprites:
        item.fields["sector"] = sector_of[int(item.fields["sector"])]

    kept_sectors = [disk.sectors[i] for i in chosen]
    offset = 0
    for sector, source in zip(kept_sectors, chosen):
        fields = sector.fields
        fields["wall_ptr"] = offset
        offset += int(fields["wall_count"])

    disk.sectors[:] = kept_sectors
    disk.walls[:] = walls
    disk.sprites[:] = sprites

    x, y = _floor_centre(disk, 0)
    disk.header["start_sector"] = 0
    disk.header["start_x"] = x
    disk.header["start_y"] = y
    #: A body stands ON the floor, so the eye is one standing height above it
    #: and Blood's z grows downward (`blood-player-body`: 16960 for a standing
    #: human, and the camera sits at chest level).
    disk.header["start_z"] = int(disk.sectors[0].fields["floor_z"]) - 16960

    return {"sectors": {str(source): index
                        for source, index in sector_of.items()},
            "walls_kept": len(walls), "walls_sealed": sealed,
            "sprites": len(sprites), "cut_edge_tile": fill,
            "start": {"sector_in_fragment": 0, "sector_in_the_map": chosen[0],
                      "x": x, "y": y,
                      "z": int(disk.header["start_z"])}}


def sidecar(name: str, question: str, sectors: list[int],
            moved: dict[str, Any], why: str) -> str:
    ids = ", ".join(str(one) for one in sorted(sectors))
    return "\n".join([
        f"# Fragment: {name}",
        "",
        f"**{question}**",
        "",
        why,
        "",
        f"Cut from E3M1: sectors **{ids}** — those are their ids in the whole "
        f"map, and an answer that names one lands where it means something. "
        f"In the fragment they are 0..{len(sectors) - 1} in that order.",
        "",
        f"{moved['walls_kept']} walls, {moved['walls_sealed']} of them sealed "
        f"where the cut runs (blocking, wearing tile "
        f"{moved['cut_edge_tile']}, the tile this piece already shows on its "
        f"own solid walls). {moved['sprites']} sprites. You start in sector "
        f"{moved['start']['sector_in_the_map']} at the floor.",
        "",
        "The sealed edges are the cut, not the map: ignore them. Everything "
        "inside them is E3M1's own geometry, untouched.",
        "",
    ]) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("map")
    parser.add_argument("-s", "--sectors", nargs="+", type=int, required=True)
    parser.add_argument("-o", "--out", required=True)
    parser.add_argument("--question", required=True)
    parser.add_argument("--why", default="")
    args = parser.parse_args(argv)

    from bloodmap.format import read_map, write_map

    disk = read_map(args.map)
    moved = cut(disk, args.sectors)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    write_map(disk, out)
    out.with_suffix(".md").write_text(
        sidecar(out.stem, args.question, args.sectors, moved, args.why),
        encoding="utf-8")
    out.with_suffix(".json").write_text(
        json.dumps({"of": args.map, "question": args.question, **moved},
                   indent=1, sort_keys=True), encoding="utf-8")
    print(f"wrote {out} ({len(disk.sectors)} sectors, "
          f"{moved['walls_kept']} walls, {moved['walls_sealed']} sealed)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
