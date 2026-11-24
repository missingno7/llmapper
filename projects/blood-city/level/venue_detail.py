"""Signature detail for the city’s major interiors.

The generic grime pass correctly dresses only the campaign's small share of
ordinary rooms.  A named venue is different: it needs a few stable cues that
say *saloon*, *shop*, *theatre*, *church*, or *service stair* before a combat
sprite is encountered.  This layer deliberately has no random choice.  Each
tile is selected through ``props.props_for``'s mined surface associations, and
each placement is attached only to a solid wall of the room that owns it.

It is not a second prop system.  It is a short declaration of intentional
exceptions to the generic 12% grime distribution.
"""

from __future__ import annotations

from typing import Any

from bloodmap.placement import PLAYER_HEIGHT
import props
import wallplane


# (context, room key, preferred face, fraction along face, tile)
#
# The tiles below are all returned by props.props_for for the owning room's
# material triple.  They are not decorative guesses: 269/965 describe the
# saloon/shop/common register, the theatre/parlor choices come from their own
# wall associations, and the church/service choices from those rooms' mined
# combinations.
WALL_DETAILS = (
    ("theatre", "saloon_main", "north", 0.23, 269),
    ("theatre", "saloon_main", "west", 0.72, 965),
    ("theatre", "parlor_gallery", "north", 0.25, 823),
    ("theatre", "parlor_range", "west", 0.62, 761),
    ("theatre", "pawn_shop", "north", 0.75, 269),
    ("church", "nave", "west", 0.62, 167, {"preferred_only": True}),
    ("church", "narthex", "north", 0.45, 617),
    ("church", "crypt_stair", "east", 0.35, 789),
    ("station", "cellar", "east", 0.62, 52),
    ("station", "hall", "north", 0.36, 929),
)

#: **Compositions**: a wall carrying more than one thing, arranged.
#:
#: Owner: "you can have a painting and description under it... text can have
#: different sizes... the whole text doesn't even need to be one colour."
#: `wallplane.composition` stacks blocks downward from a top height, each
#: reserving its own rectangle, so a caption sits under its painting instead
#: of through it -- which is what the nave's sign used to do.
#:
#: (context, room, preferred face, t, top in player heights, blocks)
#:
#: Every tile here is one `props.props_for` already returns for the owning
#: room; the arrangement is what is new, not the vocabulary. The palettes are
#: `lettering.PALETTES`, named for where the campaign uses them: `sign` is its
#: commonest at 53 letters, `dim` and `stencil` are its quieter ones.
COMPOSITIONS = (
    # St Gallow's, the room the owner named. The hanging is 2,048 x 32,768
    # units and the nave has exactly ONE solid wall; every letter of the
    # nave's sign used to be written across that wall at a fixed height,
    # straight through the hanging, at 100% coverage. Now the word is the
    # hanging's caption. Shorten the hanging by three repeat units so its
    # corner clears the vault at the original anchor z. Keep the caption
    # at the original gap of 19,379 from its drawn lower edge.
    ("church", "nave", "south", 0.50, 67424 / PLAYER_HEIGHT, "nave_hanging", (
        ("painting", 847, {"y_repeat": 61, "gap": 19379 / PLAYER_HEIGHT}),
        ("caption", "ST GALLOWS", {"style": "fascia"}),
    )),
    # A drop capital and a coloured initial: a sequence pads with its last
    # value, so `(112, 72)` is one big letter and the rest small, and
    # `("warning", "sign")` colours only the first. Three blocks, three
    # heights, on the inside face -- the fascia over the street door is a
    # separate sign in `signage.SIGNS`, which is what a theatre has.
    # (The pawn shop's LOANS column used to be composed here, on whichever
    # of its walls was the longest solid one. The pledge room pierced that
    # wall and the column moved to the far end of the shop, out of every
    # view. It is written beside the bars now, by `l3_theatre.populate`,
    # which knows where the bars are.)
)


def _blocks(rows):
    import wallplane
    out = []
    for kind, value, options in rows:
        if kind == "painting":
            out.append(wallplane.painting(int(value), **options))
        else:
            out.append(wallplane.caption(str(value), **options))
    return out


# The observer established a dark, otherwise featureless tunnel at the station
# entrance.  Two brackets mark the entry and the stair head: they make the
# corridor legible as a maintained service space without turning every room
# into a lamp gallery.  The sources belong to visible props; LightBomb derives
# the shade variation from them.
LIGHT_DETAILS = (
    ("station", "hall", "south", 0.24, props.FLAME, 2.5),
    ("station", "hall", "south", 0.76, props.FLAME, 2.5),
)


def _solid_face(layout: Any, room: Any, preferred: str, *, preferred_only=False) -> str | None:
    faces = props.solid_faces(layout, room.region_id, props.room_rect(room))
    if preferred in faces:
        return preferred
    if not faces or preferred_only:
        return None
    # Preserve a strong composition even if a future geometry revision moves a
    # doorway: select the longest remaining wall instead of mounting over it.
    rect = props.room_rect(room)
    return max(
        faces,
        key=lambda face: sum(
            (b - a) ** 2
            for a, b in zip(props.face_segment(rect, face)[0],
                            props.face_segment(rect, face)[1])),
    )


def _mount(layout: Any, placement_id: str, room: Any, preferred: str,
           t: float, tile: int, *, emits_light: bool = False,
           light_intensity: float | None = None, preferred_only=False) -> bool:
    face = _solid_face(layout, room, preferred, preferred_only=preferred_only)
    if face is None:
        return False
    return props.mount_on_wall(layout, placement_id, room, face, tile, t=t,
                               emits_light=emits_light,
                               light_intensity=light_intensity) is not None


def apply(layout: Any, contexts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Place deliberate, material-supported venue detail and source lights."""
    import wallplane

    report = {"wall_details": 0, "light_sources": 0, "compositions": 0,
              "composed_sprites": 0, "skipped": []}
    # Compositions first: they are the most deliberate thing on any wall they
    # touch, and everything after this asks the same occupancy for what is
    # left.
    for context, room_name, face, t, top, group, rows in COMPOSITIONS:
        room = contexts.get(context, {}).get(room_name)
        if room is None:
            report["skipped"].append(f"composition:{context}:{room_name}:missing")
            continue
        chosen = _solid_face(layout, room, face)
        if chosen is None:
            report["skipped"].append(f"composition:{group}:no_solid_wall")
            continue
        # A shallow inset: a composition is the wall's main event and wants
        # the width, where a loose sign is inset further to stay clear of the
        # corners.
        a1, a2 = props.face_segment(props.room_rect(room), chosen, inset=128)
        got = wallplane.composition(
            layout, f"venue:{group}", room.region_id, a1, a2,
            blocks=_blocks(rows), t=t, top_player_heights=top)
        if got["placed"]:
            report["compositions"] += 1
            report["composed_sprites"] += len(got["placed"])
        for note in got["skipped"]:
            report["skipped"].append(f"composition:{group}:{note}")

    for index, (context, room_name, face, t, tile, *options) in enumerate(WALL_DETAILS):
        room = contexts.get(context, {}).get(room_name)
        if room is None:
            report["skipped"].append(f"{context}:{room_name}:missing")
            continue
        if _mount(layout, f"venue:{context}:{room_name}:{index}", room,
                    face, t, tile, **(options[0] if options else {})):
            report["wall_details"] += 1
        else:
            report["skipped"].append(f"{context}:{room_name}:no_room")
    for index, (context, room_name, face, t, tile, intensity) in enumerate(LIGHT_DETAILS):
        room = contexts.get(context, {}).get(room_name)
        if room is None:
            report["skipped"].append(f"light:{context}:{room_name}:missing")
            continue
        if _mount(layout, f"light:venue:{context}:{room_name}:{index}", room,
                  face, t, tile, emits_light=True, light_intensity=intensity):
            report["light_sources"] += 1
        else:
            report["skipped"].append(f"light:{context}:{room_name}:no_solid_wall")
    return report
