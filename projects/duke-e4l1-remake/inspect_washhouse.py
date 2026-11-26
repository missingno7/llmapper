"""Read back the static-room repair, washhouse fixtures and preserved native records."""

from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from bloodmap.analysis import validate_map
from bloodmap.duke import read_duke_map
from bloodmap.duke_semantics import swing_group_operable
from bloodmap.format import read_map, encode_map
from bloodmap.model import record_fields as f, record_extra as e
from tools.sprite_fit import audit, faults, flat_overlaps
from status import preservation

PROJECT = Path(__file__).resolve().parent


def inspect():
    path = PROJECT / "E4L1-current.MAP"
    disk = read_map(path)
    report10 = json.loads((PROJECT / "reports/10-washhouse-applied.json").read_text())
    before = read_map(PROJECT / "snapshots" / (report10["before_sha256"] + ".MAP"))
    delta = preservation(before,disk)
    new = set(report10["sprites"].values())
    fit = {kind:[r for r in rows if r["sprite"] in new]
           for kind,rows in faults(audit(disk)).items()}
    overlaps = [r for r in flat_overlaps(disk) if r["a"] in new or r["b"] in new]
    source_path = ROOT / "maps/duke3d/E4L1.MAP"
    source = read_duke_map(source_path)
    se = source.sprites[487]
    native = f(disk.sectors[152])
    room = e(disk.sectors[152])
    entry_keys = ("tx_id","command","trigger_enter","trigger_on","trigger_off","trigger_once")
    before9 = json.loads((PROJECT / "reports/09-static-bathroom-room-applied.json").read_text())
    old_room = e(read_map(PROJECT / "snapshots" / (before9["before_sha256"] + ".MAP")).sectors[152])
    source_fixtures = [{"sprite":i, **{k:f(source.sprites[i])[k]
                         for k in ("picnum","sector","x","y","z","cstat","angle")}}
                       for i in [477,478,479,480]]
    flushes = []
    for name,index in report10["sprites"].items():
        if not name.endswith("-flush"):
            continue
        sp, extra = f(disk.sprites[index]), e(disk.sprites[index])
        flushes.append({"name":name,"sprite":index,"type":sp["type"],
                        "agrees":sp["type"]==20 and bool(sp["cstat"]&32768)
                        and extra["trigger_push"]==1 and extra["data_1"]==extra["data_2"]==369
                        and extra["tx_id"]==extra["rx_id"]==0})
    original_sources = json.loads((PROJECT/"reports/protected-duke-sources.json").read_text())
    source_checks = [{"map":r["map"],"unchanged":hashlib.sha256((ROOT/r["path"]).read_bytes()).hexdigest()==r["source_sha256"]}
                     for r in original_sources]
    result = {
        "source_sha256":hashlib.sha256(source_path.read_bytes()).hexdigest(),
        "map_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
        "counts":{k:len(getattr(disk,k)) for k in ("sectors","walls","sprites")},
        "native_round_trip_exact":encode_map(disk)==path.read_bytes(),
        "source_maps":source_checks,
        "structural_diagnostics":dict(Counter(r.severity for r in validate_map(disk))),
        "source_fixtures":source_fixtures,
        "static_room":{"sector":152,"source_sector_lotag":source.sectors[152].lotag,
                       "source_effector":487,"hitag":se.hitag,"same_hitag_st23_operator":swing_group_operable(source,se),
                       "native_type":native["type"],"marker_0":room["marker_0"],
                       "entry_signal_preserved":all(room[k]==old_room[k] for k in entry_keys),
                       "no_invented_local_use":not room["trigger_push"] and not room["trigger_wall_push"]},
        "stall_door":{"sector":61,"native_type":disk.sectors[61].type,
                      "motor_unchanged_by_washhouse_pass":e(disk.sectors[61])==e(before.sectors[61]),
                      "marker":e(disk.sectors[61])["marker_0"]},
        "pass10_preservation":delta,"fixture_fit_faults":fit,"fixture_flat_overlaps":overlaps,
        "flush_controls":flushes,
        "runtime_events_executed":False,
        "limits":"Static render and native read-back only. Live collision, flush sound/Use, door obstruction and encounters need owner play. Mirror support 57 is excluded. Fixtures are native sprite assemblies, interpreted from E2M4's sector-built stone toilet rather than copied geometry.",
    }
    (PROJECT / "reports/washhouse-readback.json").write_text(json.dumps(result,indent=2)+"\n",encoding="utf-8")
    return {"map_sha256":result["map_sha256"],"static_room":result["static_room"],
            "preservation":delta,"new_fit_faults":sum(map(len,fit.values())),
            "flat_overlaps":len(overlaps),"flush_controls_agree":all(r["agrees"] for r in flushes),
            "sources_unchanged":all(r["unchanged"] for r in source_checks)}


if __name__ == "__main__":
    print(json.dumps(inspect(),indent=2))
