"""Start a level, list the projects, and say where a level stands.

    python -m tools.project list                       # every project, by kind: levels, analyses, pilots
    python -m tools.project new coldstore --title "The Cold Store"
    python -m tools.project status coldstore           # its size, every open item, what to do next

`new` makes `projects/<name>/` from `tools/starter/`: a level that builds as it
stands (a start, a passage, a hall with a stair, light, a way out), its poses,
a test, and a page saying how the project is worked on. Nothing in it is
Gravesend's. The level is then built by its own `level/build.py`, looked at with
`tools.look`, judged with `tools.critique`, and what is learned on the way is
filed on the shared shelves (`tools.findings`, `tools.tile_contexts`).

`status` reads the build's manifest (`bloodmap.finish`), the built map and the
project's critique rounds, and writes `reports/STATUS.md` and `status.json`:
every open item with what to do about it. A project may have a status of its
own that knows its places (Gravesend's `level/status.py`): it names it in
`project.json` as `status_script`, and `status` runs that instead of writing
over its page. This is the one every level has without writing it.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import shutil
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bloodmap import project as P

STARTER = pathlib.Path(__file__).resolve().parent / "starter"


def new(name: str, title: str, home: pathlib.Path = P.HOME) -> pathlib.Path:
    """Make a project from the starter. The name is its directory's and its map's."""
    if not re.fullmatch(r"[a-z][a-z0-9]*(-[a-z0-9]+)*", name):
        raise P.ProjectError("a project's name is lower-case words joined by hyphens: ice-house")
    root = home / name
    if root.exists():
        raise P.ProjectError(f"{root} is there already")
    for source in sorted(STARTER.rglob("*")):
        if source.is_dir() or "__pycache__" in source.parts:
            continue
        target = root / str(source.relative_to(STARTER)).replace("__NAME__", name.replace("-", "_"))
        target.parent.mkdir(parents=True, exist_ok=True)
        # the title is written into Python source: as a string where it is one, and without its quotes in prose
        text = source.read_text(encoding="utf-8").replace("__NAME__", name)
        text = text.replace('"__TITLE__"', json.dumps(title)).replace("__TITLE__", title.replace('"', "'").replace("\\", "/"))
        target.write_text(text, encoding="utf-8", newline="\n")
    (root / "project.json").write_text(json.dumps({
        "$schema": P.SCHEMA, "schema_version": 1, "name": title, "kind": "level", "status": "live", "game": "blood",
        "about": "", "map": f"level/{name}.MAP", "build": "level/build.py", "ground_z": 0}, indent=2) + "\n",
        encoding="utf-8", newline="\n")
    return root


def _rel(path: pathlib.Path) -> str:
    """A path as the repository says it, or whole where the project lives outside it."""
    path = pathlib.Path(path).resolve()
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix()


def listing() -> str:
    out = []
    for kind, says in (("level", "levels: built here, played by the owner"),
                       ("analysis", "analyses: somebody else's map taken apart"),
                       ("fixture", "fixtures: maps built to test the library"),
                       ("pilot", "pilots: kept for their evidence, not worked on")):
        rows = P.projects(kind)
        out.append(f"{says}")
        out += [f"  {p.key:<26}{'' if p.live else '(frozen) '}{p.title}" + (f": {p.data['about']}" if p.data.get("about") else "")
                for p in rows] or ["  none"]
    unnamed = sorted(d.name for d in P.HOME.iterdir() if d.is_dir() and not (d / "project.json").exists())
    if unnamed:
        out.append("directories that do not say what they are (no project.json): " + ", ".join(unnamed))
    return "\n".join(out)


def stand(project: P.Project) -> dict:
    """Where a level stands: what the last build measured, read off the map, and every open item."""
    from bloodmap import completion
    from bloodmap.build_ir import BUILD_LIMITS, VANILLA_LIMITS
    from bloodmap.format import read_map

    manifest_path = project.need("reports") / "build-manifest.json"
    if not project.map.exists() or not manifest_path.exists():
        raise P.ProjectError(f"{project.key} is not built: python {_rel(project.need('build'))}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    disk = read_map(project.map)
    size = {"sectors": len(disk.sectors), "walls": len(disk.walls), "sprites": len(disk.sprites)}
    open_items: list[dict] = []

    def item(kind: str, says: str, do: str) -> None:
        open_items.append({"kind": kind, "says": says, "do": do})

    for what, count in size.items():
        if count > BUILD_LIMITS[what] * 0.9:
            item("size", f"{count} {what} of NBlood's {BUILD_LIMITS[what]}", "make room before adding: the limit is the port's")
    for row in manifest.get("rules", {}).get("open", []):
        item(f"rule-{row['severity']}", f"{row['code']} at {row['at']}: {row['says']}", "fix it in the level, or say why not in the build")
    fit = manifest.get("sprite_fit", {})
    for kind in ("sunk", "through", "squeezed", "lifted", "overlaps", "flat_overlaps", "unbacked", "sunk_actors"):
        for row in fit.get(kind, []):
            item(f"sprite-{kind}", json.dumps(row, sort_keys=True), f"python -m tools.sprite_fit {_rel(project.map)}")
    contexts = manifest.get("tile_contexts", {})
    for row in contexts.get("new", []):
        item("tile-use-new", f"tile {row['tile']} as {row['slot']} in {row['place']} ({row['count']}x): nobody has shown this use",
             f"a discovery or a mistake: python -m tools.tile_contexts show {row['tile']}, then `record` it or change it")
    for row in contexts.get("misfit", []):
        item("tile-use-misfit", f"tile {row['tile']} as {row['slot']} in {row['place']}: {row['said']}", "change the tile")
    wires = manifest.get("wires", {})
    if wires and not wires.get("agrees", True):
        item("wires", "the map's wiring differs from what was declared", "read `wires` in the manifest")
    for name in wires.get("undeclared", []):
        item("wires", f"channel {name} is used and nobody declared what it is for", "declare it on the circuit")
    for name in wires.get("silent", []):
        item("wires", f"{name} is wired and can never send", "give its sender an ON or OFF change to report")
    mark = completion.read(disk, project.map.name)
    exits = mark.get("exits", [])
    if not exits:
        item("no-exit", "nothing in the map ends the level", "wire a switch to kChannelLevelExitNormal (bloodmap.switches.exit_switch)")
    elif not any(e["reached"] for e in exits):
        item("exit-unreached", "our reader cannot get to an exit", "python -m tools.catalog map is for campaign maps; read bloodmap.completion.missed")
    for key in mark.get("keys", []):
        if not key["reached"]:
            item("key-unreached", f"{key['name']} in sector {key['sector']} is not reached", "check the way to it")
    places = {}
    critique = project.path("critique")
    if critique and critique.is_dir():
        from tools.critique import verdict

        for folder in sorted(p for p in critique.iterdir() if p.is_dir()):
            rounds = verdict(project, folder.name)
            if rounds:
                last = rounds[-1]
                places[folder.name] = {"round": last["round"], "passes": last["passes"], "named": last["named"],
                                       "blocking": last["blocking"], "missing": last["reviews_missing"]}
                if not last["passes"]:
                    item("critique", f"{folder.name}, round {last['round']}: named {last['named']!r}; "
                         + "; ".join(last["blocking"] + [f"{r} has not read it" for r in last["reviews_missing"]]),
                         f"rebuild the place, then python -m tools.critique --project {project.key} prepare {folder.name} ...")
    try:
        pose_sets = {name: len(views) for name, views in project.pose_sets().items()}
    except P.ProjectError:
        pose_sets = {}
    if not places:
        item("never-critiqued", "no blind reader has looked at any place of this level",
             f"python -m tools.critique --project {project.key} prepare <slug> --poses <set> --kind <kind>")
    kinds: dict[str, int] = {}
    for row in open_items:
        kinds[row["kind"]] = kinds.get(row["kind"], 0) + 1
    return {"project": project.key, "title": project.title, "map": _rel(project.map), "size": size,
            "limits": {"nblood": BUILD_LIMITS, "vanilla": VANILLA_LIMITS}, "stages": [s["name"] for s in manifest.get("stages", [])],
            "finishable": {"exits": exits, "keys": mark.get("keys", [])}, "pose_sets": pose_sets, "critique": places,
            "open": open_items, "open_by_kind": dict(sorted(kinds.items()))}


def page(data: dict) -> str:
    out = [f"# {data['title']}: where it stands", "",
           f"Written by `python -m tools.project status {data['project']}` from the last build; never edited.", "",
           f"- map: `{data['map']}`: {data['size']['sectors']} sectors, {data['size']['walls']} walls, {data['size']['sprites']} sprites "
           f"(NBlood's limits: {data['limits']['nblood']['sectors']}, {data['limits']['nblood']['walls']}, {data['limits']['nblood']['sprites']})",
           "- ends: " + (", ".join(f"{e['root']} ({'reached' if e['reached'] else 'NOT reached'})" for e in data["finishable"]["exits"]) or "NOTHING ends the level"),
           "- looked at from: " + (", ".join(f"`{k}` ({n})" for k, n in data["pose_sets"].items()) or "no poses yet"),
           "- critique: " + (", ".join(f"{k} round {v['round']} {'passes' if v['passes'] else 'does not pass'}" for k, v in data["critique"].items()) or "none yet"),
           "", f"## Open: {len(data['open'])}", ""]
    if not data["open"]:
        out.append("Nothing the build can see. That is not the same as good: look at it, and have it read blind.")
    for kind in data["open_by_kind"]:
        out += [f"### {kind}", ""]
        out += [f"- {row['says']}\n  - do: {row['do']}" for row in data["open"] if row["kind"] == kind]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def write_status(project: P.Project) -> dict:
    data = stand(project)
    reports = project.need("reports")
    reports.mkdir(parents=True, exist_ok=True)
    (reports / "status.json").write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8", newline="\n")
    (reports / "STATUS.md").write_text(page(data), encoding="utf-8", newline="\n")
    return data


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list")
    made = sub.add_parser("new")
    made.add_argument("name")
    made.add_argument("--title", required=True)
    status = sub.add_parser("status")
    status.add_argument("name", nargs="?")
    args = parser.parse_args(argv)
    try:
        if args.cmd == "list":
            print(listing())
        elif args.cmd == "new":
            root = new(args.name, args.title)
            print(f"{_rel(root)} is a level: read its README.md, then python {_rel(root)}/level/build.py")
        else:
            project = P.named(args.name)
            own = project.path("status_script")
            if own is not None:
                # a level whose status knows its own places writes the page itself: this must not write over it
                import subprocess

                return subprocess.run([sys.executable, str(own)], cwd=ROOT).returncode
            data = write_status(project)
            print(f"{data['title']}: {data['size']['sectors']} sectors, {data['size']['walls']} walls, {data['size']['sprites']} sprites; "
                  f"{len(data['open'])} open {data['open_by_kind']} -> {_rel(project.need('reports'))}/STATUS.md")
    except P.ProjectError as exc:
        print(exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
