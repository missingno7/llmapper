"""How the built city is played, measured from its MAP: the keys, the lock, the order it can be finished in, who and what is where.

    python projects/blood-city/level/playthrough.py            writes ../reports/gameplay.md and gameplay.json
    python projects/blood-city/level/playthrough.py --table    prints it

The intent is `references/gameplay-plan.md`; this is what the map holds. Read by
`bloodmap.supplies` (the walk, the foes, the supplies, the secrets) and
`bloodmap.completion` (what opens what).
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(Path(__file__).resolve().parent)]

from bloodmap import completion, supplies  # noqa: E402
from bloodmap.format import read_map  # noqa: E402
from bloodmap.model import record_extra, record_fields  # noqa: E402

MAP = Path(__file__).resolve().parent / "blood-city-current.MAP"
REPORTS = Path(__file__).resolve().parents[1] / "reports"
PU = 1024
STREET_BELOW = 40000                                     # a floor deeper than this is underground
#: (name, underground, x0, y0, x1, y1 in plan units): the first that holds a point is where it is
AREAS = (
    # the drowned places are kept 60 units west of where they are (`underwater.OFFSET`)
    ("the sump", True, -22, 3, -15, 14), ("the flooded branch", True, -21, 27, -13, 40), ("the slip", True, -46, 55, -34, 62),
    ("the Toshers' Den", True, 8, 41, 19.9, 50),
    ("the Cabal's chamber", True, 19, 50, 36, 72), ("the settling hall", True, 17, 41, 36, 50),
    ("the Phantom Terminus", True, 35, -22, 72, 2), ("the Weaver's Cellars", True, 6, 8.5, 18, 17.6),
    ("St Gallow's crypt", True, 27, 26, 32, 30.5), ("the stockyard", True, 46.1, 34.2, 63, 62),
    ("Graves Brook", True, 0, 17.6, 32, 26), ("the sewers", True, 26, 1, 58, 41),
    ("Gravesend Station", False, 0, -27, 60, 0), ("theatre row", False, 0, 0, 32, 15),
    ("foundry ward", False, 39, 2, 60, 37), ("the market hall", False, 3, 39.5, 15, 50), ("the arcade", False, 39, 39, 54, 50),
    ("St Gallow's", False, 20, 20, 34, 37), ("the harbour", False, 0, 55, 60, 64), ("the quay and the market square", False, 0, 37, 60, 55),
    ("the avenue", False, 32, 0, 40, 40), ("the west streets", False, 0, 14, 34, 40),
)


def area(x: float, y: float, z: float) -> str:
    under = z > STREET_BELOW
    x, y = x / PU, y / PU
    return next((name for name, below, x0, y0, x1, y1 in AREAS if below == under and x0 <= x < x1 and y0 <= y < y1), "elsewhere")


def read(path: Path = MAP) -> dict:
    disk = read_map(path)
    row = supplies.read(disk, "CITY")
    mark = completion.read(disk, "CITY")
    places: dict[str, dict] = defaultdict(lambda: {"foes": Counter(), "waiting": 0, "supplies": Counter(), "secret": Counter()})

    def floor_of(sprite: int) -> tuple[float, float, float]:
        f = record_fields(disk.sprites[sprite])
        return f["x"], f["y"], record_fields(disk.sectors[f["sector"]])["floor_z"]

    for foe in row["foes"]:
        here = places[area(*floor_of(foe["sprite"]))]
        here["foes"][foe["name"]] += 1
        if record_fields(disk.sprites[foe["sprite"]])["type"] == 18:
            here["waiting"] += 1
    for item in row["items"]:
        if item.get("carried_by"):
            continue
        here = places[area(*floor_of(item["sprite"]))]
        here["secret" if item["secret"] else "supplies"][item["name"]] += 1
    keys = []
    for k in mark["keys"]:
        wakes = sum(1 for s in _answers(disk, k["sprite"]) if record_fields(disk.sprites[s])["type"] in (18, 244, 208))
        keys.append({"key": k["name"], "at": area(*floor_of(k["sprite"])), "reached": bool(k["reached"]), "lets_loose": wakes})
    return {"way_m": round(row["length"] / 602), "way_is": row["way_is"], "sectors": row["sectors"], "reached": row["reached"],
            "taken_on_trust": row["rescued"], "keys": keys,
            "exit": [{"root": e["root"], "reached": bool(e["reached"])} for e in mark["exits"]],
            "locks": _counted(disk),
            "budget": row["budget"], "secrets": len(row["secrets"]),
            "foes": len(row["foes"]),
            "guns": [{"gun": i["name"], "at": area(*floor_of(i["sprite"])), "secret": i["secret"],
                      "foes_before": i["foes_before"]} for i in row["items"]
                     if (i["kind"] == "weapon" or i["name"] == "guns akimbo") and not i["carried_by"]],
            "places": {name: {k: dict(sorted(v.items())) if isinstance(v, Counter) else v for k, v in here.items()}
                       for name, here in sorted(places.items())}}


KEY_NAMES = ("", "skull", "eye", "fire", "dagger", "spider", "moon")


def _counted(disk) -> list[dict]:
    """Every counter that keyed switches send to: the keys it wants, and how many of them."""
    out = []
    for i, s in enumerate(disk.sprites):
        x = record_extra(s) or {}
        if record_fields(s)["type"] != 22 or not x.get("rx_id"):
            continue
        wants = sorted(k for t in disk.sprites if (y := record_extra(t)) and y["tx_id"] == x["rx_id"] and (k := y["key"]))
        if wants:
            out.append({"counter": i, "wants": [KEY_NAMES[k] for k in wants], "opens_at": int(x["data_2"])})
    return out


def _answers(disk, sprite: int) -> list[int]:
    extra = record_extra(disk.sprites[sprite])
    if not extra or not extra["tx_id"]:
        return []
    return [i for i, s in enumerate(disk.sprites) if (record_extra(s) or {}).get("rx_id") == extra["tx_id"]]


def page(data: dict) -> str:
    def some(counter):
        return ", ".join(f"{n} {name}" if n > 1 else name for name, n in counter.items()) or "-"

    b = data["budget"]
    lines = ["# How the built city is played", "",
             "Generated by `projects/blood-city/level/playthrough.py` from the MAP. Do not edit. The intent: "
             "[gameplay-plan.md](../references/gameplay-plan.md).", "",
             f"**The way**: {data['way_m']} m to {data['way_is']}; {data['reached']} of {data['sectors']} sectors walked, "
             f"{data['taken_on_trust']} taken on trust. "
             + " ".join(f"A lock counts {lock['opens_at']} keys: {', '.join(lock['wants'])}." for lock in data["locks"])
             + " The exit is " + ("reached once it opens." if all(e["reached"] for e in data["exit"]) else "NOT reached."), "",
             f"**The fight**: {data['foes']} foes at the middle difficulty; {data['secrets']} secrets. Budget: "
             + ", ".join(f"{k} {v}" for k, v in b.items() if isinstance(v, (int, float))) + ".", "",
             "## Keys", "", "| key | where | reached | lets loose |", "| --- | --- | --- | --- |"]
    lines += [f"| {k['key']} | {k['at']} | {'yes' if k['reached'] else 'NO'} | {k['lets_loose']} |" for k in data["keys"]]
    lines += ["", "## Guns", "", "| gun | where | secret | share of the foes nearer the start |", "| --- | --- | --- | --- |"]
    lines += [f"| {g['gun']} | {g['at']} | {'yes' if g['secret'] else ''} | {g['foes_before']} |"
              for g in sorted(data["guns"], key=lambda g: (g["foes_before"] is None, g["foes_before"]))]
    lines += ["", "## Place by place", "", "| place | foes (of them waiting on a wire) | supplies | in secrets |", "| --- | --- | --- | --- |"]
    lines += [f"| {name} | {some(p['foes'])}{' (' + str(p['waiting']) + ')' if p['waiting'] else ''} | {some(p['supplies'])} | {some(p['secret'])} |"
              for name, p in data["places"].items()]
    return "\n".join(lines) + "\n"


def main() -> None:
    data = read()
    text = page(data)
    if "--table" in sys.argv:
        print(text)
        return
    (REPORTS / "gameplay.md").write_text(text, encoding="utf-8")
    (REPORTS / "gameplay.json").write_text(json.dumps(data, indent=1, default=str) + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
