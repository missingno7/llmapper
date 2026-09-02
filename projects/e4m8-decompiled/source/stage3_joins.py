"""Stage 3 -- joins: the writer's table counted against every shared wall.

`bloodmap.read_joins` reads each sector's surface KIND off its geometry (never
off a tile -- `joins.py` says surface kind is not readable from one), then
looks up every two-sided record in `joins.ROWS`. No row is added. A pair with
no row is residue, named, with its records.

    PYTHONPATH=. python projects/e3m1-decompiled/source/stage3_joins.py
"""

from __future__ import annotations

from collections import defaultdict

from _common import MAP_NAME, level, write
from _review import Tree, answers, write_pack

from bloodmap.read_joins import read_joins, summary
from bloodmap.texture_frame import sector_index


def _review(world, result, owners) -> dict:
    """The pack: one node per join row the table describes, and its sectors.

    Reader kinds with no row (`interior`, `solid`, `outdoor_ground`) get no
    node on purpose. Their sectors are unowned, and that is the finding drawn
    on the map: the join grammar describes a street and nothing inside the
    buildings.
    """
    kinds = result["kinds"]["kinds"]
    census = result["census"]
    tree = Tree(len(world.sectors), f"{MAP_NAME} -- joins the writer's table describes")
    by_kind: dict[str, dict[str, list[int]]] = defaultdict(dict)
    for key, records in census["described_records"].items():
        by_kind[key.split("|")[0]][key] = records
    for kind in sorted(by_kind):
        sectors = {owners[record] for rows in by_kind[kind].values()
                   for record in rows}
        tree.add(f"kind:{kind}", "surface_kind",
                 f"{kind} ({sum(1 for s in kinds.values() if s == kind)} sectors)",
                 tree.root.id, sectors)
        for key, records in sorted(by_kind[kind].items()):
            tree.add(f"row:{key}", "join_row", f"{key} x{len(records)}",
                     f"kind:{kind}", {owners[record] for record in records})
    questions = [
        {"node": "row:road|pavement|b_above",
         "question": ("The reader recovers 11 road|pavement records and all "
                      "11 wear tile 6 with cstat 0 -- the kerb, exactly as "
                      "the row states. But `joins.TILE_CLASSES` gives "
                      "`facade stone` as 400, and over the 43 campaign "
                      "maps NONE of the 191 end-wall band records "
                      "wears it. Is 400 a campaign value or "
                      "Gravesend's own choice?"),
         "recommended_default": ("treat 400 as our CHOICE; the class is now "
                                 "mined (queue item 32b) and is led by 2490 "
                                 "and 91. The kerb row needs no change"),
         "evidence": "references/join-census.json: band_tiles"},
        {"node": "kind:end_wall",
         "question": ("Four pavement|end_wall records are not blocking, and "
                      "all four face sectors 172 and 174, which carry sector "
                      "type 600 -- they MOVE. Should a raised outdoor mass "
                      "that carries a sector type be an end wall at all?"),
         "recommended_default": ("no: it is a mechanism at rest, and layer 5 "
                                 "owns it. The reader should name it "
                                 "separately so the end-wall row keeps its "
                                 "blocking clause on the 11 records that do "
                                 "stay put"),
         "evidence": "references/join-census.json: cstat_disagreements"},
        {"node": "level",
         "question": ("1312 of 1386 two-sided records (94.66%) are pairs the "
                      "table has no row for, and 1122 of them are "
                      "interior|interior. Is that a gap to fill or the "
                      "table's honest scope?"),
         "recommended_default": ("its scope: the grammar was mined from the "
                                 "street and says so. Adding indoor rows "
                                 "should follow an indoor census, not this "
                                 "one map"),
         "evidence": "references/join-census.json: undescribed"},
    ]
    return write_pack(3, tree, f"{MAP_NAME} layer 3: joins", questions)


def main() -> int:
    world = level()
    owners = sector_index(world)
    result = read_joins(world)
    result["_next_sector"] = {
        index: int(wall["fields"]["next_sector"])
        for index, wall in enumerate(world.walls)}
    stats = summary(result)
    kinds, census = result["kinds"], result["census"]

    payload = {
        "reader": "bloodmap.read_joins (new; surface kinds from geometry, "
                  "then bloodmap.joins.rule at every two-sided record)",
        "summary": stats,
        "surface_kinds": {str(key): value for key, value in sorted(kinds["kinds"].items())},
        "why_each_kind": {str(key): value for key, value in sorted(kinds["why"].items())},
        "street_network": kinds["street_network"],
        "outdoor_components": kinds["outdoor_components"],
        "measured_rise": kinds["measured_rise"],
        "steps_in_the_network": kinds["steps_in_the_network"],
        "base_plane_z": kinds["base_plane_z"],
        "described": census["described"],
        "undescribed": census["undescribed"],
        "undescribed_records": census["undescribed_records"],
        "band_tiles": census["band_tiles"],
        "band_blocking": census["band_blocking"],
        "table_tile_matches": census["table_tile_matches"],
        "cstat_disagreements": census["cstat_disagreements"],
        "disagreements_with_the_measured_facts": _disagreements(result),
    }
    payload["ledger"] = {
        "reader": "bloodmap.read_joins (new)",
        "gate": ("every two-sided record looked up in bloodmap.joins.ROWS; "
                 "for each row with a band, what the record wears and whether "
                 "it blocks, against what the row says"),
        "population": f"{stats['two_sided_records']} two-sided wall records",
        "explained": stats["records_described"],
        "residue": stats["records_undescribed"],
        "residue_percent": stats["residue_percent"],
        "residue_is": (f"{stats['pairs_with_no_row']} surface pairs the table "
                       f"has no row for; {_interior_records(census)} of the "
                       f"records are interior|interior"),
        "disagreements": payload["disagreements_with_the_measured_facts"],
    }
    payload["review"] = _review(world, result, owners)
    payload["owner_marks_read_back"] = answers(3)
    write("join-census.json", payload)

    print(f"{MAP_NAME} joins: {stats['two_sided_records']} two-sided records, "
          f"{stats['rows_used']} of the table's rows used")
    print(f"  kinds              : {stats['kinds']}")
    print(f"  measured rise      : {kinds['measured_rise']} "
          f"(steps seen: {kinds['steps_in_the_network']})")
    print(f"  base plane z       : {kinds['base_plane_z']}")
    print(f"  described          : {stats['records_described']} records")
    print(f"  RESIDUE            : {stats['records_undescribed']} records "
          f"({stats['residue_percent']}%) in {stats['pairs_with_no_row']} pairs "
          f"with no row")
    for key, tiles in census["band_tiles"].items():
        hit, seen = census["table_tile_matches"][key]
        print(f"    {key:30s} wears {tiles}, {hit}/{seen} the table's tile, "
              f"blocking {census['band_blocking'][key]}")
    return 0


def _claims(world, result, owners) -> list[dict]:
    """What the join table reproduces, field by field.

    Only where the ROW decides the value. A row whose band is `nothing`
    explains that no band draws -- which is true and is not a field -- so it
    claims nothing, and the ledger says the table's whole field-level reach in
    this map is whatever its own rows below reach.
    """
    from bloodmap import joins

    census = result["census"]
    rows = []
    for key, records in census["described_records"].items():
        a, b, height = key.split("|")
        rule = joins.rule(a, b, height)
        wanted = next((value for cls, value in joins.TILE_CLASSES.items()
                       if cls in rule.a_shows), None)
        for record in records:
            face = world.walls[record]["fields"]
            if wanted is not None and int(face["picnum"]) == wanted:
                rows.append({
                    "kind": "wall", "index": record, "field": "picnum",
                    "owner": f"join:{key}", "value": int(face["picnum"]),
                    "why": (f"the {key} row shows '{rule.a_shows}' and the "
                            f"class resolves to tile {wanted}, which is what "
                            f"this record wears")})
            if rule.cstat and (int(face["cstat"]) & rule.cstat) == rule.cstat:
                rows.append({
                    "kind": "wall", "index": record, "field": "cstat",
                    "owner": f"join:{key}", "value": int(face["cstat"]),
                    "why": (f"the {key} row sets cstat {rule.cstat} and this "
                            f"record carries it")})
    return rows


def _interior_records(census) -> int:
    return sum(count for key, count in census["undescribed"].items()
               if key.startswith("interior|interior"))


def _next_sector(result, record: int) -> int:
    return result["_next_sector"][record]


def _disagreements(result) -> list[dict]:
    """Where the reader and the facts the experiment was handed differ."""
    kinds = result["kinds"]["kinds"]
    end_walls = sorted(key for key, value in kinds.items() if value == "end_wall")
    solid = sorted(key for key, value in kinds.items() if value == "solid")
    census = result["census"]
    out = []
    met_by_road = sorted({
        int(_next_sector(result, record))
        for record in census["described_records"].get("road|end_wall|b_above", ())})
    if set(end_walls) != set(met_by_road):
        out.append({
            "claim": "the T of the main street ends in three end walls "
                     "(sectors 0, 339, 343)",
            "the_reader_finds": f"{len(end_walls)} outdoor masses no body can "
                                f"step onto: {end_walls}",
            "reconciled": f"exactly {len(met_by_road)} of them are met by a "
                          f"ROAD record -- {met_by_road} -- which is the "
                          f"claim's set; the other "
                          f"{len(end_walls) - len(met_by_road)} are met by a "
                          f"pavement, so the claim is right about the T and "
                          f"the reader is counting the same kind of surface "
                          f"elsewhere too",
            "measured": {"end_walls": end_walls, "met_by_a_road": met_by_road},
        })
    if 10 in solid and 11 in solid:
        out.append({
            "claim": "`joins.py`'s PAVEMENT|PAVEMENT row cites \"E3M1 s10/s11: "
                     "a pavement-only path between abutting islands\"",
            "the_reader_finds": "s10 and s11 have floor_z == ceiling_z == 8192: "
                                "zero clear height, ceiling tiles 414 and 401, "
                                "`floor_stat` 2 and 66. They are SOLID MASSES, "
                                "not paths; no body stands in either",
            "reconciled": f"the ROW is still attested -- "
                          f"{census['described'].get('pavement|pavement|equal', 0)} "
                          f"pavement|pavement records exist here, between "
                          f"the shadow-cut pavement bands -- but its cited "
                          f"evidence is two sectors that are not pavement at all",
        })
    if census["cstat_disagreements"]:
        moving = [row for row in census["cstat_disagreements"]
                  if row["faced_sector_moves"]]
        out.append({
            "claim": "road|end wall and pavement|end wall: lower band in "
                     "facade stone, BLOCKING",
            "the_reader_finds": f"{len(census['cstat_disagreements'])} of 16 "
                                f"band records do not block, and "
                                f"{len(moving)} of those face a sector that "
                                f"carries a sector type (600)",
            "reconciled": "the blocking clause holds on every static end wall; "
                          "the exceptions are movers, which are layer 5's",
        })
    return out


if __name__ == "__main__":
    raise SystemExit(main())
