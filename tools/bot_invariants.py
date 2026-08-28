#!/usr/bin/env python3
"""Check a bot run's telemetry against the invariants the bot claims to hold.

These are not quality measures.  Each one asserts that the bot's *record of
what happened* is honest: that an accepted activation is never later called a
failure, that a crossing is filed against the boundary actually crossed, that
progress means progress.  A run may legitimately fail its objective and still
satisfy every invariant here; a run that violates one has corrupted its own
model of the level, whatever the outcome says.

usage: bot_invariants.py <telemetry.ndjson> [--map path/to/level.map] [--quiet]
"""
import argparse
import json
import re
import sys
from pathlib import Path


def load(path):
    rows = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if row.get("type") == "event":
            row["fields"] = dict(re.findall(r"(\w+)=(-?[\w().,]+)", row.get("detail") or ""))
            rows.append(row)
    return rows


def field(row, name, default=None):
    value = row["fields"].get(name, default)
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return value


class Report:
    def __init__(self):
        self.results = []

    def check(self, name, failures, note=""):
        self.results.append((name, list(failures), note))

    def ok(self):
        return all(not f for _, f, _ in self.results)

    def render(self, quiet):
        for name, failures, note in self.results:
            if failures:
                print("FAIL %s  (%d)" % (name, len(failures)))
                for line in failures[:6]:
                    print("       %s" % line)
                if len(failures) > 6:
                    print("       ... and %d more" % (len(failures) - 6))
            elif not quiet:
                print("ok   %s%s" % (name, ("  " + note) if note else ""))


# --- the invariants ------------------------------------------------------


def accepted_activation_is_never_called_unanswered(rows, report):
    accepted = set()
    failures = []
    for row in rows:
        if row["event"] == "interaction_engine_resolved" and field(row, "accepted") == 1:
            accepted.add(field(row, "id"))
        if row["event"] == "interaction_failed" and "NO_RESPONSE" in (row.get("detail") or ""):
            door = field(row, "door")
            failures.append("%ds door=%s was accepted earlier" % (row.get("game_time"), door))
    # Any NO_RESPONSE at all is suspect once something was accepted on the run.
    report.check("accepted_interaction_is_not_later_reported_no_response",
                 failures if accepted else [])


def answered_mechanism_is_not_retriggered(rows, report):
    """A mechanism the world answered is not pressed again while its effect
    stands.  Re-pressing a reversible mechanism undoes what it just did."""
    answered = {}
    failures = []
    for row in rows:
        event = row["event"]
        moment = row.get("game_time", 0)
        if event == "interaction_world_delta":
            answered[field(row, "id")] = moment
        elif event in ("interaction_rearmed", "boundary_closed"):
            answered.clear()
        elif event == "interaction_started":
            identity = field(row, "id")
            since = answered.get(identity)
            if since is not None and moment - since < 60:
                failures.append("%ds id=%s re-pressed %ds after its effect"
                                % (moment, identity, moment - since))
                answered.pop(identity, None)
    report.check("accepted_answered_mechanism_is_not_retriggered", failures)


def one_world_delta_per_activation(rows, report):
    """A burst of shots at one wall is one activation, not one per projectile.
    Pressing the same switch again later is a new activation and may report a
    new delta; what must not happen is the same activation reporting several."""
    pending = {}
    failures = []
    for row in rows:
        identity = field(row, "id")
        if row["event"] == "interaction_started":
            pending[identity] = [row.get("game_time"), 0]
        elif row["event"] == "interaction_world_delta":
            record = pending.setdefault(identity, [row.get("game_time"), 0])
            record[1] += 1
            if record[1] > 1:
                failures.append("id=%s reported %d deltas for the activation at %ss"
                                % (identity, record[1], record[0]))
    report.check("vector_activation_emits_one_world_delta_per_real_transition", failures)


def vertical_motion_is_not_traversal(rows, report):
    failures = []
    for row in rows:
        if row["event"] != "jump_succeeded":
            continue
        dx, dy = field(row, "dx", 0), field(row, "dy", 0)
        arrived = row["fields"].get("reason") == "entered_target_sector"
        if dx == 0 and dy == 0 and not arrived:
            failures.append("%ds target=%s moved only in z" % (row.get("game_time"), field(row, "target")))
    report.check("jump_vertical_motion_is_not_traversal_success", failures)


def crossings_name_the_boundary_crossed(rows, report, joins):
    if joins is None:
        report.check("actual_intermediate_portal_identity_is_recorded", [],
                     "(no map supplied)")
        return
    failures = []
    corrected = 0
    for row in rows:
        if row["event"] != "portal_traversed":
            continue
        a, b, w = field(row, "from"), field(row, "to"), field(row, "wall")
        if field(row, "aimed_at") not in (None, w):
            corrected += 1
        if not joins(w, a, b):
            failures.append("%ds wall=%s does not separate %s and %s"
                            % (row.get("game_time"), w, a, b))
    report.check("actual_intermediate_portal_identity_is_recorded", failures,
                 "(%d crossings corrected away from the aimed-at wall)" % corrected)


def deliberate_holds_are_not_deadlocks(rows, report):
    busy_owners = ("COMBAT", "INTERACTION", "PORTAL_WAIT", "BREAK_OBSTACLE")
    failures = []
    for row in rows:
        if row["event"] != "stationary_deadlock":
            continue
        owner = str(row["fields"].get("camera_owner", ""))
        if owner in busy_owners:
            failures.append("%ds blamed the route while %s held the camera"
                            % (row.get("game_time"), owner))
    report.check("stationary_hold_is_not_reported_as_deadlock", failures)


def search_probes_stand_still(rows, report):
    """A probe endpoint is fixed for the probe's lifetime.  Entering a new
    sector legitimately ends a local probe and starts a fresh one, so only
    compare probes issued on the same heading within one stretch of the run."""
    seen = {}
    failures = []
    for row in rows:
        event = row["event"]
        if event in ("sector_entered", "local_jump_probe_reoriented"):
            seen.clear()
            continue
        if event != "local_jump_probe":
            continue
        heading = field(row, "heading")
        target = (row["fields"].get("to_x"), row["fields"].get("to_y"))
        if heading is None or target == (None, None):
            continue
        if heading in seen and seen[heading] != target:
            failures.append("%ds heading=%s moved from %s to %s"
                            % (row.get("game_time"), heading, seen[heading], target))
        seen[heading] = target
    report.check("fixed_search_probe_does_not_move_with_player", failures)


def edge_failures_have_still_geometry(rows, report):
    failures = []
    for row in rows:
        if row["event"] not in ("frontier_failed", "local_portal_failed"):
            continue
        if row["fields"].get("evidence") == "geometry_in_motion":
            failures.append("%ds wall=%s condemned mid-travel"
                            % (row.get("game_time"), field(row, "wall")))
    report.check("edge_failure_needs_still_geometry", failures)


def build_wall_join_test(map_path):
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "map_topology", str(Path(__file__).resolve().parent / "map_topology.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    level = module.read_map(map_path)
    owner = {}
    for index, sector in enumerate(level.sectors):
        fields = sector.fields
        for wall_id in range(fields["wall_ptr"], fields["wall_ptr"] + fields["wall_count"]):
            owner[wall_id] = index

    def joins(wall_id, a, b):
        if wall_id is None or a is None or b is None:
            return False
        if wall_id not in owner:
            return False
        other = level.walls[wall_id].fields["next_sector"]
        return (owner[wall_id] == a and other == b) or (owner[wall_id] == b and other == a)

    return joins


def walking_never_beats_the_step_allowance(rows, trajectory, report):
    """The model derives one number for how far up this body walks in a
    single step, from cliptestsector's own arithmetic.  The body then goes
    and walks around.  If it ever climbs further than that in one sector
    crossing, the derivation is wrong -- and if the derivation were instead
    generous, the bot would keep walking into steps it cannot climb.

    This is the differential the staircase bug hid behind: every crossing the
    body actually made, measured against what the model said was possible."""
    allowance = None
    for row in rows:
        if row["event"] == "actor_measured":
            allowance = field(row, "step_up")
            break
    if allowance is None or not trajectory:
        report.check("actual_climbs_stay_within_the_derived_step", [],
                     "no actor measurement in this run")
        return
    failures = []
    worst = 0
    previous = None
    for point in trajectory:
        if previous is not None and point.get("sector") != previous.get("sector"):
            # z counts downwards, so a smaller z is a higher place.
            rise = previous.get("z", 0) - point.get("z", 0)
            if rise > worst:
                worst = rise
            if rise > allowance and previous.get("on_ground") and point.get("on_ground"):
                failures.append("tick %s: %d -> %d climbed %d, allowance %d"
                                % (point.get("tick"), previous.get("sector"),
                                   point.get("sector"), rise, allowance))
        previous = point
    report.check("actual_climbs_stay_within_the_derived_step", failures,
                 "steepest climb %d of %d allowed" % (worst, allowance))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("telemetry")
    parser.add_argument("--trajectory", default="")
    parser.add_argument("--map", default="")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    rows = load(args.telemetry)
    joins = build_wall_join_test(args.map) if args.map else None
    trajectory = []
    if args.trajectory and Path(args.trajectory).exists():
        for line in Path(args.trajectory).read_text(
                encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                trajectory.append(json.loads(line))
            except ValueError:
                continue

    report = Report()
    accepted_activation_is_never_called_unanswered(rows, report)
    answered_mechanism_is_not_retriggered(rows, report)
    one_world_delta_per_activation(rows, report)
    vertical_motion_is_not_traversal(rows, report)
    crossings_name_the_boundary_crossed(rows, report, joins)
    deliberate_holds_are_not_deadlocks(rows, report)
    search_probes_stand_still(rows, report)
    edge_failures_have_still_geometry(rows, report)
    walking_never_beats_the_step_allowance(rows, trajectory, report)
    report.render(args.quiet)
    return 0 if report.ok() else 1


if __name__ == "__main__":
    sys.exit(main())
