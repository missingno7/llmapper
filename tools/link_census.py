"""Count the Link across a population, and say who cannot answer it.

`kCmdLink` is the one command of the twelve that is not an edge report. The
other eleven say "you, now, do this once" and are sent from `SetSectorState`
inside the `trigger_on` / `trigger_off` flags (`triggers.cpp:140, :152` -- both
of which open with `command != kCmdLink`). The Link is re-sent from inside the
sender's **busy proc**, once per game tick for the whole of its travel, and it
carries the sender's `busy` with it. So its receivers do not act once: they
track.

That makes the interesting question not "who is on this channel" but "what does
a busy value DO to each of them", and the answer is decided by the receiver's
own type and shade fields, four of which can leave it on the channel and
completely unmoved by it. `effects.transmission` reads all of that; this walks
a population with it.

.. code-block:: bash

    python -m tools.link_census
    python -m tools.link_census --population blood-campaign --json out.json

Originals only by default: the population comes from the corpus registry, so
no directory is globbed and no generated map is counted as evidence.
"""

from __future__ import annotations

import argparse
import json
import pathlib
import sys
from collections import Counter
from typing import Any

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

from bloodmap.effects import (                                   # noqa: E402
    LINK, LINK_DRIVEN_MOVER_TYPES, receiver_index, transmission)
from bloodmap.format import read_map                             # noqa: E402
from bloodmap.patterns import list_corpus_maps                   # noqa: E402

#: The sector types that are a mechanism at all, for the denominator.
MECHANISM_TYPES = (600, 602, 612, 613, 614, 615, 616, 617, 618, 619)


def census(population: str = "blood-campaign") -> dict[str, Any]:
    entries = sorted(list_corpus_maps(population=population),
                     key=lambda entry: entry.path.stem)
    tally: Counter[str] = Counter()
    responses: Counter[str] = Counter()
    kinds: Counter[str] = Counter()
    sender_types: Counter[int] = Counter()
    sender_faults: Counter[str] = Counter()
    receiver_faults: Counter[str] = Counter()
    waves: Counter[int] = Counter()
    notable: list[dict[str, Any]] = []
    per_map: list[dict[str, Any]] = []

    for entry in entries:
        disk = read_map(entry.path)
        name = entry.path.stem.upper()
        index = receiver_index(disk)
        senders = links = 0
        for sector_id in range(len(disk.sectors)):
            wiring = transmission(disk, sector_id, receivers=index)
            if wiring is None:
                continue
            senders += 1
            tally["transmitters"] += 1
            if wiring["command"] != LINK:
                continue
            links += 1
            tally["link_senders"] += 1
            sender_types[int(disk.sectors[sector_id].fields["type"])] += 1
            if wiring["sends"] is None:
                tally["senders_that_never_send"] += 1
                notable.append({"why": "never sends", "map": name,
                                "sender": sector_id,
                                "detail": wiring["faults"][0]})
            if wiring["edge_flags_ignored"]:
                tally["link_senders_with_dead_edge_flags"] += 1
            for fault in wiring["faults"]:
                sender_faults[fault.split(":")[0][:60]] += 1
            if not wiring["receivers"]:
                tally["link_senders_with_no_receiver"] += 1
                notable.append({"why": "no receiver", "map": name,
                                "sender": sector_id,
                                "detail": f"channel {wiring['channel']}"})
            for row in wiring["receivers"]:
                tally["link_receivers"] += 1
                kinds[row["kind"]] += 1
                responses[row["response"]] += 1
                if row["kind"] == "sector" and "shade_wave" in row["needs"]:
                    waves[int(row["needs"]["shade_wave"])] += 1
                if row["faults"]:
                    tally["receivers_that_cannot_respond"] += 1
                    for fault in row["faults"]:
                        receiver_faults[fault.split(":")[0][:60]] += 1
                    notable.append({"why": "cannot respond", "map": name,
                                    "sender": sector_id, "kind": row["kind"],
                                    "receiver": row["id"],
                                    "detail": row["faults"][0]})
                #: Measured at ON, not at OFF: with `shade_always` 0 the OFF
                #: pose returns before the wave is ever consulted, so asking
                #: it would report every receiver as measurable.
                if row.get("on", {}).get("unmeasurable"):
                    tally["shade_unmeasurable_at_on"] += 1
                if row["kind"] != "sector":
                    notable.append({"why": "non-sector receiver", "map": name,
                                    "sender": sector_id, "kind": row["kind"],
                                    "receiver": row["id"],
                                    "detail": row["response"]})
        tally["mechanisms"] += sum(
            1 for sector in disk.sectors
            if int(sector.fields["type"]) in MECHANISM_TYPES)
        per_map.append({"map": name, "transmitters": senders,
                        "link_senders": links})

    return {
        "population": population,
        "maps": len(entries),
        "totals": dict(sorted(tally.items())),
        "link_sender_sector_types": {str(k): v
                                     for k, v in sorted(sender_types.items())},
        "receiver_kinds": dict(sorted(kinds.items())),
        "receiver_responses": dict(sorted(responses.items())),
        "sender_faults": dict(sorted(sender_faults.items())),
        "receiver_faults": dict(sorted(receiver_faults.items())),
        "dimmer_shade_waves": {str(k): v for k, v in sorted(waves.items())},
        "mover_receiver_types": sorted(LINK_DRIVEN_MOVER_TYPES),
        "notable": notable,
        "per_map": per_map,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--population", default="blood-campaign")
    parser.add_argument("--json", default="reports/blood-link-census.json")
    args = parser.parse_args(argv)

    out = census(args.population)
    if not out["maps"]:
        print(f"no maps in population {args.population!r}")
        return 1
    path = pathlib.Path(args.json)
    path.write_text(json.dumps(out, indent=1) + "\n",
                    encoding="utf-8", newline="\n")
    print(json.dumps({key: value for key, value in out.items()
                      if key not in ("per_map", "notable")}, indent=1))
    for row in out["notable"]:
        print(f"  {row['why']:22} {row['map']:6} s{row['sender']} "
              f"-> {row.get('kind', '')}{row.get('receiver', '')}: "
              f"{row['detail'][:90]}")
    print("wrote", path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
