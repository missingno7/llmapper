"""What the city says: shop names, street names, warnings.

Owner: "we should have ability to write sprite glyph texts... it can be
used to make some commercials and richer looking city with interesting
stuff to read."  The capability already exists and is already measured --
`bloodmap.lettering`, built for the monastery project off the 36 words the
campaign spells out (STORAGE, RATDOGS, FEINMAN MEATS, HMS VICTOR, TRACK A).
Blood has no text primitive; it has an alphabet in the ART at tiles
3808-3833 and it lays one sprite per letter, wall-aligned at cstat 208,
pitched at 1.45 times a letter's drawn width, recoloured by palette.

This module is the city's copy: which words go where, at what size, in
which palette.  The palettes are named for what they are for, so a sign's
colour carries meaning -- `sign` for commerce, `warning` for hazard,
`stencil` for utility, `rust` for what has been there too long.

A word needs wall.  At size 64 a letter is 128 units wide and the pitch is
185, so an eight-letter word wants about 1.6 plan units of uninterrupted
face; `fit_size` picks the largest size that fits rather than failing.
"""

from __future__ import annotations

from bloodmap.lettering import (LetteringError, SIZES, drawn_width,
                                text_width, write_on_wall)

import props
import wallplane

#: (sign id, room key, face, text, palette, height in player heights).
#: Height 1.4 puts a fascia just above a doorway; 0.9 is eye level.
SIGNS = [
    # --- Theatre Row: the commercial frontages ---------------------------
    ("aldermack", "theatre:aldermack_foyer", "south", "ALDERMACK", "sign", 1.5),
    ("saloon", "theatre:saloon_main", "east", "WHISKEY", "rust", 1.3),
    ("parlor", "theatre:parlor_gallery", "east", "SHOOTING", "sign", 1.3),
    ("pawn", "theatre:pawn_shop", "west", "PAWN", "sign", 1.3),
    ("backstage", "theatre:aldermack_backstage", "north", "STAGE DOOR",
     "stencil", 1.2),
    # --- the church -------------------------------------------------------
    # The nave's name is written by `venue_detail.COMPOSITIONS` instead --
    # under the hanging it belongs to, rather than as a loose word competing
    # with it for the room's ONE solid wall.  Two passes writing the same
    # word on the same wall is how it came to be written behind a 2,048 x
    # 32,768 tapestry in the first place.
    ("crypt", "church:crypt_stair", "east", "CRYPT", "dim", 1.2),
    # --- the works and its station ---------------------------------------
    ("station", "station:cellar", "north", "PUMP HOUSE", "stencil", 1.2),
    # --- the Arcade.  DukCity names roughly ten uses per map on its walls;
    # Gravesend had five venues in the whole city, which is the gap that
    # reading Duke's signage exposed.  Each unit says what it is.
    ("apothecary", "mall:unit_b", "north", "APOTHECARY", "sign", 1.3),
    ("ironmonger", "mall:unit_c", "north", "IRONMONGER", "rust", 1.3),
    ("bookseller", "mall:unit_e", "south", "BOOKS", "sign", 1.3),
    ("tobacco", "mall:unit_f", "south", "TOBACCO", "faded", 1.3),
    ("mallservice", "mall:service", "east", "STAFF ONLY", "warning", 1.2),
    # --- the sewer: the words that tell you where you are -----------------
    ("outfall", "sewer:pump_room", "north", "OUTFALL", "warning", 1.2),
    ("annex", "sewer:east_annex", "east", "NO EXIT", "warning", 1.2),
]


#: Signs on a street facade, where the room behind has no wall to spare.
#: A mall concourse has an opening on every face -- that is what makes it a
#: concourse -- so its name goes where a real one goes: outside, beside the
#: door.  (region key, segment, text, palette, height)
STREET_SIGNS = [
    ("street:market_slip", ((39936, 46592), (39936, 48128)),
     "THE ARCADE", "sign", 1.6),
]


def fit_size(text: str, span: float, *, largest: int = 96) -> int | None:
    """The biggest campaign size this word fits at, or None if none does."""
    for size in sorted((s for s in SIZES if s <= largest), reverse=True):
        if text_width(text, size) + drawn_width(size) <= span:
            return size
    return None


#: A sign may run nearly the full wall; the 256-unit inset props use to
#: keep a brazier off a corner cost ST GALLOWS its wall.
SIGN_INSET = 96


def _span(rect, face: str) -> float:
    a1, a2 = props.face_segment(rect, face, inset=SIGN_INSET)
    return ((a2[0] - a1[0]) ** 2 + (a2[1] - a1[1]) ** 2) ** 0.5


def write(layout, rooms: dict) -> dict:
    """Write every sign whose room exists and whose wall is long enough."""
    report = {"written": 0, "letters": 0, "too_long": [], "missing": [],
              "no_room": []}
    for sign_id, key, face, text, palette, height in SIGNS:
        room = rooms.get(key)
        if room is None:
            report["missing"].append(key)
            continue
        rect = props.room_rect(room)
        faces = props.solid_faces(layout, room.region_id, rect)
        if face not in faces:
            # The declared wall turned out to carry a portal; take the
            # longest solid one instead rather than writing on a doorway.
            if not faces:
                report["missing"].append(f"{key}:no solid wall")
                continue
            face = max(faces, key=lambda f: _span(rect, f))
        size = fit_size(text, _span(rect, face))
        if size is None:
            report["too_long"].append((sign_id, text))
            continue
        a1, a2 = props.face_segment(rect, face, inset=SIGN_INSET)
        # Through `wallplane`, not `write_on_wall`: the word is reserved as
        # one rectangle and moved -- along the wall first, then up or down --
        # until it covers nothing.  St Gallow's sign used to be written at a
        # fixed height straight through a 2,048 x 32,768 hanging, every
        # letter of it 100% covered.
        ids = wallplane.text(layout, f"sign:{sign_id}", room.region_id,
                             a1, a2, words=text,
                             height_player_heights=height,
                             size=size, palette=palette)
        if not ids:
            report["no_room"].append((sign_id, text))
            continue
        report["written"] += 1
        report["letters"] += len(ids)
    for sign_id, key, segment, text, palette, height in (
            (f"street_{i}", k, seg, t, pal, h)
            for i, (k, seg, t, pal, h) in enumerate(STREET_SIGNS)):
        region_id = rooms.get(key)
        if region_id is None:
            report["missing"].append(key)
            continue
        a1, a2 = segment
        span = ((a2[0] - a1[0]) ** 2 + (a2[1] - a1[1]) ** 2) ** 0.5
        size = fit_size(text, span)
        if size is None:
            report["too_long"].append((sign_id, text))
            continue
        ids = wallplane.text(layout, f"sign:{sign_id}", region_id, a1, a2,
                             words=text, height_player_heights=height,
                             size=size, palette=palette)
        if not ids:
            report["no_room"].append((sign_id, text))
            continue
        report["written"] += 1
        report["letters"] += len(ids)
    return report
