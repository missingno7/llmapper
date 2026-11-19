"""Render one mechanism before and after it fires, from the same cameras, and measure the difference.

Every other frame this project takes shows a map as it was saved, so a
critic sees one end of a mechanism and has to take the other on trust. This
finds one wiring chain (`bloodmap.wiring.chains`) by its sender, builds the
rest pose and the fired pose of everything it answers (`bloodmap.posed`),
stands cameras round what changed (`tools.look_at.ring`), renders each pose
twice through the observer, and compares the two frames pixel by pixel.

A pair in which nothing differs is a FINDING, not a failure: "fired, and
nothing visibly changed from here". The observer's manifest says whether the
changed objects were drawn at all, so the json tells that case apart from a
camera that simply could not see them.

.. code-block:: bash

    python -m tools.mechanism_look E1M1 --root "sprite 51" -o work/mech/e1m1-s51
    python -m tools.mechanism_look projects/blood-city/level/blood-city-current.MAP \\
        --root "sprite 210" -o work/mech/city-breach

Writes, under the output directory: ``rest/`` and ``posed/`` (each the posed
copy, its as-played copy and the observer's frames), ``pair.json`` and
``pairs.png`` (each pose, rest left and posed right). Outputs are renders of
commercial maps: they belong under ``work/`` and are never committed.
"""

from __future__ import annotations

import argparse
import json
import math
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

RESOURCES = ROOT / "reference" / "blood"


def _map_path(name: str) -> pathlib.Path:
    from bloodmap.corpus import corpus_map_path

    path = pathlib.Path(name)
    return path if path.exists() else corpus_map_path(name)


def changes(before, after) -> dict:
    """What differs between two copies of one map: sectors, walls, sprites."""
    from bloodmap.model import record_fields
    from bloodmap.sector_geom import wall_owners

    sectors = [i for i, (a, b) in enumerate(zip(before.sectors, after.sectors))
               if record_fields(a) != record_fields(b)]
    walls = [i for i, (a, b) in enumerate(zip(before.walls, after.walls))
             if record_fields(a) != record_fields(b)]
    sprites = [i for i, (a, b) in enumerate(zip(before.sprites, after.sprites))
               if record_fields(a) != record_fields(b)]
    owners = wall_owners(after)
    wall_sectors = sorted({owners.get(w, -1) for w in walls} - {-1})
    #: a moved floor or ceiling shows on the walls round it too: its own and
    #: the step faces of every neighbour that looks into it
    moving = set(sectors) | set(wall_sectors)
    border = [i for i, wall in enumerate(after.walls)
              if owners.get(i, -1) in moving
              or int(record_fields(wall)["next_sector"]) in moving]
    return {"sectors": sectors, "walls": walls, "sprites": sprites,
            "wall_sectors": wall_sectors, "border_walls": border}


def _focus(before, after, changed: dict) -> list[dict]:
    """Where to look: the changed geometry, and the changed sprites apart from it."""
    from bloodmap.model import record_fields
    from bloodmap.sector_geom import outline_and_holes

    groups = []
    points, zs = [], []
    for sector in sorted(set(changed["sectors"]) | set(changed["wall_sectors"])):
        for disk in (before, after):
            outline, _holes = outline_and_holes(disk, sector)
            points += [(float(x), float(y)) for x, y in outline]
        zs.append(int(record_fields(before.sectors[sector])["floor_z"]))
    if points:
        groups.append({"name": "answers", "points": points, "z": zs[0] if zs else None})
    for sprite in changed["sprites"]:
        fields = record_fields(before.sprites[sprite])
        point = (float(fields["x"]), float(fields["y"]))
        if points and min(math.hypot(point[0] - p[0], point[1] - p[1]) for p in points) < 1500:
            continue                  # the answers' cameras already look at it
        groups.append({"name": f"sprite_{sprite}", "points": [point], "z": int(fields["z"])})
    for group in groups:
        xs = [p[0] for p in group["points"]]
        ys = [p[1] for p in group["points"]]
        group["at"] = (int((min(xs) + max(xs)) / 2), int((min(ys) + max(ys)) / 2))
        group["extent"] = math.hypot(max(xs) - min(xs), max(ys) - min(ys)) / 2
    return groups


def cameras(before, after, changed: dict, count: int = 6) -> list:
    """Cameras round each changed place, standing where both poses leave a floor."""
    import dataclasses

    from bloodmap.model import record_fields
    from bloodmap.sector_geom import sector_at
    from bloodmap.viewplan import angle_toward, eye_z, portals_of
    from bloodmap.visual import HORIZ_LEVEL, Viewpoint
    from tools.look_at import ring

    rest_level, posed_level = before.to_level_ir(), after.to_level_ir()
    moving = set(changed["sectors"]) | set(changed["wall_sectors"])
    views = []

    def standable(x, y, near):
        sector = sector_at(rest_level, x, y, floor_near=near)
        if sector is None or sector in moving:
            return None
        if sector_at(posed_level, x, y, floor_near=near) != sector:
            return None
        z = eye_z(rest_level, sector)
        if z is None or eye_z(posed_level, sector) != z:
            return None
        return sector, z

    #: Through each opening into what moved, from the room on the other
    #: side: a ring round a lift in a shaft sees the shaft's walls, and the
    #: one place a player watches a lift from is the doorway onto it.
    openings = sorted(((portal, moved) for moved in moving
                       for portal in portals_of(rest_level, moved)
                       if portal["neighbour"] not in moving),
                      key=lambda item: -item[0]["width"])
    groups = _focus(before, after, changed)
    for portal, moved in openings:
        if sum(1 for v in views if v.node == "through") >= count:
            break
        mx, my = portal["midpoint"]
        cx, cy = groups[0]["at"]
        away = math.hypot(mx - cx, my - cy) or 1.0
        near = int(record_fields(rest_level.sectors[portal["neighbour"]])["floor_z"])
        for back in (1400, 2400, 800):
            x = int(mx + (mx - cx) / away * back)
            y = int(my + (my - cy) / away * back)
            stand = standable(x, y, near)
            if stand is None or any(math.hypot(v.x - x, v.y - y) < 600 for v in views):
                continue
            index = sum(1 for v in views if v.node == "through")
            views.append(Viewpoint(
                view_id=f"through_{index:02d}", x=x, y=y, z=stand[1],
                angle=int(angle_toward((x, y), (mx, my))) & 2047, horiz=HORIZ_LEVEL,
                sector=stand[0], node="through", purpose="mechanism", screenshot=True,
                note=f"through wall {portal['wall']} into sector {moved}"))
            break
    for group in groups:
        x, y = group["at"]
        radius = int(min(6000, max(1600, group["extent"] + 1600)))
        kept = 0
        for view in ring(rest_level, x, y, radius, count * 2, group["z"]):
            if kept >= count:
                break
            #: never stand on what moves, and only where the fired map puts
            #: the camera in the same room at a height it can stand in
            if standable(view.x, view.y, group["z"]) != (view.sector, view.z):
                continue
            views.append(dataclasses.replace(
                view, view_id=f"{group['name']}_{kept:02d}", node=group["name"],
                purpose="mechanism", note=f"looking at {group['name']}"))
            kept += 1
    return views


def _drawn(manifest, view_id: str, changed: dict) -> dict:
    """Which of the changed objects the observer drew in one view."""
    sectors = set(changed["sectors"]) | set(changed["wall_sectors"])
    walls = set(changed["walls"]) | set(changed.get("border_walls", ()))
    sprites = set(changed["sprites"])
    seen = {"sectors": set(), "walls": set(), "sprites": set()}
    try:
        view = manifest.view(view_id)
    except Exception:                         # noqa: BLE001 - a refused pose drew nothing
        return {k: [] for k in seen}
    for surface in view.get("surfaces", []):
        if surface.get("kind") == "sprite" and surface.get("sprite") in sprites:
            seen["sprites"].add(int(surface["sprite"]))
        elif surface.get("wall") in walls:
            seen["walls"].add(int(surface["wall"]))
        elif surface.get("kind") in ("floor", "ceiling") and surface.get("sector") in sectors:
            seen["sectors"].add(int(surface["sector"]))
    return {k: sorted(v) for k, v in seen.items()}


def compare(rest_png: pathlib.Path, posed_png: pathlib.Path) -> dict:
    """The fraction of pixels that differ and the box round them."""
    from PIL import Image, ImageChops

    a = Image.open(rest_png).convert("RGB")
    b = Image.open(posed_png).convert("RGB")
    mask = ImageChops.difference(a, b).convert("L").point(lambda v: 255 if v else 0)
    differ = mask.histogram()[255]
    return {"differ": round(differ / (a.width * a.height), 5), "pixels": differ,
            "bbox": list(mask.getbbox()) if differ else None}


def mechanism_look(map_name: str, root: str, out: pathlib.Path, *,
                   count: int = 6, empty: bool = False) -> dict:
    from bloodmap import posed, wiring
    from bloodmap.art import read_art_directory
    from bloodmap.format import read_map, write_map
    from bloodmap.visual import ObservationRequest, as_played, run_observation

    path = _map_path(map_name)
    disk = read_map(path)
    chain = posed.chain_of(wiring.chains(disk), root)
    tiles = read_art_directory(RESOURCES) if RESOURCES.is_dir() else None
    before, rest_report = posed.rested(disk, chain, tiles=tiles)
    after, report = posed.posed(disk, chain, tiles=tiles)
    changed = changes(before, after)
    views = cameras(before, after, changed, count)
    out.mkdir(parents=True, exist_ok=True)
    manifests = {}
    for end, copy in (("rest", before), ("posed", after)):
        folder = out / end
        folder.mkdir(parents=True, exist_ok=True)
        write_map(copy, folder / f"{end}.MAP")
        played = as_played(folder / f"{end}.MAP", folder, empty=empty)
        if views:
            manifests[end] = run_observation(ObservationRequest(
                map_path=played, output_dir=folder, resource_dir=RESOURCES,
                viewpoints=tuple(views), width=640, height=480,
                screenshots=True, brightness=0, rff=None))
    pairs = []
    for view in views:
        frames = {end: out / end / "frames" / f"{view.view_id}.png" for end in ("rest", "posed")}
        if not all(f.exists() for f in frames.values()):
            pairs.append({"pose": view.to_dict(), "error": "the observer wrote no frame"})
            continue
        measured = compare(frames["rest"], frames["posed"])
        drawn = {end: _drawn(manifests[end], view.view_id, changed) for end in manifests}
        saw = any(any(v.values()) for v in drawn.values())
        if measured["pixels"]:
            finding = "changed"
        elif saw:
            finding = "fired, and nothing visibly changed from here"
        else:
            finding = "what changed is out of sight from here"
        pairs.append({
            "pose": view.to_dict(),
            "rest": str(frames["rest"]), "posed": str(frames["posed"]),
            "which_is_after": "posed",
            **measured, "drew_changed": drawn, "finding": finding})
    sheet = _sheet(out, pairs)
    result = {
        "map": str(map_name), "root": root, "cause": chain.get("cause"),
        "steps": len(chain.get("steps", [])),
        "changed": changed,
        "rest_differs_from_saved": rest_report["posed"],
        "pairs": pairs, "sheet": sheet,
        "posed": report, "rest": rest_report,
        "summary": {
            "poses": len(pairs),
            "changed": sum(1 for p in pairs if p.get("finding") == "changed"),
            "nothing_visible": sum(1 for p in pairs if p.get("finding", "").startswith("fired")),
            "out_of_sight": sum(1 for p in pairs if p.get("finding", "").startswith("what")),
        },
    }
    (out / "pair.json").write_text(json.dumps(result, indent=1), "utf-8")
    return result


def _sheet(out: pathlib.Path, pairs: list[dict]) -> str | None:
    """Each pose as one row: rest on the left, posed on the right."""
    from PIL import Image

    rows = [p for p in pairs if "rest" in p]
    if not rows:
        return None
    sheet = Image.new("RGB", (1280, 480 * len(rows)))
    for index, pair in enumerate(rows):
        sheet.paste(Image.open(pair["rest"]).convert("RGB"), (0, 480 * index))
        sheet.paste(Image.open(pair["posed"]).convert("RGB"), (640, 480 * index))
    path = out / "pairs.png"
    sheet.save(path)
    return str(path)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("map", help="a corpus name (E1M1) or a path to a .MAP")
    parser.add_argument("--root", required=True, help='the chain\'s sender, e.g. "sprite 51"')
    parser.add_argument("-o", "--out", required=True)
    parser.add_argument("--count", type=int, default=6, help="cameras per changed place")
    parser.add_argument("--empty", action="store_true",
                        help="hide enemies and pickups in both renders")
    args = parser.parse_args(argv)
    result = mechanism_look(args.map, args.root, pathlib.Path(args.out),
                            count=args.count, empty=args.empty)
    print(f"{result['map']} {result['root']} by {'/'.join(result['cause'] or [])}: "
          f"{result['steps']} step(s); changed sectors {result['changed']['sectors']}, "
          f"walls {len(result['changed']['walls'])}, sprites {result['changed']['sprites']}")
    if result["rest_differs_from_saved"]:
        print(f"  at load the game already moves {result['rest_differs_from_saved']} "
              "from where the map saved them; 'rest' is the load pose")
    for row in result["posed"]["objects"]:
        said = "; ".join(row["done"] + [f"NOT POSED: {w}" for w in row["not_posed"]]
                         + [f"unsure: {w}" for w in row["undecided"]])
        print(f"  {row['object']} ({row['type']}) {row['state'][0]}->{row['state'][1]}: {said}")
    if not result["pairs"]:
        print("  no camera could stand near what changed: nothing was rendered")
    for pair in result["pairs"]:
        if "error" in pair:
            print(f"  {pair['pose']['id']}: {pair['error']}")
            continue
        print(f"  {pair['pose']['id']}: {pair['pixels']} pixels "
              f"({pair['differ'] * 100:.2f}%) differ, "
              f"box {pair['bbox']} -- {pair['finding']}")
    print(f"  {pathlib.Path(args.out) / 'pair.json'}; sheet {result['sheet']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
