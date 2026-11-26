"""Where The Signal Box is looked at from: named sets of poses in plan units, each aimed at a point.

    python -m tools.look signal-box --list
    python -m tools.look signal-box --set start -o work/signal-box

A pose is `(x, y, toward x, toward y, horiz, note)`. One plan unit is 1,024 Build units. The plan is drawn in
`level/build.py`'s docstring: the lane runs north (low y) from y 24 to the track at y 4..8, the box is east of it.
"""

from bloodmap.visual import HORIZ_DOWN, HORIZ_LEVEL, HORIZ_UP

LEVEL, UP, DOWN = HORIZ_LEVEL, HORIZ_UP, HORIZ_DOWN

POSE_SETS = {
    "start": {
        "a_start": (4.0, 23.0, 4.0, 6.0, LEVEL, "from the start, up the lane to the crossing"),
        "b_gate": (3.0, 10.0, 4.0, 2.0, LEVEL, "at the crossing, the shut gate across the road"),
        "c_track": (-10.0, 6.5, 20.0, 7.0, LEVEL, "along the track from the west, the box on the right"),
        "d_box": (3.0, 16.0, 12.0, 11.5, LEVEL, "the box's door from the lane"),
    },
    "inside": {
        "e_locking": (9.6, 13.4, 15.0, 11.5, LEVEL, "the locking room toward the stair"),
        "f_stair": (11.0, 11.5, 22.0, 11.5, UP, "up the stair to the lever room"),
        "g_frame": (25.0, 10.0, 25.0, 14.0, LEVEL, "the lever frame on the south wall"),
        "h_windows": (25.0, 13.4, 25.0, 6.0, LEVEL, "out of the windows onto the track"),
    },
    "beyond": {
        "i_far": (4.0, 2.0, 4.0, -8.0, LEVEL, "the far road and the way out"),
    },
}
