"""What a Blood level looks like from inside it.

Every other mining pass in this project reads the map file. This one reads the
*frame*: it stands the camera in each room of each campaign map, asks the
renderer what it painted, and aggregates the answers into norms a level can be
compared against.

That is worth doing because the faults found by looking at the monastery were
never faults the map file could show. A fence sunk to its waist, a door face on
the inside of its own frame, a grille edge-on in a doorway -- all structurally
valid, all obvious on screen. The map says what exists; only the renderer says
what is *seen*.

.. code-block:: bash

    python -m tools.mine_visual_norms --maps maps/blood \\
        -o knowledge/blood/design/visual-norms-v1.json

Four things are measured per frame, all of them ratios so a big map and a small
one are comparable:

``composition``
    the share of painted pixels that is floor, ceiling, wall, upper, lower,
    masked, sky or sprite. A room whose frame is two-thirds floor is a room the
    player is looking down at.

``tile_variety``
    distinct picnums in the frame. The count the eye reads as "detailed".

``depth``
    distinct sectors in the frame. How far the level lets you see, which is a
    property of its portals rather than of its lighting.

``contrast``
    the spread of shade values across the painted surfaces, pixel-weighted.
    A level with no spread is flatly lit however many lights it has in it.

Poses are deterministic: the playable sectors of a map, sorted, sampled evenly,
each looked at from its own centroid along two opposite angles. No randomness,
so two runs of the same corpus produce the same norms.
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import statistics
import tempfile
from collections import Counter
from typing import Any

from bloodmap.format import read_map
from bloodmap.player_space import PLAYER_PROFILES
from bloodmap.reachability import design_sectors
from bloodmap.visual import ObservationRequest, Viewpoint, run_observation

SCHEMA = "llmapper.blood-visual-norms"
SCHEMA_VERSION = 1

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")

#: Surface kinds the observer reports.
KINDS = ("wall", "upper", "lower", "masked", "floor", "ceiling", "sky", "sprite")

#: Eye height above the floor, in z units. Blood's z axis points down, so the
#: camera sits at `floor_z - EYE_DROP`.
#:
#: This was 3000, invented, while the project's own player profile already
#: carried the right number. `player.cpp` sets `zView = sprite.z - eyeAboveZ`
#: and the standing human's `eyeAboveZ` is 0x1600 = 5632; 2048 is the crouch.
#: So every frame measured here was taken from somewhere between a crouch and a
#: stand. The campaign and the candidate were both measured that way, so the
#: comparisons survived -- but a wrong camera makes any absolute reading wrong,
#: and it is exactly the kind of number that must come from the profile rather
#: than from a guess.
EYE_DROP = PLAYER_PROFILES["blood"].eye_height

#: Angles looked from at each pose. Two opposite ones rather than four, because
#: a frame and its reverse already cover a room's two halves and doubling the
#: sample does not change any median measurably.
ANGLES = (0, 1024)


def _centroid(disk: Any, sector_id: int) -> tuple[int, int]:
    fields = disk.sectors[sector_id].fields
    start, count = int(fields["wall_ptr"]), int(fields["wall_count"])
    xs = [int(disk.walls[w].fields["x"]) for w in range(start, start + count)]
    ys = [int(disk.walls[w].fields["y"]) for w in range(start, start + count)]
    return sum(xs) // len(xs), sum(ys) // len(ys)


def viewpoints(disk: Any, *, sample: int) -> list[Viewpoint]:
    """One pose per sampled playable sector, looked at from two angles."""
    playable = sorted(design_sectors(disk))
    if not playable:
        return []
    if len(playable) > sample:
        step = len(playable) / sample
        playable = [playable[int(i * step)] for i in range(sample)]
    out: list[Viewpoint] = []
    for sector_id in playable:
        x, y = _centroid(disk, sector_id)
        fields = disk.sectors[sector_id].fields
        floor_z, ceiling_z = int(fields["floor_z"]), int(fields["ceiling_z"])
        z = floor_z - EYE_DROP
        if z < ceiling_z:                      # a room shorter than the eye
            z = (floor_z + ceiling_z) // 2
        for angle in ANGLES:
            out.append(Viewpoint(
                f"s{sector_id}_a{angle}", x=x, y=y, z=z, angle=angle, sector=sector_id))
    return out


def frame_metrics(view: dict[str, Any]) -> dict[str, Any] | None:
    """Composition, variety, depth and contrast for one painted frame."""
    surfaces = view.get("surfaces") or []
    painted = sum(int(s.get("pixels") or 0) for s in surfaces)
    if painted <= 0:
        return None
    by_kind: Counter = Counter()
    tiles: set[int] = set()
    sectors: set[int] = set()
    shades: list[tuple[int, int]] = []
    for surface in surfaces:
        pixels = int(surface.get("pixels") or 0)
        if pixels <= 0:
            continue
        by_kind[str(surface.get("kind"))] += pixels
        tiles.add(int(surface.get("picnum", 0)))
        sectors.add(int(surface.get("sector", -1)))
        shades.append((int(surface.get("shade", 0)), pixels))
    values = [shade for shade, _ in shades]
    weighted = [shade for shade, pixels in shades for _ in range(max(1, pixels // 4096))]
    return {
        "painted": painted,
        "composition": {kind: by_kind.get(kind, 0) / painted for kind in KINDS},
        "tile_variety": len(tiles),
        "depth": len(sectors),
        "contrast": (max(values) - min(values)) if values else 0,
        "shade_spread": round(statistics.pstdev(weighted), 2) if len(weighted) > 1 else 0.0,
    }


def observe_map(path: str, *, sample: int, resource_dir: str) -> list[dict[str, Any]]:
    disk = read_map(path)
    poses = viewpoints(disk, sample=sample)
    if not poses:
        return []
    with tempfile.TemporaryDirectory() as work:
        request = ObservationRequest(
            map_path=path, output_dir=work, resource_dir=resource_dir,
            viewpoints=tuple(poses))
        manifest = run_observation(request)
        data = manifest.data
    rows = []
    for view in data.get("views", []):
        if view.get("status") != "ok":
            continue
        metrics = frame_metrics(view)
        if metrics is not None:
            rows.append(metrics)
    return rows


def _band(values: list[float], *, digits: int = 3) -> dict[str, float]:
    ordered = sorted(values)
    if not ordered:
        return {}
    def at(fraction: float) -> float:
        return ordered[min(len(ordered) - 1, int(fraction * (len(ordered) - 1)))]
    return {
        "q1": round(at(0.25), digits),
        "median": round(statistics.median(ordered), digits),
        "q3": round(at(0.75), digits),
    }


def summarize(per_map: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
    """Per-map medians first, then bands across maps.

    Aggregating frames directly would let a 300-sector map outvote a 100-sector
    one; the question is what a *level* looks like, so each level gets one vote.
    """
    metrics: dict[str, list[float]] = {}
    for rows in per_map.values():
        if not rows:
            continue
        for kind in KINDS:
            metrics.setdefault(f"composition.{kind}", []).append(
                statistics.median(r["composition"][kind] for r in rows))
        for name in ("tile_variety", "depth", "contrast", "shade_spread"):
            metrics.setdefault(name, []).append(
                statistics.median(r[name] for r in rows))
    return {name: _band(values) for name, values in sorted(metrics.items())}


def compare(rows: list[dict[str, Any]], norms: dict[str, Any]) -> list[dict[str, Any]]:
    """One level's medians against the corpus bands."""
    if not rows:
        return []
    mine: dict[str, float] = {}
    for kind in KINDS:
        mine[f"composition.{kind}"] = statistics.median(r["composition"][kind] for r in rows)
    for name in ("tile_variety", "depth", "contrast", "shade_spread"):
        mine[name] = statistics.median(r[name] for r in rows)
    out = []
    for name, value in sorted(mine.items()):
        band = norms.get(name) or {}
        if not band:
            continue
        out.append({
            "metric": name,
            "level": round(value, 3),
            "q1": band["q1"], "median": band["median"], "q3": band["q3"],
            "inside": band["q1"] <= value <= band["q3"],
        })
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("--art", default="reference/blood")
    parser.add_argument("--sample", type=int, default=24,
                        help="playable sectors sampled per map")
    parser.add_argument("--against", help="a built MAP to compare with the norms")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    per_map: dict[str, list[dict[str, Any]]] = {}
    for path in sorted(glob.glob(str(pathlib.Path(args.maps) / "*.MAP"))):
        name = pathlib.Path(path).stem.upper()
        if not CAMPAIGN.match(name) or name in per_map:
            continue
        try:
            per_map[name] = observe_map(path, sample=args.sample, resource_dir=args.art)
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")

    frames = sum(len(rows) for rows in per_map.values())
    norms = summarize(per_map)
    document = {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "maps": len(per_map),
        "frames": frames,
        "sample_per_map": args.sample,
        "angles": list(ANGLES),
        "metrics": norms,
        "reading_guide": [
            "each map contributes its own median, so a large level does not "
            "outvote a small one",
            "composition shares are of painted pixels, not of the frame, so a "
            "view into the void does not count as floor",
            "a band is what the campaign did, never what a level must do",
        ],
    }
    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")

    print(json.dumps({"maps": len(per_map), "frames": frames, "output": args.output},
                     indent=1))
    if args.against:
        rows = observe_map(args.against, sample=args.sample, resource_dir=args.art)
        print()
        print("%-26s %9s  %-24s %s" % ("metric", "level", "campaign q1..q3", ""))
        inside = 0
        table = compare(rows, norms)
        for row in table:
            inside += bool(row["inside"])
            print("%-26s %9s  %8s..%-8s %s" % (
                row["metric"], row["level"], row["q1"], row["q3"],
                "in" if row["inside"] else "OUT"))
        print("\ninside %d of %d" % (inside, len(table)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
