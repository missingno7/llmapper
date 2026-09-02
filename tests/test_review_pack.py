"""The review pack's script has to survive its own quoting.

The page is one large f-string, so a JavaScript `\\n` must be written as TWO
backslashes in the Python source. Written with one, the f-string emits a REAL
newline into a JavaScript string literal, the script dies at the first one,
and the pack renders a blank tree and an inert map -- while the file itself
looks perfectly fine and the tool exits 0. That happened, to the fact panel
and the aspect selector both, and this is the gate that would have caught it.

Verify the thing, not the call: the tool returning HTML is not evidence that
the HTML runs.
"""

from __future__ import annotations

import json
import re
import unittest


def _pack(claims=None, candidates=None) -> str:
    import sys
    from pathlib import Path

    from bloodmap.patterns import corpus_map_path

    path = corpus_map_path("E3M1", missing_ok=True)
    if not path.exists():
        raise unittest.SkipTest("E3M1 is not in the corpus")
    root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(root / "tools"))
    import review_pack

    hierarchy = root / "projects/e3m1-decompiled/review/layer7-hierarchy.json"
    if not hierarchy.exists():
        raise unittest.SkipTest("no layer hierarchy to draw")
    return review_pack.build(path, hierarchy, "test", claims, candidates)


class TheScriptRuns(unittest.TestCase):
    def test_no_javascript_string_literal_spans_a_line(self):
        page = _pack()
        script = page[page.index("<script>"):]
        offenders = []
        for number, line in enumerate(script.splitlines(), 1):
            stripped = line.strip()
            if re.match(r"^const (NODES|FACTS|ASPECTS)=", stripped):
                continue                       # JSON, checked below
            if line.count("'") % 2:
                offenders.append(f"{number}: {line[:90]}")
        self.assertEqual(offenders, [],
                         "a JS string literal spans lines: the f-string turned "
                         "a single-backslash \\n into a real newline")

    def test_every_json_constant_the_page_defines_parses(self):
        from pathlib import Path

        root = Path(__file__).resolve().parent.parent
        claims_file = root / "projects/e3m1-decompiled/claims.json"
        if not claims_file.exists():
            raise unittest.SkipTest("no claim panel to embed")
        page = _pack(json.loads(claims_file.read_text(encoding="utf-8")))
        script = page[page.index("<script>"):]
        found = 0
        for line in script.splitlines():
            stripped = line.strip()
            if not re.match(r"^const (NODES|FACTS|ASPECTS)=", stripped):
                continue
            for blob in re.findall(
                    r"=(\[.*?\]|\{.*?\});const |=(\[.*\]|\{.*\});$", stripped):
                json.loads(next(part for part in blob if part))
                found += 1
        self.assertGreaterEqual(found, 2)

    def test_the_pack_is_unchanged_without_the_claim_flags(self):
        """The tool has to keep working for anyone who does not pass them."""
        page = _pack()
        self.assertIn("const FACTS={}", page)
        self.assertIn("XMapEdit", page)

    def test_the_orientation_is_never_flipped(self):
        """+Y down is XMapEdit's, it is where the owner reads the map, and it
        is the one thing the pack may not be adapted on."""
        import inspect
        import sys
        from pathlib import Path

        sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
        import review_pack

        source = inspect.getsource(review_pack.build)
        self.assertIn("XMapEdit's orientation: +Y down. Never flip.", source)
        self.assertIn("(p[1] - min_y) * scale", source)


if __name__ == "__main__":
    unittest.main()
