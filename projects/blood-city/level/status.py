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
    for name in ("sunk", "through", "squeezed", "overlaps", "flat_overlaps",
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
        "places": places,
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
    parser.add_argument("--check", action="store_true",
                        help="exit 1 if the files are stale")
    args = parser.parse_args(argv)

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
