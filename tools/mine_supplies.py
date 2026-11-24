"""What shipped maps give the player, how far along, against what, and behind which keys and secrets.

`bloodmap.supplies` reads one map; this runs it over the campaign and over
Death Wish (read apart, because Death Wish is not Blood's own hand), keeps
the figures, and prints one map's table.

.. code-block:: bash

    python -m tools.mine_supplies                  # write knowledge/blood/design/supplies.json
    python -m tools.mine_supplies show E1M1        # one map by name
    python -m tools.mine_supplies show projects/blood-city/level/blood-city-current.MAP
    python -m tools.mine_supplies show DWE1M1 --items   # every pickup, in the order it is come to
    python -m tools.mine_supplies where "tommy gun"     # where each map first gives one
    python -m tools.mine_supplies keys --carried        # every key of every map, filtered

The findings, with what is unreliable, are in
``knowledge/blood/studies/supplies/notes.md``.

A map's ORDER (how far along a thing is) counts only where the walk reads the
map to its exit without much taking on trust (`ordered`); counts, the budget,
the stands and the secrets count for every map.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import statistics
from collections import Counter, defaultdict
from typing import Any, Iterable

from bloodmap import supplies
from bloodmap.corpus import campaign_maps, corpus_map_path, named_maps
from bloodmap.format import read_map

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "knowledge" / "blood" / "design" / "supplies.json"
KIND_ORDER = {kind: i for i, kind in enumerate(supplies.KINDS)}


def populations() -> dict[str, list[pathlib.Path]]:
    return {"campaign": campaign_maps(required=True),
            "death_wish": [p for p in named_maps() if p.stem.upper().startswith("DWE")]}


def find(name: str) -> pathlib.Path:
    path = pathlib.Path(name)
    return path if path.suffix.upper() == ".MAP" and path.exists() else corpus_map_path(name)


def ordered(row: dict[str, Any]) -> bool:
    """Whether the walk's order is worth counting on this map."""
    return (row["way_is"] == "the exit" and row["reached"] >= 0.75 * row["sectors"]
            and row["rescued"] <= 0.25 * row["reached"])


def quartiles(values: Iterable[float | None], places: int = 3) -> list[float] | None:
    """[lower quartile, median, upper quartile], or None where there is nothing."""
    got = sorted(v for v in values if v is not None)
    if not got:
        return None
    if len(got) == 1:
        return [round(got[0], places)] * 3
    low, mid, high = statistics.quantiles(got, n=4, method="inclusive")
    return [round(low, places), round(mid, places), round(high, places)]


def share(part: int, whole: int) -> float | None:
    return round(part / whole, 3) if whole else None


def counted(counter: Counter, top: int | None = None) -> dict[str, int]:
    return dict(sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0])))[:top])


def compact(row: dict[str, Any]) -> dict[str, Any]:
    """One map as it is kept: every supply type on a line, keys and secrets whole."""
    by_name: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for item in row["items"]:
        if item["kind"] != "key":
            by_name[(item["kind"], item["name"])].append(item)
    supply = []
    for (kind, name), mine in sorted(by_name.items(), key=lambda kv: (KIND_ORDER[kv[0][0]], kv[0][1])):
        plain = [i for i in mine if not i["secret"] and i["way"] is not None]
        first = min(plain, key=lambda i: i["way"], default=None)
        supply.append({
            "kind": kind, "name": name, "count": len(mine),
            "secret": sum(1 for i in mine if i["secret"]),
            "carried": sum(1 for i in mine if i["carried_by"]),
            "first": None if first is None else {
                "sprite": first["sprite"], "sector": first["sector"], "way": round(first["way"], 3),
                "area": first["area"], "foes_before": first["foes_before"]},
            "ways": [None if i["way"] is None else round(i["way"], 2)
                     for i in sorted(mine, key=lambda i: (i["way"] is None, i["way"] or 0))]})
    return {
        "map": row["map"], "ordered": ordered(row), "way_is": row["way_is"], "length": row["length"],
        "sectors": row["sectors"], "reached": row["reached"], "rescued": row["rescued"],
        "areas": row["areas"], "supply": supply, "budget": row["budget"],
        "keys": row["keys"],
        "locks": [{k: lock[k] for k in ("object", "key_name", "works", "moves", "front_way", "faces",
                                        "gates_anything")} for lock in row["locks"]],
        "secrets": [{k: s[k] for k in ("root", "sector", "super", "by", "opened", "act", "reward", "tier",
                                       "guards", "guards_inside")}
                    | {"way": None if s["at"] is None else round(s["at"] / row["length"], 3)}
                    for s in row["secrets"]],
    }


def along(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The way in tenths: what share of the fighting, the ammo and the health lies in each."""
    out = []
    good = [r for r in rows if ordered(r)]
    for tenth in range(11):                  # the last is what lies off past the exit
        low, high = tenth / 10, (tenth + 1) / 10 if tenth < 10 else 99.0
        shares: dict[str, list[float]] = defaultdict(list)
        for row in good:
            for name, things, value in (
                    ("foe_health", row["foes"], lambda t: t["health"]),
                    ("ammo_damage", [i for i in row["items"] if not i["secret"]], supplies.damage_of),
                    ("health", [i for i in row["items"] if i["kind"] == "health" and not i["secret"]],
                     lambda t: t["points"])):
                total = sum(value(t) for t in things if t["way"] is not None)
                if total:
                    shares[name].append(sum(value(t) for t in things if t["way"] is not None
                                            and low <= t["way"] < high) / total)
        out.append({"from": low, "to": high if high < 9 else None,
                    **{name: round(statistics.mean(v), 3) for name, v in sorted(shares.items())}})
    return out


def gather(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """The figures of one population."""
    good = [r for r in rows if ordered(r)]
    out: dict[str, Any] = {"maps": len(rows), "ordered_maps": len(good)}

    # -- each supply
    table: dict[tuple[str, str], dict[str, Any]] = {}
    names = sorted({(i["kind"], i["name"]) for r in rows for i in r["items"] if i["kind"] != "key"},
                   key=lambda t: (KIND_ORDER[t[0]], t[1]))
    for kind, name in names:
        counts, first_any, first_plain, before, tens = [], [], [], [], []
        total = hidden = 0
        for row in rows:
            mine = [i for i in row["items"] if (i["kind"], i["name"]) == (kind, name)]
            if not mine:
                continue
            counts.append(len(mine))
            total += len(mine)
            hidden += sum(1 for i in mine if i["secret"])
            if ordered(row):
                ways = [i for i in mine if i["way"] is not None]
                plain = [i for i in ways if not i["secret"]]
                if ways:
                    first_any.append(min(i["way"] for i in ways))
                if plain:
                    one = min(plain, key=lambda i: i["way"])
                    first_plain.append(one["way"])
                    before.append(one["foes_before"])
        table[(kind, name)] = {
            "kind": kind, "name": name, "maps": len(counts), "share_of_maps": share(len(counts), len(rows)),
            "total": total, "per_map": quartiles(counts, 1), "in_secrets": share(hidden, total),
            "first_way": quartiles(first_any), "first_way_outside_secrets": quartiles(first_plain),
            "foes_before_first": quartiles(before)}
    out["supply"] = list(table.values())
    out["hidden_by_tier"] = {}
    for tier in (1, 2, 3, 4):
        mine = [i for r in rows for i in r["items"] if i["tier"] == tier]
        out["hidden_by_tier"][str(tier)] = {
            "items": len(mine), "in_secrets": share(sum(1 for i in mine if i["secret"]), len(mine))}

    # -- the budget
    budgets = [r["budget"] for r in rows if r["budget"]["foe_health"] >= 300]
    out["budget"] = {"maps": len(budgets), **{
        name: quartiles((b[name] for b in budgets), 2) for name in (
            "foes", "foe_health", "ammo_damage", "damage_per_health", "damage_outside_secrets_per_health",
            "damage_with_drops_per_health", "health", "health_per_100", "armor", "armor_per_100",
            "spawn_markers")}}
    out["budget"]["health_in_secrets"] = share(sum(b["health_in_secrets"] for b in budgets),
                                               sum(b["health"] for b in budgets))
    out["budget"]["damage_in_secrets"] = share(sum(b["ammo_damage_in_secrets"] for b in budgets),
                                               sum(b["ammo_damage"] for b in budgets))
    kinds: Counter = Counter()
    for b in budgets:
        kinds.update(b["ammo_damage_by_kind"])
    out["budget"]["damage_by_ammo"] = {k: share(v, sum(kinds.values())) for k, v in counted(kinds).items()}
    out["along_the_way"] = along(rows)

    # -- where a supply stands
    out["placing"] = {}
    for kind in supplies.KINDS:
        mine = [i for r in rows for i in r["items"] if i["kind"] == kind and not i["carried_by"]]
        if not mine:
            continue
        out["placing"][kind] = {
            "items": len(mine),
            "fight": {k: share(v, len(mine)) for k, v in counted(Counter(i["fight"] for i in mine)).items()},
            "nearest_foe": quartiles((i["foe"] for i in mine), 0),
            "foe_met_first": share(sum(1 for i in mine if i["foe_first"]),
                                   sum(1 for i in mine if i["foe_first"] is not None)),
            "stands_on": {k: share(v, len(mine))
                          for k, v in counted(Counter(i["stands"]["on"] for i in mine)).items()},
            "to_wall": quartiles((i["stands"]["wall"] for i in mine), 0),
            "by_a_corpse": share(sum(1 for i in mine if i["stands"]["corpse"]), len(mine)),
            "alone": share(sum(1 for i in mine if i["group"] == 1), len(mine)),
            "pair": share(sum(1 for i in mine if i["group"] == 2), len(mine)),
            "three_or_more": share(sum(1 for i in mine if i["group"] >= 3), len(mine)),
            "two_the_same": share(sum(1 for i in mine if i["same"] == 2), len(mine)),
            "three_the_same": share(sum(1 for i in mine if i["same"] >= 3), len(mine))}
    groups: Counter = Counter()
    for row in rows:
        seen: dict[int, list[str]] = defaultdict(list)
        for item in row["items"]:
            seen[item["group_id"]].append(item["name"])
        for members in seen.values():
            if 2 <= len(members) <= 4:
                groups[" + ".join(sorted(members))] += 1
    out["commonest_groups"] = counted(groups, 24)

    # -- keys
    keys = [(r, k) for r in rows for k in r["keys"] if k["taken_first"] or k["at"] is None]
    per_map = [len({k["name"] for k in r["keys"]}) for r in rows]
    out["keys"] = {
        "per_map": counted(Counter(per_map)), "keys": len(keys),
        "reached": sum(1 for _r, k in keys if k["at"] is not None),
        "colours": counted(Counter(k["name"] for _r, k in keys)),
        "opens": counted(Counter(o for _r, k in keys for o in k["opens"])),
        "locks_per_key": counted(Counter(k["locks"] for _r, k in keys)),
        "carried_by_a_dude": share(sum(1 for _r, k in keys if k["carried_by"]), len(keys)),
        "in_a_secret": share(sum(1 for _r, k in keys if k["secret"]), len(keys)),
        "stands_on": counted(Counter(k["stands"] for _r, k in keys)),
        "guards_within_4096": quartiles((k["guards"] for _r, k in keys), 1),
        "unguarded": share(sum(1 for _r, k in keys if not k["guards"]), len(keys)),
        "something_on_pickup": share(sum(1 for _r, k in keys if k["on_pickup"]), len(keys)),
        "dudes_woken_on_pickup": share(sum(1 for _r, k in keys if k["on_pickup"].get("dudes")), len(keys)),
        "way_opened_on_pickup": share(sum(1 for _r, k in keys if k["opens_on_pickup"]), len(keys)),
    }
    if good:
        mine = [(r, k) for r, k in keys if ordered(r) and k["at"] is not None]
        locked = [(r, k) for r, k in mine if k["lock_met_first"] is not None]
        met = [(r, k) for r, k in locked if k["lock_met_first"]]
        both = [(k["to_lock"] / k["out_from_lock"]) for _r, k in met
                if k["to_lock"] is not None and k["out_from_lock"] > 2048]
        first_way: dict[int, list[float]] = defaultdict(list)
        for row in good:
            seen = []
            for k in row["keys"]:
                if k["way"] is not None and k["name"] not in seen:
                    seen.append(k["name"])
                    first_way[len(seen)].append(k["way"])
        out["keys"]["ordered"] = {
            "keys": len(mine), "gate_read": share(sum(1 for _r, k in mine if k["gates"]), len(mine)),
            "way_of_nth_key": {str(n): quartiles(v) for n, v in sorted(first_way.items()) if len(v) >= 4},
            "lock_met_before_key": share(len(met), len(locked)),
            "key_seen_before_it_can_be_had": share(sum(1 for _r, k in mine if k["glimpsed"]), len(mine)),
            "key_to_lock": quartiles((k["to_lock"] for _r, k in mine), 0),
            "key_to_lock_way": quartiles(k["to_lock_way"] for _r, k in mine),
            "back_over_out": quartiles(both, 2),
            "comes_back_shorter": share(sum(1 for v in both if v < 0.7), len(both)),
        }
        order: Counter = Counter()
        for row in good:
            names_in = []
            for k in row["keys"]:
                if k["way"] is not None and k["name"] not in names_in:
                    names_in.append(k["name"])
            if names_in:
                order[names_in[0]] += 1
        out["keys"]["ordered"]["first_colour"] = counted(order)

    # -- secrets
    secrets = [(r, s) for r in rows for s in r["secrets"]]
    out["secrets"] = {
        "per_map": quartiles((len(r["secrets"]) for r in rows), 1), "secrets": len(secrets),
        "super": sum(1 for _r, s in secrets if s["super"]),
        "opened": counted(Counter(s["opened"] for _r, s in secrets)),
        "credited_by": counted(Counter(s["by"] for _r, s in secrets)),
        "best_tier": {str(k): v for k, v in sorted(Counter(s["tier"] for _r, s in secrets).items())},
        "holds_nothing_we_read": share(sum(1 for _r, s in secrets if not s["reward"]), len(secrets)),
        "items_each": quartiles((len(s["reward"]) for _r, s in secrets if s["reward"]), 1),
        "guards": quartiles((s["guards"] for _r, s in secrets), 1),
        "unguarded": share(sum(1 for _r, s in secrets if not s["guards"]), len(secrets)),
        "rewards": counted(Counter(n for _r, s in secrets for n in s["reward"]), 24),
        "way": quartiles(s["at"] / r["length"] for r, s in secrets if ordered(r) and s["at"] is not None),
    }
    by_open: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for _r, s in secrets:
        by_open[s["opened"]].append(s)
    out["secrets"]["best_tier_by_opening"] = {
        opened: {"secrets": len(mine), "with_tier_3_or_4": share(sum(1 for s in mine if s["tier"] >= 3), len(mine))}
        for opened, mine in sorted(by_open.items())}
    return out


def read(path: pathlib.Path) -> dict[str, Any]:
    return supplies.read(read_map(path), path.stem.upper())


def mine() -> dict[str, Any]:
    from concurrent.futures import ProcessPoolExecutor

    result: dict[str, Any] = {
        "$schema": supplies.SCHEMA, "schema_version": supplies.SCHEMA_VERSION,
        "reading_guide": [
            "single player, difficulty 2 (Lightly Broiled); locked-out sprites are not counted",
            "way: distance walked at least to stand there, over the distance of the exit (1.0)",
            "area: how many keys the way takes; 0 is open from the start",
            "ordered: the walk reached the exit and took at most a quarter of the map on trust; "
            "every figure with a way in it is over ordered maps only",
            "three figures together are the lower quartile, the median and the upper quartile",
            "damage is a convention (bloodmap.supplies.DAMAGE_PER_ROUND): one round, one target",
        ], "populations": {}, "maps": {}}
    with ProcessPoolExecutor(max_workers=6) as pool:
        for name, paths in populations().items():
            rows = list(pool.map(read, paths))
            result["populations"][name] = gather(rows)
            for row in rows:
                result["maps"][row["map"]] = compact(row)
    return result


# ---------------------------------------------------------------------------
# Printing one map
# ---------------------------------------------------------------------------

def _way(value: float | None) -> str:
    return "  -- " if value is None else f"{value:5.2f}"


def table(row: dict[str, Any], items: bool = False) -> str:
    b = row["budget"]
    lines = [
        f"SUPPLIES OF {row['map']}  single player, difficulty {row['skill']}",
        f"  {row['sectors']} sectors, {row['reached']} walked ({row['rescued']} of them taken on trust); "
        f"the way is {row['length']} units ({row['length'] / 602:.0f} m) to {row['way_is']}",
        f"  the order is {'trusted' if ordered(row) else 'NOT trusted on this map'}",
        "AREAS  (by how many keys the way takes)"]
    for area in row["areas"]:
        lines.append(f"  area {area['area']}: {area['sectors']:4} sectors, way {area['from']:.2f}-{area['to']:.2f}, "
                     f"{area['foes']} foes ({area['foe_health']} health), {area['items']} pickups")
    lines.append("SUPPLY                      count  secret  first way / area / foes before   every way")
    c = compact(row)
    for s in c["supply"]:
        first = s["first"]
        said = ("in secrets only" if first is None else
                f"{first['way']:.2f} / {first['area']} / {first['foes_before']:.0%}  sprite {first['sprite']}")
        ways = " ".join("--" if w is None else f"{w:.2f}" for w in s["ways"][:14])
        lines.append(f"  {s['kind']:8}{s['name']:<20}{s['count']:4}{s['secret']:8}   {said:<34} {ways}"
                     + (" ..." if len(s["ways"]) > 14 else ""))
    lines += [
        "BUDGET",
        f"  foes {b['foes']} ({b['placed']} placed, {b['spawn_markers']} spawn markers), {b['foe_health']} health: "
        + ", ".join(f"{n} {v}" for v, n in sorted(b["by_foe"].items(), key=lambda t: -t[1])),
        f"  ammo damage {b['ammo_damage']} = {b['damage_per_health']} a health point; outside secrets "
        f"{b['damage_outside_secrets_per_health']}; with what cultists drop {b['damage_with_drops_per_health']}",
        "  by ammo: " + ", ".join(f"{k} {v}" for k, v in sorted(b["ammo_damage_by_kind"].items(),
                                                               key=lambda t: -t[1])),
        f"  health {b['health']} ({b['health_in_secrets']} in secrets) = {b['health_per_100']} per 100 foe health; "
        f"armor {b['armor']} = {b['armor_per_100']} per 100",
        "  along the way, tenths  (foe health | ammo damage | health, shares outside secrets)"]
    for tenth in along_one(row):
        until = "more" if tenth["to"] is None else f"{tenth['to']:.1f} "
        lines.append(f"    {tenth['from']:.1f}-{until} {tenth['foe_health']:4.0%} | "
                     f"{tenth['ammo_damage']:4.0%} | {tenth['health']:4.0%}")
    plain = [i for i in row["items"] if i["kind"] != "key"]
    if plain:
        lines.append("  where supplies stand: " + ", ".join(
            f"{k} {v}" for k, v in counted(Counter(i["stands"]["on"] for i in plain)).items())
            + "; fight " + ", ".join(f"{k} {v}" for k, v in counted(Counter(i["fight"] for i in plain)).items()))
    lines.append("KEYS  (in the order they are come to)")
    for k in row["keys"]:
        lines.append(
            f"  {k['name']:<7} sprite {k['sprite']:<5} sector {k['sector']:<5} way {_way(k['way'])}  "
            f"needs {k['needs']}  {k['stands']}{', carried by a ' + k['carried_by'] if k['carried_by'] else ''}"
            f", {k['guards']} guards{', by a corpse' if k['corpse'] else ''}")
        lines.append(
            f"          {k['locks']} lock(s): {', '.join(k['opens']) or 'none read'}; nearest lock way "
            f"{_way(k['lock_way'])} ({'met before the key' if k['lock_met_first'] else 'not met before the key'}); "
            f"key to lock {k['to_lock']}; gates {k['unlocks_sectors']} sectors"
            + (f"; seen from sector {k['glimpsed']['from_sector']} with {k['glimpsed']['still_to_go']} to walk"
               if k["glimpsed"] else "")
            + (f"; taking it: {k['on_pickup']}" if k["on_pickup"] else "")
            + (f"; taking it opens {k['opens_on_pickup']} sectors" if k["opens_on_pickup"] else ""))
    if not row["keys"]:
        lines.append("  none")
    lines.append("SECRETS")
    for s in row["secrets"]:
        at = None if s["at"] is None else s["at"] / row["length"]
        lines.append(f"  {s['root']:<12} way {_way(at)}  {s['opened']:<34} guards {s['guards']} "
                     f"({s['guards_inside']} inside)  tier {s['tier']}  {', '.join(s['reward']) or 'nothing we read'}"
                     + ("  SUPER" if s["super"] else ""))
    if not row["secrets"]:
        lines.append("  none")
    if items:
        lines.append("EVERY PICKUP  (in the order it is come to)")
        for i in sorted(row["items"], key=lambda i: (i["way"] is None, i["way"] or 0, i["sprite"])):
            lines.append(f"  {_way(i['way'])}  {i['name']:<18} sprite {i['sprite']:<5} sector {i['sector']:<5} area "
                         f"{i['area']}  {i['fight']:<8} foe {i['foe']}  {i['stands']['on']}"
                         + (f"; {i['group']} together" if i["group"] > 1 else "")
                         + ("; by a corpse" if i["stands"]["corpse"] else "") + ("; SECRET" if i["secret"] else "")
                         + (f"; carried by a {i['carried_by']}" if i["carried_by"] else ""))
    return "\n".join(lines)


def along_one(row: dict[str, Any]) -> list[dict[str, Any]]:
    out = []
    for tenth in range(11):
        low, high = tenth / 10, (tenth + 1) / 10 if tenth < 10 else 99.0
        got = {"from": low, "to": high if high < 9 else None}
        for name, things, value in (
                ("foe_health", row["foes"], lambda t: t["health"]),
                ("ammo_damage", [i for i in row["items"] if not i["secret"]], supplies.damage_of),
                ("health", [i for i in row["items"] if i["kind"] == "health" and not i["secret"]],
                 lambda t: t["points"])):
            total = sum(value(t) for t in things if t["way"] is not None) or 1
            got[name] = sum(value(t) for t in things if t["way"] is not None and low <= t["way"] < high) / total
        out.append(got)
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="what")
    one = sub.add_parser("show", help="one map, by name or path")
    one.add_argument("map")
    one.add_argument("--items", action="store_true", help="every pickup, in order")
    one.add_argument("--skill", type=int, default=supplies.DEFAULT_SKILL)
    where = sub.add_parser("where", help="where each kept map gives a supply")
    where.add_argument("name")
    keyed = sub.add_parser("keys", help="every key of every kept map")
    keyed.add_argument("--carried", action="store_true")
    keyed.add_argument("--glimpsed", action="store_true")
    keyed.add_argument("--wakes", action="store_true")
    args = parser.parse_args(argv)
    if args.what == "show":
        path = find(args.map)
        print(table(supplies.read(read_map(path), path.stem.upper(), args.skill), args.items))
        return 0
    if args.what in ("where", "keys"):
        kept = json.loads(OUTPUT.read_text("utf-8"))["maps"]
        for name, row in kept.items():
            if args.what == "where":
                for s in row["supply"]:
                    if s["name"] == args.name:
                        print(f"{name:<8} {s['count']} ({s['secret']} in secrets) first {s['first']}"
                              + ("" if row["ordered"] else "  [order not trusted]"))
            else:
                for k in row["keys"]:
                    if (args.carried and not k["carried_by"]) or (args.glimpsed and not k["glimpsed"]) or (
                            args.wakes and not k["on_pickup"].get("dudes")):
                        continue
                    print(f"{name:<8} {k['name']:<7} sprite {k['sprite']} sector {k['sector']} way {k['way']} "
                          f"{k['stands']} guards {k['guards']} opens {k['opens']} lock way {k['lock_way']} "
                          f"taking it {k['on_pickup']}")
        return 0
    result = mine()
    OUTPUT.write_text(json.dumps(result, indent=1, sort_keys=False) + "\n", encoding="utf-8", newline="\n")
    for name, pop in result["populations"].items():
        print(f"{name}: {pop['maps']} maps, {pop['ordered_maps']} with a trusted order")
    print(f"wrote {OUTPUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
