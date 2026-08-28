"""Writing on the walls, the way Blood writes on them.

Blood has no text primitive. What it has is an alphabet in the ART -- tiles 3808
to 3833, `A` through `Z`, monospace at 8 by 11 pixels -- and its levels spell
things out one sprite per letter. E1M4 is full of it: STORAGE over a warehouse
door, RATDOGS on a crate, FORTUNES, SEEING IS BELIEVING. E1M2 marks TRACK A,
E2M1 names a ship HMS VICTOR, E3M2 has FEINMAN MEATS and a LOADING bay.

Every convention here is measured off those 36 words:

``cstat``
    208 in 108 of the 132 letters -- wall-aligned (16), hitscan (64) and 128.
    A letter lies flat along the wall it is painted on.

``size``
    square repeats, always, at 48, 64, 72, 96, 104, 136 or 224. The drawn width
    of a letter is ``x_repeat * 8 / 4``, its height ``y_repeat * 4 * 11``.

``pitch``
    the gap from one letter's centre to the next is **1.45 times its drawn
    width**, and remarkably steadily: 1.33, 1.50, 1.45, 1.41, 1.48 and 1.51 at
    the six sizes with enough samples to measure. So a word is laid out on its
    own size, not on a fixed spacing.

``pal``
    the colour. This is the part with no equivalent anywhere else in the format:
    the same 26 tiles are recoloured by palette lookup, and the campaign uses
    eight of them -- 4 most (53 letters), then 0, 5, 11, 12, 14, 13 and 3. A
    sign's colour is a property of the sign, not of the tile.

``shade``
    -8, in 95 of 132.

Direction matters and is easy to get backwards. A wall sprite's angle is the
normal of its face, so text runs *perpendicular* to it -- and reading the
campaign along the wrong perpendicular turns STORAGE into EGAROTS, which is how
this module's first draft was found to be wrong.
"""

from __future__ import annotations

from math import hypot
from typing import Any

#: Tile 3808 is `A`, and the alphabet runs unbroken to `Z` at 3833.
FIRST_LETTER = 3808
LAST_LETTER = 3833

#: Every letter tile is 8 by 11 pixels. The font is monospace, which is what
#: makes a single pitch work.
LETTER_WIDTH = 8
LETTER_HEIGHT = 11

#: Wall-aligned, hitscan, 128. 108 of the campaign's 132 letters.
LETTER_CSTAT = 208

#: Centre-to-centre spacing, as a multiple of a letter's drawn width.
PITCH = 1.45

#: The campaign's own shade for a letter.
LETTER_SHADE = -8

#: Sizes the campaign writes at, smallest to largest. `x_repeat`, and `y_repeat`
#: equals it: 16,746 of Blood's 18,858 sprites are drawn square and every letter
#: is among them.
SIZES = (48, 64, 72, 96, 104, 136, 224)

#: The palettes the campaign paints letters in, by how much it uses each. Named
#: from where they appear rather than from a colour, because the colour is a
#: lookup table in the RFF and the name should say what it is for.
PALETTES = {
    "default": 0,       # 31 letters: LOADING, HMS
    "sign": 4,          # 53, the commonest: SEEING IS BELIEVING, WHOA
    "warning": 5,       # 17: TRACK A, MEATS
    "cold": 11,         # 11: FEINMAN
    "rust": 12,         # 9: RATDOGS
    "stencil": 14,      # 7: STORAGE
    "faded": 13,        # 2
    "dim": 3,           # 2
}


class LetteringError(ValueError):
    """Something that cannot be written with this alphabet."""


def tile_for(character: str) -> int | None:
    """The tile for a letter, or None for a space."""
    if character == " ":
        return None
    upper = character.upper()
    if not ("A" <= upper <= "Z"):
        raise LetteringError(
            f"Blood's alphabet is A-Z and a space; {character!r} is not in it")
    return FIRST_LETTER + ord(upper) - ord("A")


def letter_from(picnum: int) -> str | None:
    if FIRST_LETTER <= picnum <= LAST_LETTER:
        return chr(ord("A") + picnum - FIRST_LETTER)
    return None


def drawn_width(size: int) -> float:
    """A letter's width in map units at this repeat."""
    return size * LETTER_WIDTH / 4.0


def pitch_for(size: int) -> float:
    return drawn_width(size) * PITCH


def text_width(text: str, size: int) -> float:
    """How much wall a word needs, centre of first letter to centre of last."""
    return max(0, len(text) - 1) * pitch_for(size)


def write_on_wall(layout: Any, sign_id: str, region_id: str, *,
                  a1: tuple[int, int], a2: tuple[int, int], text: str,
                  height_player_heights: float,
                  t: float = 0.5, size: int = 64,
                  palette: str | int = "default",
                  offset_player_widths: float = 0.12,
                  shade: int = LETTER_SHADE) -> list[str]:
    """Paint a word along a wall, one sprite per letter.

    `t` is where the *middle* of the word sits along the wall, so a caller
    centres a sign by leaving it alone. Returns the placement ids.
    """
    if not text.strip():
        raise LetteringError(f"{sign_id}: nothing to write")
    pal = PALETTES.get(palette, palette) if isinstance(palette, str) else int(palette)
    if isinstance(pal, str):
        raise LetteringError(
            f"{sign_id}: no palette named {palette!r}; "
            f"known: {', '.join(sorted(PALETTES))}")

    span = hypot(a2[0] - a1[0], a2[1] - a1[1])
    if span <= 0:
        raise LetteringError(f"{sign_id}: the wall has no length")
    needed = text_width(text, size) + drawn_width(size)
    if needed > span:
        raise LetteringError(
            f"{sign_id}: {text!r} at size {size} needs {needed:.0f} units of wall "
            f"and the wall is {span:.0f}; use a smaller size or a longer wall")

    pitch = pitch_for(size)
    middle = (len(text) - 1) / 2.0
    out = []
    for index, character in enumerate(text):
        picnum = tile_for(character)
        if picnum is None:
            continue                       # a space is a gap, not a sprite
        offset = (index - middle) * pitch
        placement_id = f"{sign_id}_{index:02d}"
        layout.place_on_wall(
            placement_id, region_id, a1=a1, a2=a2,
            t=t + offset / span,
            height_player_heights=height_player_heights,
            offset_player_widths=offset_player_widths,
            type=0, picnum=picnum, cstat=LETTER_CSTAT, shade=shade,
            pal=pal, x_repeat=size, y_repeat=size,
        )
        out.append(placement_id)
    return out


def read_sign(disk: Any, sector: int | None = None) -> list[tuple[str, list[int]]]:
    """Every word written in letter sprites, and the palettes it uses.

    The inverse of `write_on_wall`, and the way this module was checked: run it
    over the campaign and it should say STORAGE, not EGAROTS.
    """
    import math
    from collections import defaultdict

    groups: dict[tuple[int, int, int], list[tuple[int, int, int, int]]] = defaultdict(list)
    for sprite in disk.sprites:
        fields = sprite.fields
        picnum = int(fields["picnum"])
        if letter_from(picnum) is None:
            continue
        here = int(fields["sector"])
        if sector is not None and here != sector:
            continue
        groups[(here, int(fields["z"]), int(fields["angle"]))].append(
            (int(fields["x"]), int(fields["y"]), picnum, int(fields["pal"])))

    out = []
    for (_, _, angle), items in groups.items():
        radians = (angle - 512) * math.pi / 1024.0
        ux, uy = math.cos(radians), math.sin(radians)
        items.sort(key=lambda row: row[0] * ux + row[1] * uy)
        word = "".join(letter_from(row[2]) or "" for row in items)
        out.append((word, sorted({row[3] for row in items})))
    return out
