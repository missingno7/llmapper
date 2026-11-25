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
    from bloodmap.aperture import observe_openings
    return [row for row in observe_openings("candidate", disk)
            if row["aperture"]]


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
    report = {"repainted": 0, "left": 0, "by_tile": {}, "fixed": 0}
    for row in _rows(disk):
        if row["lintel_player_heights"] <= 0 or row["lintel_continues_facade"]:
            continue
        record = level.walls[int(row["wall"])]
        if isinstance(record, dict) and record.get("fixed_texture_frame"):
            # a wall painted with its own frame (`paint_wall(fixed_frame=
            # True)`): a fall of water whose tile is also its band
            report["fixed"] += 1
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


#: leaves of wood, and what a doorway they close is made of all through: the campaign's sills, jambs and heads under wooden
#: doors are planks (20 and 68 lead both lists over its 192 doorways to the open; E1M1 s59, s90; E1M3 s135's whole frame)
WOODEN_LEAVES = frozenset(range(22, 28)) | {30}
WOOD, STONE, STONE_FRONTS = 20, 253, {110}


def neutral(level) -> dict:
    """No doorway to the open wears the room behind it: from the street to the room side of the leaf it is one frame.

    The owner, 2026-11-25: "some door around city has floor and ceiling in door
    aperature area from the room inside, so from the outside it looks bad, I
    would give it some neutral textures or something". A leaf sector and the
    reveal behind it took their room's floor (carpet, chequers) and ceiling
    (office tiles), and every reveal's jambs were the crumbling plaster. A
    doorway is read here as it is walked: from a leaf through whatever is
    roofed and no deeper than a wall, both ways, to the street and to the room.
    A shopfront's reveal before its glass is the same thing without a leaf.
    """
    sectors = [s["fields"] if isinstance(s, dict) else s.fields for s in level.sectors]
    walls = [w["fields"] if isinstance(w, dict) else w.fields for w in level.walls]

    def ring(i):
        s = sectors[i]
        return range(int(s["wall_ptr"]), int(s["wall_ptr"]) + int(s["wall_count"]))

    def sky(i):
        return bool(int(sectors[i]["ceiling_stat"]) & 1)

    def depth(i):
        xs = [int(walls[w]["x"]) for w in ring(i)]
        ys = [int(walls[w]["y"]) for w in ring(i)]
        return min(max(xs) - min(xs), max(ys) - min(ys))

    def beyond(i):
        return {int(walls[w]["next_sector"]) for w in ring(i) if int(walls[w]["next_sector"]) >= 0}

    def glazed(i):
        return any(int(walls[w]["cstat"]) & 16 for w in ring(i))

    doorways, done = [], set()
    for i, s in enumerate(sectors):
        if int(s["type"]) != 600:
            continue
        faces = {int(walls[int(walls[w]["next_wall"])]["picnum"]) for w in ring(i) if int(walls[w]["next_wall"]) >= 0}
        if not faces & WOODEN_LEAVES:
            continue
        parts, open_air = {i}, False
        for first in beyond(i):
            chain, at, came, out = [], first, i, False
            while True:
                if sky(at):
                    out = True
                    break
                on = beyond(at) - {came}
                if depth(at) > 1126 or len(chain) > 4 or not on or (len(on) != 1 and not all(sky(n) for n in on)):
                    break
                chain.append(at)
                came, at = at, next(iter(on))
            # the street's side all the way; the room's, the reveal the leaf closes against and no more
            parts.update(chain if out else [n for n in chain[:1] if depth(n) <= 320])
            open_air |= out
        if open_air:
            doorways.append((parts, {int(sectors[n]["floor_picnum"]) for p in parts for n in beyond(p) if sky(n)}))
    report = {"doorways": len(doorways), "sectors": 0, "shopfronts": 0}
    for parts, _streets in doorways:
        stone = any(int(sectors[p]["floor_picnum"]) in STONE_FRONTS for p in parts)
        tile = 110 if stone else WOOD
        for p in parts:
            sectors[p]["floor_picnum"] = sectors[p]["ceiling_picnum"] = tile
            for key in ("floor_x_panning", "floor_y_panning", "ceiling_x_panning", "ceiling_y_panning"):
                sectors[p][key] = 0
            for w in ring(p):
                f = walls[w]
                if int(f["next_sector"]) < 0:
                    n = walls[int(f["point2"])]
                    length = abs(int(n["x"]) - int(f["x"])) + abs(int(n["y"]) - int(f["y"]))
                    f["picnum"], f["x_panning"], f["y_panning"] = tile, 0, 0
                    f["x_repeat"], f["y_repeat"] = max(1, round(length / 128)), 8
                elif int(f["next_sector"]) in parts and int(sectors[int(f["next_sector"])]["type"]) != 600:
                    # the head over the leaf, where the way to it is taller than it is
                    f["picnum"], f["x_panning"], f["y_panning"] = tile, 0, 0
            done.add(p)
    report["sectors"] = len(done)
    # the strip of sill and soffit before a shop's glass
    for i, s in enumerate(sectors):
        if sky(i) or i in done or depth(i) > 320 or glazed(i) or int(s["type"]):
            continue
        near = beyond(i)
        if not any(sky(n) for n in near) or not any(not sky(n) and glazed(n) and depth(n) <= 320 for n in near):
            continue
        jambs = collections.Counter(int(walls[w]["picnum"]) for w in ring(i) if int(walls[w]["next_sector"]) < 0)
        wooden = any(t in (20, 28, 68, 84, 88) for t in jambs)
        s["floor_picnum"] = s["ceiling_picnum"] = WOOD if wooden else STONE
        report["shopfronts"] += 1
    # a barred or glazed window's own sill and head, where they were the room's wall
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
