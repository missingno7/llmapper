#!/usr/bin/env python3
"""Human-readable story of one bot run: what it decided and why."""
import argparse
import collections
import json
from pathlib import Path

STORY = [
    "run_started", "sector_entered", "goal_changed", "frontier_selected",
    "blocked_frontier_selected", "portal_traversed", "door_traversed",
    "objective_budget_exhausted", "opportunity_dormant", "objective_invalidated",
    "backtrack_started", "key_acquired", "pickup_collected", "interaction_started",
    "interaction_accepted", "interaction_rejected", "interaction_world_delta",
    "enemy_killed", "combat_engaged", "exploration_stuck_snapshot", "failure",
    "nav_route_selected", "jump_traversal", "waiting_for_mechanism",
    "branch_pushed", "branch_exhausted", "navigation_failed_bounded",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("telemetry")
    parser.add_argument("--events", default="")
    parser.add_argument("--from-time", type=int, default=0)
    parser.add_argument("--collapse", action="store_true",
                        help="hide immediate repeats of the same event+detail")
    args = parser.parse_args()
    wanted = set(args.events.split(",")) if args.events else set(STORY)

    rows = [json.loads(line) for line in
            Path(args.telemetry).read_text(encoding="utf-8", errors="replace").splitlines()
            if line.strip()]
    previous = None
    suppressed = 0
    for row in rows:
        event = row.get("event")
        if row.get("type") == "summary":
            print("--- SUMMARY", json.dumps(row))
            continue
        if event not in wanted or row.get("game_time", 0) < args.from_time:
            continue
        detail = str(row.get("detail") or "")
        signature = (event, detail)
        if args.collapse and signature == previous:
            suppressed += 1
            continue
        if suppressed:
            print("        ... x%d" % suppressed)
            suppressed = 0
        previous = signature
        print("%4ds  %-28s %s" % (row.get("game_time", 0), event, detail[:130]))


if __name__ == "__main__":
    main()
