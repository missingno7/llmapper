"""The looks-good loop, at object scale.

A set-piece ships in a district only after this has run on it: rendered
from standing eye height at player approach distance, beside the
campaign's own nearest instance of the same class under identical
settings, with the measurable half checked against the class's mined
ranges and the whole thing written into a packet.

The comparison is the point, and it is why the campaign frames are
rendered here rather than remembered.  Comparing against memory is how the
sky bug survived four iterations; comparing against a frame rendered from
the same binary at the same size in the same session is what caught it.

    python projects/blood-city/level/object_loop.py --piece plaza_fountain

Taste stays human.  What passes measurably but still looks wrong goes to
`reports/review-queue.md` as "compare these two frames", not as "is this
good".
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from bloodmap.format import read_map
from bloodmap.viewplan import eye_z
from bloodmap.visual import ObservationRequest, Viewpoint, run_observation

from look import LEVEL, sector_at

PROJECT = pathlib.Path(__file__).resolve().parents[1]
CURRENT = PROJECT / "level" / "blood-city-current.MAP"
KNOWLEDGE = ROOT / "knowledge" / "blood" / "design" / "set-pieces-v1.json"
PLAYER = 16960
PLAN = 1024

#: How far back a player stands to look at a thing, and from where.
APPROACH = (2.5 * PLAN, 1.5 * PLAN, 4.0 * PLAN, 1.0 * PLAN)
BEARINGS = {"south": (0, 1), "west": (-1, 0), "east": (1, 0), "north": (0, -1)}

#: The pieces under the loop: what they are, where, and which campaign
#: instance of the same class to stand beside them.
PIECES = {
    "plaza_fountain": {
        "class": "basin",
        "note": "the plaza fountain, built by setpieces.basin",
        "rect_plan": (21.5, 43.5, 24.5, 46.5),
        "host_hint": (26.0, 45.0),
        "ranges": {"width_plan": (2.0, 3.4), "depth_plan": (2.0, 3.4)},
    },
    "saloon_counter": {
        "class": "raised block",
        "note": "the saloon bar, built by setpieces.counter",
        "rect_plan": (5.0, 9.0, 8.0, 10.0),
        "host_hint": (9.5, 12.5),
        "ranges": {"width_plan": (0.5, 3.0), "depth_plan": (0.5, 1.75)},
    },
    "church_altar": {
        "class": "two-tier raised",
        "note": "the chancel altar, built by setpieces.altar",
        "rect_plan": (28.25, 22.25, 29.5, 23.25),
        "host_hint": (29.4, 27.0),   # the nave: an altar is seen from the nave
        "ranges": {"width_plan": (0.5, 2.0), "depth_plan": (0.5, 2.0)},
    },
}


def approach_poses(level, rect, prefix: str, host=None) -> list[Viewpoint]:
    """Stand off the object and look at it, from up to three sides.

    `host` is the sector the object stands in.  Without it the first
    bearing that resolves to *any* sector wins, and the first reference
    render this loop produced was a corridor with a doorway in it -- the
    camera had stood through a wall from the basin it was supposed to be
    comparing.  A viewpoint with no line of sight to the object is not a
    weak comparison, it is not a comparison.
    """
    x0, y0, x1, y1 = rect
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    half = max(x1 - x0, y1 - y0) / 2
    out = []
    for name, (dx, dy) in BEARINGS.items():
        placed = None
        for back in APPROACH:
            px = int(cx + dx * (half + back))
            py = int(cy + dy * (half + back))
            sector = sector_at(level, px, py)
            if sector is None:
                continue
            if host is not None and sector != host:
                continue
            z = eye_z(level, sector)
            if z is None:
                continue
            angle = int(math.atan2(cy - py, cx - px) * 1024 / math.pi) & 2047
            placed = Viewpoint(
                view_id=f"{prefix}_{name}", x=px, y=py, z=z, angle=angle,
                horiz=LEVEL, sector=sector, node=f"{prefix}:{name}",
                purpose="object", screenshot=True,
                note=f"{prefix} from the {name}, {back / PLAN:.1f} units back")
            break
        if placed is not None:
            out.append(placed)
        if len(out) >= 3:
            break
    return out


def sectors_rect(level, sectors) -> tuple[float, float, float, float]:
    xs, ys = [], []
    for sector_id in sectors:
        s = level.sectors[sector_id]
        start = int(s["fields"]["wall_ptr"]) if isinstance(s, dict) else s.wall_ptr
        count = int(s["fields"]["wall_count"]) if isinstance(s, dict) else s.wall_count
        for w in range(start, start + count):
            wall = level.walls[w]
            f = wall["fields"] if isinstance(wall, dict) else wall
            xs.append(int(f["x"]))
            ys.append(int(f["y"]))
    return min(xs), min(ys), max(xs), max(ys)


def render(map_path, views, out_dir):
    out_dir.mkdir(parents=True, exist_ok=True)
    run_observation(ObservationRequest(
        map_path=map_path, output_dir=out_dir,
        resource_dir=ROOT / "reference" / "blood", viewpoints=views,
        width=640, height=480, screenshots=[v.view_id for v in views],
        brightness=0, rff=None))
    return sorted((out_dir / "frames").glob("*.png"))


#: What each class looks like in ONE example, tested on the example's own
#: geometry rather than on its class's.  The first version of this asked
#: "does this class contain a sunk example?" and then rendered whichever
#: example came first -- E1M5 [40, 41, 316, 317], tiers [0.0], a flat
#: alcove -- so the reference frame was a corridor with a doorway in it.
#: A class is a distribution; a reference has to be an instance.
def _is_basin(example) -> bool:
    tiers = example["tiers"]
    return (example["drop"] <= -0.2 and len(example["sectors"]) >= 3
            and len(tiers) >= 3 and max(tiers) <= 0.1)


def _is_raised_block(example) -> bool:
    return (len(example["sectors"]) == 1
            and 0.30 <= example["rise"] <= 0.55
            and max(example["footprint_plan"]) <= 2.0)


def _is_two_tier(example) -> bool:
    return (len(example["sectors"]) == 2 and len(example["tiers"]) == 2
            and 0.55 <= example["rise"] <= 1.1 and example["drop"] >= 0)


TESTS = {"basin": _is_basin, "raised block": _is_raised_block,
         "two-tier raised": _is_two_tier}


def campaign_instance(class_name: str, prefer=("E1M", "E2M", "E3M", "E4M")):
    """The campaign's nearest instance of this class, preferring base maps.

    Ranked by whether the map is base campaign and, for a basin, by how
    evenly its tiers descend -- an even descent is what makes the class
    read as one object rather than as a hole with a ledge.
    """
    test = TESTS.get(class_name)
    if test is None:
        return None, None
    with KNOWLEDGE.open(encoding="utf-8") as handle:
        data = json.load(handle)
    best = None
    for cls in data["classes"]:
        for example in cls["examples"]:
            if not test(example):
                continue
            base = 0 if any(example["map"].startswith(p) for p in prefer) else 1
            tiers = example["tiers"]
            gaps = [round(b - a, 2) for a, b in zip(tiers, tiers[1:])]
            evenness = (max(gaps) - min(gaps)) if len(gaps) > 1 else 0.0
            rank = (base, evenness, -len(example["sectors"]))
            if best is None or rank < best[0]:
                best = (rank, cls, example)
    return (best[1], best[2]) if best else (None, None)


def measure(level, rect, spec) -> list[tuple[str, bool, str]]:
    """The half of the verdict that is not taste."""
    x0, y0, x1, y1 = rect
    width, depth = (x1 - x0) / PLAN, (y1 - y0) / PLAN
    rows = []
    ranges = spec.get("ranges", {})
    for key, value in (("width_plan", width), ("depth_plan", depth)):
        if key in ranges:
            lo, hi = ranges[key]
            rows.append((f"{key} {value:.2f} in [{lo}, {hi}]",
                         lo <= value <= hi,
                         "inside the class's mined range"))
    return rows


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--piece", action="append", default=[])
    ap.add_argument("--tag", default="objects")
    args = ap.parse_args(argv)

    ours = read_map(CURRENT).to_level_ir()
    packet_dir = PROJECT / "reports" / "objects"
    packet_dir.mkdir(parents=True, exist_ok=True)

    for name in (args.piece or sorted(PIECES)):
        spec = PIECES[name]
        rect = tuple(int(v * PLAN) for v in spec["rect_plan"])
        # Our own poses need the same host constraint the reference ones
        # get: the first altar frames were a blank wall, the camera having
        # stood outside the chancel entirely.
        hint = spec.get("host_hint")
        host = (sector_at(ours, int(hint[0] * PLAN), int(hint[1] * PLAN))
                if hint else None)
        views = approach_poses(ours, rect, name, host=host)
        if not views:
            print(f"  ! {name}: no approach pose lands in a sector")
            continue
        mine_dir = PROJECT / "reports" / "looks" / f"{args.tag}-{name}"
        frames = render(CURRENT, views, mine_dir)

        cls, example = campaign_instance(spec["class"])
        ref_frames = []
        ref_note = "no campaign instance of this class is in the knowledge file"
        if example is not None:
            ref_map = ROOT / "maps" / "blood" / f"{example['map']}.MAP"
            ref_level = read_map(ref_map).to_level_ir()
            ref_rect = sectors_rect(ref_level, example["sectors"])
            ref_views = approach_poses(ref_level, ref_rect, f"ref_{name}",
                                       host=example.get("host"))
            ref_note = (f"{example['map']} sectors {example['sectors']} "
                        f"(tiers {example['tiers']}), class of "
                        f"{cls['occurrences']} pieces across "
                        f"{len(cls['maps'])} maps")
            if ref_views:
                ref_dir = PROJECT / "reports" / "looks" / f"{args.tag}-{name}-ref"
                ref_frames = render(ref_map, ref_views, ref_dir)

        if example is not None and not ref_frames:
            ref_note += "  (NO VALID VIEWPOINT: every approach bearing left "
            ref_note += "the host sector, so no comparison was rendered)"
        rows = measure(ours, rect, spec)
        lines = [f"# Object loop: {name}", "",
                 f"*{spec['note']}*", "",
                 f"**Class**: {spec['class']} — {ref_note}", "",
                 "## Measured", ""]
        for label, ok, why in rows:
            lines.append(f"- {'PASS' if ok else 'FAIL'} — {label} ({why})")
        lines += ["", "## Frames", "",
                  "Ours, at standing eye height and player approach distance:",
                  ""]
        lines += [f"- `{p.relative_to(PROJECT)}`" for p in frames]
        lines += ["", "The campaign's instance of the same class, same "
                  "binary, same size, same session:", ""]
        lines += ([f"- `{p.relative_to(PROJECT)}`" for p in ref_frames]
                  or ["- (none rendered)"])
        lines += ["", "## Verdict", "",
                  "Measured checks above. The comparison itself is a taste "
                  "call and goes to the review queue as a pair of frames, "
                  "not as a question.", ""]
        packet = packet_dir / f"{name}.md"
        packet.write_text("\n".join(lines), encoding="utf-8")
        passed = sum(1 for _, ok, _ in rows if ok)
        print(f"  {name}: {len(frames)} frames, {len(ref_frames)} reference, "
              f"{passed}/{len(rows)} measured checks -> {packet.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
