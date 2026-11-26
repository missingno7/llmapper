"""Where The Cold Store is looked at from: named sets of poses in plan units, each aimed at a point.

    python -m tools.look cold-store --list
    python -m tools.look cold-store --set start -o work/cold-store

A pose is `(x, y, toward x, toward y, horiz, note)`, with an optional seventh
item naming the floor it stands on where places are stacked
(`bloodmap.viewplan.named_poses`). One plan unit is 1,024 Build units. A fixed
set stays as it is, so that before and after line up; add a fresh set for a
new place.
"""

from bloodmap.visual import HORIZ_DOWN, HORIZ_LEVEL, HORIZ_UP

LEVEL, UP, DOWN = HORIZ_LEVEL, HORIZ_UP, HORIZ_DOWN

POSE_SETS = {
    "start": {
        "a_entry": (0.6, 2.2, 3.0, 1.5, LEVEL, "from where the player starts, toward the passage"),
        "b_store": (1.5, 1.2, 1.5, -1.5, LEVEL, "the side store from the entry: the key"),
        "c_door": (4.2, 1.5, 7.0, 1.5, LEVEL, "down the passage to the locked door"),
    },
    "hall": {
        "a_in": (7.6, 1.5, 12.0, 1.5, LEVEL, "into the hall from its door"),
        "b_stair": (9.0, -0.5, 13.5, 1.5, LEVEL, "the stair from the hall's north-west corner"),
        "c_back": (12.5, 3.2, 7.2, 1.5, LEVEL, "back at the door from the hall's floor"),
        "d_landing": (16.6, 1.5, 18.2, 1.5, LEVEL, "the landing and the way out", -20480),
    },
}
