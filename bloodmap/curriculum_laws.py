"""The laws the mechanism tutorials teach, each with the citation that made it.

A law here is never an assertion on its own. It is a statement plus a
DETECTOR, and the detector runs over the mined tutorials to produce the
evidence; a law whose detector finds nothing is reported as unsupported rather
than quietly kept. Three grades, and the grade says where the authority is:

* ``engine``     -- read out of NBlood's source. The strongest: it says what
                    the machine does, not what anyone believes it does.
* ``documented`` -- stated in `maps/blood/mechanism/xmapedit.pdf`, the 981-page
                    XMAPEDIT manual the owner shipped with the curriculum.
                    Authoritative about intent and about conventions the
                    engine does not enforce.
* ``derived``    -- measured across the tutorial corpus. Weakest, and the only
                    grade where a counterexample is expected to turn up.

Several of these CORRECT this project's previous model, and each such law
carries the correction in `corrects` so the report can list them together.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from .curriculum import Reading

Detector = Callable[[list[Reading]], list[str]]


@dataclass
class Law:
    """One thing the curriculum teaches."""

    id: str
    statement: str
    grade: str
    cites: list[str] = field(default_factory=list)
    detect: Detector | None = None
    corrects: str = ""
    evidence: list[str] = field(default_factory=list)

    def as_json(self) -> dict[str, Any]:
        out = {"id": self.id, "statement": self.statement,
               "grade": self.grade, "cites": self.cites,
               "evidence": self.evidence[:12],
               "evidence_count": len(self.evidence)}
        if self.corrects:
            out["corrects"] = self.corrects
        return out


def _movers(readings: list[Reading]):
    for reading in readings:
        for construct in reading.constructs:
            if construct.markers:
                yield reading, construct


# --------------------------------------------------------------------------
# detectors
# --------------------------------------------------------------------------

def _marker_conventions(readings: list[Reading]) -> list[str]:
    """Both marker placements appear, because only the difference is read."""
    at_poses = [f"{r.name} s{c.sector}" for r, c in _movers(readings)
                if c.drawn_at is not None]
    parked = [f"{r.name} s{c.sector}" for r, c in _movers(readings)
              if c.drawn_at is None]
    return ([f"{len(at_poses)} place the pair at the two poses"] + at_poses[:4]
            + [f"{len(parked)} park the pair elsewhere"] + parked[:4])


def _motion_crosses_storage(readings: list[Reading]) -> list[str]:
    out = []
    for reading, construct in _movers(readings):
        if len(construct.motion_sectors) > 1:
            out.append(f"{reading.name} s{construct.sector} deforms "
                       f"{len(construct.motion_sectors)} sectors")
    return out


def _motion_stays_home(readings: list[Reading]) -> list[str]:
    return [f"{reading.name} s{construct.sector}"
            for reading, construct in _movers(readings)
            if construct.motion_sectors == [construct.sector]]


def _z_is_state_anchored(readings: list[Reading]) -> list[str]:
    out = []
    for reading in readings:
        for construct in reading.constructs:
            if not construct.z_pair:
                continue
            pair = construct.z_pair
            if (pair["off_floor_z"] != pair["on_floor_z"]
                    or pair["off_ceiling_z"] != pair["on_ceiling_z"]):
                out.append(f"{reading.name} s{construct.sector} type "
                           f"{construct.type_id}")
    return out


def _wall_buttons(readings: list[Reading]) -> list[str]:
    out = []
    for reading in readings:
        for construct in reading.constructs:
            if construct.buttons:
                out.append(f"{reading.name} s{construct.sector} is shoved "
                           f"through walls {construct.buttons}")
    return out


def _relays(readings: list[Reading]) -> list[str]:
    out = []
    for reading in readings:
        count = reading.sprite_roles.get("generator: trigger (a relay)", 0)
        if count:
            out.append(f"{reading.name}: {count} relay sprite(s)")
    return out


def _carried_members(readings: list[Reading]) -> list[str]:
    return [f"{reading.name} s{construct.sector} carries "
            f"{len(construct.carried_sprites)} sprite(s)"
            for reading, construct in _movers(readings)
            if construct.carried_sprites]


def _stack_faults(readings: list[Reading]) -> list[str]:
    out = []
    for reading in readings:
        for pair in reading.stacks:
            for fault in pair.get("faults", ()):
                out.append(f"{reading.name}: {fault}")
    return out


def _slot_pressure(readings: list[Reading]) -> list[str]:
    """Sectors spending three or more of their single-slot resources."""
    out = []
    for reading in readings:
        for construct in reading.constructs:
            if len(construct.slots) >= 3:
                out.append(f"{reading.name} s{construct.sector}: "
                           + ", ".join(construct.slots))
    return out


def _effect_networks(readings: list[Reading]) -> list[str]:
    return [f"{reading.name} s{construct.sector} drives "
            + ", ".join(f"s{s}" for s in construct.drives)
            for reading in readings for construct in reading.constructs
            if construct.drives]


#: `kSwitchBase`..`kSwitchMax` in common_game.h. Only these go through
#: `SetSpriteState`, and only these are bound by the edge rule.
SWITCH_ROLES = ("switch: toggle", "switch: one-way", "switch: combination",
                "switch: padlock")


def _switches_declare_edges(readings: list[Reading]) -> list[str]:
    """Every SWITCH in the curriculum, checked for an edge flag.

    The law is positive, so the evidence is the population: if the author
    never ships a silent switch across ninety-eight maps, that is the finding.
    A switch that failed would be named here instead.
    """
    checked, silent = 0, []
    for reading in readings:
        for ends in reading.wiring["channels"].values():
            for sender in ends["tx"]:
                if sender.get("role") not in SWITCH_ROLES:
                    continue
                checked += 1
                if not sender["edges"]:
                    silent.append(f"{reading.name}: {sender['role']} sprite "
                                  f"{sender['id']} declares no edge")
    return ([f"{checked} switches checked, {len(silent)} silent"] + silent)


# --------------------------------------------------------------------------
# the laws
# --------------------------------------------------------------------------

LAWS: list[Law] = [
    Law(
        id="drawn-geometry-is-the-on-pose",
        grade="engine",
        statement=(
            "The geometry SAVED in the map is the pose at busy 65536, which "
            "is state ON. `trInit` translates the sector by -65536 of the "
            "marker delta, records THAT as the base with `setBaseWallSect`, "
            "and only then applies the sector's own busy. So the base -- the "
            "OFF pose -- is the drawn outline minus the marker delta, always, "
            "whatever the author intended."),
        cites=["NBlood/source/blood/src/triggers.cpp:2224-2245 (trInit)",
               "DOOR-CURTAINS.map s3: drawn tip y -1152, delta +896, "
               "base y -2048 == the OFF marker, to the unit"],
        corrects=(
            "We had this as a convention -- 'the mapper draws at the ON pose'. "
            "It is not a convention, it is what the loader does, and it holds "
            "even when the author drew the other pose by mistake."),
    ),
    Law(
        id="slide-markers-are-a-vector-not-two-places",
        grade="engine",
        statement=(
            "For a SLIDE, the marker pair contributes only its difference. "
            "`TranslateSector` moves each base point by "
            "`interpolate(m1, m2, busy) - m1`, so the pair's absolute "
            "position on the grid is free: a pair parked anywhere with the "
            "right separation drives the sector identically."),
        cites=["NBlood/source/blood/src/triggers.cpp:879-928 "
               "(TranslateSector: x + vc - a4)",
               "xmapedit.pdf p.240: the arrow's tail is the OFF position and "
               "its point the ON position"],
        detect=_marker_conventions,
        corrects=(
            "`motion.drawn_pose` compared a moved vertex against the markers' "
            "ABSOLUTE coordinates and called the answer the drawn pose. That "
            "only works for the pairs an author placed at the two poses; for "
            "the rest it measures nothing. It is a convention check, and is "
            "now named as one."),
    ),
    Law(
        id="a-rotate-marker-is-the-pivot-and-carries-the-angle",
        grade="engine",
        statement=(
            "A ROTATE has one marker and reads it differently from a slide: "
            "its x/y are the PIVOT that `RotatePoint` turns the sector about "
            "-- absolute position matters here -- and its `ang` is the ON "
            "angle, interpolated from 0. Reusing the slide's reading on a "
            "rotator gets both wrong."),
        cites=["NBlood/source/blood/src/triggers.cpp:2229-2231 (the "
               "single-marker call passes a8=0, a11=pMark1->ang)",
               "NBlood/source/blood/src/triggers.cpp:889-905 (RotatePoint "
               "about a4,a5)"],
    ),
    Law(
        id="state-becomes-busy-at-load",
        grade="engine",
        statement=(
            "`state` is the only thing that decides where a mechanism starts: "
            "at load, `if (pXSector->state) pXSector->busy = 65536`. The same "
            "line exists for XWALL and XSPRITE, so walls and sprites keep "
            "state the same way sectors do."),
        cites=["NBlood/source/blood/src/triggers.cpp:2186-2188 (XWALL), "
               ":2210-2211 (XSECTOR), :2266-2268 (XSPRITE)"],
    ),
    Law(
        id="a-path-sector-fails-silently",
        grade="engine",
        statement=(
            "`InitPath` looks for a path marker whose `data_1` matches the "
            "sector's `data`, and when there is none it prints a system "
            "message and RETURNS. The sector stays in the map, keeps its "
            "type, and never moves. A path mechanism with a mistyped id is "
            "not an error anyone sees -- it is a dead sector."),
        cites=["NBlood/source/blood/src/triggers.cpp:1745-1774 (InitPath)"],
    ),
    Law(
        id="a-transmitter-must-declare-an-edge",
        grade="engine",
        statement=(
            "`SetSpriteState` only calls `evSend` inside `if (triggerOn && "
            "state)` or `if (triggerOff && !state)`. A toggle, one-way or "
            "padlock switch with neither flag transmits NOTHING however "
            "correct its channel is. A COMBINATION switch is different: it "
            "sends from its own arm of `OperateSprite`, `if (command == "
            "kCmdLink && txID > 0)`, outside those guards -- which is why the "
            "curriculum's six edgeless switches are all combination switches "
            "on command 5, and why they work."),
        cites=["NBlood/source/blood/src/triggers.cpp:100-130 (SetSpriteState)",
               "NBlood/source/blood/src/triggers.cpp:475-493 (kSwitchCombo "
               "sends kCmdLink outside the edge guards)",
               "SPRITE-OTHERSP.map sprites 66-70, 72: combination switches, "
               "command 5, no edge flags",
               "xmapedit.pdf p.239: the curtain's own wiring sets Send When "
               "Going ON and Going OFF"],
        detect=_switches_declare_edges,
        corrects=(
            "We generalised this to every transmitter, and `motion.transmitter` "
            "REFUSES to build a sender without an edge. That is too broad: it "
            "binds switches, because switches are what `SetSpriteState` "
            "handles. Relays (kGenTrigger), sector-sound sprites and "
            "command-carrying decorations transmit by other paths and carry "
            "no edge flags in the tutorials -- five of them do exactly that."),
    ),
    Law(
        id="the-button-is-the-surface-you-touch",
        grade="documented",
        statement=(
            "The tutorials do not wire a shove with the sector's "
            "`trigger_wall_push`. They put an XWALL on each face you are "
            "meant to touch -- type 0 Decoration, tx on the mechanism's "
            "channel, command Toggle, Trigger On Push -- and the sector "
            "merely RECEIVES that channel. The mechanism's own tx slot stays "
            "free, and the button is exactly the surface, not the room."),
        cites=["xmapedit.pdf p.239 (Folding Door/Curtain, step 1)",
               "DOOR-CURTAINS.map s3: walls 38/39/40 each carry tx 100, "
               "command 3, trigger_push; the sector carries only rx 100"],
        detect=_wall_buttons,
        corrects=(
            "Our curtain constructor set `trigger_push` and "
            "`trigger_wall_push` on the SECTOR unconditionally, and a commit "
            "message of mine claimed DOOR-CURTAINS s3 carries them. It does "
            "not: s3's whole XSECTOR is rx 100, two busy times and the marker "
            "pair."),
    ),
    Law(
        id="a-mechanisms-sprites-are-members-of-it",
        grade="documented",
        statement=(
            "A sprite inside a moving sector does not move with it by "
            "default: it has to be flagged into the motion the same way a "
            "wall is. The manual makes this an explicit step for the "
            "curtain's sound sprite, and every curtain in the tutorial has "
            "its sector-sound sprite flagged."),
        cites=["xmapedit.pdf p.240: make the SFX sprite blue so it moves with "
               "the door",
               "DOOR-CURTAINS.map s3: sprite 0 (kSoundSector) carries a carry "
               "bit"],
        detect=_carried_members,
    ),
    Law(
        id="a-link-is-a-congruent-pair-of-planes",
        grade="documented",
        statement=(
            "The two halves of a room-over-room are a portal, so they must be "
            "the same size and shape, both must carry tile 504 on the plane "
            "that faces the other, their markers must sit ON those planes "
            "rather than floating, and `data_1` is what pairs them when a map "
            "has more than one."),
        cites=["xmapedit.pdf p.364-365 (ROR: Room Over Room)"],
    ),
    Law(
        id="a-link-sector-wants-a-simple-silhouette",
        grade="derived",
        statement=(
            "The manual blames HOMs on over-complicated link sectors, and the "
            "shape of the outer loop is where that shows: every working link "
            "sector in ROR1 and ROR2 has a four- or six-wall CONVEX outer "
            "loop with its complexity in inner loops, while BADROR -- the map "
            "the manual points at to show the glitches -- cuts its alcoves "
            "into the boundary and gets a ten-wall concave one. This is a "
            "RISK, not a rule: STACKS3DSPACES itself has two concave link "
            "sectors and ships as a working example."),
        cites=["xmapedit.pdf p.364: do not over-complicate the shape",
               "STACKS3DSPACES-BADROR.map s0 and s7 (concave, 10 walls)",
               "STACKS3DSPACES-ROR1.map, STACKS3DSPACES-ROR2.map (all convex)"],
        detect=_stack_faults,
    ),
    Law(
        id="motion-crosses-storage-boundaries-by-default",
        grade="derived",
        statement=(
            "A mechanism deforming more than its own sector is the NORMAL "
            "case in the curriculum, not the pathology we treated it as. "
            "`dragpoint` moves a vertex for every wall incident on it, so any "
            "flagged wall shared with a neighbour drags that neighbour too."),
        cites=["NBlood/source/build/src/engine.cpp:13071 (dragpoint)"],
        detect=_motion_crosses_storage,
        corrects=(
            "We modelled a construct as owning its own sector and treated a "
            "motion reaching a neighbour as a defect to be engineered away. "
            "The tutorials say the opposite: it is the default, and what "
            "matters is whether the construct DECLARED the sectors it moves."),
    ),
    Law(
        id="the-fin-is-an-isolation-technique",
        grade="derived",
        statement=(
            "Confining a motion to one sector is a deliberate construction, "
            "not a property of the mechanism type: the fabric is drawn as an "
            "internal fin so every moved vertex is interior to the sector's "
            "own outline. It is what you build when the room must not be "
            "disturbed -- and the same map slides other curtains straight "
            "into their neighbours where that does not matter."),
        cites=["DOOR-CURTAINS.map s3, s24, s53 (motion set is the sector "
               "itself); s10 in the same map deforms two"],
        detect=_motion_stays_home,
    ),
    Law(
        id="z-motion-is-state-anchored-too",
        grade="derived",
        statement=(
            "The vertical has the same shape as the horizontal: a z-moving "
            "sector carries `off_floor_z`/`on_floor_z` and "
            "`off_ceiling_z`/`on_ceiling_z`, one pair per plane, and `state` "
            "chooses between them exactly as it chooses between markers. A "
            "lift is the pair with the floor travelling; a ceiling door is "
            "the pair with the ceiling travelling; both planes may travel at "
            "once."),
        cites=["MACHINERY-LIFT.map s2 (floor 8192 -> -24576, ceiling still), "
               "s6 (both planes travel)",
               "NBlood/source/blood/src/triggers.cpp:2246 "
               "(ZTranslateSector from the same busy)"],
        detect=_z_is_state_anchored,
    ),
    Law(
        id="the-relay-is-a-sprite",
        grade="derived",
        statement=(
            "When the author needs a channel to fan out, to be delayed, or to "
            "change command on the way, they drop a kGenTrigger (sprite type "
            "700): it receives on one channel and transmits on another, with "
            "its own busy and wait. It is the move that gets a second "
            "transmitter into a sector that has already spent its one tx."),
        cites=["MACHINERY-LIFT.map sprite 127: rx 106, tx 115, command 3, "
               "wait 16",
               "common_game.h:440 (kGenTrigger = 700)"],
        detect=_relays,
    ),
    Law(
        id="one-xsector-is-one-of-each",
        grade="derived",
        statement=(
            "A sector has exactly one XSECTOR, and an XSECTOR has one rx, one "
            "tx, one state machine, one shade wave, one wind, one panning, "
            "one bob and one z pair. Compositions therefore collide over "
            "them, and the tutorials are full of sectors carrying three or "
            "more at once -- which is how close to the ceiling ordinary "
            "authoring runs."),
        cites=["MACHINERY-LIFT.map s25: rx, state, z pair and bob on one "
               "sector",
               "MACHINERY-LIFT.map s16: tx, state, z pair, driving the light "
               "in s17"],
        detect=_slot_pressure,
    ),
    Law(
        id="a-mechanism-sentence-includes-what-it-drives",
        grade="derived",
        statement=(
            "Mechanisms in the curriculum routinely transmit onward as part "
            "of doing their job -- a lift that dims the shaft, a curtain that "
            "brightens the room behind it. The downstream effect is not "
            "decoration bolted on afterwards; it is in the same XSECTOR as "
            "the motion, and reading the mechanism without it reads half a "
            "sentence."),
        cites=["MACHINERY-LIFT.map s16 -> s17 (command 5 Link to a shade "
               "wave)",
               "DOOR-CURTAINS.map s21 -> s20 (the same pattern)"],
        detect=_effect_networks,
    ),
]


def evaluate(readings: list[Reading]) -> list[Law]:
    """Run every detector and attach its evidence."""
    for law in LAWS:
        if law.detect is None:
            law.evidence = []
            continue
        law.evidence = law.detect(readings)
    return LAWS


def unsupported(laws: list[Law]) -> list[str]:
    """Laws that claim a measurable thing and did not measure it."""
    return [law.id for law in laws if law.detect is not None and not law.evidence]
