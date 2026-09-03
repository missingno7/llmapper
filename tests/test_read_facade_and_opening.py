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


class TheCityAsksForTwoKinds(unittest.TestCase):
    """The fail-first: what the 296 undescribed records are made of."""

    @classmethod
    def setUpClass(cls):
        from bloodmap.read_joins import join_census, surface_kinds

        cls.level = _level(CITY)
        cls.read = surface_kinds(cls.level)
        cls.kinds = cls.read["kinds"]
        cls.census = join_census(cls.level, cls.kinds)

    @unittest.expectedFailure
    #: THE MODEL CHANGED UNDER THIS TEST, on the owner's W12: a building is
    #: no longer a SECTOR standing on the pavement, it is a VOID in it, and
    #: `engine.cpp:4688` is the reason -- a roof-height real ceiling beside
    #: the sky clips everything above its line behind it. So the city has no
    #: facade sectors and no opening sectors for the reader to name, and the
    #: finding this test records is about a map that no longer exists. Kept
    #: as the record it is; queue item 39 asks P15 what a facade is when the
    #: building is not a sector.
    def test_the_296_falls_to_134_and_the_rest_is_water(self):
        """The 296 the two kinds were proposed against, and what is left.

        The surprise is that the writer's table already HAD the rows. It has
        carried `pavement|facade`, `facade|opening`, `interior|facade` and
        `opening|pavement` since the grammar was written; the READER could
        not produce the kinds, so 162 of the writer's own rows were
        unreachable on the map the writer built. Naming the kinds did not
        add a row. It made 162 records able to find the row that was already
        there.
        """
        #: THE MAP MOVED UNDER THESE NUMBERS. St Gallow's was re-parented
        #: into its shell after they were taken, so the city has eight
        #: church rooms where it had one: 1112 two-sided records against
        #: 1058, and 978 described against 924. What did NOT move is the
        #: finding: the residue is 134 either way, and every one of it is
        #: the waterfront.
        self.assertEqual(self.census["two_sided_records"], 1112)
        self.assertEqual(self.census["records_described"], 978)
        self.assertEqual(self.census["records_undescribed"], 134)
        self.assertEqual(set(self.census["undescribed"]),
                         {"shore|water|equal", "water|shore|equal",
                          "water|water|equal", "water|solid|equal",
                          "solid|water|equal"},
                         "everything the city leaves undescribed is now its "
                         "waterfront, which is a different item")

    @unittest.expectedFailure
    #: THE MODEL CHANGED UNDER THIS TEST, on the owner's W12: a building is
    #: no longer a SECTOR standing on the pavement, it is a VOID in it, and
    #: `engine.cpp:4688` is the reason -- a roof-height real ceiling beside
    #: the sky clips everything above its line behind it. So the city has no
    #: facade sectors and no opening sectors for the reader to name, and the
    #: finding this test records is about a map that no longer exists. Kept
    #: as the record it is; queue item 39 asks P15 what a facade is when the
    #: building is not a sector.
    def test_nine_masses_are_facades_and_three_are_not(self):
        """Twelve raised masses; nine hold rooms and three terminate a street."""
        from bloodmap.read_joins import END_WALL, FACADE

        counts = self.read["counts"]
        self.assertEqual(counts.get(FACADE), 9)
        self.assertEqual(counts.get(END_WALL), 3)

    @unittest.expectedFailure
    #: THE MODEL CHANGED UNDER THIS TEST, on the owner's W12: a building is
    #: no longer a SECTOR standing on the pavement, it is a VOID in it, and
    #: `engine.cpp:4688` is the reason -- a roof-height real ceiling beside
    #: the sky clips everything above its line behind it. So the city has no
    #: facade sectors and no opening sectors for the reader to name, and the
    #: finding this test records is about a map that no longer exists. Kept
    #: as the record it is; queue item 39 asks P15 what a facade is when the
    #: building is not a sector.
    def test_the_nine_shopfronts_are_openings(self):
        from bloodmap.read_joins import OPENING

        self.assertEqual(self.read["counts"].get(OPENING), 9)
        self.assertEqual(
            sorted(index for index, kind in self.kinds.items()
                   if kind == OPENING),
            [101, 104, 107, 110, 113, 116, 126, 130, 133],
            "the last three moved when the church took eight sectors "
            "where it had one")

    @unittest.expectedFailure
    #: THE MODEL CHANGED UNDER THIS TEST, on the owner's W12: a building is
    #: no longer a SECTOR standing on the pavement, it is a VOID in it, and
    #: `engine.cpp:4688` is the reason -- a roof-height real ceiling beside
    #: the sky clips everything above its line behind it. So the city has no
    #: facade sectors and no opening sectors for the reader to name, and the
    #: finding this test records is about a map that no longer exists. Kept
    #: as the record it is; queue item 39 asks P15 what a facade is when the
    #: building is not a sector.
    def test_no_record_is_an_end_wall_with_a_room_behind_it_any_more(self):
        """The pair that made no architectural sense is gone from the census."""
        undescribed = self.census["undescribed"]
        for pair in ("end_wall|interior|b_below", "interior|end_wall|b_above",
                     "pavement|interior|equal", "interior|pavement|equal"):
            self.assertNotIn(pair, undescribed, f"{pair} should be named now")

    @unittest.expectedFailure
    #: THE MODEL CHANGED UNDER THIS TEST, on the owner's W12: a building is
    #: no longer a SECTOR standing on the pavement, it is a VOID in it, and
    #: `engine.cpp:4688` is the reason -- a roof-height real ceiling beside
    #: the sky clips everything above its line behind it. So the city has no
    #: facade sectors and no opening sectors for the reader to name, and the
    #: finding this test records is about a map that no longer exists. Kept
    #: as the record it is; queue item 39 asks P15 what a facade is when the
    #: building is not a sector.
    def test_162_records_reach_a_row_that_was_always_there(self):
        """Which rows the two kinds unlocked, and how many records each holds."""
        described = self.census["described"]
        unlocked = {pair: count for pair, count in described.items()
                    if "facade" in pair or "opening" in pair}
        self.assertEqual(sum(unlocked.values()), 312)
        self.assertEqual(unlocked, {
            "pavement|facade|b_above": 61, "facade|pavement|b_below": 61,
            "facade|interior|b_below": 58, "interior|facade|b_above": 58,
            "facade|opening|b_below": 18, "opening|facade|b_above": 18,
            "pavement|opening|equal": 9, "opening|pavement|equal": 9,
            "interior|opening|equal": 10, "opening|interior|equal": 10},
            "facade|interior went 45 -> 58 and interior|opening 9 -> 10: "
            "the church has eight rooms against one, and its narthex is "
            "the tenth room a mouth opens onto")
        #: 162 of the 284 were undescribed before -- every facade|interior,
        #: facade|opening and opening|* record. The other 122 are the
        #: pavement|facade pairs, which WERE described, as pavement|end_wall:
        #: the same records under a row that called a building a termination.
        self.assertEqual(924 - 762, 162)
        self.assertEqual(unlocked["pavement|facade|b_above"]
                         + unlocked["facade|pavement|b_below"], 122)


class TheRoofTestIsRelational(unittest.TestCase):
    """A facade is not a tile number; it is a mass whose top roofs a room."""

    @unittest.expectedFailure
    #: THE MODEL CHANGED UNDER THIS TEST, on the owner's W12: a building is
    #: no longer a SECTOR standing on the pavement, it is a VOID in it, and
    #: `engine.cpp:4688` is the reason -- a roof-height real ceiling beside
    #: the sky clips everything above its line behind it. So the city has no
    #: facade sectors and no opening sectors for the reader to name, and the
    #: finding this test records is about a map that no longer exists. Kept
    #: as the record it is; queue item 39 asks P15 what a facade is when the
    #: building is not a sector.
    def test_the_citys_masses_agree_with_the_rooms_they_hold(self):
        from bloodmap.read_joins import FACADE, adjacency, surface_kinds

        level = _level(CITY)
        read = surface_kinds(level)
        graph = adjacency(level)
        facades = [index for index, kind in read["kinds"].items()
                   if kind == FACADE]
        self.assertEqual(len(facades), 9)
        for index in facades:
            top = int(level.sectors[index]["fields"]["floor_picnum"])
            ceilings = {int(level.sectors[other]["fields"]["ceiling_picnum"])
                        for other in graph.get(index, ())
                        if read["kinds"].get(other) in ("interior", "opening")}
            self.assertIn(top, ceilings,
                          f"sector {index} was called a facade, so its top "
                          f"must be a tile one of its rooms wears as a roof")

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
    """Its measurement, so the name can be argued with."""

    @unittest.expectedFailure
    #: THE MODEL CHANGED UNDER THIS TEST, on the owner's W12: a building is
    #: no longer a SECTOR standing on the pavement, it is a VOID in it, and
    #: `engine.cpp:4688` is the reason -- a roof-height real ceiling beside
    #: the sky clips everything above its line behind it. So the city has no
    #: facade sectors and no opening sectors for the reader to name, and the
    #: finding this test records is about a map that no longer exists. Kept
    #: as the record it is; queue item 39 asks P15 what a facade is when the
    #: building is not a sector.
    def test_every_opening_stands_at_its_pavements_own_z(self):
        from bloodmap.read_joins import (
            OPENING, PAVEMENT, adjacency, surface_kinds)

        for path in (CITY,):
            level = _level(path)
            read = surface_kinds(level)
            graph = adjacency(level)
            openings = [index for index, kind in read["kinds"].items()
                        if kind == OPENING]
            self.assertTrue(openings)
            for index in openings:
                here = int(level.sectors[index]["fields"]["floor_z"])
                level_pavements = [
                    other for other in graph.get(index, ())
                    if read["kinds"].get(other) == PAVEMENT
                    and int(level.sectors[other]["fields"]["floor_z"]) == here]
                self.assertTrue(level_pavements,
                                f"sector {index} was called an opening")

    def test_an_opening_reaches_a_room(self):
        from bloodmap.read_joins import OPENING, adjacency, surface_kinds

        level = _level(CITY)
        read = surface_kinds(level)
        graph = adjacency(level)
        for index, kind in read["kinds"].items():
            if kind != OPENING:
                continue
            self.assertTrue(
                [other for other in graph.get(index, ())
                 if read["kinds"].get(other) in ("interior", OPENING)],
                f"an opening with no room behind it is a pavement, not an "
                f"opening (sector {index})")
