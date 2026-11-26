"""Read back the recording device and render its saved and collapsed endpoints."""

import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from bloodmap.art import read_art_directory
from bloodmap.duke import read_duke_map
from bloodmap.format import read_map, write_map
from bloodmap.model import record_fields, record_extra
from bloodmap.posed import chain_of, posed, rested
from bloodmap.wiring import chains
from bloodmap import project as P
from briefing import declare, compiled
from tools.look import observe, pose_hash, poses_for

PROJECT = Path(__file__).resolve().parent


def inspect():
    map_path = PROJECT / "E4L1-current.MAP"
    source_hash = hashlib.sha256(map_path.read_bytes()).hexdigest()
    disk = read_map(map_path)
    added = json.loads((PROJECT / "reports/06-briefing-recorder-applied.json").read_text())["sprites"]
    circuit, _ = declare(disk, added=added, use_channel=record_extra(disk.walls[2318])["tx_id"])
    wiring = circuit.read_back(compiled(disk, added), disk)
    wiring["source_sha256"] = source_hash
    (PROJECT / "reports/briefing-wire-readback.json").write_text(json.dumps(wiring, indent=2) + "\n")
    if not wiring["agrees"]:
        raise ValueError("Briefing wire read-back disagrees; inspect its report")
    chain = chain_of(chains(disk), "wall 2318")
    tiles = read_art_directory(ROOT / "reference/blood")
    before, rest_report = rested(disk, chain, tiles=tiles)
    after, pose_report = posed(disk, chain, tiles=tiles)
    output = PROJECT / "evidence/briefing-mechanism"
    output.mkdir(parents=True, exist_ok=True)
    project = P.read(PROJECT)
    for name, state in (("rest", before), ("collapsed", after)):
        copy = output / (name + ".MAP")
        write_map(state, copy)
        observe(copy, poses_for(project, state.to_level_ir(), "briefing"), output / name, empty=True, source=map_path,
                about={"project": project.key, "pose_sets": ["briefing"], "poses_sha256": pose_hash(project, ["briefing"]),
                       "state": f"{name}: the chain from wall 2318 posed (bloodmap.posed)"})
    duke_path = ROOT / "maps/duke3d/E4L1.MAP"
    duke = read_duke_map(duke_path)
    report = {
        "source_sha256": source_hash,
        "duke_sha256": hashlib.sha256(duke_path.read_bytes()).hexdigest(),
        "owner_identification": "Self-destructible Mission Impossible tape player",
        "source_wall": {"index": 2318, "fields": record_fields(duke.walls[2318])},
        "source_master_switch": {"index": 119, "fields": record_fields(duke.sprites[119])},
        "source_exploders": [{"index": i, "fields": record_fields(duke.sprites[i])} for i in (114, 115, 116)],
        "source_effectors": [{"index": i, "fields": record_fields(duke.sprites[i])} for i in (117, 118, 120)],
        "source_semantics": [
            "sector.cpp CheckDoorTile includes DOORTILE23 (4391); P_ActivateSwitch sends wall lotag to G_OperateMasterSwitches and plays hitag sound.",
            "actors.cpp MASTERSWITCH counts hitag in 30Hz ticks then arms same-sector SEENINE; SEENINE shares arming by hitag and counts lotag down by 3 per tick.",
            "actors.cpp DETONATE sets matching SE13 t_data[2], starting expansion to the authored sector heights.",
            "DEFS.CON DESTRUCT=327; USER.CON binds it to detruct2.voc. No Blood briefing speech has been substituted.",
        ],
        "native_contract": {
            "one_shot_use": bool(record_extra(disk.walls[2318])["trigger_once"]),
            "arming_seconds": record_extra(disk.sprites[added["briefing-arm-delay"]])["wait_time"] / 10,
            "collapse_seconds": record_extra(disk.sprites[added["briefing-collapse-delay"]])["wait_time"] / 10,
            "exploder_fuses_seconds": {str(i): record_extra(disk.sprites[i])["wait_time"] / 10 for i in (327, 328, 329)},
            "explanation": "Normal invisible sprites return from state 1 to rest state 0 after waitTime; Off-only reporting sends On to the listeners. NBlood triggers.cpp SetSpriteState and default OperateSprite.",
            "timing_approximation": "2.6667s MasterSwitch and 0.2778/0.5556/0.8333s fuses rounded to Blood tenths; collapse starts at the rounded first detonation. Source speech and intermediate SE13 travel are not reproduced exactly.",
        },
        "chain": chain,
        "rest": rest_report,
        "collapsed": pose_report,
        "endpoints": {str(i): {"rest": record_fields(before.sectors[i])["floor_z"],
                               "collapsed": record_fields(after.sectors[i])["floor_z"],
                               "authored_on": record_extra(disk.sectors[i])["on_floor_z"]}
                      for i in (390, 403, 405)},
        "runtime_events_executed": False,
        "limits": "Posed final heights, not an explosion animation, timer execution, damage test, speech playback or proof of Use reach.",
    }
    if hashlib.sha256(map_path.read_bytes()).hexdigest() != source_hash:
        raise ValueError("Map changed during inspection; refresh the evidence")
    (PROJECT / "reports/briefing-mechanism.json").write_text(json.dumps(report, indent=2) + "\n")
    return {"wiring_agrees": wiring["agrees"], "endpoints": report["endpoints"],
            "source_sha256": source_hash, "runtime_events_executed": False}


if __name__ == "__main__":
    print(json.dumps(inspect(), indent=2))
