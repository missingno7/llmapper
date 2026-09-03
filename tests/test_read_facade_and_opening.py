"""`facade` and `opening`: the two kinds the city's 296 unnamed joins asked for.

Written fail-first against `projects/blood-city/level/slice2-streets.MAP`,
which our own writer built. 1058 of its records are two-sided, 762 were
described by the join grammar and **296 were not** — and 144 of those 296 were
pairs that say nothing about architecture:

* `end_wall|interior` and its mirror, 126 records. An end wall is defined as
  "an outdoor mass no body can step onto"; a room behind one is a
  contradiction the grammar had no word for. What the map built is a
  BUILDING: a raised mass whose top is the roof over the rooms it holds.
* `pavement|interior` and its mirror, 18 records, and 18 of `interior|interior`.
  What the map built is a SHOPFRONT: a sector at the pavement's own z with the
  pavement on one side and the room on the other.

Both kinds are decided by a measurement, never by a tile constant. The
facade's roof test is RELATIONAL — the mass's top must wear a tile that one
of the rooms it opens onto wears on its CEILING, which is what a roof IS —
and that is why it fires on Gravesend's nine buildings and on E3M1's one, and
does NOT fire on E1M2's raised mass, whose top is 49 and whose three rooms are
ceilinged 68.

**The finding these tests were written to catch is not the one they found.**
The writer's table has carried `pavement|facade`, `facade|opening`,
`interior|facade` and `opening|pavement` since the grammar was written. The
reader could not produce the kinds, so 162 of the writer's own rows were
unreachable on the map the writer built, and 122 more records were described
by a row that called a building a termination. Naming the kinds added no row.
It let 284 records find rows that were already there, and dropped the city's
undescribed count from 296 to 134 — all of it now the waterfront.

The campaign guard is the last class: the two kinds must not cost the three
decompiled maps anything. They do not. E3M1 gains a facade (the four-sector
mass 118/165/166/343) and a shopfront (206), E1M2 gains a shopfront (128),
E4M8 gains neither, and no map loses a described record.
"""

from __future__ import annotations

import unittest


def _level(path):
    from bloodmap.format import read_map

    return read_map(path).to_level_ir()


def _corpus(name):
    from bloodmap.patterns import corpus_map_path

    try:
        return _level(corpus_map_path(name))
    except Exception as error:  # pragma: no cover - corpus-dependent
        raise unittest.SkipTest(f"{name} is not readable here: {error}")


CITY = "projects/blood-city/level/slice2-streets.MAP"


class TheCityNoLongerHasAFacadeToName(unittest.TestCase):
    """The map the two kinds were proposed against has been rebuilt.

    They were proposed against 296 undescribed records on
    `slice2-streets.MAP`, 126 of which were `end_wall|interior` -- a room
    behind a termination, which is a contradiction. Naming `facade` and
    `opening` let 284 records reach rows the writer's table had carried all
    along, and dropped the undescribed count to 134.

    Then the owner's second walk (queue item 39, P14b) found that the whole
    construction was wrong for a different reason: `engine.cpp:4688` raises
    umost to the far ceiling line whenever one of two ceilings is not
    parallaxed, so a roof-height slab beside the street cut off everything
    above it behind -- 85 records of it. **E3M1's buildings are not sectors
    at all**: its facades ARE the one-sided records of its outdoor sectors,
    122 of them. The city was rebuilt to that, and a building there is now a
    VOID in the island with its rooms inside it.

    So the city has no `facade` and no `opening` any more, and the kind that
    was proposed against it still names E3M1's one building. That is the
    right way round: a kind justified by the campaign rather than by our own
    map. The city's numbers are pinned here as they now are, so a rebuild
    that quietly reintroduced roof-height slabs beside the street would show.
    """

    @classmethod
    def setUpClass(cls):
        from bloodmap.read_joins import join_census, surface_kinds

        cls.level = _level(CITY)
        cls.read = surface_kinds(cls.level)
        cls.kinds = cls.read["kinds"]
        cls.census = join_census(cls.level, cls.kinds)

    def test_a_building_is_a_void_so_there_is_no_facade_and_no_opening(self):
        from bloodmap.read_joins import FACADE, OPENING

        self.assertNotIn(FACADE, self.read["counts"])
        self.assertNotIn(OPENING, self.read["counts"])
        self.assertEqual(self.read["counts"], {
            "solid": 10, "water": 23, "road": 34, "pavement": 84,
            "end_wall": 3, "shore": 19, "interior": 26})

    def test_three_masses_remain_and_they_terminate_streets(self):
        """The three that never held a room still do not."""
        from bloodmap.read_joins import END_WALL

        self.assertEqual(self.read["counts"][END_WALL], 3)

    def test_the_contradiction_the_two_kinds_were_named_for_is_gone(self):
        """`end_wall|interior` -- a room behind a termination -- appears
        nowhere, and this time because there is no such geometry rather than
        because the pair was renamed."""
        for pair in ("end_wall|interior|b_below", "interior|end_wall|b_above"):
            self.assertNotIn(pair, self.census["undescribed"])
            self.assertNotIn(pair, self.census["described"])

    def test_what_the_city_still_leaves_undescribed(self):
        """188 of 854, and two thirds of it is the waterfront."""
        self.assertEqual(self.census["two_sided_records"], 854)
        self.assertEqual(self.census["records_described"], 666)
        self.assertEqual(self.census["records_undescribed"], 188)
        water = sum(count for pair, count in self.census["undescribed"].items()
                    if "water" in pair or "shore" in pair)
        self.assertEqual(water, 134)
class TheRoofTestIsRelational(unittest.TestCase):
    """A facade is not a tile number; it is a mass whose top roofs a room.

    Measured on E3M1 and E1M2 rather than on the city: the city was rebuilt so
    that a building is a void with no sector of its own, which is how E3M1
    builds one, and a map with no facade cannot test the facade rule.
    """

    def test_e3m1s_mass_wears_the_tile_its_room_wears_as_a_ceiling(self):
        from bloodmap.read_joins import FACADE, adjacency, surface_kinds

        level = _corpus("E3M1")
        read = surface_kinds(level)
        graph = adjacency(level)
        facades = sorted(index for index, kind in read["kinds"].items()
                         if kind == FACADE)
        self.assertEqual(facades, [118, 165, 166, 343])
        tops = {int(level.sectors[index]["fields"]["floor_picnum"])
                for index in facades}
        ceilings = {int(level.sectors[other]["fields"]["ceiling_picnum"])
                    for index in facades
                    for other in graph.get(index, ())
                    if read["kinds"].get(other) in ("interior", "opening")}
        self.assertEqual(tops, {379})
        self.assertIn(379, ceilings,
                      "the mass is a facade because its top IS the room's roof")

    def test_e1m2s_raised_mass_is_not_a_facade_because_its_top_roofs_nothing(self):
        from bloodmap.read_joins import FACADE, adjacency, surface_kinds

        level = _corpus("E1M2")
        read = surface_kinds(level)
        graph = adjacency(level)
        self.assertNotIn(FACADE, read["counts"],
                         "E1M2's mass 126 has three rooms behind it and a top "
                         "tile of 49 that none of them wears: a mass with "
                         "rooms is not automatically a facade")
        top = int(level.sectors[126]["fields"]["floor_picnum"])
        ceilings = {int(level.sectors[other]["fields"]["ceiling_picnum"])
                    for other in graph.get(126, ())
                    if read["kinds"].get(other) == "interior"}
        self.assertEqual(top, 49)
        self.assertNotIn(top, ceilings)


class TheCampaignGuard(unittest.TestCase):
    """What the two kinds do to the three decompiled maps, stated.

    They are not neutral, and pretending otherwise would be the failure this
    guard exists to catch. E3M1 has one building the city's definition names
    -- the four-sector mass 118/165/166/343, whose top is 379 and whose room
    wears 379 as its ceiling -- and one shopfront, sector 206. E1M2 has one
    shopfront, sector 128. E4M8 has neither.
    """

    def test_e3m1_gains_one_facade_of_four_sectors_and_one_opening(self):
        from bloodmap.read_joins import FACADE, OPENING, surface_kinds

        read = surface_kinds(_corpus("E3M1"))
        self.assertEqual(sorted(index for index, kind in read["kinds"].items()
                                if kind == FACADE), [118, 165, 166, 343])
        self.assertEqual(sorted(index for index, kind in read["kinds"].items()
                                if kind == OPENING), [206])
        self.assertEqual(read["counts"].get("end_wall"), 4,
                         "the other three masses stay terminations, and one "
                         "of them is two sectors, so four sectors remain")

    def test_e1m2_gains_one_opening_and_no_facade(self):
        from bloodmap.read_joins import FACADE, OPENING, surface_kinds

        read = surface_kinds(_corpus("E1M2"))
        self.assertNotIn(FACADE, read["counts"])
        self.assertEqual(sorted(index for index, kind in read["kinds"].items()
                                if kind == OPENING), [128])

    def test_e4m8_reads_exactly_as_it_did(self):
        from bloodmap.read_joins import FACADE, OPENING, surface_kinds

        read = surface_kinds(_corpus("E4M8"))
        self.assertNotIn(FACADE, read["counts"])
        self.assertNotIn(OPENING, read["counts"])
        self.assertEqual(read["counts"], {"solid": 2, "road": 1,
                                          "pavement": 1, "end_wall": 1,
                                          "interior": 75})


class AnOpeningIsAThreshold(unittest.TestCase):
    """Its measurement, so the name can be argued with.

    On E3M1 and E1M2, the two maps that have one. The city's nine shopfronts
    were the population this was written against and they are gone: a
    building there is a void now, so its rooms meet the pavement through a
    one-sided record rather than through a sector.
    """

    def test_every_opening_stands_at_its_pavements_own_z(self):
        from bloodmap.read_joins import (
            OPENING, PAVEMENT, adjacency, surface_kinds)

        for name, expected in (("E3M1", [206]), ("E1M2", [128])):
            level = _corpus(name)
            read = surface_kinds(level)
            graph = adjacency(level)
            openings = sorted(index for index, kind in read["kinds"].items()
                              if kind == OPENING)
            self.assertEqual(openings, expected, name)
            for index in openings:
                here = int(level.sectors[index]["fields"]["floor_z"])
                level_pavements = [
                    other for other in graph.get(index, ())
                    if read["kinds"].get(other) == PAVEMENT
                    and int(level.sectors[other]["fields"]["floor_z"]) == here]
                self.assertTrue(level_pavements,
                                f"{name} sector {index} was called an opening")

    def test_an_opening_reaches_a_room(self):
        from bloodmap.read_joins import OPENING, adjacency, surface_kinds

        for name in ("E3M1", "E1M2"):
            level = _corpus(name)
            read = surface_kinds(level)
            graph = adjacency(level)
            for index, kind in read["kinds"].items():
                if kind != OPENING:
                    continue
                self.assertTrue(
                    [other for other in graph.get(index, ())
                     if read["kinds"].get(other) in ("interior", OPENING)],
                    f"an opening with no room behind it is a pavement, not an "
                    f"opening ({name} sector {index})")
