"""Find the views where Build cannot decide which of two sectors is in front.

.. code-block:: bash

    python -m tools.render_conflicts MAP.MAP observation.json

Build orders what it draws by sorting *bunches* of walls, and the whole sort
rests on `wallfront` (build/src/engine.cpp:2227), which is a purely 2D test: it
takes the two walls' x/y and the viewer's x/y, and there is no z in it anywhere.
For two walls lying on the same line it finds ``t1 == 0 && t2 == 0`` and returns
**-1**, and the sort at engine.cpp:9739 answers a -1 with ``continue`` -- so the
pair is never ordered and whichever bunch the loop happens to be holding is drawn
first. The engine says so itself, one line above::

    closest = 0;              //Almost works, but not quite :(

For a level that stacks storeys this is the failure that matters. A ground floor
and the floor above it have the same outline, so every wall of one is coincident
with a wall of the other. While only one of them is on screen nothing is wrong.
The moment a viewpoint holds **both** -- looking in from the side, through two
openings in one facade -- the renderer has two unorderable bunches covering the
same screen columns, and which one wins is an artifact of wall order.

That is a property of the *view*, not of the map, so it cannot be settled by
reading geometry alone -- and it should not be settled by looking at pictures
either. **The renderer is asked directly.** `bunchfront` in the XMapEdit fork
(`xmapedit/src/engine.c`) records every pair it could not rank, at the point of
failure:

    if (obs_enabled && verdict < 0)
        obs_note_unorderable(thesector[l], thesector[r], verdict, ...);

and the observer emits them per view as ``unorderable``. `bunchfront` returns -1
in two harmless cases first, when the two bunches share no screen column at all;
those return before the instrumented line, so what reaches the report is only a
`wallfront` failure on bunches that *do* overlap in x -- two sets of pixels in
the same columns with nothing deciding which wins.

That is the fault itself rather than a symptom, and it replaces the older
heuristic here, which paired coincident-walled sectors found in the map file with
overlapping screen bounding boxes. The heuristic and the renderer disagreed about
which pairs on BB4 were at fault; the renderer is the authority. The heuristic is
kept behind `--bbox` for comparing the two.

The campaign's own practice, for scale: 22 unjoined coincident wall pairs in
113,912 walls across 44 maps. Six maps have any at all, and the worst has six.
"""

from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bloodmap.format import read_map
from bloodmap.planar_geom import classify_segment_pair
from tools.measure_draw_order import classify_conflicts

#: The three ways `classify_segment_pair` says "these two lie on one line".
COINCIDENT = {
    "exact_reversed_coincident",
    "exact_same_direction_coincident",
    "partial_collinear_overlap",
}


def wall_owners(disk) -> dict[int, int]:
    owner: dict[int, int] = {}
    for index, sector in enumerate(disk.sectors):
        first = int(sector.fields["wall_ptr"])
        count = int(sector.fields["wall_count"])
        for wall in range(first, first + count):
            owner[wall] = index
    return owner


def segments(disk) -> list[tuple[tuple[int, int], tuple[int, int]]]:
    out = []
    for wall in disk.walls:
        fields = wall.fields
        end = disk.walls[int(fields["point2"])].fields
        out.append(((int(fields["x"]), int(fields["y"])),
                    (int(end["x"]), int(end["y"]))))
    return out


def unorderable_pairs(disk) -> dict[tuple[int, int], int]:
    """Sector pairs sharing a wall line with no portal between them.

    Returned with how many wall pairs they share, because one shared wall is a
    corner touching and four is one room sitting exactly on another.
    """
    owner = wall_owners(disk)
    seg = segments(disk)
    bucket: dict[tuple, list[int]] = collections.defaultdict(list)
    for index, (start, end) in enumerate(seg):
        if start != end:
            bucket[tuple(sorted((start, end)))].append(index)

    found: dict[tuple[int, int], int] = collections.Counter()
    for walls in bucket.values():
        for i, left in enumerate(walls):
            for right in walls[i + 1:]:
                if owner[left] == owner[right]:
                    continue
                relation = classify_segment_pair(*seg[left], *seg[right])
                if relation is None or str(relation["kind"]) not in COINCIDENT:
                    continue
                paired = (int(disk.walls[left].fields["next_wall"]) == right
                          and int(disk.walls[right].fields["next_wall"]) == left)
                if not paired:
                    found[tuple(sorted((owner[left], owner[right])))] += 1
    return dict(found)


def box_overlap(a: list[int], b: list[int]) -> int:
    """Area shared by two screen bounding boxes, in pixels."""
    width = min(a[2], b[2]) - max(a[0], b[0]) + 1
    height = min(a[3], b[3]) - max(a[1], b[1]) + 1
    return width * height if width > 0 and height > 0 else 0


def drawn_by_sector(view: dict) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = collections.defaultdict(list)
    for surface in view.get("surfaces", ()):
        if int(surface.get("pixels") or 0) <= 0:
            continue
        if "bbox" not in surface:
            continue
        out[int(surface["sector"])].append(surface)
    return out


def overlap_pairs_at_risk(disk) -> dict[tuple[int, int], int]:
    """Overlapping sectors the tiered validator could not prove safe.

    Coincident walls are the sharpest case, but any two sectors that share
    ground can be handed to `wallfront` together, so the question is asked of
    both populations.
    """
    from bloodmap import overlap_visibility as ov

    out: dict[tuple[int, int], int] = {}
    for verdict in ov.audit(disk):
        if verdict.safe:
            continue
        out[tuple(sorted(verdict.sectors))] = 0
    return out


def reported(manifest: dict) -> list[dict]:
    """What the renderer itself said it could not order.

    One row per (view, sector pair). `asked` is how many times the sort put the
    question and got no answer, and `why` separates walls lying on one line from
    walls that properly cross -- `wallfront` returns -1 and -2 respectively and
    the sort treats both the same.
    """
    out: list[dict] = []
    for view in manifest.get("views", ()):
        if view.get("status") != "ok":
            continue
        for item in view.get("unorderable", ()):
            out.append({
                "view": view["id"], "camera": view["camera"],
                "sectors": list(item["sectors"]),
                "why": item.get("why"), "verdict": item.get("verdict"),
                "columns": item.get("columns"), "asked": item.get("asked", 1),
            })
    out.sort(key=lambda row: -row["asked"])
    return out


def conflicts(disk, manifest: dict, *, overlaps: bool = False) -> list[dict]:
    """Every view that drew both halves of a pair the renderer cannot order."""
    pairs = overlap_pairs_at_risk(disk) if overlaps else unorderable_pairs(disk)
    out: list[dict] = []
    for view in manifest.get("views", ()):
        if view.get("status") != "ok":
            continue
        drawn = drawn_by_sector(view)
        for (left, right), shared_walls in pairs.items():
            if left not in drawn or right not in drawn:
                continue
            worst = 0
            witness = None
            for a in drawn[left]:
                for b in drawn[right]:
                    area = box_overlap(a["bbox"], b["bbox"])
                    if area > worst:
                        worst, witness = area, (a, b)
            if worst <= 0:
                continue
            out.append({
                "view": view["id"],
                "camera": view["camera"],
                "sectors": [left, right],
                "shared_walls": shared_walls,
                "overlap_pixels": worst,
                "overlap_share": round(worst / max(1, int(
                    view.get("frame", {}).get("pixels") or 1)), 4),
                "surfaces": [
                    {k: witness[i][k] for k in ("kind", "wall", "picnum", "bbox")
                     if k in witness[i]} for i in (0, 1)
                ],
            })
    out.sort(key=lambda item: -item["overlap_pixels"])
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("map")
    parser.add_argument("manifest")
    parser.add_argument("-o", "--out", default=None)
    parser.add_argument("--top", type=int, default=15)
    parser.add_argument("--bbox", action="store_true",
                        help="use the old screen-bounding-box heuristic instead "
                             "of the renderer's own report")
    parser.add_argument("--overlaps", action="store_true",
                        help="ask about every overlapping pair the tiered "
                             "validator could not prove safe, not only the "
                             "pairs with coincident walls")
    args = parser.parse_args(argv)

    disk = read_map(args.map)
    manifest = json.loads(pathlib.Path(args.manifest).read_text(encoding="utf-8"))
    views = len([v for v in manifest.get("views", ()) if v.get("status") == "ok"])

    if args.bbox:
        pairs = (overlap_pairs_at_risk(disk) if args.overlaps
                 else unorderable_pairs(disk))
        found = conflicts(disk, manifest, overlaps=args.overlaps)
        bad_views = {item["view"] for item in found}
        print(f"[bbox heuristic] {len(pairs)} candidate pair(s); "
              f"{len(bad_views)} of {views} view(s) drew both halves of one")
    found = reported(manifest)
    if not found and not any("unorderable" in v for v in manifest.get("views", ())):
        print("this manifest predates the instrumented observer -- rebuild "
              "xmapedit/src_blood/observe and re-run the sweep, or pass --bbox")
        return 1
    bad_views = {item["view"] for item in found}
    seen: dict[tuple[int, int], int] = collections.Counter()
    for item in found:
        pair = tuple(sorted(item["sectors"]))
        seen[pair] += item["asked"]
    print("the renderer could not rank {} sector pair(s); "
          "{} of {} view(s) hit one".format(len(seen), len(bad_views), views))
    payload = {
        "$schema": "llmapper.render-conflicts",
        "map": args.map,
        "source": "bunchfront, via the instrumented observer",
        "pairs": [{"sectors": list(k), "asked": n}
                  for k, n in seen.most_common()],
        "views_rendered": views,
        "views_with_a_conflict": sorted(bad_views),
        "conflicts": found,
    }
    split = classify_conflicts(disk, payload)
    payload.update({
        "overlapping_pairs": split["pairs_overlapping"],
        "coplanar_pairs": split["pairs_coplanar"],
        "same_sector_pairs": split["pairs_same_sector"],
        "per_thousand": split["per_thousand"],
        "per_thousand_two_sector": split["per_thousand_two_sector"],
        "per_thousand_overlapping": split["per_thousand_overlapping"],
        "per_thousand_coplanar": split["per_thousand_coplanar"],
        "per_thousand_same_sector": split["per_thousand_same_sector"],
    })
    print("  overlapping {} ({}/1000), coplanar neighbours {} ({}/1000), "
          "same-sector {} ({}/1000)".format(
              split["n_overlapping"], split["per_thousand_overlapping"],
              split["n_coplanar"], split["per_thousand_coplanar"],
              split["n_same_sector"], split["per_thousand_same_sector"]))
    overlap_set = {tuple(p["sectors"]) for p in split["pairs_overlapping"]}
    for pair, asked in seen.most_common(args.top):
        why = next(r["why"] for r in found
                   if tuple(sorted(r["sectors"])) == pair)
        if pair[0] == pair[1]:
            kind = "same-sector"
        elif pair in overlap_set:
            kind = "overlap"
        else:
            kind = "coplanar"
        print(f"  [{kind:11}] sectors {pair[0]:>4}/{pair[1]:<4} "
              f"asked {asked:4d}  {why}")
    if args.out:
        pathlib.Path(args.out).write_text(json.dumps(payload, indent=1) + "\n",
                                          encoding="utf-8")
        print("wrote " + args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
