"""What Blood makes solid is solid: the last word on every thing's two bits, what stops a body and what stops a bullet.

The owner, 2026-11-25: "Check if there are no other sprites that supposed to be blocking and
are not, like lamps and other stuff". `tools.mine_solidity` counts the two bits by tile and by
how it stands; where eight or more of Blood's agree, four in five, the city's agree with them.
Only ever more solid: nothing of the city's that stops a body is made to let it through. A
body on the ground is let be (two in three of Blood's block, and one trips on them), and so is
what lies flat.
"""

from __future__ import annotations

from collections import Counter

def apply(disk) -> dict:
    """Set the bits; what was set, by tile."""
    import json
    from bloodmap.model import record_fields
    from tools import mine_solidity as S
    table = json.loads(S.DATA.read_text("utf-8"))["tiles"]
    made: dict[str, Counter] = {"body": Counter(), "bullet": Counter()}
    for row in S.faults(disk, table):
        f = record_fields(disk.sprites[row["sprite"]])
        for what in row["lacks"]:
            f["cstat"] = int(f["cstat"]) | {"body": 1, "bullet": 256}[what]
            made[what][row["tile"]] += 1
    return {what: dict(sorted(rows.items())) for what, rows in made.items()}
