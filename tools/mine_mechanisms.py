"""What a Blood mechanism looks like as a network.

`llmapper channels` reads the wiring of one map.  Nothing says what wiring
*normally* looks like, so there is no way to tell an ordinary mechanism from an
elaborate one, and no shape to aim at when authoring one.

A Blood level is not a handful of doors.  The median campaign map runs **47
user channels**, each a small transmitter/receiver network, and the interesting
ones are not the 1-to-1 switch-and-door pairs but the fan-outs and fan-ins.

.. code-block:: bash

    python -m tools.mine_mechanisms --maps maps/blood \\
        -o knowledge/blood/design/mechanisms-v1.json

Channels below :data:`FIRST_USER_CHANNEL` are the engine's own -- secrets, level
exit, text, player slots -- and are counted separately, because they are
protocol rather than design.
"""

from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import statistics
from collections import Counter, defaultdict
from typing import Any

from bloodmap.format import read_map

SCHEMA = "llmapper.mechanism-shapes"
SCHEMA_VERSION = 1

CAMPAIGN = re.compile(r"^E[1-46]M[1-9]$")

#: Channels below this are reserved by the engine (see the mechanics document).
FIRST_USER_CHANNEL = 30


def observe(path: pathlib.Path) -> dict[str, Any]:
    disk = read_map(path)
    transmit: dict[int, list[tuple[str, int]]] = defaultdict(list)
    receive: dict[int, list[tuple[str, int]]] = defaultdict(list)
    reserved: Counter = Counter()

    for kind, items in (("sprite", disk.sprites), ("sector", disk.sectors), ("wall", disk.walls)):
        for item in items:
            if item.extra is None:
                continue
            fields = item.extra.fields
            type_id = int(item.fields["type"])
            tx = int(fields.get("tx_id", 0))
            rx = int(fields.get("rx_id", 0))
            if tx >= FIRST_USER_CHANNEL:
                transmit[tx].append((kind, type_id))
            elif tx:
                reserved[tx] += 1
            if rx >= FIRST_USER_CHANNEL:
                receive[rx].append((kind, type_id))
            elif rx:
                reserved[rx] += 1

    channels = sorted(set(transmit) | set(receive))
    records = []
    for channel in channels:
        senders = transmit.get(channel, [])
        listeners = receive.get(channel, [])
        records.append({
            "channel": channel,
            "transmitters": len(senders),
            "receivers": len(listeners),
            "receiver_types": sorted({type_id for _kind, type_id in listeners}),
            "transmitter_types": sorted({type_id for _kind, type_id in senders}),
        })
    return {
        "map": path.stem.upper(),
        "user_channels": len(channels),
        "reserved_uses": sum(reserved.values()),
        "channels": records,
    }


def _shape(record: dict[str, Any]) -> str:
    """A channel's wiring, named by what it does rather than by its counts."""
    senders, listeners = record["transmitters"], record["receivers"]
    if not senders and listeners:
        return "orphan_receiver"
    if senders and not listeners:
        return "orphan_transmitter"
    if senders == 1 and listeners == 1:
        return "one_to_one"
    if senders == 1:
        return "fan_out"
    if listeners == 1:
        return "fan_in"
    return "mesh"


def build(observations: list[dict[str, Any]]) -> dict[str, Any]:
    per_map = [obs["user_channels"] for obs in observations]
    shapes: Counter = Counter()
    sizes: list[int] = []
    receiver_types: Counter = Counter()
    transmitter_types: Counter = Counter()
    fan_out_widths: list[int] = []
    fan_in_widths: list[int] = []

    for obs in observations:
        for record in obs["channels"]:
            shape = _shape(record)
            shapes[shape] += 1
            sizes.append(record["transmitters"] + record["receivers"])
            for type_id in record["receiver_types"]:
                receiver_types[type_id] += 1
            for type_id in record["transmitter_types"]:
                transmitter_types[type_id] += 1
            if shape == "fan_out":
                fan_out_widths.append(record["receivers"])
            elif shape == "fan_in":
                fan_in_widths.append(record["transmitters"])

    total = sum(shapes.values())

    def band(values: list[int]) -> dict[str, Any]:
        if not values:
            return {}
        ordered = sorted(values)
        return {
            "median": statistics.median(ordered),
            "p90": ordered[int(0.9 * (len(ordered) - 1))],
            "max": ordered[-1],
        }

    return {
        "$schema": SCHEMA,
        "schema_version": SCHEMA_VERSION,
        "first_user_channel": FIRST_USER_CHANNEL,
        "maps": len(observations),
        "user_channels_per_map": band(per_map),
        "objects_per_channel": band(sizes),
        "shapes": {
            name: {"count": count, "share": round(count / total, 3)}
            for name, count in shapes.most_common()
        },
        "fan_out_receivers": band(fan_out_widths),
        "fan_in_transmitters": band(fan_in_widths),
        "receiver_types": [
            {"type": type_id, "channels": count} for type_id, count in receiver_types.most_common(15)
        ],
        "transmitter_types": [
            {"type": type_id, "channels": count} for type_id, count in transmitter_types.most_common(15)
        ],
        "reading_guide": [
            "a one-to-one channel is a switch and the thing it opens; the design "
            "interest is in the fan-outs and fan-ins",
            "orphan channels are not necessarily faults -- the campaign carries "
            "them too, so a converted map with a few is in normal company",
            "a share is what the campaign did, never what a level must do",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--maps", default="maps/blood")
    parser.add_argument("-o", "--output")
    args = parser.parse_args(argv)

    observations = []
    seen: set[str] = set()
    for path in sorted(glob.glob(str(pathlib.Path(args.maps) / "*.MAP"))):
        name = pathlib.Path(path).stem.upper()
        if name in seen or not CAMPAIGN.match(name):
            continue
        seen.add(name)
        try:
            observations.append(observe(pathlib.Path(path)))
        except Exception as error:
            print(f"skipped {name}: {type(error).__name__}: {error}")

    document = build(observations)
    if args.output:
        out = pathlib.Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({
        "maps": document["maps"],
        "user_channels_per_map": document["user_channels_per_map"],
        "shapes": {k: v["share"] for k, v in document["shapes"].items()},
        "output": args.output,
    }, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
