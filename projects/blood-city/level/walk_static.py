"""A route read off the map, and looked at -- NOT a walk.

    python projects/blood-city/level/walk_static.py --to belfry -o experiments/church-skyline/route

Nothing here moves a player.  It answers a narrower question honestly:

* does `bloodmap.conditional` find a way from the player start to a named
  place, and which mechanisms have to be worked on the way (a sector chain
  through openings a standing body fits, doors counted as actions);
* what does the observer paint from a standing eye in each sector of that
  chain, facing the next one.

What it cannot say, and what only a running game can: whether the body's
clip radius fits every corner, whether a door actually answers Use, whether a
step is climbable at speed, whether anything is in the way.  The output says
so in its own `claims` block, the way BloodForge's reports do, so a frame
strip from this tool is never mistaken for a play record.

The project rule stands: Blood City does not launch NBlood (handoff.md,
"Standing disciplines").
"""

from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import sys
from collections import deque

ROOT = pathlib.Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))

from bloodmap import conditional
from bloodmap.format import read_map
from bloodmap.viewplan import angle_toward, eye_z, interior_point
from bloodmap.visual import ObservationRequest, Viewpoint, run_observation

PROJECT = pathlib.Path(__file__).resolve().parents[1]
PU = 1024

#: Places a route can be asked for, in plan units.
PLACES = {
    "nave": (29.4, 27.0),
    "chancel": (29.4, 23.3),
    "tower": (31.0, 23.3),
    "belfry": (32.9, 22.9),
    "narthex": (31.2, 28.6),
    "cemetery": (23.9, 30.0),
    "avenue_at_church": (35.5, 28.7),
}


def sector_at_grade(level, x: int, y: int) -> int | None:
    """The sector at a point whose floor is nearest street level.

    The sewer runs under the avenue, so a point in plan can lie in two
    sectors; a plain point query returns the first and a route to "the belfry"
    was once answered with a route to the drain beneath it.
    """
    from bloodmap.viewpoints import _contains
    from resolution import GRADE
    hits = [index for index in range(len(level.sectors))
            if _contains(level, index, x, y)]
    if not hits:
        return None
    def floor(index):
        sector = level.sectors[index]
        fields = sector["fields"] if isinstance(sector, dict) else sector.fields
        return int(fields["floor_z"])
    return min(hits, key=lambda index: abs(floor(index) - GRADE))


def _graph_under(graph, held) -> dict[int, set[int]]:
    """The directed sector graph `ConditionalGraph.reachable` floods."""
    out = {sector: set(n) for sector, n in graph.base.items()}
    held = conditional.Held(frozenset(held.channels | graph.fired_at_start),
                            held.keys, held.operated)
    for edge in graph.edges:
        if conditional._edge_enabled(edge, held):
            out.setdefault(edge.sectors[0], set()).add(edge.sectors[1])
    return out


def _path(adjacency, start: int, goal: int) -> list[int] | None:
    seen = {start: None}
    queue = deque([start])
    while queue:
        here = queue.popleft()
        if here == goal:
            out = []
            while here is not None:
                out.append(here)
                here = seen[here]
            return out[::-1]
        for there in sorted(adjacency.get(here, ())):
            if there not in seen:
                seen[there] = here
                queue.append(there)
    return None


def route(disk, level, place: str) -> dict:
    x, y = (int(v * PU) for v in PLACES[place])
    goal = sector_at_grade(level, x, y)
    graph = conditional.build_graph(disk)
    rest = graph.at_rest()
    at_rest = graph.reachable(rest)
    # Work every mechanism a body can reach, a round at a time, and remember
    # which ones were needed before the goal came within reach.
    held, actions, reached = rest, [], at_rest
    while goal not in reached:
        todo = [a for a in graph.available_actions(held, reached)]
        if not todo:
            break
        before = len(reached)
        for action in todo:
            held = held.with_action(action)
            actions.append(action)
        reached = graph.reachable(held)
        if len(reached) == before:
            break
    path = _path(_graph_under(graph, held), graph.start, goal) \
        if goal in reached else None
    gated = {edge.sectors: edge for edge in graph.edges}
    on_path = []
    if path:
        for a, b in zip(path, path[1:]):
            edge = gated.get((a, b))
            if edge is not None:
                on_path.append({"from": a, "to": b,
                                "mechanism": f"{edge.mechanism_kind} {edge.mechanism}",
                                "verdict": edge.verdict})
    return {
        "place": place, "at": [x, y], "goal_sector": goal,
        "start_sector": graph.start,
        "reachable_at_rest": goal in at_rest,
        "reachable_after_working_mechanisms": goal in reached,
        "reachable_if_everything_worked":
            goal in graph.reachable(graph.everything_worked()),
        "sectors_at_rest": len(at_rest),
        "sectors_everything_worked":
            len(graph.reachable(graph.everything_worked())),
        "sector_path": path,
        "mechanisms_on_path": on_path,
        "actions_taken_first": [a.describes() for a in actions],
        "base": graph.summary.get("base"),
    }


def storyboard(level, path: list[int]) -> list[Viewpoint]:
    """A standing eye in each sector of the chain, facing the next."""
    points = [interior_point(level, sector) for sector in path]
    views = []
    for index, (sector, point) in enumerate(zip(path, points)):
        z = eye_z(level, sector)
        ahead = next((p for p in points[index + 1:] if p and p != point), None)
        if point is None or z is None or ahead is None:
            continue
        views.append(Viewpoint(
            view_id=f"step_{index:02d}_s{sector}", x=point[0], y=point[1], z=z,
            angle=int(angle_toward(point, ahead)) & 2047, horiz=100,
            sector=sector, node=f"sector:{sector}", purpose="route",
            screenshot=True, note=f"route sector {index} of {len(path)}"))
    return views


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--map", default=str(PROJECT / "level" / "blood-city-current.MAP"))
    parser.add_argument("--to", action="append", default=[])
    parser.add_argument("--render", default=None,
                        help="which --to place gets the frame strip")
    parser.add_argument("-o", "--out", required=True)
    args = parser.parse_args(argv)
    map_path = pathlib.Path(args.map)
    disk = read_map(map_path)
    level = disk.to_level_ir()
    out_dir = pathlib.Path(args.out)
    if not out_dir.is_absolute():
        out_dir = PROJECT / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    places = args.to or sorted(PLACES)
    result = {
        "$schema": "llmapper.static-route",
        "schema_version": 1,
        "map": map_path.name,
        "map_sha256": hashlib.sha256(map_path.read_bytes()).hexdigest(),
        "claims": {
            "a_player_was_moved": False,
            "the_engine_was_run": False,
            "collision_was_tested": False,
            "doors_were_operated": False,
            "a_sector_chain_exists_in_the_map": True,
            "frames_are_what_a_standing_eye_would_see": True,
        },
        "routes": [route(disk, level, place) for place in places],
    }
    render = args.render or (places[0] if len(places) == 1 else None)
    if render:
        chosen = next(r for r in result["routes"] if r["place"] == render)
        if chosen["sector_path"]:
            views = storyboard(level, chosen["sector_path"])
            run_observation(ObservationRequest(
                map_path=map_path, output_dir=out_dir,
                resource_dir=pathlib.Path("reference/blood"), viewpoints=views,
                width=640, height=480, screenshots=[v.view_id for v in views],
                brightness=0, rff=None))
            result["storyboard"] = [v.view_id for v in views]
    (out_dir / "static-route.json").write_text(
        json.dumps(result, indent=2) + "\n", "utf-8")
    for r in result["routes"]:
        print(f"{r['place']:18s} sector {r['goal_sector']}: at rest "
              f"{r['reachable_at_rest']}, after mechanisms "
              f"{r['reachable_after_working_mechanisms']}, path "
              f"{len(r['sector_path'] or [])} sectors, gates on it "
              f"{[m['mechanism'] for m in r['mechanisms_on_path']]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
