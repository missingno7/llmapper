"""Judge a before/after design experiment from what the observer measured.

    python -m tools.judge_experiment projects/blood-city/experiments/church-skyline

An experiment directory holds `hypothesis.json` (written before the change),
`before/` and `after/` (two `look.py` runs of the SAME pose set), and receives
`result.json`.  This prints and records the measurements a prediction can be
held to -- it does not decide whether the level got better.  That needs eyes.

What is measured, per view present in both runs:

* `sky_share`     painted share of the frame that is parallax ceiling
* `changed_px`    pixels that differ between the two frames (0 = identical)
* `tall_wall_px`  pixels painted by one-sided walls of the tallest sky sectors
* `upper_steps`   walls painted as an upper step between two open sectors --
                  a drawn sky seam, which should never happen
* `ceiling_leak_px` pixels of a roofed sector's ceiling painted from the top
                  row of an outdoor frame: a room under a see-over roof
                  leaking into the sky, which should never happen either

and for each map: sha256, counts, and `bloodmap.skyline.profile`.

Identity is by content: every frame and both maps are hashed into the result,
so a later reader can tell whether the evidence is still the evidence.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from bloodmap import skyline
from bloodmap.format import read_map


def sha256(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _changed_pixels(left: pathlib.Path, right: pathlib.Path) -> int | None:
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return None
    a = Image.open(left).convert("RGB")
    b = Image.open(right).convert("RGB")
    if a.size != b.size:
        return a.size[0] * a.size[1]
    diff = ImageChops.difference(a, b).convert("L")
    return sum(diff.histogram()[1:])


def measure_run(run_dir: pathlib.Path) -> dict:
    observation = json.loads((run_dir / "observation.json").read_text("utf-8"))
    # The run's own copy of the MAP, when `look.py` left one: the path the
    # observer was given is overwritten by the next build, the copy is not.
    map_path = run_dir / "observed.MAP"
    if not map_path.exists():
        recorded = observation["map"]
        map_path = pathlib.Path(recorded["path"] if isinstance(recorded, dict)
                                else recorded)
        if not map_path.is_absolute():
            map_path = ROOT / map_path
    disk = read_map(map_path)
    sectors = [s.fields for s in disk.sectors]
    walls = [w.fields for w in disk.walls]
    sky = {i for i, s in enumerate(sectors) if int(s["ceiling_stat"]) & 1}
    prof = skyline.profile(disk)
    tallest = set(prof["tallest_sectors"])
    frame = observation.get("frame") or {}
    views = {}
    for view in observation["views"]:
        width = (view.get("frame") or frame).get("width", 640)
        height = (view.get("frame") or frame).get("height", 480)
        total = width * height
        sky_px = tall_px = 0
        seams = []
        # A roofed sector's ceiling painted from the top row of an outdoor
        # frame is an interior leaking into the sky over a low wall: Build
        # keeps one open span per screen column, and a room under a roof that
        # is being looked over paints into it.
        leaks = [int(s["pixels"]) for s in view.get("surfaces", ())
                 if s["kind"] == "ceiling" and int(s["sector"]) not in sky
                 and int(view["camera"]["sector"]) in sky
                 and int(s["bbox"][1]) <= 1]
        for surface in view.get("surfaces", ()):
            kind, sector = surface["kind"], int(surface["sector"])
            if kind == "sky":
                sky_px += int(surface["pixels"])
            if kind == "wall" and sector in tallest:
                tall_px += int(surface["pixels"])
            if kind == "upper" and sector in sky:
                other = int(walls[int(surface["wall"])]["next_sector"])
                if other in sky and int(surface["pixels"]) > 0:
                    seams.append(int(surface["wall"]))
        png = run_dir / "frames" / f"{view['id']}.png"
        views[view["id"]] = {
            "status": view["status"],
            "camera": {k: view["camera"][k]
                       for k in ("x", "y", "z", "angle", "horiz")},
            "sky_share": round(sky_px / total, 4),
            "tall_wall_px": tall_px,
            "upper_steps": seams,
            "ceiling_leak_px": sum(leaks),
            "frame_sha256": sha256(png) if png.exists() else None,
        }
    return {
        "map": str(map_path.relative_to(ROOT)) if map_path.is_relative_to(ROOT)
        else str(map_path),
        "map_sha256": sha256(map_path),
        "sectors": len(sectors), "walls": len(walls),
        "sprites": len(disk.sprites),
        "skyline": prof,
        "views": views,
    }


def compare(directory: pathlib.Path, runs: dict, left: str, right: str) -> dict:
    a, b = runs[left]["views"], runs[right]["views"]
    return {
        view_id: {
            "same_pose": a[view_id]["camera"] == b[view_id]["camera"],
            "sky_share": [a[view_id]["sky_share"], b[view_id]["sky_share"]],
            "tall_wall_px": [a[view_id]["tall_wall_px"],
                             b[view_id]["tall_wall_px"]],
            "changed_px": _changed_pixels(
                directory / left / "frames" / f"{view_id}.png",
                directory / right / "frames" / f"{view_id}.png"),
        } for view_id in a if view_id in b}


def judge(directory: pathlib.Path, pairs: list[tuple[str, str]]) -> dict:
    result = {"$schema": "llmapper.design-experiment-result",
              "schema_version": 1,
              "hypothesis_sha256": sha256(directory / "hypothesis.json"),
              "runs": {}, "compare": {}}
    for left, right in pairs:
        for name in (left, right):
            if name not in result["runs"]:
                result["runs"][name] = measure_run(directory / name)
        result["compare"][f"{left}->{right}"] = compare(
            directory, result["runs"], left, right)
    return result


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory")
    parser.add_argument("--pair", action="append", default=[],
                        help="LEFT:RIGHT run directories to compare "
                             "(default before:after)")
    args = parser.parse_args(argv)
    directory = pathlib.Path(args.directory)
    pairs = [tuple(p.split(":", 1)) for p in (args.pair or ["before:after"])]
    result = judge(directory, pairs)
    (directory / "result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", "utf-8")
    for name, run in result["runs"].items():
        print(f"{name}: {run['map_sha256'][:12]} sectors {run['sectors']} "
              f"walls {run['walls']} skyline {run['skyline']['by_bodies']}")
    for pair, rows in result["compare"].items():
        print(pair)
        for view_id, row in rows.items():
            print(f"  {view_id:18s} sky {row['sky_share'][0]:.3f}->"
                  f"{row['sky_share'][1]:.3f}  tall px {row['tall_wall_px'][0]}"
                  f"->{row['tall_wall_px'][1]}  changed {row['changed_px']}"
                  f"{'' if row['same_pose'] else '  POSE MOVED'}")
    seams = {name: {v: d["upper_steps"] for v, d in run["views"].items()
                    if d["upper_steps"]} for name, run in result["runs"].items()}
    print("drawn sky seams:", {k: v for k, v in seams.items() if v} or "none")
    leaks = {name: {v: d["ceiling_leak_px"] for v, d in run["views"].items()
                    if d["ceiling_leak_px"]} for name, run in result["runs"].items()}
    print("interior ceilings leaking into the sky:",
          {k: v for k, v in leaks.items() if v} or "none")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
