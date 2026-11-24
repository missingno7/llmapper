"""Many places on one sheet, each from where it can be seen: the pictures a comparison starts from.

`tools.study` photographs a room from inside it and `tools.look_at` from a ring
round a point. Neither asks whether the thing can be SEEN from there: the study
of ritual places (2026-11-24) came back with four views of the plinth under
E1M7's altar. This stands its cameras only where the line to the subject is
clear (`bloodmap.sight.sees`, through the portals and over the steps), spreads
them round it, and adds the highest spot that overlooks it, because a stage or
a circle is read from above. Forty places from thirty maps are one sheet of
frames, so a question ("how do people build a ritual circle?") is answered by
looking and not by reading records.

.. code-block:: bash

    python -m tools.gallery E1M7:41 E6M6:213 DWE2M8:133 -o work/gallery/ritual
    python -m tools.gallery --list places.txt --views 2 -o out      # one subject a line
    python -m tools.gallery E1M6@9000,24000,-20000 -o out           # a point, and its z

A subject is ``MAP:sector`` or ``MAP@x,y[,floor z]``; a community map is named
by its file name. The sheet is in pages of twelve frames.
"""

from __future__ import annotations

import argparse
import math
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NEAR, FAR, STEP = 900, 7000, 320      # how far a camera may stand, and the grid it is tried on
CLEAR = 160                           # no nearer a wall than this: a nose on a pillar is no view


def map_path(name: str) -> pathlib.Path:
    from bloodmap.corpus import corpus_map_path
    if pathlib.Path(name).exists():
        return pathlib.Path(name)
    try:
        return pathlib.Path(corpus_map_path(name))
    except Exception:
        want = name.lower().removesuffix(".map")
        for path in sorted((ROOT / "maps" / "blood").rglob("*")):
            if path.suffix.lower() == ".map" and path.stem.lower() == want:
                return path
        raise


def subject_of(level, text: str):
    """(map name, sector, x, y, z of what is looked at)."""
    from bloodmap.sector_geom import sector_at
    from bloodmap.viewplan import eye_z, interior_point
    if "@" in text:
        name, at = text.split("@", 1)
        parts = [int(float(v)) for v in at.split(",")]
        near = parts[2] if len(parts) > 2 else None
        sector = sector_at(level, parts[0], parts[1], floor_near=near)
        if sector is None:
            raise SystemExit(f"{text}: in no sector")
        x, y = parts[:2]
    else:
        name, number = text.rsplit(":", 1)
        sector = int(number)
        x, y = interior_point(level, sector) or next(
            (int(s["fields"]["x"]), int(s["fields"]["y"])) for s in level.sprites
            if int(s["fields"]["sector"]) == sector)
    z = eye_z(level, sector)
    return name, sector, x, y, (z if z is not None else int(level.sectors[sector]["fields"]["floor_z"]) - 4096)


def spots(level, sector: int, x: int, y: int, z: int) -> list[tuple[int, int, int, int, float]]:
    """Every grid point round the subject where a body stands and sees it: (x, y, eye z, sector, distance)."""
    from bloodmap.player_space import PLAYER_PROFILES
    from bloodmap.sector_geom import outline_and_holes, sector_walls, wall_segment
    from bloodmap.sight import near_sectors, sees
    from bloodmap.viewplan import _distance_to_loop, eye_z

    body = PLAYER_PROFILES["blood"].standing_height
    out = []
    for other in near_sectors(level, sector, x, y, FAR):
        fields = level.sectors[other]["fields"]
        if int(fields["floor_z"]) - int(fields["ceiling_z"]) < body:
            continue
        outline, holes = outline_and_holes(level, other)
        if not outline:
            continue
        eye = eye_z(level, other)
        from bloodmap.sector_geom import point_in_loop
        x0, x1 = min(p[0] for p in outline), max(p[0] for p in outline)
        y0, y1 = min(p[1] for p in outline), max(p[1] for p in outline)
        solid = [wall_segment(level, w) for w in sector_walls(level, other)
                 if int(level.walls[w]["fields"]["next_sector"]) < 0]
        tried = 0
        for gx in range(max(x0, x - FAR) // STEP * STEP, min(x1, x + FAR) + 1, STEP):
            for gy in range(max(y0, y - FAR) // STEP * STEP, min(y1, y + FAR) + 1, STEP):
                far = math.hypot(gx - x, gy - y)
                if not NEAR <= far <= FAR or point_in_loop((gx, gy), outline) != 1:
                    continue
                if any(point_in_loop((gx, gy), h) for h in holes):
                    continue
                if any(_distance_to_loop((gx, gy), seg) < CLEAR for seg in solid):
                    continue
                tried += 1
                if tried > 400:
                    break
                if not sees(level, other, (gx, gy, eye), (x, y, z)) or crowded(level, gx, gy, x, y):
                    continue
                #: the subject is a patch, not a point: how much of a ring round it is seen too
                ring = sum(sees(level, other, (gx, gy, eye), (x + 640 * math.cos(a), y + 640 * math.sin(a), z))
                           for a in (k * math.pi / 3 for k in range(6)))
                out.append((gx, gy, eye, other, far, ring))
    best = max((f[5] for f in out), default=0)
    return [f for f in out if f[5] >= best - 1]


def crowded(level, px: int, py: int, x: int, y: int) -> bool:
    """Would somebody's back fill the frame: an upright sprite close in front of the camera?"""
    ux, uy = x - px, y - py
    far = math.hypot(ux, uy) or 1
    for sprite in level.sprites:
        f = sprite["fields"]
        dx, dy = int(f["x"]) - px, int(f["y"]) - py
        if abs(dx) > 1100 or abs(dy) > 1100 or int(f["cstat"]) & 48 or int(f["cstat"]) & 32768:
            continue
        along, across = (dx * ux + dy * uy) / far, abs(dx * uy - dy * ux) / far
        if 0 < along < min(1100, far) and across < 0.5 * along + 60 and int(f["y_repeat"]) >= 32:
            return True
    return False


def choose(found, x: int, y: int, count: int):
    """The overlook, then spots spread round the subject, at the distance that shows it whole."""
    if not found:
        return []
    want = sorted(f[4] for f in found)[int(len(found) * 0.6)]
    picked = [min(found, key=lambda f: (f[2], abs(f[4] - want)))]          # the highest eye
    while len(picked) < min(count, len(found)):
        def worth(f):
            turn = math.atan2(f[1] - y, f[0] - x)
            apart = min(abs(math.remainder(turn - math.atan2(p[1] - y, p[0] - x), 2 * math.pi)) for p in picked)
            return apart * 2000 - abs(f[4] - want)
        best = max(found, key=worth)
        if best in picked:
            break
        picked.append(best)
    return picked


def shoot(subject: str, out: pathlib.Path, views: int):
    from bloodmap.format import read_map
    from bloodmap.viewplan import angle_toward
    from bloodmap.visual import HORIZ_LEVEL, ObservationRequest, Viewpoint, as_played, run_observation

    name = subject.split("@")[0] if "@" in subject else subject.rsplit(":", 1)[0]
    path = map_path(name)
    place = out / subject.replace(":", "_").replace("@", "_").replace(",", "_").replace(".", "_")
    place.mkdir(parents=True, exist_ok=True)
    try:
        played = as_played(path, place)
        level = read_map(played, verify_crc=False).to_level_ir()
        _name, sector, x, y, z = subject_of(level, subject)
        chosen = choose(spots(level, sector, x, y, z), x, y, views)
        poses = []
        for k, (px, py, pz, inside, far, _ring) in enumerate(chosen):
            #: 1 in horiz is about a 1/100 slope of the view; keep the subject in the middle of the frame
            horiz = int(max(-60, min(160, HORIZ_LEVEL - 100 * ((z - pz) / 16) / max(far, 1))))
            poses.append(Viewpoint(view_id=f"v{k}", x=px, y=py, z=pz, angle=int(angle_toward((px, py), (x, y))) & 2047,
                                   horiz=horiz, sector=inside, node=f"v{k}", purpose="loop", screenshot=True,
                                   note=subject))
        if not poses:
            return subject, [], "nowhere to see it from"
        run_observation(ObservationRequest(map_path=played, output_dir=place, resource_dir=ROOT / "reference" / "blood",
                                           viewpoints=poses, width=640, height=480,
                                           screenshots=[v.view_id for v in poses], brightness=0, rff=None))
        return subject, [place / "frames" / f"{v.view_id}.png" for v in poses], ""
    except Exception as error:           # one broken community map must not lose the sheet
        return subject, [], f"{type(error).__name__}: {error}"


def sheet(rows, out: pathlib.Path, width: int = 640, columns: int = 3, per_page: int = 12) -> list[pathlib.Path]:
    from PIL import Image, ImageDraw
    frames = [(f"{subject}  {k}", f) for subject, files, _why in rows for k, f in enumerate(files) if f.exists()]
    height = int(width * 3 / 4)
    pages = []
    for start in range(0, len(frames), per_page):
        part = frames[start:start + per_page]
        page = Image.new("RGB", (width * columns, height * ((len(part) + columns - 1) // columns)))
        draw = ImageDraw.Draw(page)
        for i, (label, file) in enumerate(part):
            at = ((i % columns) * width, (i // columns) * height)
            page.paste(Image.open(file).convert("RGB").resize((width, height)), at)
            draw.rectangle([at[0], at[1], at[0] + 8 * len(label), at[1] + 14], fill=(0, 0, 0))
            draw.text((at[0] + 3, at[1] + 1), label, fill=(255, 255, 0))
        pages.append(out / f"page-{start // per_page:02d}.png")
        page.save(pages[-1])
    return pages


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("subjects", nargs="*")
    parser.add_argument("--list", help="a file with one subject a line")
    parser.add_argument("--views", type=int, default=3)
    parser.add_argument("--width", type=int, default=640)
    parser.add_argument("--columns", type=int, default=3)
    parser.add_argument("--per-page", type=int, default=12)
    parser.add_argument("-o", "--out", required=True)
    args = parser.parse_args(argv)
    subjects = list(args.subjects)
    if args.list:
        subjects += [line.split()[0] for line in pathlib.Path(args.list).read_text("utf-8").splitlines() if line.strip()]
    out = pathlib.Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(6) as pool:
        rows = list(pool.map(lambda s: shoot(s, out, args.views), subjects))
    for subject, files, why in rows:
        print(f"{subject}: {len(files)} views {why}")
    for page in sheet(rows, out, args.width, args.columns, args.per_page):
        print(page)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
