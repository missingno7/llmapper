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
face; the style steps down its own size ladder rather than failing.
"""

from __future__ import annotations



import props
import wallplane

#: (sign id, room key, face, text, **style**, height in player heights).
#:
#: The fifth column used to be a bare palette and the size was whatever
#: the old `fit_size` could get on the wall -- so a look was half authored
#: and half accident. It is a `wallplane.STYLES` name now: a measured
#: (size, palette, shade) combination the campaign actually writes, which
#: steps down its own ladder when the wall is short. `works` is the look
#: DWE puts on POWER PLANT; `department` is MEDLAB and OPERATIONS; `breach`
#: is WALL BREACH and CONTROL ROOM.
#:
#: Height 1.4 puts a fascia just above a doorway; 0.9 is eye level.
SIGNS = [
    # --- Theatre Row: the commercial frontages ---------------------------
    ("aldermack", "theatre:aldermack_foyer", "south", "ALDERMACK", "fascia", 1.5),
    ("saloon", "theatre:saloon_main", "east", "WHISKEY", "banner", 1.3),
    ("parlor", "theatre:parlor_gallery", "east", "SHOOTING", "fascia", 1.3),
    ("pawn", "theatre:pawn_shop", "west", "PAWN", "fascia", 1.3),
    ("backstage", "theatre:aldermack_backstage", "north", "STAGE DOOR",
     "notice", 1.2),
    # --- the church -------------------------------------------------------
    # The nave's name is written by `venue_detail.COMPOSITIONS` instead --
    # under the hanging it belongs to, rather than as a loose word competing
    # with it for the room's ONE solid wall.  Two passes writing the same
    # word on the same wall is how it came to be written behind a 2,048 x
    # 32,768 tapestry in the first place.
    ("crypt", "church:crypt_stair", "east", "CRYPT", "notice", 1.2),
    # --- the works and its station ---------------------------------------
    ("station", "station:cellar", "north", "PUMP HOUSE", "works", 1.2),
    # --- the Arcade.  DukCity names roughly ten uses per map on its walls;
    # Gravesend had five venues in the whole city, which is the gap that
    # reading Duke's signage exposed.  Each unit says what it is.
    ("apothecary", "mall:unit_b", "north", "APOTHECARY", "fascia", 1.3),
    ("ironmonger", "mall:unit_c", "north", "IRONMONGER", "banner", 1.3),
    ("bookseller", "mall:unit_e", "south", "BOOKS", "fascia", 1.3),
    ("tobacco", "mall:unit_f", "south", "TOBACCO", "fascia", 1.3),
    ("mallservice", "mall:service", "east", "STAFF ONLY", "department", 1.2),
    # --- the sewer: the words that tell you where you are -----------------
    ("outfall", "sewer:pump_room", "north", "OUTFALL", "breach", 1.2),
    ("annex", "sewer:east_annex", "east", "NO EXIT", "breach", 1.2),
]


#: Signs on a street facade, where the room behind has no wall to spare.
#: A mall concourse has an opening on every face -- that is what makes it a
#: concourse -- so its name goes where a real one goes: outside, beside the
#: door.  (region key, segment, text, palette, height)
STREET_SIGNS = [
    ("street:market_slip", ((39936, 46592), (39936, 48128)),
     "THE ARCADE", "fascia", 1.6),
]


#: `fit_size` used to live here: it picked the largest of
#: `lettering.SIZES` that fitted the wall, independently of the sign's
#: palette, so a sign's look was half authored and half accident.  A
#: `wallplane.TextStyle` owns both halves -- it knows its own size and the
#: ladder it may step down -- so choosing one is the style's job now.

#: A sign may run nearly the full wall; the 256-unit inset props use to
#: keep a brazier off a corner cost ST GALLOWS its wall.
SIGN_INSET = 96


def _span(rect, face: str) -> float:
    a1, a2 = props.face_segment(rect, face, inset=SIGN_INSET)
    return ((a2[0] - a1[0]) ** 2 + (a2[1] - a1[1]) ** 2) ** 0.5


def write(layout, rooms: dict) -> dict:
    """Write every sign whose room exists and whose wall is long enough."""
    report = {"written": 0, "letters": 0, "missing": [], "no_room": []}
    for sign_id, key, face, text, style, height in SIGNS:
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
        a1, a2 = props.face_segment(rect, face, inset=SIGN_INSET)
        # Through `wallplane`, not `write_on_wall`: the word is reserved as
        # one rectangle and moved -- along the wall first, then up or down --
        # until it covers nothing.  St Gallow's sign used to be written at a
        # fixed height straight through a 2,048 x 32,768 hanging, every
        # letter of it 100% covered.
        ids = wallplane.text(layout, f"sign:{sign_id}", room.region_id,
                             a1, a2, words=text, style=style,
                             height_player_heights=height)
        if not ids:
            report["no_room"].append((sign_id, text))
            continue
        report["written"] += 1
        report["letters"] += len(ids)
    for sign_id, key, segment, text, style, height in (
            (f"street_{i}", k, seg, t, st, h)
            for i, (k, seg, t, st, h) in enumerate(STREET_SIGNS)):
        region_id = rooms.get(key)
        if region_id is None:
            report["missing"].append(key)
            continue
        a1, a2 = segment
        ids = wallplane.text(layout, f"sign:{sign_id}", region_id, a1, a2,
                             words=text, style=style,
                             height_player_heights=height)
        if not ids:
            report["no_room"].append((sign_id, text))
            continue
        report["written"] += 1
        report["letters"] += len(ids)
    return report
