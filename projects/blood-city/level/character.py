"""The character sheet: what each named place is, and whether it shows.

The owner, 2026-11-18: "I would like you to come up with some tools or
conventions how to really make the places to be memorable, have
character, more details, combination of sprites and textures like other
blood levels are doing." And: "think about stuff in relations, like this
machine connects to this, there is a control panel here, there is a dirty
water tank, the water goes there".

The convention, in four lines a place must be able to answer:

``hero``       the ONE thing a visitor would describe it by
``exemplar``   the Blood room its detail is transcribed from
``layers``     which of `tools.place_character`'s layers it carries: the
               build MEASURES these, the sheet does not claim them
``relations``  what connects to what inside it: (from, to, how)
``study``      the study it was built from (`tools/study.py`): where Blood
               built such a place, looked at, and what was decided. A
               place built from the word for it is how the first crypt
               came to be a brick room with grey boxes.

A place with no hero is a room. A place whose measured layers are fewer
than a quarter of the campaign's rooms of its size carry is THIN, and the
build says so by name. Nothing here places a sprite: it is the gate the
detail work answers to (`detailing.py` is the hands).
"""

from __future__ import annotations

from typing import Any

#: Places the owner has asked to have rebuilt with what is known now, in their
#: words. `status.py` lists each as an open item ("owner-rework").
OWNER_REWORK: dict[str, str] = {
    # The Aldermack, the first they named, was rebuilt 2026-11-23 and waits for their walk.
    "other old places": "2026-11-23: \"There are other places that were done with old process and old "
                        "knoweledge which we would do today much better.\"",
}

#: name -> a point inside it (world units), its hero and its exemplar
PLACES: dict[str, dict[str, Any]] = {
    "pump machine hall": {
        "at": (45056, 11500),
        "hero": "a sludge belt through two pulsing presses, between a "
                "settling basin and a filter drum",
        "exemplar": "E3M5 crusher line s44-52; E3M3 generator consoles; "
                    "E3M6 tanks s410-417",
    },
    "foundry underpass": {
        "at": (43008, 23000), "floor": 24576, "study": "underpass",
        "hero": "a brick passage under the works from the yard to the "
                "avenue, ending at the barred mouth of a metro that was "
                "never finished",
        "exemplar": "E1M2 s103-105 (the passage to the waiting hall); the "
                    "owner's DNE3L6 for the metro beyond the bars",
    },
    "foundry loading alcove": {
        "at": (47104, 24768), "floor": 24576, "study": "doors-and-mechanisms",
        "hero": "two iron-banded freight leaves part into recessed tracks "
                "to reveal a chain-lit loading alcove with shotgun shells",
        "exemplar": "DOOR-SLIDINGD s3 (opposed solid slider)",
    },
    "RAT DOGS": {
        "at": (52800, 12800), "study": "ratdogs-stand",
        "hero": "a works canteen that sells rats: a hatch on the yard with "
                "rats steaming on a burning grill, RAT DOGS over it, "
                "stand-up tables inside and a freezer of carcasses behind",
        "exemplar": "E1M4 s167 (the grill), s170 (the kitchen), s171 (the "
                    "sign RATDOGS); E1M2 s185/s257 (the buffet and its "
                    "kitchen wall); E1M3 s305 (the freezer); E3M2 s258 "
                    "(the butcher and his tools); study "
                    "canteen-freezer-dining",
    },
    "St Gallow's nave": {
        "at": (29440, 30500), "study": "church",
        "hero": "a clerestory of stained glass over the aisle, the "
                "outside's lancets seen from within",
        "exemplar": "E1M5 walls 29/31 (paired glass); E3M2 s312-314",
    },
    "St Gallow's crypt": {
        "at": (28700, 27300), "floor": 61440, "study": "crypt",
        "hero": "one closed stone sarcophagus under a gravestone slab, in a rubble vault "
                "hung with cobwebs and gold plaques, a line of powder "
                "barrels along its east wall",
        "exemplar": "E1M1 s150 (rubble 110, earth 270), its sarcophagus "
                    "s1-3/27/28, plaques sprites 185-189, cobwebs 150-154",
    },
    "the Weaver's Cellars": {
        "at": (11264, 12800), "floor": 61440, "study": "spider-lair",
        "hero": "brood alcoves walled in silk, a cocoon in each, under a "
                "ceiling where the spiders and their mother hang upside down",
        "exemplar": "E2M8 s52 (silk 1057 alcoves, cocoon 1061, victims 1059, "
                    "mothers on the ceiling); CHORROR s414 (web fringe 1067/1068, "
                    "ceiling spiders, the web 410 across the way in)",
    },
    "Stockyard Drain": {
        "at": (50944, 54272), "floor": 63488, "study": "stockyard-drain",
        "hero": "a tiled race of blood running north from the slaughterhouse "
                "pipe and carcass rack into the Foundry Main",
        "exemplar": "E1M8 s389 (the River Ride's drag), s251 (blood pipes); "
                    "TEDE1M4 s82 (wash-room tiles); E3M2 s258 (hung carcasses)",
    },
    "Stockyard sampling chamber": {
        "at": (55424, 59264), "floor": 63488, "study": "stockyard-trolley",
        "hero": "a low iron sampling trolley runs across the blood to a lit "
                "valve alcove, with a call button on each dry berth",
        "exemplar": "#2WAYCAR s1 (rigid floor that carries its rider); "
                    "E1M2 s34 and sprites 384–391 (track and wheels)",
    },
    "Settling Hall service lift": {
        "at": (19968, 45184), "floor": 102400, "study": "doors-and-mechanisms",
        "hero": "a metal filter deck on the west quay that rises past the "
                "tanks to the gallery, with a work light and call button at each landing",
        "exemplar": "MACHINERY-LIFT s2/s14 and sprite 9 (fixed-roof floor lift and remote call)",
    },
    "the Rat King's Shrine": {
        "at": (55040, 48000), "floor": 61440, "study": "rat-king-shrine",
        "hero": "a low pipe leading to candles around a knot of rats and "
                "a heart on a stepped stone altar",
        "exemplar": "E1M5 s71 (candle recess); DWE1M5 s610 (candles and remains "
                    "on stone); E1M4 s167 (rats on the grill)",
    },
    "Phantom Terminus": {
        "at": (52160, -11184), "floor": 118784, "study": "ghost-station",
        "hero": "a lighted ghost carriage taking its last passenger from "
                "the shuttered platform to the brick stop",
        "exemplar": "DWE3M2 s481 and s246 for the station, sprite 208 for the "
                    "departure; E1M2 s3 for the seated passengers, and SSR3 "
                    "s5 and s46 looking at s45 for the cars",
    },
    "Gravesend Station": {
        "at": (13312, -11500), "floor": -12288, "study": "station",
        "hero": "a green-banded carriage standing at a platform under a "
                "plank canopy, seen through a line of riveted columns",
        "exemplar": "E1M2 s271/s272/s34 (hall, platform, track); STATION "
                    "s128 (the solid car, livery 1665); tunnel STATION "
                    "s131-137; an enterable car is NOT built. "
                    "DOOR-ROTATING s4 (fare turnstile)",
    },
    "saloon": {
        "at": (7168, 11800), "study": "saloon",
        "hero": "a dim bar room with a lit plank counter, stools along "
                "it and whiskey lettered on the wall",
        "exemplar": "E1M2 s278 (height, light); DWE3M1 sprites 539-547 "
                    "(stools); soffit and back bar NOT yet built",
    },
    "Aldermack auditorium": {
        "at": (23040, 9500), "study": "aldermack-rebuild",
        "hero": "a hanged performer over a bloodied trap, framed by the curtain "
                "and seen past the last audience still in its seats",
        "exemplar": "DWE1M9 s245–249 and s274–279 (terraces, cloth and apse), "
                    "sprites 752, 832–833 and 963–964 (rails, step lights and beam); "
                    "SCHOOL_ s177–182 (frame); HUNT s674 (performer and shadow)",
    },
    "Aldermack backstage": {
        "at": (18400, 7680), "study": "aldermack-rebuild",
        # The saved-open fire doors are wide enough for the room reader
        # to include the auditorium. Stop it at their shared frame.
        "stop_at": ((19392, 9472),),
        "hero": "a callboard and keeper's lamp across from the parlor passage",
        "exemplar": "E3M4 s391 (framed service bays); E3M6 s458 (workbench); "
                    "HUNT s673 and sprites 1681/1683-1685 (trick table and balloon)",
    },
    "Aldermack dressing room": {
        "at": (18368, 12032), "study": "aldermack-rebuild",
        "hero": "a lit run of mirrors leading to a portrait against the red drapes",
        "exemplar": "REALM4 s181 (drapery and candelabra); E2M4 sprite 275 "
                    "(vanity mirror); E6M1 s47 (clothes rail)",
    },
    "harbour": {
        "at": (30720, 58368), "floor": 37888, "study": "harbour",
        "hero": "a moored hull between two rock headlands, the sea "
                "running out to a skerry and the sky",
        "exemplar": "DWE3M4 s636-648 (bands, ring); DWE2M6 s931-940 "
                    "(rock), s621-626 (piles)",
    },
    "arcade concourse": {
        "at": (46080, 46080),
        "hero": "a tall concourse of glazed shopfronts, and a service "
                "corridor with something behind its wall",
        "exemplar": "E4M9 concourse; E6M1 shopfronts; E3M4 sprite 331",
    },
}


DESTINATION_AREA_M, DESTINATION_BODIES = 14.0, 1.93


def relations() -> dict[str, list]:
    """Every declared relation, by place."""
    import l3_mall
    import l3_shed

    return {
        "pump machine hall": [list(r) for r in l3_shed.RELATIONS],
        "arcade concourse": [[
            "service extinguisher", "service cache",
            f"channel {l3_mall.SECRET_CHANNEL}: shot, it opens the wall "
            "behind it and three charges go off; the cache is a secret"]],
    }


def wired(disk) -> dict[int, dict[str, int]]:
    """Channel -> how many things send on it and how many listen."""
    out: dict[int, dict[str, int]] = {}
    for group in (disk.sprites, disk.sectors, disk.walls):
        for item in group:
            extra = getattr(item, "extra", None)
            fields = getattr(extra, "fields", None) or {}
            for key in ("tx_id", "rx_id"):
                channel = int(fields.get(key, 0) or 0)
                if channel >= 100:
                    out.setdefault(channel, {"tx_id": 0, "rx_id": 0})[key] += 1
    return out


def engine_channels_wired(disk) -> list[dict[str, Any]]:
    """Engine channels this level uses as a wire of its own.

    Channels below 100 are the engine's: it sends on some (the level
    starting) and listens on others (a secret found). A level that both
    sends AND listens on one is using it as its own wire. Not one of the
    campaign's 43 maps does, so here it is a fault to look at, whether or
    not it happens to work; `wired` above cannot see it, because it only
    counts a level's own channels.
    """
    from bloodmap import wiring
    from bloodmap.blood_types import RESERVED_CHANNELS

    nodes = wiring.nodes(disk)
    out = []
    for channel in sorted({node["tx"] for node in nodes} & {node["rx"] for node in nodes}):
        if 0 < channel < wiring.USER_CHANNELS_FROM:
            out.append({
                "channel": channel,
                "name": (RESERVED_CHANNELS.get(channel) or {}).get("name", "unnamed"),
                "senders": [node["id"] for node in nodes if node["tx"] == channel],
                "listeners": [node["id"] for node in nodes if node["rx"] == channel]})
    return out


def sheet(disk) -> dict[str, Any]:
    """Measure every named place and say which are thin."""
    from tools import place_character as pc

    geom = pc.Geometry(disk)
    reference = pc.load_norms() if pc.NORMS.exists() else None
    related = relations()
    report: dict[str, Any] = {"places": {}, "thin": [], "unfound": []}
    for name, spec in PLACES.items():
        #: space is stacked: the crypt lies under the nave, so a place under
        #: or over the street also says which floor it means
        hits = [i for i in range(len(geom.sectors))
                if geom.contains(i, *spec["at"])]
        want = spec.get("floor", 8192)
        seed = min(hits, key=lambda i: (abs(int(
            geom.sectors[i]["floor_z"]) - want), geom.area(i)),
            default=None)
        if seed is None:
            report["unfound"].append(name)
            continue
        stops = spec.get("stop_at", ())
        boundary = [i for i, sector in enumerate(geom.sectors)
                    if int(sector["floor_z"]) == want
                    and any(geom.contains(i, *point) for point in stops)]
        profile = pc.profile(geom, pc.place_of(geom, seed, avoid=boundary))
        verdict = pc.judge(profile, reference) if reference else {}
        report["places"][name] = {
            "hero": spec["hero"], "exemplar": spec["exemplar"],
            "layers": [k for k, v in profile["layers"].items() if v],
            "layer_count": profile["layer_count"],
            "campaign_p25": verdict.get("campaign_p25"),
            "campaign_p50": verdict.get("campaign_p50"),
            "missing": verdict.get("missing", []),
            "wall_tiles": profile["wall_tiles"],
            "shade_spread": profile["shade_spread"],
            "metres": profile["metres"],
            "free_floor_share": profile["free_floor_share"],
            "cramped": verdict.get("cramped", []),
            "relations": related.get(name, []),
            "study": spec.get("study"),
        }
        if verdict.get("thin"):
            report["thin"].append(name)
        #: A NAMED place is a destination: it may not be smaller or lower
        #: than the campaign's median indoor room (14M of floor, 1.93
        #: bodies), whatever Blood's cupboards measure.
        if not profile["sky"]:
            small = verdict.setdefault("cramped", [])
            if profile["area_M"] < DESTINATION_AREA_M:
                small.append(f"{profile['area_M']}M of floor (a destination "
                             f"wants {DESTINATION_AREA_M}M)")
            if profile["clear_bodies"] < DESTINATION_BODIES:
                small.append(f"{profile['clear_bodies']} bodies high (a "
                             f"destination wants {DESTINATION_BODIES})")
            report["places"][name]["cramped"] = small
        if verdict.get("cramped"):
            report.setdefault("cramped", {})[name] = verdict["cramped"]
    #: which named places were built without a finished study
    from tools import study as _study
    report["unstudied"] = sorted(
        name for name, spec in PLACES.items()
        if not spec.get("study")
        or _study.notes_written(_study.STUDIES / spec["study"]))
    channels = wired(disk)
    report["dangling_channels"] = sorted(
        channel for channel, ends in channels.items()
        if not ends["tx_id"] or not ends["rx_id"])
    report["engine_channels_wired"] = engine_channels_wired(disk)
    return report
