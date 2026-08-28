#!/usr/bin/env python3
"""Auditable, non-scalar scorecard for one LLMapper bot run.

Every number is derived from an event the bot actually emitted.  Nothing is
collapsed into a single quality score, and no metric is aliased onto another
(a collected key is not the same fact as an observed object).
"""
import argparse
import collections
import json
from pathlib import Path


def rows(path):
    if not Path(path).exists():
        return []
    out = []
    for line in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def kv(detail):
    """Parse the bot's key=value key=value detail strings."""
    fields = {}
    for token in str(detail or "").split():
        if "=" in token:
            key, _, value = token.partition("=")
            fields[key] = value
    return fields


def as_int(value, default=-1):
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def summarize(telemetry_path, trajectory_path):
    telemetry = rows(telemetry_path)
    trajectory = rows(trajectory_path)
    events = collections.Counter(r.get("event") for r in telemetry if r.get("type") == "event")
    summary = next((r for r in reversed(telemetry) if r.get("type") == "summary"), {})

    # --- exploration -----------------------------------------------------
    entered = [kv(r.get("detail")) for r in telemetry if r.get("event") == "sector_entered"]
    visited = {as_int(f.get("sector")) for f in entered}
    visited.discard(-1)
    visited |= {r.get("sector") for r in trajectory if r.get("sector") is not None}

    depths = [as_int(f.get("depth"), 0) for f in entered if "depth" in f]
    branches = {f.get("branch") for f in entered if "branch" in f}
    branches.discard(None)

    # First-arrival times give the real "new space" progress curve.
    first_seen, order = {}, []
    for r in telemetry:
        if r.get("event") != "sector_entered":
            continue
        sector = as_int(kv(r.get("detail")).get("sector"))
        if sector >= 0 and sector not in first_seen:
            first_seen[sector] = r.get("game_time", 0)
            order.append((r.get("game_time", 0), sector))
    end_time = summary.get("game_time",
                           trajectory[-1].get("game_time", 0) if trajectory else 0)
    gaps, previous = [], 0
    for moment, _ in order:
        gaps.append(moment - previous)
        previous = moment
    gaps.append(end_time - previous)
    longest_no_new_space = max(gaps) if gaps else end_time

    # --- tiny-loop detection ---------------------------------------------
    transitions = collections.Counter()
    last, ab_loops, recent = None, 0, []
    for sector in [r.get("sector") for r in trajectory]:
        if sector is None or sector == last:
            continue
        if last is not None:
            transitions[(last, sector)] += 1
            recent.append((last, sector))
            if len(recent) >= 4 and recent[-1] == recent[-3] and recent[-2] == recent[-4]:
                ab_loops += 1
        last = sector

    # --- stationary while useful work existed ----------------------------
    stationary_run, longest_stationary = 0, 0
    for before, after in zip(trajectory, trajectory[1:]):
        moved = (before.get("x"), before.get("y"), before.get("z")) != \
                (after.get("x"), after.get("y"), after.get("z"))
        step = after.get("game_time", 0) - before.get("game_time", 0)
        stationary_run = 0 if moved else stationary_run + step
        longest_stationary = max(longest_stationary, stationary_run)

    backtracks = collections.Counter()
    for r in telemetry:
        if r.get("event") == "backtrack_started":
            backtracks[kv(r.get("detail")).get("reason", "UNSPECIFIED")] += 1

    # What the bot took, read from what it actually did: the affordance
    # records say what each thing is by Blood's own type number, and the
    # delivery events say which of them it went and took.
    kinds = {}
    for r in telemetry:
        if r.get("event") != "affordance_mapped":
            continue
        fields = kv(r.get("detail"))
        identity = fields.get("affordance")
        if identity is not None and identity not in kinds:
            kinds[identity] = (fields.get("kind"), as_int(fields.get("type"), -1))
    taken = []
    for r in telemetry:
        if r.get("event") != "action_delivered":
            continue
        identity = kv(r.get("detail")).get("affordance")
        if identity is not None:
            taken.append(identity)
    pickups = collections.Counter()
    keys = []
    for identity in taken:
        kind, item = kinds.get(identity, (None, -1))
        if kind != "collect":
            continue
        # Blood's key items are the first seven item types.
        if 100 <= item <= 106:
            name = "key%d" % (item - 99)
            if name not in keys:
                keys.append(name)
            pickups["key"] += 1
        elif 100 <= item <= 150:
            pickups["item"] += 1
        else:
            pickups["ammo_or_weapon"] += 1
    keys.sort()

    damage_dealt = sum(as_int(kv(r.get("detail")).get("amount"), 0)
                       for r in telemetry if r.get("event") == "damage_dealt")
    damage_taken = sum(as_int(kv(r.get("detail")).get("amount"), 0)
                       for r in telemetry if r.get("event") == "bot_damaged")
    health = [r.get("health") for r in trajectory if r.get("health") is not None]

    return {
        "result": summary.get("result", "RUNTIME_ERROR"),
        "failure_reason": summary.get("failure_reason", ""),
        "exploration": {
            "simulated_seconds": end_time,
            "unique_sectors_visited": len(visited),
            "unique_sectors_observed": summary.get("observed_sectors", len(visited)),
            "max_exploration_depth": max(depths) if depths else 0,
            "branches_opened": len(branches),
            "new_destinations_entered": len(first_seen),
            "longest_no_new_space_seconds": longest_no_new_space,
            "sector_order": [s for _, s in order],
        },
        "navigation": {
            "portals_traversed": events["portal_traversed"],
            "route_steps_failed": events["route_step_failed"],
            "nav_edges_rearmed": events["nav_edge_failure_rearmed"],
            "objectives_budget_exhausted": events["objective_budget_exhausted"],
            "distinct_transitions": len(transitions),
            "repeated_transition_loops": ab_loops,
            "hottest_transitions": [{"edge": "%d->%d" % (a, b), "count": n}
                                    for (a, b), n in transitions.most_common(5) if n > 2],
            "longest_stationary_seconds": longest_stationary,
        },
        "traversal": {
            "walk_step": events["portal_traversed"],
            "jump_attempted": events["jump_input_emitted"],
            "jump_succeeded": events["jump_succeeded"] + events["jump_traversal_completed"],
            "crouch_used": events["crouch_started"],
            "drop_taken": events["drop_traversal"],
        },
        "interaction": {
            "use_pulses": events["use_pulse"],
            "engine_accepted_uses": events["interaction_accepted"],
            "engine_rejected_uses": events["interaction_rejected"],
            "mechanisms_opened": events["interaction_world_delta"],
            "doors_traversed": events["door_traversed"],
            "routes_unblocked": events["interaction_follow_through_ready"],
        },
        "items": {
            "keys_acquired": keys,
            "pickups_by_category": dict(pickups),
            "total_pickups": sum(pickups.values()),
        },
        "combat": {
            "enemies_seen": events["enemy_observed"],
            "enemies_engaged": events["combat_engaged"],
            "enemies_killed": events["enemy_killed"],
            "shots_fired": events["attack_fired"],
            "melee_swings": events["melee_swing"],
            "damage_dealt": damage_dealt,
            "damage_taken": damage_taken,
            "min_health": min(health) if health else None,
            "died": summary.get("result") == "DIED",
        },
        "backtracking": {"total": sum(backtracks.values()), "by_reason": dict(backtracks)},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("telemetry")
    parser.add_argument("trajectory")
    parser.add_argument("--output")
    parser.add_argument("--brief", action="store_true")
    args = parser.parse_args()
    out = summarize(args.telemetry, args.trajectory)
    if args.output:
        Path(args.output).write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    if args.brief:
        exploration = out["exploration"]
        print(json.dumps({
            "result": out["result"],
            "secs": exploration["simulated_seconds"],
            "sectors": exploration["unique_sectors_visited"],
            "depth": exploration["max_exploration_depth"],
            "gap": exploration["longest_no_new_space_seconds"],
            "loops": out["navigation"]["repeated_transition_loops"],
            "backtracks": out["backtracking"]["total"],
            "kills": out["combat"]["enemies_killed"],
            "keys": len(out["items"]["keys_acquired"]),
            "pickups": out["items"]["total_pickups"],
        }))
    else:
        print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
