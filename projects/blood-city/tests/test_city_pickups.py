"""What is picked up is the size Blood's is, and nothing that is a trap or a pickup in Blood stands about as a decoration."""

from collections import Counter, defaultdict
from pathlib import Path
import unittest

from bloodmap.corpus import campaign_maps
from bloodmap.format import read_map
from bloodmap.model import record_fields

CITY = Path("projects/blood-city/level/blood-city-current.MAP")
#: drawn as decorations all the same, and why
ALSO = {1270: "iron mounts on the carousel", 1745: "iron mounts on the carousel", 518: "a book: its item is none the engine has"}


@unittest.skipUnless(CITY.exists() and campaign_maps(), "the city or the campaign is not here")
class Pickups(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.size, cls.kind = defaultdict(Counter), defaultdict(Counter)
        for path in campaign_maps():
            for sprite in read_map(path).sprites:
                f = record_fields(sprite)
                if f["cstat"] & 32768 or f["picnum"] <= 0:
                    continue
                cls.kind[f["picnum"], f["cstat"] >> 4 & 3][f["type"]] += 1
                if 40 <= f["type"] <= 150:
                    cls.size[f["type"]][f["picnum"], f["x_repeat"], f["y_repeat"]] += 1
        cls.ours = [record_fields(s) for s in read_map(CITY).sprites]

    def test_a_pickup_is_the_size_bloods_is(self):
        for f in self.ours:
            seen = self.size.get(f["type"])
            if 40 <= f["type"] <= 150 and seen and sum(seen.values()) >= 5:
                self.assertEqual((f["picnum"], f["x_repeat"], f["y_repeat"]), seen.most_common(1)[0][0], f)

    def test_no_trap_and_no_pickup_is_a_decoration(self):
        for f in self.ours:
            if f["cstat"] & 32768 or f["picnum"] <= 0 or f["type"] != 0 or f["picnum"] in ALSO:
                continue
            seen = self.kind.get((f["picnum"], f["cstat"] >> 4 & 3))
            if not seen or sum(seen.values()) < 8 or seen[0]:
                continue
            top, count = seen.most_common(1)[0]
            if count >= 0.9 * sum(seen.values()):
                self.assertFalse(40 <= top <= 150 or 201 <= top <= 260 or 452 <= top <= 459, (f["picnum"], top, f["x"], f["y"]))


if __name__ == "__main__":
    unittest.main()
