"""Stage 7 -- the plan: the solver's inverse, in plan units and nothing else.

Decisions section 20 calls this the acid test. `bloodmap.read_plan` recovers
the street graph with width classes, the islands with their bands and the
blocks with their envelopes, in `city_plan.py`'s language: no picnums, no z,
no Build units, one stated conversion.

    PYTHONPATH=. python projects/e3m1-decompiled/source/stage7_plan.py
"""

from __future__ import annotations

from _common import level, write
from _review import Tree, answers, write_pack

from bloodmap.read_joins import surface_kinds
from bloodmap.read_plan import PLAN_UNIT, WIDTH_CLASSES, read_plan, summary
from bloodmap.texture_frame import sector_index


def _review(world, plan) -> dict:
    tree = Tree(len(world.sectors), "E3M1 -- the plan")
    tree.add("streets", "plan", f"the street graph ({len(plan['edges'])} edges, "
             f"{len(plan['junctions'])} junctions)", tree.root.id,
             [index for run in plan["corridors"] for index in run["sectors"]])
    for run in plan["corridors"]:
        tree.add(run["corridor_id"], run["role"],
                 f"{run['corridor_id']} {run['role']} "
                 f"{run['carriageway_class']['nearest']} "
                 f"({run['carriageway_pu']} pu carriageway, "
                 f"{run['full_width_pu']} full)",
                 "streets", run["sectors"])
    tree.add("islands", "plan", f"islands with bands ({len(plan['islands'])})",
             tree.root.id,
             [index for row in plan["islands"] for index in row["sectors"]])
    for row in plan["islands"]:
        tree.add(f"plan:{row['island']}", "island",
                 f"{row['island']} bands {row['band_pu']} pu", "islands",
                 row["sectors"])
    tree.add("blocks", "plan", f"blocks with envelopes ({len(plan['blocks'])})",
             tree.root.id,
             [index for block in plan["blocks"] for index in block["sectors"]])
    for block in plan["blocks"][:12]:
        tree.add(block["block_id"], "block",
                 f"{block['block_id']} envelope {block['envelope_pu']} pu",
                 "blocks", block["sectors"])
    fill = plan["rectangular_fill"]
    questions = [
        {"node": "streets",
         "question": (f"A street has a CARRIAGEWAY and a FULL WIDTH and they "
                      f"land in different classes: E3M1's main street is "
                      f"{plan['corridors'][0]['carriageway_pu']} pu of "
                      f"carriageway ("
                      f"{plan['corridors'][0]['carriageway_class']['nearest']}) "
                      f"and {plan['corridors'][0]['full_width_pu']} with its "
                      f"pavements ("
                      f"{plan['corridors'][0]['full_width_class']['nearest']}). "
                      f"Which does `city_plan`'s width class mean?"),
         "recommended_default": ("the FULL width: the plan's grid is a running "
                                 "sum of street widths and block columns, and "
                                 "a pavement is part of the street rather "
                                 "than of the block. State it in city_plan.py; "
                                 "the reader gives both until it is stated"),
         "evidence": "references/plan.json: corridors"},
        {"node": "blocks",
         "question": (f"The reader recovers {len(plan['blocks'])} blocks by "
                      f"connectivity of everything that is not ground. The "
                      f"largest holds {len(plan['blocks'][0]['sectors'])} "
                      f"sectors, which is a whole side of the city rather "
                      f"than one building. Is a block a connected mass, or "
                      f"something smaller the reader cannot yet see?"),
         "recommended_default": ("smaller: a block in `city_plan` is one "
                                 "buildable rectangle and E3M1's masses run "
                                 "together through their interiors. The "
                                 "reader should cut a mass at its street "
                                 "frontages -- that is layer 7's next "
                                 "measurement, and it is named as missing "
                                 "rather than guessed"),
         "evidence": "references/plan.json: blocks"},
        {"node": "level",
         "question": (f"Every plan element is a RECT and a sector is not. "
                      f"E3M1's ground fills its own bounding rectangles "
                      f"{fill['median']:.0%} of the time at the median and "
                      f"{fill['worst']:.0%} at the worst. How much of that "
                      f"loss is the schematic allowed?"),
         "recommended_default": ("state it rather than bound it: the plan is "
                                 "schematic by contract, and the fill is the "
                                 "honest measure of what the schematic drops. "
                                 "The solver's own output should carry the "
                                 "same number so the two can be compared"),
         "evidence": "references/plan.json: rectangular_fill"},
    ]
    return write_pack(7, tree, "E3M1 layer 7: the plan", questions)


def main() -> int:
    world = level()
    owners = sector_index(world)
    kinds = surface_kinds(world, owners=owners)["kinds"]
    plan = read_plan(world, kinds, owners=owners)
    stats = summary(plan)

    payload = {
        "reader": "bloodmap.read_plan (new; the solver's inverse)",
        "summary": stats,
        "plan_unit_build": PLAN_UNIT,
        "width_classes_pu": WIDTH_CLASSES,
        "corridors": plan["corridors"],
        "edges": plan["edges"],
        "junctions": [row["corridor_id"] for row in plan["junctions"]],
        "islands": plan["islands"],
        "blocks": plan["blocks"],
        "candidates": plan["candidates"],
        "rectangular_fill": plan["rectangular_fill"],
        "residue_sectors": plan["residue_sectors"],
        "ledger": {
            "reader": "bloodmap.read_plan (new)",
            "gate": ("every ground sector assigned to a street, an island or "
                     "an area, and every extent stated in plan units with the "
                     "nearest width class and its residual"),
            "population": f"{len(plan['ground_sectors'])} ground sectors",
            "explained": len(plan["ground_sectors"]) - len(plan["residue_sectors"]),
            "residue": len(plan["residue_sectors"]),
            "residue_percent": stats["residue_percent"],
            "residue_is": "ground on no street, island or area",
            "disagreements": [],
        },
    }
    payload["review"] = _review(world, plan)
    payload["owner_marks_read_back"] = answers(7)
    write("plan.json", payload)

    print(f"E3M1 plan, 1 pu = {PLAN_UNIT} Build units")
    for run in plan["corridors"]:
        print(f"    {run['corridor_id']} {run['role']:8s} sectors "
              f"{run['sectors']} ratio {run['ratio']:5.2f}  carriageway "
              f"{run['carriageway_pu']:5.2f} pu "
              f"({run['carriageway_class']['nearest']}), full "
              f"{run['full_width_pu']:5.2f} pu "
              f"({run['full_width_class']['nearest']}), length "
              f"{run['length_pu']} pu")
    for row in plan["islands"]:
        print(f"    {row['island']} sectors {row['sectors']} bands "
              f"{row['band_pu']} pu")
    print(f"  blocks             : {len(plan['blocks'])}, largest envelope "
          f"{plan['blocks'][0]['envelope_pu']} pu over "
          f"{len(plan['blocks'][0]['sectors'])} sectors")
    print(f"  rectangular fill   : median {plan['rectangular_fill']['median']}, "
          f"worst {plan['rectangular_fill']['worst']}")
    print(f"  candidates         : {plan['candidates']}")
    print(f"  RESIDUE            : {plan['residue_sectors']} "
          f"({stats['residue_percent']}%)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
