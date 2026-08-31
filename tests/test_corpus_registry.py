"""Corpus registry regressions: population comes from the directory.

The corpus was reorganized (owner, 2026-08-31) into provenance directories with
`multiplayer/` mode subdirectories. These tests pin the resolution rules on a
synthetic tree so they run without the local corpus, plus a handful of gates
against the real corpus that skip cleanly when it is absent.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from bloodmap.format import encode_map
from bloodmap.patterns import (
    CORPUS_VIEWS,
    POPULATIONS,
    PatternError,
    build_corpus_manifest,
    classify_map_population,
    clear_corpus_cache,
    corpus_root,
    filename_population_hint,
    list_corpus_maps,
    list_original_maps,
    observed_mode,
    resolve_corpus_map,
    unadmitted_corpus_maps,
)
from tests.helpers import synthetic_map


ROOT = Path(__file__).resolve().parents[1]
CORPUS = Path(os.environ.get("BLOODMAP_CORPUS", ROOT / "maps" / "blood"))


def _has_corpus() -> bool:
    return (CORPUS / "campaign").is_dir()


class SyntheticCorpusTests(unittest.TestCase):
    """A miniature corpus with the same shape as the real one."""

    #: relative path -> (population, mode, tier)
    LAYOUT = {
        "campaign/E1M1.MAP": ("blood-campaign", "sp", None),
        "campaign/E6M9.MAP": ("blood-campaign", "sp", None),
        "campaign/multiplayer/BB1.MAP": ("blood-bloodbath", "multiplayer", None),
        "curated/DWE1M1.MAP": ("community-curated", "sp", None),
        "curated/TEDE1M4.MAP": ("community-curated", "sp", None),
        "curated/SSHIVE.MAP": ("community-curated", "sp", None),
        "curated/multiplayer/DWBB2.MAP": ("community-curated", "multiplayer", None),
        "curated/multiplayer/DM3.MAP": ("community-curated", "multiplayer", None),
        "conversions/DNE3L1.MAP": ("own-conversion", "unknown", None),
        "community/WHATEVER.MAP": ("community", "unknown", None),
        "community/chronicles1/BCE1M1.MAP": ("community", "unknown", None),
        "mechanism/#MIRROR.MAP": ("mechanism-tutorial", "unknown", None),
        "mechanism/Vanilla/helix.map": ("mechanism-tutorial", "unknown", None),
    }

    @classmethod
    def setUpClass(cls) -> None:
        cls._tmp = tempfile.mkdtemp(prefix="llmapper-corpus-")
        cls.root = Path(cls._tmp)
        payload = encode_map(synthetic_map())
        for index, relative in enumerate(cls.LAYOUT):
            path = cls.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            # Distinct bytes per map so content-hash joins stay meaningful.
            path.write_bytes(payload + bytes([index]))
        # tiered/ is the same community maps under a heuristic tier.
        for tier, name in (("S", "WHATEVER.MAP"), ("questionable", "BCE1M1.MAP")):
            source = next(p for p in cls.root.rglob(name) if "community" in p.parts)
            destination = cls.root / "tiered" / tier / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(source.read_bytes())
        clear_corpus_cache()

    @classmethod
    def tearDownClass(cls) -> None:
        clear_corpus_cache()
        shutil.rmtree(cls._tmp, ignore_errors=True)

    def test_every_directory_resolves_to_its_population_and_mode(self):
        for relative, (population, mode, _tier) in self.LAYOUT.items():
            with self.subTest(relative=relative):
                item = resolve_corpus_map(self.root / relative, root=self.root)
                self.assertEqual(item.population, population)
                self.assertEqual(item.mode, mode)
                self.assertEqual(item.relative, relative)

    def test_death_wish_and_tede_are_curated_not_conversions(self):
        """Owner correction 2026-08-31; the old table called all three files
        `conversion`, which mislabeled two hand-picked community sets."""
        for name in ("curated/DWE1M1.MAP", "curated/TEDE1M4.MAP",
                     "curated/multiplayer/DWBB2.MAP"):
            self.assertEqual(
                resolve_corpus_map(self.root / name, root=self.root).population,
                "community-curated",
            )
        self.assertEqual(
            resolve_corpus_map(self.root / "conversions/DNE3L1.MAP", root=self.root).population,
            "own-conversion",
        )

    def test_bloodbath_is_only_the_campaign_multiplayer_subdirectory(self):
        found = list_original_maps(self.root, population="blood-bloodbath")
        self.assertEqual([p.name for p in found], ["BB1.MAP"])
        curated_mp = [
            item.name for item in
            list_corpus_maps(self.root, population="community-curated", mode="multiplayer")
        ]
        self.assertEqual(sorted(curated_mp), ["DM3.MAP", "DWBB2.MAP"])

    def test_campaign_excludes_hand_picked_and_converted_maps(self):
        names = {p.name for p in list_original_maps(self.root, population="blood-campaign")}
        self.assertEqual(names, {"E1M1.MAP", "E6M9.MAP"})

    def test_community_and_tiered_are_one_population_with_tier_metadata(self):
        community = list_corpus_maps(self.root, population="community")
        self.assertEqual(len(community), 2, "tiered/ must not double-count community maps")
        self.assertEqual(
            {item.name: item.tier for item in community},
            {"WHATEVER.MAP": "S", "BCE1M1.MAP": "questionable"},
        )
        self.assertEqual(
            [item.name for item in list_corpus_maps(self.root, population="community", tier="S")],
            ["WHATEVER.MAP"],
        )

    def test_reference_view_is_campaign_plus_curated(self):
        view = list_corpus_maps(self.root, view="reference")
        self.assertEqual(
            sorted(item.relative for item in view),
            sorted(r for r in self.LAYOUT if r.startswith(("campaign/", "curated/"))),
        )
        self.assertEqual(
            set(CORPUS_VIEWS["reference"]),
            {"blood-campaign", "blood-bloodbath", "community-curated"},
        )
        for item in view:
            self.assertNotIn(item.population, {"community", "own-conversion", "mechanism-tutorial"})

    def test_a_working_file_in_campaign_is_quarantined_not_mined(self):
        """An editor autosave landing in `campaign/` must never become
        authoritative original-campaign evidence."""
        stray = self.root / "campaign" / "ASAVE1.map"
        stray.write_bytes(encode_map(synthetic_map()) + b"\xff")
        try:
            names = {p.name for p in list_original_maps(self.root, population="blood-campaign")}
            self.assertNotIn("ASAVE1.map", names)
            self.assertEqual(
                [item.relative for item in unadmitted_corpus_maps(self.root)],
                ["campaign/ASAVE1.map"],
            )
            loose = list_corpus_maps(self.root, population="blood-campaign", strict=False)
            self.assertIn("ASAVE1.map", {item.name for item in loose})
        finally:
            stray.unlink()

    def test_arbitrary_community_filenames_do_not_steal_a_population(self):
        """A community file named like a campaign map stays community."""
        impostor = self.root / "community" / "E1M1.MAP"
        impostor.write_bytes(encode_map(synthetic_map()) + b"\xfe")
        clear_corpus_cache()
        try:
            item = resolve_corpus_map(impostor, root=self.root)
            self.assertEqual(item.population, "community")
            self.assertEqual(item.filename_hint, "blood-campaign")
            self.assertTrue(item.hint_conflict)
            campaign = {p.name for p in list_original_maps(self.root, population="blood-campaign")}
            self.assertEqual(campaign, {"E1M1.MAP", "E6M9.MAP"})
            self.assertEqual(len(list_original_maps(self.root, population="blood-campaign")), 2)
        finally:
            impostor.unlink()
            clear_corpus_cache()

    def test_unknown_population_and_view_fail_closed(self):
        with self.assertRaises(PatternError):
            list_corpus_maps(self.root, population="canonical")
        with self.assertRaises(PatternError):
            list_corpus_maps(self.root, view="everything")
        with self.assertRaises(PatternError):
            list_corpus_maps(self.root, tier="AAA")
        with self.assertRaises(PatternError):
            resolve_corpus_map(self.root / "scratch" / "X.MAP", root=self.root)

    def test_manifest_records_layout_populations_and_views(self):
        manifest = build_corpus_manifest(self.root)
        self.assertEqual(manifest["map_count"], len(self.LAYOUT))
        self.assertEqual(manifest["populations"]["blood-campaign"]["map_count"], 2)
        self.assertEqual(manifest["populations"]["community"]["map_count"], 2)
        self.assertEqual(manifest["views"]["reference"]["map_count"], 8)
        self.assertEqual(manifest["cross_population_duplicates"], [])
        self.assertTrue(any("DWE" in note for note in manifest["provenance_notes"]))
        json.dumps(manifest)                       # the manifest must serialize

    def test_a_flat_directory_still_resolves_by_filename(self):
        flat = self.root / "flat"
        flat.mkdir(exist_ok=True)
        payload = encode_map(synthetic_map())
        (flat / "E2M4.MAP").write_bytes(payload)
        (flat / "DWE1M2.MAP").write_bytes(payload + b"\x01")
        try:
            names = [p.name for p in list_original_maps(flat, population="blood-campaign")]
            self.assertEqual(names, ["E2M4.MAP"])
            curated = [p.name for p in list_original_maps(flat, population="community-curated")]
            self.assertEqual(curated, ["DWE1M2.MAP"])
        finally:
            shutil.rmtree(flat)

    def test_corpus_root_honours_the_environment_override(self):
        previous = os.environ.get("BLOODMAP_CORPUS")
        os.environ["BLOODMAP_CORPUS"] = str(self.root)
        try:
            self.assertEqual(corpus_root(), self.root)
            self.assertEqual(len(list_corpus_maps()), len(self.LAYOUT))
        finally:
            if previous is None:
                os.environ.pop("BLOODMAP_CORPUS", None)
            else:
                os.environ["BLOODMAP_CORPUS"] = previous


class FilenameHintTests(unittest.TestCase):
    def test_hints_carry_the_owner_provenance_correction(self):
        self.assertEqual(filename_population_hint("DWE1M1.MAP"), "community-curated")
        self.assertEqual(filename_population_hint("TEDE1M9.MAP"), "community-curated")
        self.assertEqual(filename_population_hint("DWBB2.MAP"), "community-curated")
        self.assertEqual(filename_population_hint("DNE3L1.MAP"), "own-conversion")
        self.assertEqual(filename_population_hint("BB6.MAP"), "blood-bloodbath")
        self.assertEqual(filename_population_hint("E1M1.MAP"), "blood-campaign")
        self.assertIsNone(filename_population_hint("PYRAMIDT.MAP"))

    def test_loose_paths_classify_fail_closed(self):
        self.assertEqual(classify_map_population("work/BB2-RECONSTRUCTION-v3.MAP"), "generated")
        self.assertEqual(classify_map_population("work/E1M1-BLOOD.MAP"), "generated")
        self.assertEqual(classify_map_population("community/PYRAMIDT.MAP"), "other")
        self.assertNotIn("conversion", POPULATIONS)


class FailClosedGateTests(unittest.TestCase):
    """An unsupported file is reported, never normalized or silently dropped."""

    def setUp(self):
        self._tmp = tempfile.mkdtemp(prefix="llmapper-gate-")
        self.addCleanup(shutil.rmtree, self._tmp, True)
        self.root = Path(self._tmp)

    def test_an_unsupported_map_is_reported_with_a_reason(self):
        from bloodmap.cli import _losslessness_gate

        broken = self.root / "NOTAMAP.MAP"
        broken.write_bytes(b"NOPE" + b"\x00" * 64)
        item = _losslessness_gate(broken)
        self.assertEqual(item["status"], "fail")
        self.assertFalse(item["parse"])
        self.assertIn("failure_reason", item)
        self.assertTrue(item["failure_reason"])
        self.assertEqual(broken.read_bytes(), b"NOPE" + b"\x00" * 64, "the gate must not rewrite")

    def test_a_truncated_map_is_reported_not_repaired(self):
        from bloodmap.cli import _losslessness_gate

        good = encode_map(synthetic_map())
        truncated = self.root / "SHORT.MAP"
        truncated.write_bytes(good[: len(good) // 2])
        item = _losslessness_gate(truncated)
        self.assertEqual(item["status"], "fail")
        self.assertIn("failure_reason", item)
        self.assertEqual(len(truncated.read_bytes()), len(good) // 2)

    def test_a_supported_map_passes_the_same_gate(self):
        from bloodmap.cli import _losslessness_gate

        path = self.root / "OK.MAP"
        path.write_bytes(encode_map(synthetic_map()))
        item = _losslessness_gate(path)
        self.assertEqual(item["status"], "pass")
        self.assertTrue(item["parse"] and item["byte_exact"] and item["ir_byte_exact"])
        self.assertEqual(item["map_version"], "0x0700")
        self.assertNotIn("failure_reason", item)


@unittest.skipUnless(_has_corpus(), "no local Blood MAP corpus; set BLOODMAP_CORPUS to enable")
class LocalCorpusTests(unittest.TestCase):
    """Gates against the real corpus. They skip cleanly when it is absent."""

    def test_campaign_is_exactly_the_original_episode_maps(self):
        import re

        names = sorted(p.name for p in list_original_maps(CORPUS, population="blood-campaign"))
        self.assertTrue(names)
        for name in names:
            self.assertRegex(name.upper(), r"^E\dM\d\.MAP$", f"{name} is not a campaign map")
        on_disk = sorted(
            p.name for p in (CORPUS / "campaign").glob("*")
            if p.is_file() and p.suffix.lower() == ".map"
            and re.match(r"^E\dM\d$", p.stem.upper())
        )
        self.assertEqual(names, on_disk)

    def test_bloodbath_is_exactly_the_campaign_multiplayer_directory(self):
        names = sorted(p.name for p in list_original_maps(CORPUS, population="blood-bloodbath"))
        on_disk = sorted(
            p.name for p in (CORPUS / "campaign" / "multiplayer").glob("*")
            if p.is_file() and p.suffix.lower() == ".map"
        )
        self.assertEqual(names, on_disk)
        self.assertTrue(all(n.upper().startswith("BB") for n in names), names)

    def test_curated_and_conversion_prefixes_land_where_the_owner_says(self):
        curated = {p.name.upper() for p in list_original_maps(CORPUS, population="community-curated")}
        conversions = {p.name.upper() for p in list_original_maps(CORPUS, population="own-conversion")}
        self.assertTrue({n for n in curated if n.startswith("DWE")})
        self.assertTrue({n for n in curated if n.startswith("TEDE")})
        self.assertTrue(all(n.startswith("DNE") for n in conversions), conversions)
        self.assertFalse(curated & conversions)

    def test_community_is_not_double_counted_through_tiered(self):
        community = list_corpus_maps(CORPUS, population="community")
        relatives = [item.relative for item in community]
        self.assertEqual(len(relatives), len(set(relatives)))
        self.assertTrue(all(r.startswith("community/") for r in relatives))
        self.assertTrue(any(item.tier for item in community), "tier metadata never attached")

    def test_declared_mode_agrees_with_player_starts(self):
        for item in list_corpus_maps(CORPUS, population="blood-bloodbath"):
            with self.subTest(map=item.name):
                self.assertIn(observed_mode(item.path), {"multiplayer", "ambiguous"})


if __name__ == "__main__":
    unittest.main()
