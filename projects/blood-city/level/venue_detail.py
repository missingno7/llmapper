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

import props


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
    ("theatre", "aldermack_foyer", "north", 0.70, 793),
    ("theatre", "aldermack_backstage", "south", 0.45, 431),
    ("theatre", "pawn_shop", "north", 0.75, 269),
    ("mall", "unit_a", "north", 0.30, 965),
    ("mall", "unit_b", "west", 0.68, 269),
    ("mall", "unit_c", "north", 0.68, 610),
    ("mall", "unit_d", "west", 0.30, 965),
    ("mall", "unit_e", "east", 0.72, 269),
    ("church", "nave", "north", 0.20, 847),
    ("church", "nave", "west", 0.62, 167),
    ("church", "narthex", "north", 0.45, 617),
    ("church", "crypt_stair", "east", 0.35, 789),
    ("station", "cellar", "east", 0.62, 52),
    ("station", "hall", "north", 0.36, 929),
)

# The observer established a dark, otherwise featureless tunnel at the station
# entrance.  Two brackets mark the entry and the stair head: they make the
# corridor legible as a maintained service space without turning every room
# into a lamp gallery.  The sources belong to visible props; LightBomb derives
# the shade variation from them.
LIGHT_DETAILS = (
    ("station", "hall", "south", 0.24, props.FLAME, 2.5),
    ("station", "hall", "south", 0.76, props.FLAME, 2.5),
)


def _solid_face(layout: Any, room: Any, preferred: str) -> str | None:
    faces = props.solid_faces(layout, room.region_id, props.room_rect(room))
    if preferred in faces:
        return preferred
    if not faces:
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
           light_intensity: float | None = None) -> bool:
    face = _solid_face(layout, room, preferred)
    if face is None:
        return False
    props.mount_on_wall(layout, placement_id, room, face, tile, t=t,
                        emits_light=emits_light,
                        light_intensity=light_intensity)
    return True


def apply(layout: Any, contexts: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Place deliberate, material-supported venue detail and source lights."""
    report = {"wall_details": 0, "light_sources": 0, "skipped": []}
    for index, (context, room_name, face, t, tile) in enumerate(WALL_DETAILS):
        room = contexts.get(context, {}).get(room_name)
        if room is None:
            report["skipped"].append(f"{context}:{room_name}:missing")
            continue
        if _mount(layout, f"venue:{context}:{room_name}:{index}", room,
                  face, t, tile):
            report["wall_details"] += 1
        else:
            report["skipped"].append(f"{context}:{room_name}:no_solid_wall")
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
