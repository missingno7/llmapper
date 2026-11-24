"""How Blood times its blasts: every chain of exploders in the named maps, read by `bloodmap.blasts` and written to a shelf.

    python -m tools.mine_blasts                      knowledge/blood/design/blast-chains.json
    python -m tools.mine_blasts show DWE3M5 155      one chain, blast by blast, and what else is on its wire
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from statistics import median

from bloodmap import blasts, corpus
from bloodmap.blood_types import SPRITE_TYPES
from bloodmap.format import read_map
from bloodmap.model import record_extra, record_fields
from bloodmap.player_space import PLAYER_PROFILES

OUT = Path("knowledge/blood/design/blast-chains.json")
BODY = PLAYER_PROFILES["blood"].standing_height


def name(type_id: int) -> str:
    entry = SPRITE_TYPES.get(type_id)
    return (entry.get("name") if isinstance(entry, dict) else getattr(entry, "name", None)) or str(type_id)


def senders(disk, channel: int) -> list[str]:
    out = []
    for kind, records in (("sprite", disk.sprites), ("wall", disk.walls), ("sector", disk.sectors)):
        for index, record in enumerate(records):
            extra = record_extra(record)
            if extra and extra["tx_id"] == channel:
                out.append(f"{kind} {index} ({name(int(record_fields(record)['type'])) if kind == 'sprite' else kind})")
    return out


def run() -> dict:
    rows = []
    for path in corpus.named_maps():
        disk = read_map(path)
        for chain in blasts.chains(disk, at_least=4):
            gaps = [b - a for a, b in zip(chain.steps, chain.steps[1:])]
            rows.append({"map": path.stem, "channel": chain.channel, "blasts": len(chain.blasts),
                         "moments": len(chain.steps), "first": chain.steps[0] / 10, "lasts": chain.lasts,
                         "gap": median(gaps), "rise_bodies": round(chain.rise / BODY, 2), "run": round(chain.run),
                         "with": sorted({name(t) for _i, t in chain.others}), "sector": chain.blasts[0].sector})
    rows.sort(key=lambda r: (-r["moments"], r["map"], r["channel"]))
    climbing = [r for r in rows if r["rise_bodies"] >= 2]
    return {"$schema": "llmapper.blast-chains", "maps": len({r["map"] for r in rows}), "chains": len(rows),
            "gap_tenths_median": median(r["gap"] for r in rows), "lasts_median": median(r["lasts"] for r in rows),
            "blasts_median": median(r["blasts"] for r in rows), "climb_two_bodies": len(climbing),
            "with_quake": sum("kMarkerEarthQuake" in r["with"] for r in rows),
            "with_voice": sum("kSoundPlayer" in r["with"] for r in rows), "rows": rows}


def show(map_name: str, channel: int) -> None:
    path = Path(map_name) if map_name.lower().endswith(".map") else corpus.corpus_map_path(map_name)
    disk = read_map(path)
    chain = next((c for c in blasts.chains(disk, at_least=1) if c.channel == channel), None)
    if chain is None:
        sys.exit(f"{map_name}: no exploder listens on channel {channel}")
    print(f"{map_name} channel {channel}: {len(chain.blasts)} blasts in {len(chain.steps)} moments over {chain.lasts:.1f} s, "
          f"up {chain.rise / BODY:.1f} bodies, over {chain.run:.0f} units")
    print("  sent by", "; ".join(senders(disk, channel)) or "nothing")
    first = chain.blasts[0]
    for b in chain.blasts:
        print(f"  {b.wait / 10:5.1f} s  sprite {b.sprite} sector {b.sector}  {b.x - first.x:+6d} {b.y - first.y:+6d}  "
              f"up {(first.z - b.z) / BODY:+.2f}")
    for index, type_id in chain.others:
        extra = record_extra(disk.sprites[index])
        print(f"  beside: sprite {index} {name(type_id)}",
              {k: extra[k] for k in ("wait_time", "tx_id", "command", "data_1", "data_2", "data_4") if extra[k]})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("what", nargs="?", default="run", choices=("run", "show"))
    parser.add_argument("map", nargs="?")
    parser.add_argument("channel", nargs="?", type=int)
    args = parser.parse_args()
    if args.what == "show":
        return show(args.map, args.channel)
    data = run()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print({k: v for k, v in data.items() if k != "rows"})
    for row in data["rows"][:12]:
        print(row)


if __name__ == "__main__":
    main()
