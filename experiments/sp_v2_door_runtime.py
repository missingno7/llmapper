"""Bounded NBlood Use probes for SP-v2 critical gates."""

from __future__ import annotations

import json
from pathlib import Path

from experiments.sp_progression_v2 import write_action_fixture


SCENARIOS = (
    {
        "id": "ordinary-crypt",
        "kind": "ordinary-crypt",
        "expect_visible_change": True,
        "note": "hallway Use on Wallpush crypt door should open the slab",
    },
    {
        "id": "keyed-locked",
        "kind": "keyed-locked",
        "expect_visible_change": False,
        "note": "Use without skull key must not open; HUD lock text may still change the shot",
    },
    {
        "id": "archive-switch",
        "kind": "archive-switch",
        "expect_visible_change": True,
        "note": "wall switch TX 100 should move the remote gallery door if it is in view; may fail if door is off-camera",
    },
)


def write_fixtures(root: Path) -> list[dict]:
    rows = []
    for item in SCENARIOS:
        path = root / f"{item['id']}.MAP"
        compiled = write_action_fixture(item["kind"], path)
        start = compiled.layout.player_start
        rows.append({
            **item,
            "map": str(path),
            "player": {"x": start.x, "y": start.y, "z": start.z, "angle": start.angle, "region": start.region_id},
            "sectors": len(compiled.level.sectors),
        })
    return rows


def main() -> None:
    root = Path("work/nblood-sp-v2")
    root.mkdir(parents=True, exist_ok=True)
    fixtures = write_fixtures(root)
    report = {
        "$schema": "llmapper.sp-v2-door-runtime",
        "schema_version": 1,
        "engine": "NBlood ActionScan via oracle-nblood-action (Use/E)",
        "fixtures": fixtures,
        "probes": [],
        "limitations": [
            "oracle compares screenshots, not XSECTOR.state",
            "locked Use may show a HUD message without opening",
            "remote door may be off-camera from the switch pose",
        ],
    }
    nblood = Path("reference/blood/nblood.exe")
    game = Path("reference/blood")
    if nblood.is_file():
        from bloodmap.oracle import run_nblood_action_oracle
        for item in fixtures:
            work = root / item["id"]
            try:
                probe = run_nblood_action_oracle(
                    item["map"], nblood=nblood, game_dir=game,
                    work_dir=work, settle_seconds=2.0,
                )
            except Exception as exc:
                probe = {"status": "error", "error": str(exc)}
            visible = bool((probe.get("probe") or {}).get("visible_state_changed"))
            control_error = (probe.get("probe") or {}).get("input_control_error")
            expected = item["expect_visible_change"]
            if control_error or probe.get("status") == "error":
                match = False
                verdict = "inconclusive"
            else:
                match = visible == expected
                verdict = "pass" if match else "fail"
            report["probes"].append({
                "id": item["id"],
                "expect_visible_change": expected,
                "visible_state_changed": visible,
                "oracle_status": probe.get("status"),
                "verdict": verdict,
                "matches_expectation": match,
                "probe": probe,
            })
    else:
        report["probes"].append({"id": "skipped", "reason": "nblood.exe missing"})
    Path("reports/SP-v2-door-runtime.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n",
    )
    print(json.dumps({p.get("id"): p.get("oracle_status") or p.get("reason") for p in report["probes"]}))


if __name__ == "__main__":
    main()
