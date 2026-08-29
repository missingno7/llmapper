"""How Blood stacks storeys, measured on the maps that do most of it.

.. code-block:: bash

    python -m tools.mine_storeys BB4 BB9 E6M1 E3M1 E4M2

BB4 is the worked example: 71 sectors, and 41% of them take part in an overlap.
It does nothing clever -- no one-way walls, no disconnected components. Its
safety comes from two ordinary properties, and this measures both so a
constructor can default to them:

* the storeys sit in different height bands, so `updatesectorz_compat`'s z-aware
  fallback (build/src/engine.cpp:13454, via `inside_z_p` at build.h:1733) never
  picks the wrong one;
* the stairs between them put several portal hops and a solid floor between any
  overlapping pair, so no viewpoint reaches both.

What is measured, per map: where the storey floors sit and how far apart, how
much of the plan the storeys share, the shape of the runs that connect them, and
how the outer shell relates to the stacked core. Running it over several maps is
the point -- it separates BB4's choices from the convention.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from bloodmap import overlap_visibility as ov
from bloodmap.format import read_map

#: One standing Blood human. `bloodmap.player_space`.
PH = 16960

#: A storey band is where floors cluster; anything within this of each other is
#: the same storey. Half a body: smaller than any floor-to-floor in the corpus
#: and larger than a step.
BAND_TOLERANCE = 8192

#: What counts as a step rather than a storey, in Build units.
#:
#: NOT the player's 4096-unit maximum step-up, which is what this was set to
#: first and it hid the answer: BB4 joins its storeys with fourteen portals of
#: exactly 6144, and a 4096 filter reported that the map with the clearest
#: stacking in the corpus contains no stairs at all. Half a body is the honest
#: line -- above it the two floors are different storeys, below it they are one
#: run, whether or not a body can climb each riser unaided.
STEP_MAX = 8192


def polygon_area(loop: list[tuple[int, int]]) -> float:
    total = 0
    for index, (x1, y1) in enumerate(loop):
        x2, y2 = loop[(index + 1) % len(loop)]
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def sector_area(disk, sector_id: int) -> float:
    loops = ov.sector_loops(disk, sector_id)
    if not loops:
        return 0.0
    return polygon_area(loops[0]) - sum(polygon_area(l) for l in loops[1:])


def storey_bands(disk, sectors: list[int]) -> list[dict]:
    """Where the floors cluster, weighted by how much floor is at each height."""
    by_floor: dict[int, float] = collections.defaultdict(float)
    for sector_id in sectors:
        floor = int(disk.sectors[sector_id].fields["floor_z"])
        by_floor[floor] += sector_area(disk, sector_id)

    bands: list[dict] = []
    for floor in sorted(by_floor):
        if bands and floor - bands[-1]["floor_z"] <= BAND_TOLERANCE:
            band = bands[-1]
            band["area"] += by_floor[floor]
            band["members"].append(floor)
            continue
        bands.append({"floor_z": floor, "area": by_floor[floor],
                      "members": [floor]})
    total = sum(b["area"] for b in bands) or 1.0
    for band in bands:
        band["share"] = round(band["area"] / total, 4)
        band["floor_bodies"] = round(band["floor_z"] / PH, 2)
    return bands


def storey_runs(disk) -> list[dict]:
    """Chains of sectors whose floors climb in steps a body can take.

    A stair is not a sector type in Build, so it is recovered: neighbours whose
    floors differ by no more than the player's maximum step, walked while the
    sign of the change stays the same. The turn is the angle between the first
    and last step's direction of travel, which is what says whether the run is
    straight or doubles back.
    """
    forward, _backward = ov.flood_graph(disk)
    floors = [int(s.fields["floor_z"]) for s in disk.sectors]
    centres = []
    for index in range(len(disk.sectors)):
        loops = ov.sector_loops(disk, index)
        if not loops:
            centres.append(None)
            continue
        xs = [p[0] for p in loops[0]]
        ys = [p[1] for p in loops[0]]
        centres.append((sum(xs) / len(xs), sum(ys) / len(ys)))

    used: set[int] = set()
    runs: list[dict] = []
    for start in range(len(disk.sectors)):
        if start in used or centres[start] is None:
            continue
        for first in forward[start]:
            rise = floors[first] - floors[start]
            if rise == 0 or abs(rise) > STEP_MAX:
                continue
            chain = [start, first]
            while True:
                here = chain[-1]
                nxt = [n for n in forward[here]
                       if n not in chain and centres[n] is not None
                       and 0 < abs(floors[n] - floors[here]) <= STEP_MAX
                       and (floors[n] - floors[here]) * rise > 0]
                if len(nxt) != 1:
                    break
                chain.append(nxt[0])
            # Two steps is a stoop, three is a stair. BB4's connecting runs are
            # short, and a filter tuned on E3M1's long flights reported that the
            # map with the clearest stacking has no stairs at all.
            if len(chain) < 3:
                continue
            if any(s in used for s in chain[1:-1]):
                continue
            used.update(chain[1:-1])
            steps = [floors[chain[i + 1]] - floors[chain[i]]
                     for i in range(len(chain) - 1)]
            legs = [
                math.degrees(math.atan2(centres[chain[i + 1]][1] - centres[chain[i]][1],
                                        centres[chain[i + 1]][0] - centres[chain[i]][0]))
                for i in range(len(chain) - 1)
            ]
            turn = (legs[-1] - legs[0] + 180) % 360 - 180
            span = math.hypot(centres[chain[-1]][0] - centres[chain[0]][0],
                              centres[chain[-1]][1] - centres[chain[0]][1])
            runs.append({
                "sectors": chain,
                "steps": len(chain) - 1,
                "total_rise": sum(steps),
                "total_rise_bodies": round(abs(sum(steps)) / PH, 2),
                "step_rise": collections.Counter(steps).most_common(1)[0][0],
                "run_units": round(span),
                "tread": round(span / max(1, len(chain) - 1)),
                "turn_degrees": round(turn),
            })
            break
    return runs


def plan_share(disk, verdicts: list) -> dict:
    """How much of a lower storey the one above it actually covers."""
    shares = []
    for verdict in verdicts:
        left, right = verdict.sectors
        upper, lower = ((left, right)
                        if int(disk.sectors[left].fields["floor_z"])
                        < int(disk.sectors[right].fields["floor_z"])
                        else (right, left))
        low_area = sector_area(disk, lower)
        if low_area <= 0:
            continue
        shares.append(min(1.0, sector_area(disk, upper) / low_area))
    shares.sort()
    if not shares:
        return {}
    return {
        "n": len(shares),
        "q1": round(shares[len(shares) // 4], 2),
        "median": round(shares[len(shares) // 2], 2),
        "q3": round(shares[3 * len(shares) // 4], 2),
    }


def shell_of(disk, sectors: set[int]) -> dict | None:
    """The biggest sector that contains stacked ones -- the yard or the outer hall.

    BB4's storeys sit inside a shared outer shell rather than standing free, and
    whether that is a convention or one map's choice is exactly what running this
    over several maps answers.
    """
    best = None
    for index in range(len(disk.sectors)):
        if index in sectors:
            continue
        area = sector_area(disk, index)
        if area <= 0:
            continue
        loops = ov.sector_loops(disk, index)
        if not loops:
            continue
        # Point-in-polygon, not bounding box. A bbox test made BB4's shell come
        # out as the water link's partner room, parked 171 bodies down in free
        # map space, whose box swallows everything.
        from bloodmap.planar_geom import point_in_loops

        outline = [loops[0]]
        held = 0
        for other in sectors:
            other_loops = ov.sector_loops(disk, other)
            if not other_loops:
                continue
            oxs = [p[0] for p in other_loops[0]]
            oys = [p[1] for p in other_loops[0]]
            centre = (sum(oxs) // len(oxs), sum(oys) // len(oys))
            if point_in_loops(centre, outline) == 1:
                held += 1
        if held and (best is None or held > best["holds"]):
            fields = disk.sectors[index].fields
            best = {
                "sector": index, "holds": held,
                "floor_bodies": round(int(fields["floor_z"]) / PH, 2),
                "clear_bodies": round(
                    (int(fields["floor_z"]) - int(fields["ceiling_z"])) / PH, 2),
                "parallax": bool(int(fields["ceiling_stat"]) & 1),
            }
    return best


def measure(name: str, disk) -> dict:
    verdicts = ov.audit(disk)
    involved = sorted({s for v in verdicts for s in v.sectors})
    runs = storey_runs(disk)
    bands = storey_bands(disk, involved) if involved else []
    floor_to_floor = [bands[i + 1]["floor_z"] - bands[i]["floor_z"]
                      for i in range(len(bands) - 1)]
    hops = []
    forward, _ = ov.flood_graph(disk)
    undirected = [set(s) for s in forward]
    for index, neighbours in enumerate(forward):
        for other in neighbours:
            undirected[other].add(index)
    for verdict in verdicts:
        left, right = verdict.sectors
        seen = {left}
        frontier = collections.deque([(left, 0)])
        found = None
        while frontier and found is None:
            node, depth = frontier.popleft()
            if depth >= 24:
                continue
            for other in undirected[node]:
                if other == right:
                    found = depth + 1
                    break
                if other not in seen:
                    seen.add(other)
                    frontier.append((other, depth + 1))
        hops.append(found)
    joined = sorted(h for h in hops if h is not None)
    return {
        "map": name,
        "sectors": len(disk.sectors),
        "overlapping_pairs": len(verdicts),
        "sectors_involved": len(involved),
        "share_of_map": round(len(involved) / max(1, len(disk.sectors)), 3),
        "by_cut": dict(collections.Counter(v.cut for v in verdicts)),
        "storey_bands": [
            {k: b[k] for k in ("floor_z", "floor_bodies", "share")} for b in bands],
        "floor_to_floor": floor_to_floor,
        "floor_to_floor_bodies": [round(f / PH, 2) for f in floor_to_floor],
        "plan_share": plan_share(disk, verdicts),
        "hops": ({"min": joined[0], "q1": joined[len(joined) // 4],
                  "median": joined[len(joined) // 2],
                  "q3": joined[3 * len(joined) // 4], "max": joined[-1],
                  "unjoined": len(hops) - len(joined)} if joined else {}),
        "runs": runs,
        "shell": shell_of(disk, set(involved)) if involved else None,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("maps", nargs="*", default=["BB4"])
    parser.add_argument("-o", "--out",
                        default="knowledge/blood/design/storeys-v1.json")
    args = parser.parse_args(argv)

    root = pathlib.Path(__file__).resolve().parent.parent
    rows = []
    for name in args.maps:
        path = root / "maps" / "blood" / f"{name}.MAP"
        if not path.exists():
            print(f"no such map: {name}")
            continue
        row = measure(name, read_map(str(path)))
        rows.append(row)
        print(f"\n=== {name}: {row['sectors']} sectors, "
              f"{row['overlapping_pairs']} overlapping pairs across "
              f"{row['sectors_involved']} sectors ({row['share_of_map']:.0%})")
        print("   cuts:", row["by_cut"])
        print("   storey floors (bodies):",
              [b["floor_bodies"] for b in row["storey_bands"]])
        print("   floor to floor (bodies):", row["floor_to_floor_bodies"])
        print("   plan share upper/lower:", row["plan_share"])
        print("   hops between overlapping pairs:", row["hops"])
        if row["shell"]:
            print("   outer shell:", row["shell"])
        for run in row["runs"][:4]:
            print(f"   run: {run['steps']} steps of {run['step_rise']}, "
                  f"rise {run['total_rise_bodies']} bodies, tread {run['tread']}, "
                  f"turn {run['turn_degrees']} deg")

    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({
        "$schema": "llmapper.blood-storeys", "schema_version": 1,
        "reading_guide": [
            "a storey band is where floor heights cluster, weighted by floor area",
            "plan share is the upper sector's area over the lower's, capped at 1",
            "a run is a chain of neighbours each within one player step of the last",
            "turn is the angle between the first and last step's direction",
        ],
        "maps": rows,
    }, indent=1) + "\n", encoding="utf-8")
    print("\nwrote " + str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
