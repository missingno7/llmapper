"""Make the city's openings pass the grammar's own audit.

`bloodmap.aperture` is adopted for the thirteen z-motion doors -- they
compile through `frame_z_doors`, which inserts the reveals.  What was never
done is the other half: running `aperture.audit` over the finished map and
acting on what it says.

The audit reads a built map, so a declaration cannot satisfy it; only the
geometry and the tiles can.  It reported **37 findings**, of two kinds:

* **26 lintels that do not continue their facade.**  The band above a mouth
  wore the material's *opening* tile rather than the room's wall.  Those are
  two different rules about two different surfaces and the project had
  applied one to both: the jamb rule (74% of campaign multi-tile rooms wear
  the opening tile on the sides of their own openings) is about the reveal,
  and the aperture grammar's is about the band above -- which 47% of Blood's
  apertures carry as plain continuing wall.  `continue_lintels` repaints
  exactly those walls and no others.

* **11 pinches wider than a door.**  Every one is a *seam*: two sky-ceilinged
  street regions meeting along a shared edge, or a light pool's rim.  The
  grammar wants such a leaf named (`full_height`), and naming is a
  declaration the audit cannot see -- there is nothing in the map to change.
  Filed as grammar request #15 rather than papered over: a full-height
  opening between two regions that already share a facade and a ceiling is
  not an aperture, and counting it as one hides the openings that are.
"""

from __future__ import annotations

import collections


def _rows(disk):
    from tools.mine_apertures import observe
    return [row for row in observe("candidate", disk) if row["aperture"]]


def seam(row) -> bool:
    """Two rooms that already agree: not an opening, a shared edge.

    Same facade tile on both sides and no lintel at all means nothing was
    pierced -- the regions simply meet.  Kept as a named predicate because
    it is the whole of the argument in grammar request #15.
    """
    return (row["lintel_player_heights"] <= 0
            and row["leaf_player_heights"] >= row["facade_player_heights"] - 0.01)


def continue_lintels(level, disk) -> dict:
    """Repaint every band above a mouth with the wall it interrupts.

    A two-sided wall's `picnum` is what Build draws on its **upper step** --
    the band between the top of the opening and the ceiling.  That is the
    lintel, and it is the only thing this touches: the masked middle
    (`over_picnum`) and the one-sided facade walls are left alone.
    """
    report = {"repainted": 0, "left": 0, "by_tile": {}}
    for row in _rows(disk):
        if row["lintel_player_heights"] <= 0 or row["lintel_continues_facade"]:
            continue
        want = int(row["facade_picnum"])
        fields = level.walls[int(row["wall"])]["fields"]
        if int(fields["picnum"]) == want:
            report["left"] += 1
            continue
        fields["picnum"] = want
        report["repainted"] += 1
        report["by_tile"][want] = report["by_tile"].get(want, 0) + 1
    return report


def report(disk) -> dict:
    """What the grammar still objects to, split by whether it is a seam."""
    from bloodmap.aperture import audit
    findings = audit(disk)
    rows = {(r["sector"], r["wall"]): r for r in _rows(disk)}
    kinds = collections.Counter()
    seams = 0
    for finding in findings:
        row = rows.get((finding["sector"], finding["wall"]))
        if row is not None and seam(row):
            seams += 1
            continue
        kinds[finding["kind"]] += 1
    return {"findings": len(findings), "seams": seams,
            "real": sum(kinds.values()), "by_kind": dict(kinds)}
