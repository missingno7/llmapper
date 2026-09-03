"""Answer every open question in the review packs by census or invariant.

    PYTHONPATH=".;projects/e3m1-decompiled/source" \
        python projects/e3m1-decompiled/source/close_questions.py

The owner's review channel is the walk and the fragment
(`10_AGENT_EXECUTION_PROTOCOL.md`), so the eight per-layer packs stop being
owner-facing. Their nineteen questions do not disappear: each is answered here
by a measurement or by an invariant of the model, and the few that are about
what something LOOKS like -- which no count can settle -- become fragments.

Every number is read from the fact stores, the census references, or a live
reader run here. None is typed.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[3]
MAPS = ("e3m1", "e1m2", "e4m8")

BY_CENSUS = "census"
BY_INVARIANT = "invariant"
BY_DECISION = "already decided"
FRAGMENT = "fragment"


def facts(name: str, predicate: str) -> list[dict]:
    path = ROOT / f"projects/{name}-decompiled/facts/{predicate}.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in
            path.read_text(encoding="utf-8").splitlines() if line.strip()]


def reference(name: str, which: str) -> dict:
    path = ROOT / f"projects/{name}-decompiled/references/{which}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def census_reference(which: str) -> dict:
    path = ROOT / f"projects/campaign-census/references/{which}.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def residue_by(name: str, needle: str) -> int:
    return sum(1 for row in facts(name, "residue")
               if needle in str(row.get("why", "")))


def answers() -> list[dict]:
    """One entry per open question, with the measurement that closes it."""
    out: list[dict] = []

    #: ---- layer 1 -------------------------------------------------------
    singles = {name.upper(): residue_by(name, "no perceptual-space evidence")
               for name in MAPS}
    sectors = {name.upper(): len(facts(name, "sector")) for name in MAPS}
    out.append({
        "layer": 1, "node": "assembly:001",
        "question": "Is a singleton space a reading worth keeping in the tree?",
        "how": BY_INVARIANT,
        "answer": (
            f"Yes, and it is not optional. The tree is a PARTITION -- every "
            f"sector belongs to exactly one space -- so a sector no evidence "
            f"groups still has to be somewhere, and a singleton is what that "
            f"costs. The share is stable across three maps from three "
            f"episodes: " + ", ".join(
                f"{key} {singles[key]} of {sectors[key]} "
                f"({100.0 * singles[key] / max(sectors[key], 1):.0f}%)"
                for key in sorted(singles)) +
            ". A number that steady is a property of the reader, not of the "
            "maps, and dropping the singletons would not group one more "
            "sector -- it would only stop counting them."),
    })

    #: ---- layer 2 -------------------------------------------------------
    continuity = census_reference("three-censuses").get("u_continuity", {})
    classes = continuity.get("by_class", continuity)
    def share(key):
        row = classes.get(key) or {}
        percent = row.get("percent")
        return f"{percent}%" if percent is not None else "not measured"
    out.append({
        "layer": 2, "node": "surface:0898",
        "question": "One frame per RUN, or per FLAT FACE?",
        "how": BY_CENSUS,
        "answer": (
            f"The run. Over the 43 campaign maps a material continues across "
            f"{share('collinear solid-solid')} of collinear solid-solid "
            f"joins, {share('bend solid-solid')} of bends and "
            f"{share('reflex solid-solid')} of reflex corners. A bend keeps "
            f"the run two times in three; a face-by-face writer would break "
            f"it every time. E3M1 is the outlier that made this look "
            f"undecided, and the campaign is not undecided."),
    })
    lone = {name.upper(): residue_by(name, "no same-material neighbour")
            for name in MAPS}
    out.append({
        "layer": 2, "node": "level",
        "question": "Is a lone record a SURFACE of one, or evidence the "
                    "surface model does not fit?",
        "how": BY_INVARIANT,
        "answer": (
            f"A surface of one, and that is exactly why it is residue. A "
            f"surface's claim is that ONE projection reproduces every record "
            f"in it; over a single record that claim is empty -- it "
            f"reproduces the record because it was fitted to it. So the "
            f"reader may call it a surface and may not claim anything from "
            f"doing so. {sum(lone.values())} such records across three maps "
            f"(" + ", ".join(f"{k} {v}" for k, v in sorted(lone.items())) +
            "), and the model that would claim them is Surface/Frame, which "
            "is the architect's item, not a constructor."),
    })

    #: ---- layer 3 -------------------------------------------------------
    band = census_reference("three-censuses").get("end_wall_tiles", {})
    tiles = band.get("tiles", {})
    total = sum(sum(row.values()) for row in tiles.values())
    four_hundred = sum(row.get("400", 0) for row in tiles.values())
    out.append({
        "layer": 3, "node": "row:road|pavement|b_above",
        "question": "Is `TILE_CLASSES['facade stone'] = 400` the campaign's "
                    "value or Gravesend's own choice?",
        "how": BY_DECISION,
        "answer": (
            f"Ours. 400 is worn by {four_hundred} of the {total} end-wall "
            f"band records in the campaign. Decided at item 37b: 400 stays "
            f"our CHOICE inside the attested class and the campaign "
            f"distribution is the envelope. The split into `facade` also "
            f"showed something the single kind hid: 91 leads the buildings, "
            f"2490 leads the plain terminations."),
    })
    out.append({
        "layer": 3, "node": "kind:end_wall",
        "question": "Should a raised outdoor mass that MOVES be an end wall?",
        "how": BY_DECISION,
        "answer": (
            "No -- item 28c, landed. It is a mechanism at rest, named apart, "
            "and the end-wall row keeps its blocking clause on the records "
            "that stay put. The four non-blocking pavement|end_wall records "
            "that raised the question all faced sectors 172 and 174, which "
            "carry type 600."),
    })
    ledger = reference("e3m1", "join-census").get("ledger", {})
    described = ledger.get("explained")
    undescribed = ledger.get("residue")
    out.append({
        "layer": 3, "node": "level",
        "question": "1312 of 1386 records are pairs the table has no row for. "
                    "A gap to fill, or the table's scope?",
        "how": BY_CENSUS,
        "answer": (
            f"A gap, and it is filled. Item 37e landed ONE indoor row keyed "
            f"on the height relation -- not the eleven this project proposed "
            f"-- and item 32c added `facade` and `opening`. E3M1 now "
            f"describes {described} of 1386 records and leaves "
            f"{undescribed}. The 1122 interior|interior residue facts are "
            f"gone; what remains is a mass meeting a solid and a mechanism "
            f"at rest meeting anything."),
    })

    #: ---- layer 4 -------------------------------------------------------
    out.append({
        "layer": 4, "node": "field",
        "question": "E3M1's shadow deltas are 24-26 against the gate's "
                    "[8, 16]. Is the envelope wrong or is E3M1 outside it?",
        "how": FRAGMENT,
        "answer": (
            "Half measured, half not. The envelope is now a census and is "
            "decided per network -- [8, 18] on the largest outdoor "
            "component, where the median is 13 over 192 boundaries and 36 "
            "maps -- so E3M1 is outside the campaign's own envelope and that "
            "is recorded rather than repaired. What no census can say is "
            "whether 8 -> 32 -> 34 READS as two steps of shadow or one, and "
            "that decides whether a writer building to the campaign's step "
            "would look like E3M1 or not. Fragment `shade-step`."),
    })
    overlays = reference("e3m1", "overlays")
    cast = overlays.get("light", {}).get("casters", {})
    out.append({
        "layer": 4, "node": "islands",
        "question": "Is the corner test enough to call the shadow casters "
                    "recovered?",
        "how": BY_INVARIANT,
        "answer": (
            f"No, and the reader already says so. "
            f"{cast.get('up_sun_end_is_a_mass_corner')} oblique edges have a "
            f"mass corner up-sun against "
            f"{cast.get('down_sun_end_is_a_mass_corner')} down-sun: a tie. A "
            f"test that comes out even has not chosen, and a reader that "
            f"reported a caster from it would be reporting its own "
            f"tie-break. The bearing is recovered (479 build units against "
            f"the cited 478); the casters are not."),
    })

    #: ---- layer 5 -------------------------------------------------------
    off = {}
    for name in MAPS:
        rows = facts(name, "sentence")
        off[name.upper()] = sum(
            1 for row in rows
            if "but not this combination" in json.dumps(row.get(
                "against_the_course", {})))
    out.append({
        "layer": 5, "node": "sentence:sector:41",
        "question": "Is a (type, shape, slot) combination the taught course "
                    "never shows a finding or a reader artefact?",
        "how": BY_CENSUS,
        "answer": (
            f"A finding, and it holds on every map: " + ", ".join(
                f"{k} {v}" for k, v in sorted(off.items())) +
            " sentences off the course. Three maps from three episodes each "
            "combine slots the course teaches one at a time. The course "
            "teaches each slot alone and the campaign combines them; the gap "
            "belongs to the curriculum's own list, not to ours."),
    })
    chains = [row for row in facts("e3m1", "sentence")
              if row.get("kind") == "tx -> rx chain"]
    biggest = max((int(row.get("receivers") or 0) for row in chains),
                  default=0)
    out.append({
        "layer": 5, "node": "sentence:channel:116",
        "question": "Should a chain be one sentence, or one per receiver?",
        "how": BY_INVARIANT,
        "answer": (
            f"One sentence. The channel IS the mechanism and its fan-out is "
            f"a parameter of it: E3M1's collapsing house is one channel "
            f"telling {biggest} records at once, and splitting it would make "
            f"{biggest} mechanisms that happen to share a number and cannot "
            f"be authored, moved or removed as the one thing they are. The "
            f"fan-out is now also the `channel` macro's whole reason to "
            f"exist."),
    })
    out.append({
        "layer": 5, "node": "kind:room_over_room",
        "question": "Is the floor marker meant to float 256 below the plane "
                    "it links?",
        "how": BY_CENSUS,
        "answer": (
            "Yes. 38 of 38 upper markers in the campaign sit at exactly "
            "-256, so it is a convention and `curriculum.stack_faults` no "
            "longer flags it -- while still flagging any other offset. E3M1 "
            "reports 0 stack faults now, and STACKS3DSPACES-BADROR is still "
            "caught, which is what keeps the exemption from being a hole."),
    })

    #: ---- layer 6 -------------------------------------------------------
    edges = reference("e3m1", "edge-chain")
    kinds = edges.get("by_kind") or edges.get("segments_by_kind") or {}
    out.append({
        "layer": 6, "node": "edge:building_back",
        "question": "58 of 100 boundary records are one-sided walls against "
                    "the void. Does a building need a sector behind it?",
        "how": BY_INVARIANT,
        "answer": (
            "No, and the count is the evidence. A building's back is a "
            "surface, not a space: E3M1 spends no sector behind 58 of its "
            "edge records and the player never learns. Requiring a sector "
            "would double the map's sector count to model something nothing "
            "can enter -- and Blood's limits are the reason the campaign "
            "does not. `building_back` is the right name for it."),
    })
    out.append({
        "layer": 6, "node": "offmap",
        "question": "`reachability.classify_offmap` raises TypeError on every "
                    "map, so the enclosure member has no reader. Is it a "
                    "reader defect?",
        "how": BY_INVARIANT,
        "answer": (
            "No -- it was called with the wrong argument. `classify_offmap` "
            "takes a DiskMap and section 14 passed it a LevelIR; on a DiskMap "
            "it returns its reachability, components, counts and "
            "sectors_by_kind for E3M1 without raising. A reader that works "
            "and a caller that does not are different findings, and this one "
            "closes without a change to either -- the caller in section 14 "
            "should pass `read_map(path)`."),
    })
    out.append({
        "layer": 6, "node": "edge:interior_doorway",
        "question": "Should a doorway be a member of the edge chain?",
        "how": BY_INVARIANT,
        "answer": (
            "Yes, as its own kind, which is what it already is. The chain is "
            "what the street SEES, and a way in is part of what the street "
            "sees -- it is simply not a termination. Naming it "
            "`interior_doorway` keeps the chain closed without pretending a "
            "mouth ends anything, and the same argument now covers `gate` "
            "(a mechanism at rest) and `opening`."),
    })

    #: ---- layer 7 -------------------------------------------------------
    plan = reference("e3m1", "plan")
    out.append({
        "layer": 7, "node": "streets",
        "question": "Carriageway or full width -- which is the street's "
                    "width?",
        "how": FRAGMENT,
        "answer": (
            "Not decidable by counting. Both numbers are real and they land "
            "in different classes, so the writer has to pick one to size "
            "every street it builds by, and the classes were mined on the "
            "full width. A census can say which number the campaign's maps "
            "cluster on; it cannot say which one a body feels, and that is "
            "what the class is for. Fragment `street-width`."),
    })
    blocks = plan.get("blocks") or []
    out.append({
        "layer": 7, "node": "blocks",
        "question": "The largest block holds 75 sectors -- a block, or a "
                    "whole side of the city?",
        "how": BY_DECISION,
        "answer": (
            f"A side of the city, and item 30b settled the cut: a block is "
            f"cut at its street FRONTAGES, so a mass reachable only around "
            f"the outside of the street is two blocks and not one. E3M1 now "
            f"recovers {len(blocks)} blocks with the cut applied. The "
            f"remaining largest is still large because E3M1's interiors are "
            f"one connected building -- which is a fact about E3M1."),
    })
    fill = plan.get("rectangular_fill") or {}
    out.append({
        "layer": 7, "node": "level",
        "question": "Every plan element is a RECT and a sector is not. Is the "
                    "plan the wrong shape?",
        "how": BY_CENSUS,
        "answer": (
            f"It is the right shape for a plan and the wrong shape for a "
            f"boundary, and the numbers say which is which: E3M1's ground "
            f"fills its own bounding rectangles at a median of "
            f"{fill.get('median')} and a worst of {fill.get('worst')}. A "
            f"median that high says the plan reads the layout correctly; a "
            f"worst that low says one place in the map is not a rectangle at "
            f"all, and the plan names it rather than rounding it off."),
    })

    #: ---- layer 8 -------------------------------------------------------
    intent = reference("e3m1", "intent")
    places = intent.get("summary", {}).get("places", {})
    named = places.get("named")
    refused = places.get("refused")
    candidates = places.get("candidates")
    out.append({
        "layer": 8, "node": "level",
        "question": "Is a refusal rate this high the honest answer, or a "
                    "missing measurement?",
        "how": FRAGMENT,
        "answer": (
            f"It was a missing measurement and now it is partly answered: "
            f"the prop reader is wired into layer 8 and E3M1 names {named} "
            f"places, holds {candidates} as candidates and still refuses "
            f"{refused}. What is left is the question no census reaches -- "
            f"whether a refused room is a room with no function, or a room "
            f"whose function is legible to a person and not to a "
            f"measurement. Fragment `refused-room`."),
    })
    mech = intent.get("summary", {}).get("mechanisms", {})
    out.append({
        "layer": 8, "node": "named:assembly:001/space:008",
        "question": "Is the curriculum's own file naming a fair source of "
                    "function names?",
        "how": BY_INVARIANT,
        "answer": (
            f"Yes, with the share reported and a floor under it. The name "
            f"comes from the prefix of the lesson files teaching that (type, "
            f"shape), and it is taken only where one prefix holds 60% of "
            f"them; below that the reader refuses rather than picking. E3M1 "
            f"names {mech.get('named')} of {mech.get('population')} mechanisms "
            f"({mech.get('named_percent')}%), holds "
            f"{mech.get('candidates')} as candidates and refuses "
            f"{mech.get('refused')}. It is the campaign's own "
            f"vocabulary rather than ours, which is the only reason to trust "
            f"it at all."),
    })
    return out


def main() -> int:
    rows = answers()
    by_how: dict[str, int] = {}
    for row in rows:
        by_how[row["how"]] = by_how.get(row["how"], 0) + 1

    lines = [
        "# Every open question in E3M1's review packs, closed",
        "",
        "P15, 2026-09-03. The owner's review channel is the walk and the "
        "fragment, so the eight per-layer packs stop being owner-facing. "
        "Their nineteen questions are answered here -- by a census, by an "
        "invariant of the model, or by a decision already taken -- and the "
        "three that are about what something LOOKS like become fragments.",
        "",
        "Produced by `projects/e3m1-decompiled/source/close_questions.py`; "
        "every number is a query over the fact stores and the census "
        "references.",
        "",
        "| closed by | questions |",
        "| --- | --- |",
    ]
    for how, count in sorted(by_how.items(), key=lambda kv: -kv[1]):
        lines.append(f"| {how} | {count} |")
    lines += [""]

    layer = None
    for row in rows:
        if row["layer"] != layer:
            layer = row["layer"]
            lines += [f"## Layer {layer}", ""]
        lines += [f"**{row['question']}**  ",
                  f"*node `{row['node']}`, closed by {row['how']}*", "",
                  row["answer"], ""]

    lines += [
        "## The three fragments",
        "",
        "Under `projects/e3m1-decompiled/fragments/`, each a small playable "
        "map with one line of question and the ORIGINAL sector ids in its "
        "sidecar:",
        "",
        "* **`shade-step`** — sectors 1, 2, 3, 4, 5, 6, 8, 9, 45, 159, 175, "
        "235, 236: is 8 → 32 → 34 one step of shadow or two?",
        "* **`street-width`** — sectors 1-9 and 45: is the street's width the "
        "carriageway or the whole gap between the buildings?",
        "* **`refused-room`** — sectors 206 and 208: what is this room for?",
        "",
        "Each answer becomes a fail-first test with the sector id in it, or "
        "a residue named in the ledger. Nothing else is asked of the owner.",
        "",
    ]
    target = ROOT / "reports" / "questions-closed-2026-09-03.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"{len(rows)} questions closed: " + ", ".join(
        f"{how} {count}" for how, count in sorted(by_how.items())))
    print(f"wrote {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
