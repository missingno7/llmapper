"""Mark our map readers against the campaign: can they finish what is known to be finishable.

Every campaign map can be finished, its keys picked up and its rooms stood
in, and each declares its own secret count. `bloodmap.completion` reads one
map and says what our readers found of that; this runs it over the campaign
and keeps the score in ``knowledge/blood/design/reading-scorecard-v1.json``.

    python -m tools.reading_check            # the table, and write the file
    python -m tools.reading_check E1M1       # one map, in full
    python -m tools.reading_check --check    # exit 1 if the file is stale

The file is a ratchet, not a claim. A map listed under `missed` is one our
readers cannot yet read to its end; the entry says what they failed to find.
A reader that improves moves a map off the list, and the test that holds the
file fails until it is rewritten -- in either direction.
"""

from __future__ import annotations

import argparse
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCORECARD = ROOT / "knowledge" / "blood" / "design" / "reading-scorecard-v1.json"


def gather(population: str | None = None) -> dict:
    """The campaign's score; or, with `population`, another corpus population's.

    The readers were tuned on the campaign and are scored on it, so its
    number flatters them. `--population community-curated` is the same mark
    on maps no rule here was fitted to. It is printed and not kept: nobody
    has shown those maps can all be finished.
    """
    from bloodmap import completion
    from bloodmap.corpus import campaign_maps, list_corpus_maps
    from bloodmap.format import read_map

    rows = []
    paths = (campaign_maps(required=True) if population is None
             else [item.path for item in list_corpus_maps(population=population)])
    for path in paths:
        try:
            mark = completion.read(read_map(path), path.stem.upper())
        except Exception as error:               # a held-out map may not read at all
            if population is None:
                raise
            rows.append({"map": path.stem.upper(), "space": 0, "reached": 0,
                         "exits": 0, "exit_reached": False, "keys": 0,
                         "keys_reached": 0,
                         "secrets": {"declared": None, "credited_normal": 0},
                         "older_reader": {"exit_reachable": None},
                         "missed": [f"the reader failed: {type(error).__name__}: {error}"[:160]]})
            continue
        rows.append({
            "map": mark["map"], "space": mark["space"], "reached": mark["reached"],
            "exits": len(mark["exits"]), "exit_reached": mark["exit_reached"],
            "keys": len(mark["keys"]),
            "keys_reached": sum(1 for row in mark["keys"] if row["reached"]),
            "secrets": mark["secrets"],
            "older_reader": mark["older_reader"],
            "missed": completion.missed(mark)})
    total = {
        "maps": len(rows),
        "exit_reached": sum(1 for row in rows if row["exit_reached"]),
        "exit_reached_by_the_older_reader": sum(
            1 for row in rows if row["older_reader"]["exit_reachable"]),
        "keys": sum(row["keys"] for row in rows),
        "keys_reached": sum(row["keys_reached"] for row in rows),
        "player_space_sectors": sum(row["space"] for row in rows),
        "player_space_reached": sum(row["reached"] for row in rows),
        "secret_counts_agree": sum(
            1 for row in rows
            if row["secrets"]["declared"] == row["secrets"]["credited_normal"]),
        "read_to_the_end": sum(1 for row in rows if not row["missed"]),
    }
    return {
        "$schema": "llmapper.reading-scorecard", "schema_version": 1,
        "reading_guide": [
            "the ground truth is that a shipped campaign map can be finished: "
            "nothing here was labelled by anyone",
            "exit_reached, keys_reached and reached are what "
            "`bloodmap.conditional.frontier` stands in by its last round; "
            "the exit, keys and secrets are found by `bloodmap.wiring`",
            "a secret's number is its type (0 normal, more super; "
            "endgame.cpp:240), and the level's total counts the normal ones",
            "`missed` is the reader's shortfall on that map, never the map's",
        ],
        "total": total, "maps": rows}


def render(card: dict) -> str:
    return json.dumps(card, indent=1) + "\n"


def stale() -> bool:
    return (not SCORECARD.exists()
            or SCORECARD.read_text(encoding="utf-8").replace("\r\n", "\n")
            != render(gather()))


def table(card: dict) -> str:
    total = card["total"]
    lines = [
        f"{total['maps']} campaign maps, every one of them finishable",
        f"  the exit is reached in        {total['exit_reached']} "
        f"(the older reader: {total['exit_reached_by_the_older_reader']})",
        f"  keys reached                  {total['keys_reached']} of {total['keys']}",
        f"  player space stood in         {total['player_space_reached']} of "
        f"{total['player_space_sectors']} sectors",
        f"  secret counts that agree      {total['secret_counts_agree']}",
        f"  read to the end, nothing missed  {total['read_to_the_end']}",
        ""]
    for row in card["maps"]:
        lines.append(
            f"{row['map']:<6} space {row['reached']:>3}/{row['space']:<3} "
            f"exit {'yes' if row['exit_reached'] else 'NO ':<3} "
            f"keys {row['keys_reached']}/{row['keys']}  "
            + ("; ".join(row["missed"]) or "read to the end"))
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("map", nargs="?", help="one map, in full")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--population",
                        help="mark another corpus population (printed, not kept)")
    args = parser.parse_args(argv)
    if args.population:
        print(table(gather(args.population)).replace(
            "campaign maps, every one of them finishable",
            f"{args.population} maps, not known to be finishable"))
        return 0
    if args.map:
        from bloodmap import completion
        from bloodmap.corpus import corpus_map_path
        from bloodmap.format import read_map

        path = (pathlib.Path(args.map) if args.map.upper().endswith(".MAP")
                else corpus_map_path(args.map))
        mark = completion.read(read_map(path), path.stem.upper())
        print(json.dumps(mark, indent=1))
        print("missed:", completion.missed(mark) or "nothing")
        return 0
    if args.check:
        if stale():
            print(f"{SCORECARD.relative_to(ROOT).as_posix()} is stale; "
                  f"run python -m tools.reading_check")
            return 1
        return 0
    card = gather()
    SCORECARD.write_text(render(card), encoding="utf-8", newline="\n")
    print(table(card))
    print(f"\nwrote {SCORECARD.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
