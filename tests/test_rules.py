"""A rule that does not know how sure it is cannot be trusted.

The registry exists because this project had been enforcing habits as laws. Four
of its checks, run back over Blood's own maps, broke the campaign at 0.03%,
2.33%, 11.20% and 12.98% -- and all four had been compiler errors. One of them
cost three rails in the chapel, deleted on the stated grounds that Blood does
not do that, when Blood does it 295 times.

So severity is derived from the measured rate and never chosen, and a rule with
no measurement has no severity at all.

The grading has already corrected two rules added in the same session as the
registry itself:

* `floor-aligned-sprite-rests-on-a-surface` breaks the campaign **31.5%** of the
  time. Flat sprites hanging in the air are ordinary in Blood -- they are
  platforms, ledges and signs -- so this is a note. The sprite bridge over the
  carnival pit is in that 31.5% on purpose.
* `glass-is-breakable` breaks it **53.7%**. Half the panes in the campaign
  cannot be shot out. The level may still choose to break its own; it may not
  claim Blood requires it.
"""

from __future__ import annotations

import glob
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
#: The campaign population directory (corpus reorganized 2026-08-31).
MAPS = ROOT / "maps" / "blood" / "campaign"
CANDIDATE = ROOT / "projects" / "reasoned-authoring-v1" / "level" / "candidate-v7.MAP"


def campaign_paths() -> list[str]:
    return [
        path for path in sorted(glob.glob(str(MAPS / "*.MAP")))
        if re.match(r"^E[1-46]M[1-9]$", Path(path).stem.upper())
    ]


class RegistryTests(unittest.TestCase):

    def test_every_rule_has_evidence_that_resolves(self):
        from bloodmap import rules_blood            # noqa: F401
        from bloodmap.rules import RULES, unresolved_sources

        self.assertGreater(len(RULES), 5)
        self.assertEqual([], unresolved_sources())

    def test_every_rule_states_why(self):
        from bloodmap import rules_blood            # noqa: F401
        from bloodmap.rules import RULES

        for rule_id, rule in RULES.items():
            self.assertTrue(rule.statement.strip(), rule_id)
            self.assertTrue(rule.because.strip(), rule_id)
            self.assertGreater(len(rule.because), 40,
                               "%s: 'because' should say the mechanism" % rule_id)

    def test_severity_comes_from_the_rate(self):
        from bloodmap.rules import ERROR_RATE, WARNING_RATE, severity_for

        self.assertEqual(severity_for(0.0), "error")
        self.assertEqual(severity_for(ERROR_RATE - 1e-9), "error")
        self.assertEqual(severity_for(ERROR_RATE), "warning")
        self.assertEqual(severity_for(WARNING_RATE - 1e-9), "warning")
        self.assertEqual(severity_for(WARNING_RATE), "note")
        self.assertEqual(severity_for(0.9), "note")

    def test_an_ungraded_rule_is_not_enforced(self):
        """The whole point: you may not enforce what you have not measured."""
        from bloodmap.format import read_map
        from bloodmap.rules import Finding, Rule, Violation, evaluate

        invented = Rule(
            id="invented-rule", statement="nothing may be blue",
            because="a claim with no measurement behind it, which is the case "
                    "this test exists to cover",
            source="corpus", scope="map",
            check=lambda disk: Finding(1, (Violation("map", "everything"),)),
        )
        disk = read_map(campaign_paths()[0])
        findings = evaluate(disk, grades={}, rules=[invented])
        self.assertEqual([f.code for f in findings], ["rule-ungraded"])


@unittest.skipUnless(bool(campaign_paths()), "no Blood campaign maps")
class GradeTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from bloodmap.rules import load_grades

        cls.grades = load_grades()

    def test_the_grades_have_been_measured(self):
        from bloodmap import rules_blood            # noqa: F401
        from bloodmap.rules import RULES

        missing = sorted(set(RULES) - set(self.grades))
        self.assertEqual(missing, [], "run python -m tools.grade_rules")

    def test_the_engine_laws_come_out_as_errors(self):
        """If an engine rule grades as a habit, either the rule or the reading
        of the engine is wrong, and both are worth knowing."""
        for rule_id in ("dude-carries-an-xsprite", "marker-names-a-real-owner",
                        "two-sided-wall-is-reciprocal", "flat-tile-power-of-two",
                        "sky-is-never-below-a-roof",
                        "ceiling-mover-is-not-open-to-the-sky",
                        "stack-portal-wears-the-mirror-tile",
                        "link-marker-carries-an-xsprite", "link-marker-is-paired"):
            self.assertEqual(self.grades[rule_id].severity, "error", rule_id)

    def test_the_two_rules_the_grading_demoted_stay_demoted(self):
        """Both were added as hard checks and both describe habits."""
        self.assertGreater(self.grades["floor-aligned-sprite-rests-on-a-surface"].rate, 0.2)
        self.assertGreater(self.grades["glass-is-breakable"].rate, 0.4)
        for rule_id in ("floor-aligned-sprite-rests-on-a-surface", "glass-is-breakable"):
            self.assertEqual(self.grades[rule_id].severity, "note", rule_id)

    def test_the_blocked_wall_rule_is_a_habit_not_a_law(self):
        """The one that cost three rails. Blood does it about seven times a map."""
        grade = self.grades["blocked-wall-not-invisible-kerb"]
        self.assertGreater(grade.violations, 250)
        self.assertEqual(grade.severity, "note")


@unittest.skipUnless(CANDIDATE.exists() and bool(campaign_paths()), "no candidate")
class CandidateTests(unittest.TestCase):

    #: One known finding, named rather than hidden. `transmitter-reports-an-
    #: edge` was added 2026-09-01 after the owner found five dead switches in
    #: the pattern zoo, and running it over the older projects turned up this
    #: too: candidate-v7's sprite 290 is a type-0, picnum-0 placeholder
    #: carrying `tx_id 1` and `command 67` with neither edge flag, so
    #: `triggers.cpp` never calls evSend for it. Nothing in
    #: `candidate_v7.py` emits it, so it did not come from the generator and
    #: is not this run's to rewrite -- a shipped artifact of another project
    #: gets reported, not silently patched.
    #: Four more, found 2026-09-01 when `tile-sits-in-an-attested-slot`
    #: started judging walls by the BAND the engine draws rather than the
    #: field the tile is stored in (`bloodmap.render_slots`,
    #: `knowledge/blood/design/usage-kinds-v2.json`). Walls 577, 579, 593 and
    #: 595 are a masked pair between sectors 76 and 77, cstat 0x51
    #: (block+masked+hitscan) with `over_picnum` **110** -- the bulk wall
    #: stone, which the campaign draws 2513 times as a white wall, 574 times
    #: on an upper step and 513 on a lower one, and **never once** as a
    #: masked middle. Blood builds masked panes out of doors, grates and
    #: glass (266, 330, 463, 502 ...); this one is made of the wall. The
    #: storage vocabulary could not see it at all: it checked `picnum` on
    #: walls and never looked at `over_picnum`. Reported, not patched --
    #: candidate-v7 is another project's shipped artifact.
    KNOWN = {("transmitter-reports-an-edge", "sprite 290"),
             ("tile-sits-in-an-attested-slot", "wall[577]"),
             ("tile-sits-in-an-attested-slot", "wall[579]"),
             ("tile-sits-in-an-attested-slot", "wall[593]"),
             ("tile-sits-in-an-attested-slot", "wall[595]")}

    def test_the_candidate_breaks_no_engine_law(self):
        from bloodmap import rules_blood            # noqa: F401
        from bloodmap.format import read_map
        from bloodmap.rules import evaluate

        errors = [f for f in evaluate(read_map(CANDIDATE)) if f.severity == "error"]
        found = {(f.code, f.location) for f in errors}
        self.assertEqual(set(), found - self.KNOWN)

    def test_the_known_finding_is_still_there_to_be_fixed(self):
        # If it is ever repaired this fails, which is the point: a waiver
        # that outlives its defect is how a defect becomes invisible again.
        from bloodmap import rules_blood            # noqa: F401
        from bloodmap.format import read_map
        from bloodmap.rules import evaluate

        errors = {(f.code, f.location) for f in evaluate(read_map(CANDIDATE))
                  if f.severity == "error"}
        self.assertEqual(errors & self.KNOWN, self.KNOWN)


@unittest.skipUnless(bool(campaign_paths()), "no Blood campaign maps")
class RoomOverRoomTests(unittest.TestCase):
    """The stack constructor, checked by the rules and by the miner.

    Mining the campaign's 251 paired links separates two things usually spoken
    of as one: a **water** link is a congruent copy parked a median of 81 player
    widths away and overlapping in plan 7% of the time; a **stack** sits a median
    of 0.8 away and overlaps 66% of the time. Only the second is room over room.

    Three things are unanimous over all 38 stack pairs and are therefore built
    rather than offered: tile 504 on both surfaces, an XSprite on both markers,
    and a shared link id. The median of `lower ceiling - upper floor` is exactly
    zero, so the constructor makes the two rooms meet at one plane instead of
    checking that the author did.
    """

    def _stack(self):
        from bloodmap.planar_layout import PlanarLayout
        from bloodmap.roomoverroom import room_over_room

        layout = PlanarLayout(name="stacktest")
        box = [(0, 0), (4096, 0), (4096, 4096), (0, 4096)]
        beside = [(4096, 0), (8192, 0), (8192, 4096), (4096, 4096)]
        layout.add_region("region:upper", box, floor_z=0, ceiling_z=-16384)
        layout.add_region("region:lower", box, floor_z=16384, ceiling_z=8192)
        layout.add_region("region:beside", beside, floor_z=0, ceiling_z=-16384)
        layout.add_connection("c", "region:upper", "region:beside",
                              a1=(4096, 0), a2=(4096, 4096))
        layout.set_player_start("region:beside", x=6144, y=2048, z=0)
        built = room_over_room(layout, "stack:test", "region:upper",
                               "region:lower", link_id=1, at=(2048, 2048))
        return layout, built

    def test_the_constructor_builds_a_stack_the_miner_recognises(self):
        from tools.mine_stacks import observe

        layout, _ = self._stack()
        rows = observe("stacktest", layout.compile().level.to_disk_map())
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["family"], "stack")
        self.assertTrue(row["paired"])
        self.assertTrue(row["congruent"])
        self.assertTrue(row["overlaps_in_plan"])
        self.assertEqual(row["offset"], [0, 0])

    def test_the_two_rooms_meet_at_one_plane(self):
        layout, _ = self._stack()
        self.assertEqual(layout.regions["region:lower"].ceiling_z,
                         layout.regions["region:upper"].floor_z)

    def test_both_surfaces_wear_the_mirror_tile(self):
        from bloodmap.roomoverroom import MIRROR_TILE

        layout, _ = self._stack()
        self.assertEqual(layout.regions["region:upper"].floor_picnum, MIRROR_TILE)
        self.assertEqual(layout.regions["region:lower"].ceiling_picnum, MIRROR_TILE)

    def test_it_breaks_no_rule(self):
        from bloodmap import rules_blood            # noqa: F401
        from bloodmap.rules import evaluate, load_grades

        layout, _ = self._stack()
        disk = layout.compile().level.to_disk_map()
        errors = [f for f in evaluate(disk, grades=load_grades())
                  if f.severity == "error"]
        self.assertEqual([], [(f.code, f.location) for f in errors])

    def test_a_room_that_is_not_underneath_is_refused(self):
        from bloodmap.planar_layout import PlanarLayout
        from bloodmap.roomoverroom import StackError, room_over_room

        layout = PlanarLayout(name="bad")
        box = [(0, 0), (4096, 0), (4096, 4096), (0, 4096)]
        layout.add_region("region:a", box, floor_z=0, ceiling_z=-16384)
        layout.add_region("region:b", box, floor_z=-8192, ceiling_z=-16384)
        with self.assertRaises(StackError):
            room_over_room(layout, "s", "region:a", "region:b",
                           link_id=1, at=(2048, 2048))
