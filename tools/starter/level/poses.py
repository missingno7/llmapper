"""Where __TITLE__ is looked at from: named sets of poses in plan units, each aimed at a point.

    python -m tools.look __NAME__ --list
    python -m tools.look __NAME__ --set start -o work/__NAME__

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
        "a_entry": (0.8, 1.5, 3.0, 1.5, LEVEL, "from where the player starts, toward the passage"),
        "b_hall": (7.6, 1.5, 12.0, 1.5, LEVEL, "into the hall from the passage's mouth"),
        "c_stair": (9.0, -0.5, 13.0, 1.5, LEVEL, "the hall's stair from its north-west corner"),
    },
}
