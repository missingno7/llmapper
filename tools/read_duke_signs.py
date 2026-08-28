"""What Duke's maps say, read out of their letter sprites.

Duke 3D writes on its walls the same way Blood does -- one sprite per
character out of a font in the ART -- but with a different alphabet and a
different mapping.  `reference/duke3d/DEFS.CON` names them:

    define STARTALPHANUM 2822      the small font
    define ENDALPHANUM   2915
    define BIGALPHANUM   2940
    define MINIFONT      3072

and the mapping is positional from ASCII `!`: tile = start + (ord(c) - 33).
So 2854 is `A`, 2837 is `0`, and a word is a run of these sprites sharing a
wall.

This is a reading tool, not an authoring one.  The point is that a sign
tells you what its designer thought the room was for -- which is evidence
about intent that no geometry census can give.

    python tools/read_duke_signs.py DukCity1 DukCity2 DukCity3 DukCity4
"""

from __future__ import annotations

import argparse
import collections
import math
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from bloodmap.duke import read_duke_map

#: (base tile for `!`, last tile).  The bases are not all what DEFS.CON
#: literally says: `BIGALPHANUM 2940` is the tile of **A**, not of `!`, so
#: the big font's `!` sits 32 tiles lower at 2908.  Decoded with 2940 as
#: the base, "SHOPPING CENTER" reads out as "3(/00).'#%.4%2" -- every
#: character shifted by exactly the ASCII gap between `!` and `A`.  The
#: same correction applies to MINIFONT.
#: (first tile, the character that tile draws, last tile).  Only the first
#: font is laid out the way `DEFS.CON` suggests:
#:
#:   2822..2915  the full ASCII font, 2822 draws `!`  (STARTALPHANUM)
#:   2940..2965  capitals only, 2940 draws `A`        (BIGALPHANUM)
#:   2966..2991  capitals again, a second style
#:
#: `BIGALPHANUM 2940` is the tile of **A**, not of `!`: decoded from `!`,
#: the sign that reads SHOPPING CENTER comes out as "3(/00).'#%.4%2" --
#: every character shifted by the ASCII gap between the two.  And the block
#: above it is not that font's lowercase.  Read as a second A-Z it spells
#: SWISS BANKS, SBS CLUB, BANK, PUB, INFO: DukCity1's businesses.
FONTS = (
    ("alphanum", 2822, "!", 2915),
    ("big", 2940, "A", 2965),
    ("big2", 2966, "A", 2991),
)


def char_from(picnum: int):
    """The character this tile draws, and which font it belongs to."""
    for name, first, draws, last in FONTS:
        if first <= picnum <= last:
            code = ord(draws) + picnum - first
            if 33 <= code <= 126:
                return chr(code), name
    return None


def read_signs(m) -> list[dict]:
    """Every word written in letter sprites, with where it is."""
    groups: dict[tuple, list] = collections.defaultdict(list)
    for sp in m.sprites:
        found = char_from(sp.picnum)
        if found is None:
            continue
        character, font = found
        # A word shares a wall: same sector, same height, same facing.
        groups[(sp.sector, round(sp.z / 512), sp.angle, font)].append(
            (sp.x, sp.y, character, sp.picnum))
    out = []
    for (sector, _z, angle, font), items in groups.items():
        # Letters run perpendicular to a wall sprite's normal; reading along
        # the wrong perpendicular spells the word backwards.
        radians = (angle - 512) * math.pi / 1024.0
        ux, uy = math.cos(radians), math.sin(radians)
        items.sort(key=lambda row: row[0] * ux + row[1] * uy)
        word = "".join(row[2] for row in items)
        if len(word.strip()) < 2:
            continue
        out.append({"text": word, "sector": sector, "font": font,
                    "letters": len(items)})
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("maps", nargs="+")
    ap.add_argument("--dir", default="maps/duke3d")
    args = ap.parse_args(argv)
    for name in args.maps:
        path = pathlib.Path(args.dir) / f"{name}.map"
        try:
            m = read_duke_map(path)
        except Exception as exc:
            print(f"!! {name}: {exc}")
            continue
        signs = read_signs(m)
        total = sum(s["letters"] for s in signs)
        print(f"\n== {name}: {len(signs)} signs, {total} letters")
        for sign in sorted(signs, key=lambda s: -s["letters"]):
            print(f"   [{sign['font']:8s} sector {sign['sector']:4d}] "
                  f"{sign['text']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
