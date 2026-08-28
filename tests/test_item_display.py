"""The appearance table has to be the campaign's, not a memory of it.

`APPEARANCE` maps a Blood type to the picnum, repeat, cstat, pal and statnum the
campaign gives it, and it is how this project stops its pickups rendering as
tile 0. It was written by hand, and twelve of its fields disagreed with the mode
they claimed to be. Nothing noticed until a skull key in the monastery came out
half again too big and a size check said so.

The disagreements were not marginal readings. All 29 campaign sprites of type
100 use repeat 32 against a table saying 48; all 546 of type 201 use picnum 2820
and pal 3 against a table saying 3584 and 0. A hand-written corpus constant is a
claim about the corpus, so this re-derives the whole table from the maps and
fails on any field that has drifted.
"""

from __future__ import annotations

import glob
import re
import unittest
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAPS = ROOT / "maps" / "blood"

FIELDS = ("picnum", "cstat", "x_repeat", "y_repeat", "status", "pal")


def campaign_maps() -> list[str]:
    return [
        path for path in sorted(glob.glob(str(MAPS / "*.MAP")))
        if re.match(r"^E[1-46]M[1-9]$", Path(path).stem.upper())
    ]


@unittest.skipUnless(bool(campaign_maps()), "no Blood campaign maps")
class AppearanceTableTests(unittest.TestCase):

    @classmethod
    def setUpClass(cls) -> None:
        from bloodmap.format import read_map
        from bloodmap.item_display import APPEARANCE

        cls.observed: dict[int, dict[str, Counter]] = defaultdict(
            lambda: defaultdict(Counter))
        for path in campaign_maps():
            for sprite in read_map(path).sprites:
                fields = sprite.fields
                type_id = int(fields["type"])
                if type_id not in APPEARANCE:
                    continue
                for name in FIELDS:
                    cls.observed[type_id][name][int(fields[name])] += 1

    def test_every_field_is_the_mode_the_campaign_actually_uses(self):
        from bloodmap.item_display import APPEARANCE

        checked = 0
        for type_id, spec in sorted(APPEARANCE.items()):
            counts = self.observed.get(type_id)
            if not counts:
                continue                      # a type this corpus never places
            for name, declared in spec.items():
                mode, hits = counts[name].most_common(1)[0]
                total = sum(counts[name].values())
                checked += 1
                self.assertEqual(
                    declared, mode,
                    "type %d %s: table says %s, the campaign says %s in %d of %d"
                    % (type_id, name, declared, mode, hits, total))
        self.assertGreater(checked, 60, "the table stopped covering the corpus")

    def test_the_types_in_the_table_are_types_the_campaign_places(self):
        """A row for a type Blood never uses is a row nothing can check."""
        from bloodmap.item_display import APPEARANCE

        missing = sorted(t for t in APPEARANCE if t not in self.observed)
        self.assertEqual(missing, [], "table rows with no corpus behind them")
