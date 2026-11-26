"""Look at a level from its named poses, as the game shows it, through the XMapEdit observer.

    python -m tools.look blood-city --set trunk -o work/trunk     # a project's pose sets (its `level/poses.py`)
    python -m tools.look blood-city --list                        # which sets it has
    python -m tools.look blood-city --set fair --empty            # nobody and nothing to pick up: the place alone
    python -m tools.look blood-city --set fair --empty --mute     # and no word on any sign, board or wall
    python -m tools.look duke-e4l1-remake --set quarry --posed "sprite 334" -o work/x   # a chain at its other end
    python -m tools.look --ref E3M1 --sectors 12,119 -o work/ref  # the same call on a campaign map's rooms
    python -m tools.look --map some.MAP --sectors 4,9 -o work/x   # or on any map

A pose is written in the project's plan units and aimed at a point
(`bloodmap.viewplan.named_poses`), so a set stays comparable from build to
build. The frame is the map as a player meets it (`bloodmap.visual.as_played`):
starts, markers and sounds hidden, lit torches burning. The run keeps the map
it looked at beside its frames. The game is never started: the observer renders
from a pose.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bloodmap import project as P
from bloodmap.corpus import corpus_map_path
from bloodmap.format import read_map
from bloodmap.viewplan import named_poses, sector_poses
from bloodmap.visual import ObservationRequest, Viewpoint, as_played, run_observation

RESOURCES = ROOT / "reference" / "blood"


def digest(path) -> str:
    return hashlib.sha256(pathlib.Path(path).read_bytes()).hexdigest()


def pose_hash(project: P.Project, names: list[str]) -> str:
    """The identity of some of a project's pose sets as written: a camera moved is a different look."""
    sets = project.pose_sets()
    missing = [name for name in names if name not in sets]
    if missing:
        raise P.ProjectError(f"{project.key} has no pose set {', '.join(missing)}: python -m tools.look {project.key} --list")
    said = {name: sets[name] for name in sorted(names)}
    return hashlib.sha256(json.dumps(said, sort_keys=True, default=list).encode("utf-8")).hexdigest()


def hide_words(map_path, *, walls: bool = True, blank: int = 255) -> int:
    """Hide every sign, board and letter in a map file, in place (`bloodmap.tile_looks.word_tiles`); returns how many.

    A sprite of words is made invisible. A wall that wears words wears `blank`
    (255, a plain metal) instead; a masked wall of words loses its mask. For a
    reader asked to name a place from its shapes, not from what it says.
    """
    from bloodmap.format import read_map, write_map
    from bloodmap.model import record_fields
    from bloodmap.tile_looks import word_tiles

    quiet = word_tiles()
    disk = read_map(map_path)
    count = 0
    for sprite in disk.sprites:
        fields = record_fields(sprite)
        if int(fields["picnum"]) in quiet and not int(fields["cstat"]) & 32768:
            fields["cstat"] = int(fields["cstat"]) | 32768
            count += 1
    for wall in disk.walls if walls else ():
        fields = record_fields(wall)
        if int(fields["picnum"]) in quiet:
            fields["picnum"] = blank
            count += 1
        if int(fields["over_picnum"]) in quiet:
            if int(fields["cstat"]) & 16:
                fields["cstat"] = int(fields["cstat"]) & ~16
            fields["over_picnum"] = blank
            count += 1
    write_map(disk, map_path)
    return count


def poses_for(project: P.Project, level, name: str, refused: list[str] | None = None) -> list[Viewpoint]:
    """One of a project's pose sets as viewpoints in a built map of it."""
    sets = project.pose_sets()
    if name not in sets:
        raise P.ProjectError(f"{project.key} has no pose set {name!r}: python -m tools.look {project.key} --list")
    return named_poses(level, sets[name], unit=project.plan_unit, ground_z=project.ground_z, refused=refused)


def observe(map_path, views: list[Viewpoint], out_dir, *, empty: bool = False, mute: bool = False,
            source=None, about: dict | None = None, width: int = 640, height: int = 480):
    """Render `views` of a map as played into `out_dir/frames`, keep the map that was looked at, and say so in `render.json`.

    `source` is the map the drawn one stands for when they differ (a posed
    copy of it); `about` is added to `render.json` (the project, the pose
    sets and their hash, the state drawn).
    """
    out_dir = pathlib.Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    source = pathlib.Path(source or map_path)
    before = digest(source)
    played = as_played(map_path, out_dir, empty=empty)
    hidden = hide_words(played) if mute else 0
    manifest = run_observation(ObservationRequest(
        map_path=played, output_dir=out_dir, resource_dir=RESOURCES, viewpoints=views,
        width=width, height=height, screenshots=[v.view_id for v in views], brightness=0, rff=None))
    # the path is overwritten by the next build, and a frame whose map is gone is not evidence of anything
    shutil.copyfile(map_path, out_dir / "observed.MAP")
    if digest(source) != before:
        raise RuntimeError(f"{source} was saved while it was being looked at: look again")
    frames = {v.view_id: digest(out_dir / "frames" / f"{v.view_id}.png") for v in views
              if (out_dir / "frames" / f"{v.view_id}.png").exists()}
    (out_dir / "render.json").write_text(json.dumps({
        "map": source.resolve().relative_to(ROOT).as_posix() if source.resolve().is_relative_to(ROOT) else str(source),
        "source_sha256": before, "observed_sha256": digest(played), **(about or {}),
        "empty": empty, "words_hidden": hidden if mute else None, "views": [v.view_id for v in views],
        "frames": frames, "runtime_events_executed": False}, indent=1) + "\n", encoding="utf-8")
    return manifest


def posed_copy(map_path, root: str, out_dir) -> tuple[pathlib.Path, dict]:
    """A copy of a map with everything the chain from `root` ("sprite 334") answers in its other state, and the report."""
    from bloodmap.format import write_map
    from bloodmap.posed import chain_of, posed
    from bloodmap.wiring import chains

    from bloodmap.art import read_art_directory

    disk = read_map(map_path)
    # with the ART a switch's second picture and a rider's extent are read, not assumed
    result, report = posed(disk, chain_of(chains(disk), root), tiles=read_art_directory(ROOT / RESOURCES))
    out = pathlib.Path(out_dir) / "posed.MAP"
    out.parent.mkdir(parents=True, exist_ok=True)
    write_map(result, out)
    (out.parent / "posed.json").write_text(json.dumps(report, indent=1, default=str) + "\n", encoding="utf-8")
    return out, report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("project", nargs="?", help=f"a project under projects/ (or ${P.ENV})")
    parser.add_argument("--set", dest="pose_set", action="append", default=[])
    parser.add_argument("--list", action="store_true", help="name the project's pose sets and how many views each has")
    parser.add_argument("--map", default=None, help="another build of the project, or any map with --sectors")
    parser.add_argument("--ref", default=None, help="a corpus map by name, e.g. E3M1")
    parser.add_argument("--sectors", default="", help="sector ids to look at from inside")
    parser.add_argument("-o", "--out", default=None)
    parser.add_argument("--tag", default="latest", help="without -o: the folder under the project's reports/looks")
    parser.add_argument("--empty", action="store_true", help="hide enemies and pickups too: the place alone")
    parser.add_argument("--mute", action="store_true", help="hide every sign, board and letter, on sprites and walls")
    parser.add_argument("--posed", default=None, metavar="SENDER",
                        help='draw the chain this sender starts ("sprite 334") at its other end')
    args = parser.parse_args(argv)

    sectors = [int(s) for s in args.sectors.split(",") if s]
    project = None
    try:
        if args.project or not (args.ref or (args.map and sectors)):
            project = P.named(args.project)
        if args.list:
            if project is None:
                parser.error("--list names a project's pose sets: say which project")
            for name, views in project.pose_sets().items():
                print(f"  {name:<28}{len(views)} views")
            return 0
        if args.out is None and project is None:
            parser.error("say where the frames go: -o <dir>")
        if not sectors and not args.pose_set:
            parser.error("say which poses: --set <name> (see --list), or --sectors")
        out_dir = pathlib.Path(args.out or (project.need("reports") / "looks" / args.tag))
        map_path = corpus_map_path(args.ref) if args.ref else pathlib.Path(args.map) if args.map else project.map
        about: dict = {"sectors": sectors} if sectors else {
            "project": project.key, "pose_sets": args.pose_set, "poses_sha256": pose_hash(project, args.pose_set)}
        drawn_map = map_path
        if args.posed:
            # a pose stands on the floor of the state drawn, not of the state saved
            drawn_map, report = posed_copy(map_path, args.posed, out_dir)
            about["state"] = f"posed: the chain from {args.posed} at its other end"
            print(f"posed {args.posed}: {len(report.get('objects', []))} objects in their other state")
        level = read_map(drawn_map).to_level_ir()
        refused: list[str] = []
        if sectors:
            views = sector_poses(level, sectors)
        else:
            views = [v for name in args.pose_set for v in poses_for(project, level, name, refused)]
    except P.ProjectError as exc:
        print(exc, file=sys.stderr)
        return 2
    for said in refused:
        print(f"  ! {said} -- pose skipped")
    if not views:
        print("no poses resolved")
        return 1
    observe(drawn_map, views, out_dir, empty=args.empty, mute=args.mute, source=map_path, about=about)
    drawn = [v for v in views if (out_dir / "frames" / f"{v.view_id}.png").exists()]
    print(f"{len(drawn)} frames -> {out_dir}")
    if len(drawn) < len(views):
        print("  NOT drawn:", ", ".join(v.view_id for v in views if v not in drawn))
    for view in views:
        print(f"  {view.view_id}: sector {view.sector} z {view.z} -- {view.note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
