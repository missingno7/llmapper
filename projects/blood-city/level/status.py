"""Where the city stands, as data an agent can query before it touches anything.

An agent starting on Gravesend needs four things it cannot work out cheaply:
how big the build is, what state each named place is in, what is open, and
what nobody has verified. They existed -- in a build manifest of 38 keys, in
critique rounds under the studies, and in one agent's private notes -- and the
two pages that claimed to summarise them described September's map.

This reads those sources and writes two files beside the manifest:

``reports/status.json``  every place and every open item, one record each
``reports/STATUS.md``    forty lines to read first, generated from it

Nothing here is typed by hand, and `tests/test_city_status.py` fails while
either file is stale. The build runs this as its last step; run it again
after recording a critique round.

.. code-block:: bash

    python projects/blood-city/level/status.py                 # rewrite both files
    python projects/blood-city/level/status.py --place station # one place, and what is open on it
    python projects/blood-city/level/status.py --kind refused  # one kind of open item
    python projects/blood-city/level/status.py --check         # exit 1 if stale

An open item says what is wrong, where, which pass or file owns it, and the
command that shows it. It does not say what to do about it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import sys
from collections import Counter
from typing import Any

LEVEL = pathlib.Path(__file__).resolve().parent
PROJECT = LEVEL.parent
ROOT = PROJECT.parents[1]
sys.path.insert(0, str(ROOT))

MANIFEST = PROJECT / "reports" / "build-manifest.json"
MAP = LEVEL / "blood-city-current.MAP"
STATUS_JSON = PROJECT / "reports" / "status.json"
STATUS_MD = PROJECT / "reports" / "STATUS.md"
STUDIES = ROOT / "knowledge" / "blood" / "studies"

SCHEMA = "llmapper.blood-city-status"
MAP_REL = "projects/blood-city/level/blood-city-current.MAP"
LINT = f"python -m tools.sprite_fit {MAP_REL}"


def _text(path: pathlib.Path) -> str:
    return path.read_text(encoding="utf-8").replace("\r\n", "\n")


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _pass_owners() -> dict[str, str]:
    """Manifest key -> where an agent opens the code that filled it.

    Read off `build_skeleton.py` itself. A key filled by
    ``ctx["manifest"]["goods"] = goods.stock(...)``, or from a name that was
    itself assigned that way a few lines up, is owned by that module's
    function. Any other key is owned by the line of the build that fills it.
    """
    source = (LEVEL / "build_skeleton.py").read_text(encoding="utf-8")
    alias = {short: module for module, short in
             re.findall(r"^\s*import (\w+) as (\w+)\s*$", source, re.M)}
    script = "projects/blood-city/level/build_skeleton.py"
    owners = {}
    for found in re.finditer(r'ctx\["manifest"\]\["(\w+)"\]\s*=\s*([\w.]+)', source):
        key, value = found.group(1), found.group(2)
        if key in owners:
            continue
        line = source.count(chr(10), 0, found.start()) + 1
        owners[key] = f"{script}:{line}"
        if "." not in value:
            made = list(re.finditer(
                rf"^\s*{re.escape(value)}\s*=\s*(\w+)\.(\w+)\(", source[:found.start()], re.M))
            if not made:
                continue
            module, function = made[-1].group(1), made[-1].group(2)
        else:
            module, _dot, function = value.partition(".")
        module = alias.get(module, module)
        if (LEVEL / f"{module}.py").exists():
            owners[key] = f"projects/blood-city/level/{module}.py:{function}"
    return owners


def _stages(ran: list[dict[str, str]]) -> list[dict[str, str]]:
    """The build's stages in the order they ran, each with the line it starts at.

    The names and what each does are the manifest's, so a stage listed here
    is one that ran. The line is read off `build_skeleton.py` as it is now.
    """
    source = (LEVEL / "build_skeleton.py").read_text(encoding="utf-8")
    script = "projects/blood-city/level/build_skeleton.py"
    line = {found.group(1): source.count(chr(10), 0, found.start()) + 1
            for found in re.finditer(r'^[ \t]*STAGE\("([\w-]+)",', source, re.M)}
    return [{"name": row["name"], "says": row["says"],
             "at": f"{script}:{line[row['name']]}" if row["name"] in line
             else f"{script} (no longer has a stage of this name: rebuild)"}
            for row in ran]


def stage_seconds() -> dict[str, float]:
    """What each stage took in the last build on this machine, if there was one."""
    timings = ROOT / "work" / "blood-city-stages.json"
    if not timings.exists():
        return {}
    return {row["name"]: row["seconds"]
            for row in json.loads(timings.read_text(encoding="utf-8"))}


def _critique(slug: str | None) -> dict[str, Any] | None:
    """The last critique round of a study, or None if it has never had one."""
    if not slug or not (STUDIES / slug / "critique").is_dir():
        return None
    from tools.critique import verdict

    rounds = verdict(slug)
    if not rounds:
        return None
    last = rounds[-1]
    return {
        "round": last["round"], "passes": bool(last["passes"]),
        "scores": last["scores"], "named_as": last["named"],
        "readers_missing": last["reviews_missing"],
        "blocking": last["blocking"],
        "packet": f"knowledge/blood/studies/{slug}/critique/round-{last['round']}",
    }


SHOWCASE = ROOT / "projects" / "blood-city" / "reports" / "showcase"


def _showcase() -> list[dict[str, Any]]:
    """Each showcase place's latest judged round (`tools.showcase`).

    The blind reader's word on the best of eight hundred views of a place:
    what it called it, what it named the winner with every sign and person
    hidden, whether that counts as recognised, and what the place lacks.
    """
    latest: dict[str, dict[str, Any]] = {}
    rounds = sorted((int(p.name.split("-")[1]), p) for p in SHOWCASE.glob("round-*")
                    if (p / "verdicts.json").exists())
    for number, folder in rounds:
        finals = json.loads((folder / "finalists.json").read_text("utf-8"))
        for key, row in json.loads((folder / "verdicts.json").read_text("utf-8")).items():
            if not row.get("ok"):
                continue
            blind = row.get("blind_name", {})
            latest[key] = {
                "key": key, "title": finals.get(key, {}).get("title", key),
                "round": number, "called": row.get("place", ""),
                "blind": blind.get("name", ""),
                "recognised": bool(blind.get("recognised")),
                "lacks": row.get("lacks", ""), "fix": row.get("fix", ""),
                "report": f"projects/blood-city/reports/showcase/round-{number}/showcase.md",
            }
    return [latest[k] for k in sorted(latest)]


def gather() -> dict[str, Any]:
    """Every source read once, into the one document both files come from."""
    from bloodmap.build_ir import BUILD_LIMITS
    from bloodmap.format import read_map

    import character

    manifest_text = _text(MANIFEST)
    manifest = json.loads(manifest_text)
    disk = read_map(MAP)
    counts = {"sectors": len(disk.sectors), "walls": len(disk.walls),
              "sprites": len(disk.sprites)}
    owners = _pass_owners()
    sheet = manifest["character"]

    places = []
    open_items: list[dict[str, Any]] = []

    def item(kind: str, says: str, *, place: str | None = None,
             owner: str, see: str, at: str | None = None) -> None:
        record = {"kind": kind, "place": place, "says": says,
                  "owner": owner, "see": see}
        if at:
            record["at"] = at
        open_items.append(record)

    for name, row in sheet["places"].items():
        declared = character.PLACES.get(name, {})
        slug = declared.get("study")
        critique = _critique(slug)
        places.append({
            "name": name, "at": list(declared.get("at", ())),
            "hero": row.get("hero"),
            "study": slug,
            "layers": {"has": row["layers"], "missing": row["missing"],
                       "campaign_p25": row["campaign_p25"],
                       "campaign_p50": row["campaign_p50"]},
            "metres": row.get("metres"),
            "cramped": row.get("cramped") or [],
            "critique": critique,
        })
        sheet_owner = "projects/blood-city/level/character.py:PLACES"
        if not slug:
            item("unstudied", "built without a study of how Blood built one",
                 place=name, owner=sheet_owner,
                 see='python -m tools.study <slug> --want "..." --seed MAP:sector!')
        for layer in row["missing"]:
            item("missing-layer", f"carries no {layer} layer", place=name,
                 owner="projects/blood-city/level/detailing.py",
                 see="python -m tools.place_character --help")
        for fault in row.get("cramped") or []:
            item("cramped", fault, place=name,
                 owner="projects/blood-city/level/scale.py",
                 see="the scale lines the build prints")
        if slug and critique is None:
            item("never-critiqued", "no blind reader has looked at this place",
                 place=name, owner="tools/critique.py",
                 see=f"python -m tools.critique prepare {slug} --poses <set> --kind <kind>")
        elif critique and not critique["passes"]:
            for line in critique["blocking"]:
                reader, _colon, said = line.partition(": ")
                item("critique", said, place=name, owner=f"blind reader: {reader}",
                     see=f"{critique['packet']}/review-{reader}.md")
            for reader in critique["readers_missing"]:
                item("critique", f"round {critique['round']} has no {reader} reading",
                     place=name, owner="tools/critique.py", see=critique["packet"])

    for name, said in character.OWNER_REWORK.items():
        item("owner-rework", said, place=name, owner="the owner",
             see="study it (tools.study), then rebuild; which other old places: the never-critiqued "
                 "and missing-layer items here")

    uses = manifest.get("tile_contexts", {})
    for row in uses.get("new", []):
        item("uncatalogued-use",
             f"tile {row['tile']} as {row['slot']} in {row['place']} ({row['count']}x): "
             f"no map and no reading shows it there -- record what it is, or fix it",
             owner="bloodmap/tile_contexts.py",
             at=f"{row['first'][0]}[{row['first'][1]}]",
             see=f"python -m tools.tile_contexts show {row['tile']}")
    for row in uses.get("misfit", []):
        item("misfit-use",
             f"tile {row['tile']} as {row['slot']} in {row['place']} ({row['count']}x): "
             f"recorded as a misfit there -- {row['said'][0]}",
             owner="bloodmap/tile_contexts.py",
             at=f"{row['first'][0]}[{row['first'][1]}]",
             see=f"python -m tools.tile_contexts show {row['tile']}")
    for row in uses.get("outside", []):
        item("outside-campaign",
             f"tile {row['tile']} as {row['slot']} in {row['place']} ({row['count']}x) "
             f"rests on {row['source']} evidence ({row['maps']} maps), not the campaign's",
             owner="bloodmap/tile_contexts.py",
             see=f"python -m tools.tile_contexts show {row['tile']}")

    showcase = _showcase()
    for row in showcase:
        if not row["recognised"]:
            item("unrecognised",
                 f"named \"{row['blind']}\" from its best view with signs hidden; "
                 f"the reader's fix: {row['fix']}",
                 place=row["title"], owner="tools/showcase.py",
                 see=f"{row['report']}; python -m tools.showcase run --place {row['key']}")

    for name in sheet.get("thin", []):
        item("thin", "fewer layers than a quarter of the campaign's rooms of its size",
             place=name, owner="projects/blood-city/level/detailing.py",
             see="the character lines the build prints")
    for name in sheet.get("unfound", []):
        item("unfound", "named on the character sheet and not found in the map",
             place=name, owner="projects/blood-city/level/character.py:PLACES",
             see="the character lines the build prints")
    for channel in sheet.get("dangling_channels", []):
        item("dangling-channel", f"channel {channel} is sent or heard by one end only",
             owner="projects/blood-city/level/character.py",
             see=f"python -m tools.catalog mechanisms {MAP_REL}")

    for row in sheet.get("engine_channels_wired", []):
        item("engine-channel",
             f"channel {row['channel']} ({row['name']}) is the engine's, and the level "
             f"sends on it ({', '.join(row['senders'])}) and listens on it "
             f"({', '.join(row['listeners'])}); no campaign map does, and a "
             f"level's own channels start at 100",
             owner="projects/blood-city/level/character.py:engine_channels_wired",
             see=f"python -m tools.catalog mechanisms {MAP_REL}")

    # The same mark the campaign's maps are given. A shipped map can be
    # finished; ours is held to that by the reader that is held to them.
    from bloodmap import completion

    finish = completion.read(disk, "BLOOD-CITY")
    for said in completion.missed(finish):
        item("cannot-finish", said,
             owner="bloodmap/completion.py (the reader reaches the exit in 38 of "
                   "43 campaign maps: check a shortfall before believing it)",
             see=f"python -m tools.catalog map {MAP_REL}")

    wires = manifest.get("wires", {})
    for row in wires.get("wires", []):
        for fault in row["faults"]:
            item("wire-fault", f"wire {row['name']} ({row['says']}): {fault}",
                 owner="projects/blood-city/level/build_skeleton.py (the module "
                       "that declares the wire: grep its name)",
                 see=f"python -m tools.catalog mechanisms {MAP_REL}")
    for row in wires.get("silent", []):
        item("silent-sender",
             f"{row['id']} ({row['type']}) has channel {row['channel']} to send on "
             f"and reports neither its ON nor its OFF change, so it never sends",
             owner="bloodmap/wiring.py:Circuit (declare the wire; `when` sets the report)",
             see=f"python -m tools.catalog mechanisms {MAP_REL}")
    for row in wires.get("undeclared", []):
        item("undeclared-wire",
             f"channel {row['channel']} is typed by hand: "
             f"{', '.join(row['senders']) or 'nothing'} send(s), "
             f"{', '.join(row['listeners']) or 'nothing'} answer(s), and no "
             f"wire says what it is for",
             owner="bloodmap/wiring.py:Circuit (declare it where its number is typed: "
                   "grep the number under projects/blood-city/level)",
             see=f"python -m tools.catalog mechanisms {MAP_REL}")

    rules = manifest.get("rules", {})
    for row in rules.get("open", []):
        item(f"rule-{row['severity']}", f"{row['code']}: {row['says']}",
             owner=f"bloodmap/rules_blood.py: {row['code']}", at=row["at"],
             see=f"python -m tools.grade_rules --no-write --against {MAP_REL}")

    def from_pass(key: str) -> str:
        return owners.get(key, "projects/blood-city/level/build_skeleton.py")

    for said in manifest.get("goods", {}).get("refused", []):
        where, _colon, what = said.partition(": ")
        item("refused", what or said, place=where, owner=from_pass("goods"),
             see="the goods lines the build prints")
    for said in manifest.get("venue_details", {}).get("skipped", []):
        parts = said.split(":")
        item("skipped", f"venue detail not placed: {parts[-1]}",
             place="/".join(parts[:-1]), owner=from_pass("venue_details"),
             see="the venue detail line the build prints")
    for said in manifest.get("flat_dropped", []):
        item("dropped", said, owner=from_pass("flat_dropped"),
             see="the 'flat sprites dropped' line the build prints")
    fit = manifest.get("sprite_fit", {})
    for name in ("sunk", "through", "squeezed", "lifted", "overlaps", "flat_overlaps",
                 "sunk_actors", "on_travelling_floor"):
        for row in fit.get(name) or []:
            item(f"sprite-{name.replace('_', '-')}", json.dumps(row, sort_keys=True),
                 owner="the pass that placed the sprite; find it by tile",
                 at=f"sector[{row['sector']}]" if isinstance(row, dict) and "sector" in row else None,
                 see=LINT)
    for tile in manifest.get("lost_wall_tiles", {}).get("tiles", []):
        item("lost-tile", f"{tile} is authored on walls and drawn on no band",
             owner="bloodmap/render_slots.py decides what is drawn",
             see="the READ-BACK DIFF lines the build prints")

    by_kind = Counter(row["kind"] for row in open_items)
    return {
        "$schema": SCHEMA, "schema_version": 1,
        "built_from": {
            "manifest_sha256": _sha(manifest_text),
            "map_sha256": hashlib.sha256(MAP.read_bytes()).hexdigest(),
            "map": MAP_REL,
        },
        "build": {
            **counts,
            "limits": dict(BUILD_LIMITS),
            "headroom": {key: round(1 - counts[key] / BUILD_LIMITS[key], 3)
                         for key in counts},
            "command": "python projects/blood-city/level/build_skeleton.py",
            "read_back_agrees": bool(manifest.get("readback", {}).get("agrees")),
            "rules": rules.get("by_severity", {}),
        },
        "stages": _stages(manifest.get("stages", [])),
        "finish": {"exits": finish["exits"], "exit_reached": finish["exit_reached"],
                   "keys": finish["keys"], "locked": finish["locked"],
                   "secrets": finish["secrets"], "space": finish["space"],
                   "reached": finish["reached"],
                   "gated_areas": finish["gated_areas"]},
        "wires": [{key: row[key] for key in ("name", "says", "channel", "engine",
                                              "when", "then")}
                  for row in wires.get("declared", [])],
        "places": places,
        "showcase": showcase,
        "open": open_items,
        "open_by_kind": dict(sorted(by_kind.items())),
        "not_verified": [
            "no play session is recorded here: whether the level is fun, or "
            "can be finished, is known only from the owner's walks "
            "(tests/test_city_second_walk.py, tests/test_city_third_walk.py)",
            "traversal is a static reading of the map "
            "(projects/blood-city/level/walk_static.py), not a walk",
            "a critique score is a blind reader's opinion of frames, recorded "
            "as said; it is not a measurement",
        ],
    }


def brief(status: dict[str, Any]) -> str:
    """The page to read first: forty lines, generated from the data."""
    build = status["build"]
    lines = [
        "# Blood City: where it stands",
        "",
        "Generated by `projects/blood-city/level/status.py` from the build "
        "manifest and the critique rounds. Do not edit: a test fails when "
        "this page and the build disagree. The data is `status.json` beside it.",
        "",
        f"**Build**: {build['sectors']} sectors, {build['walls']} walls, "
        f"{build['sprites']} sprites "
        f"({round(100 * (1 - build['headroom']['walls']))}% of NBlood's wall limit). "
        f"`{build['command']}` takes about a minute and is deterministic. "
        f"Read-back {'agrees' if build['read_back_agrees'] else 'DISAGREES'}; "
        f"rules: {build['rules']}.",
        "",
        f"The build runs {len(status['stages'])} named stages in order "
        "(" + ", ".join(row["name"] for row in status["stages"]) + "). "
        "`python projects/blood-city/level/status.py --stages` gives each "
        "one's line in the build and what it took.",
        "",
        f"**Can it be finished**: "
        + ("yes by our reader" if status["finish"]["exit_reached"]
           else "NO: " + ("there is no exit" if not status["finish"]["exits"]
                          else "the exit is never reached"))
        + f"; {status['finish']['reached']} of {status['finish']['space']} "
        f"player-space sectors reached in {len(status['finish']['gated_areas'])} "
        f"gated areas (`python -m tools.catalog map {MAP_REL}`).",
        "",
        f"**Wiring**: {len(status['wires'])} wire(s) are declared with their "
        f"purpose (`status.py --wires`); "
        f"{status['open_by_kind'].get('undeclared-wire', 0)} channel(s) on the "
        f"map are still typed by hand, and "
        f"{status['open_by_kind'].get('silent-sender', 0)} sender(s) can never send.",
        "",
        "## Places",
        "",
        "| place | study | layers | critique | open |",
        "| --- | --- | --- | --- | --- |",
    ]
    per_place = Counter(row["place"] for row in status["open"] if row["place"])
    for place in status["places"]:
        layers = place["layers"]
        critique = place["critique"]
        if critique is None:
            said = "never"
        else:
            scores = "/".join(str(v) for v in critique["scores"].values())
            said = (f"round {critique['round']}: "
                    f"{'passes' if critique['passes'] else 'not passed'} ({scores})")
        missing = f", lacks {', '.join(layers['missing'])}" if layers["missing"] else ""
        lines.append(
            f"| {place['name']} | {place['study'] or '**none**'} | "
            f"{len(layers['has'])} (campaign median {layers['campaign_p50']}){missing} | "
            f"{said} | {per_place.get(place['name'], 0)} |")
    shown = status.get("showcase") or []
    if shown:
        known = sum(row["recognised"] for row in shown)
        missed = [f"{row['title']} (\"{row['blind']}\", round {row['round']})"
                  for row in shown if not row["recognised"]]
        lines += [
            "", "## Showcase", "",
            f"Each place's best view of about 800, chosen and named by a blind "
            f"reader (`python -m tools.showcase`): recognised from it with every "
            f"sign hidden, {known} of {len(shown)}."
            + (f" Not: {'; '.join(missed)}." if missed else "")
            + " Every place's verdict, lacks and fix: `status.json` (showcase).",
        ]
    lines += ["", "## Open", ""]
    for kind, count in status["open_by_kind"].items():
        lines.append(f"- `{kind}`: {count}")
    lines += [
        "",
        "```bash",
        "python projects/blood-city/level/status.py --place station   # one place",
        "python projects/blood-city/level/status.py --kind refused    # one kind",
        "```",
        "",
        "Each open item names what is wrong, where, the pass or file that "
        "owns it, and the command that shows it.",
        "",
        "## Not verified",
        "",
    ]
    lines += [f"- {said}" for said in status["not_verified"]]
    return "\n".join(lines) + "\n"


def render(status: dict[str, Any]) -> tuple[str, str]:
    return json.dumps(status, indent=1) + "\n", brief(status)


def write() -> dict[str, Any]:
    status = gather()
    data, page = render(status)
    STATUS_JSON.write_text(data, encoding="utf-8", newline="\n")
    STATUS_MD.write_text(page, encoding="utf-8", newline="\n")
    return status


def stale() -> list[str]:
    """Which of the two files does not match what the sources give today."""
    data, page = render(gather())
    out = []
    for path, text in ((STATUS_JSON, data), (STATUS_MD, page)):
        if not path.exists() or _text(path) != text:
            out.append(path.relative_to(ROOT).as_posix())
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--place", help="one place, by any part of its name")
    parser.add_argument("--kind", help="one kind of open item")
    parser.add_argument("--stages", action="store_true",
                        help="the build's stages: where each starts, what it took")
    parser.add_argument("--wires", action="store_true",
                        help="the level's declared wiring: what each wire is for")
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if the files are stale")
    args = parser.parse_args(argv)

    if args.wires:
        for row in gather()["wires"]:
            print(f"{row['name']}  [channel {row['channel']}"
                  f"{' ' + row['engine'] if row['engine'] else ''}]  {row['says']}")
            print(f"    when {'; '.join(row['when']) or 'the engine sends'}")
            print(f"    then {'; '.join(row['then']) or 'the engine hears'}")
        return 0

    if args.stages:
        took = stage_seconds()
        for row in gather()["stages"]:
            seconds = f"{took[row['name']]:6.1f} s" if row["name"] in took else "       -"
            print(f"{row['name']:<18}{seconds}  {row['at'].rsplit('/', 1)[1]:<26}{row['says']}")
        if not took:
            print("no timings here: they are written by a build on this machine")
        return 0

    if args.check:
        behind = stale()
        for path in behind:
            print(f"{path} is stale; run python projects/blood-city/level/status.py")
        return 1 if behind else 0

    if args.place or args.kind:
        status = gather()
        wanted = (args.place or "").lower()
        for place in status["places"]:
            if wanted and wanted in place["name"].lower():
                print(json.dumps(place, indent=1))
        shown = 0
        for row in status["open"]:
            if args.kind and row["kind"] != args.kind:
                continue
            if wanted and wanted not in (row["place"] or "").lower():
                continue
            print(json.dumps(row))
            shown += 1
        print(f"{shown} open item(s)")
        return 0

    status = write()
    print(f"wrote {STATUS_JSON.relative_to(ROOT).as_posix()} and STATUS.md: "
          f"{len(status['places'])} places, {len(status['open'])} open "
          f"{status['open_by_kind']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
