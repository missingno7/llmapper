"""One entry point for "what do we know about this?".

The acceptance is the owner's three questions -- tile 332, swinging doors,
E1M4 sector 26 -- answered with sources from one call.
"""

import unittest

from bloodmap.knowledge_index import (
    DERIVED, GRADES, INTERPRETED, OWNER, Entry, KnowledgeIndexError,
    build_index, load_index, lookup,
)


def entry(subject="332", says="tile 332 is grate/lattice", terms=("grate",),
          provenance=OWNER, kind="tile", source="somewhere.json"):
    return Entry(subject_kind=kind, subject=subject, says=says,
                 provenance=provenance, source=source, terms=tuple(terms))


class MatchingTest(unittest.TestCase):
    def test_a_bare_number_matches_a_whole_token_only(self):
        # A substring search for 332 also finds 2332, the stack marker,
        # which is a different tile meaning a different thing.
        self.assertTrue(entry("332").matches("332"))
        self.assertFalse(entry("2332", says="tile 2332 is a stack marker",
                               terms=()).matches("332"))

    def test_a_plural_query_reaches_a_singular_term(self):
        self.assertTrue(entry(terms=("swinging door",)).matches("swinging doors"))

    def test_every_word_of_the_query_has_to_land(self):
        item = entry(terms=("swinging door",))
        self.assertFalse(item.matches("swinging window"))

    def test_an_empty_query_matches_nothing(self):
        self.assertFalse(entry().matches("   "))

    def test_matching_ignores_case_and_punctuation(self):
        self.assertTrue(entry(terms=("swinging door",)).matches("Swinging, Door!"))


class LookupTest(unittest.TestCase):
    def setUp(self):
        self.pool = [
            entry("332", "tile 332 is grate/lattice", ("grate",), OWNER),
            entry("blood-rotating-doors", "Rotating doors, censused",
                  ("swinging door", "turnstile"), DERIVED, kind="family"),
            entry("turnstile", "promoted; still missing passage proof",
                  ("turnstile",), INTERPRETED, kind="constructor"),
        ]

    def test_a_query_returns_its_sources(self):
        found = lookup("grate", entries=self.pool)
        self.assertEqual(found["results"], 1)
        self.assertEqual(found["entries"][0]["source"], "somewhere.json")

    def test_the_owner_is_listed_before_measurement_and_interpretation(self):
        found = lookup("turnstile", entries=self.pool)
        grades = [item["provenance"] for item in found["entries"]]
        self.assertEqual(grades, sorted(grades, key=lambda g: GRADES.index(g)))

    def test_results_can_be_narrowed_by_provenance(self):
        found = lookup("turnstile", entries=self.pool, provenance=INTERPRETED)
        self.assertEqual(found["results"], 1)
        self.assertEqual(found["entries"][0]["subject_kind"], "constructor")

    def test_results_can_be_narrowed_by_subject_kind(self):
        found = lookup("turnstile", entries=self.pool, subject_kind="family")
        self.assertEqual(found["results"], 1)

    def test_an_unknown_filter_is_refused_rather_than_returning_nothing(self):
        with self.assertRaises(KnowledgeIndexError):
            lookup("x", entries=self.pool, provenance="PROBABLY")
        with self.assertRaises(KnowledgeIndexError):
            lookup("x", entries=self.pool, subject_kind="vibe")

    def test_a_query_nothing_knows_about_relaxes_and_says_so(self):
        # Answering "no" to "E1M4 sector 26" when the map is well documented
        # is worse than answering "nothing about that sector; here is the
        # map" -- as long as the relaxation is stated.
        found = lookup("turnstile sector 4096", entries=self.pool)
        self.assertTrue(found["nothing_known_about_the_exact_query"])
        #: Words come off the end until something matches, so the answer
        #: names the widest query that still had sources.
        self.assertEqual(found["relaxed_to"], "turnstile")
        self.assertGreater(found["results"], 0)

    def test_an_exact_hit_is_not_marked_as_relaxed(self):
        found = lookup("grate", entries=self.pool)
        self.assertIsNone(found["relaxed_to"])
        self.assertFalse(found["nothing_known_about_the_exact_query"])


class RealIndexTest(unittest.TestCase):
    """Built over the repository as it stands."""

    def setUp(self):
        self.entries = load_index()

    def test_it_indexes_all_three_provenance_grades(self):
        grades = {item.provenance for item in self.entries}
        self.assertEqual(grades, set(GRADES))

    def test_the_owner_anchors_are_in_it_and_are_owner_provenance(self):
        found = lookup("332", entries=self.entries)
        self.assertEqual(found["results"], 1)
        self.assertEqual(found["entries"][0]["provenance"], OWNER)
        self.assertIn("grate", found["entries"][0]["says"])

    def test_swinging_doors_reaches_the_rotating_door_census(self):
        # A prose-only report. Indexing JSON alone missed it entirely.
        found = lookup("swinging doors", entries=self.entries)
        self.assertGreater(found["results"], 0)
        self.assertTrue(any("rotating-doors" in item["source"]
                            for item in found["entries"]))

    def test_a_sector_question_is_answered_or_honestly_relaxed(self):
        found = lookup("E1M4 sector 26", entries=self.entries)
        self.assertGreater(found["results"], 0)
        #: Nothing has measured that sector, so the answer is about its map
        #: and the relaxation is stated rather than hidden.
        self.assertTrue(found["nothing_known_about_the_exact_query"])

    def test_a_sector_something_does_know_about_answers_exactly(self):
        found = lookup("E1M4 sector 295", entries=self.entries)
        self.assertFalse(found["nothing_known_about_the_exact_query"])
        self.assertGreater(found["results"], 0)

    def test_every_entry_names_the_file_it_came_from(self):
        for item in self.entries:
            self.assertTrue(item.source, item.subject)

    def test_the_index_is_a_pointer_not_a_second_store(self):
        document = build_index()
        self.assertIn("not a second copy", document["note"])
        self.assertEqual(document["count"], len(document["entries"]))


if __name__ == "__main__":
    unittest.main()
