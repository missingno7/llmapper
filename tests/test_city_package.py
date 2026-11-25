"""What is given out is the map that is played and a readme that is true of it."""

from pathlib import Path
import sys
import unittest

from bloodmap.format import read_map

LEVEL = Path("projects/blood-city/level")


class Package(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(LEVEL))
        import package
        cls.P = package
        if not package.PLAYED.exists():
            raise unittest.SkipTest("the city is not built here")
        cls.files = package.files()
        cls.readme = cls.files[package.README_NAME]

    def test_the_form(self):
        """Plain ASCII, DOS line ends, the template's 72 columns."""
        lines = self.readme.decode("ascii").split("\r\n")
        self.assertFalse([line for line in lines if "\n" in line or "\t" in line])
        self.assertFalse([line for line in lines if len(line) > self.P.COLUMNS])

    def test_the_templates_headings(self):
        text = self.readme.decode("ascii")
        for heading in ("General information", "Installation instructions", "Play Information", "Compatibility", "Suggested play",
                        "Construction", "Walkthrough and secrets guide", "Copyright / Permissions", "Where to get this MAP"):
            self.assertIn(f"* {heading} *", text)

    def test_every_secret_is_in_the_guide(self):
        text = self.readme.decode("ascii")
        counted = self.P.counts(read_map(self.P.PLAYED))["secrets"]
        guide = text.split("THE SECRETS")[1]
        self.assertEqual([n for n in range(1, 99) if f"\r\n{n:>2}. " in guide], list(range(1, counted + 1)))

    def test_what_is_given_out_agrees_with_itself(self):
        """The readme that was packed is of the map that was packed with it: builds go on after a release."""
        packed, readme = self.P.OUT / self.P.MAP_NAME, self.P.OUT / self.P.README_NAME
        if not packed.exists():
            self.skipTest("nothing is packed here")
        text = " ".join(readme.read_text(encoding="ascii").split())
        n = self.P.counts(read_map(packed))
        self.assertIn(f"{n['sectors']} sectors, {n['walls']} walls, {n['sprites']} sprites", text)
        self.assertIn(n["foes"], text)


if __name__ == "__main__":
    unittest.main()
