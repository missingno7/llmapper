"""Campaign-modal Blood sprite appearance for known types.

Build renders ``picnum``, not the type name. Leaving pickups at tile 0 shows the
default/empty masonry tile. Values are the modal (type -> picnum / repeat /
cstat / pal) counts from the original ``maps/blood/E*.MAP`` campaign files.

They were, at least. The table was written by hand and twelve of its fields did
not match the mode they claimed to be, which nothing noticed until a key in this
level came out half again too big and `tools.mine_sprite_heights` said so. The
disagreements were not close ones -- all 29 campaign keys of type 100 use repeat
32 against the table's 48, and all 546 sprites of type 201 use picnum 2820 and
pal 3 against the table's 3584 and 0 -- so they are corrected here to what the
corpus actually does.

`tests/test_item_display.py` now re-derives the whole table from the maps, so a
hand-written value that drifts from the campaign fails rather than waits.
"""

from __future__ import annotations

from typing import Any

# type_id -> appearance. status 3 is kStatItem; markers/starts use status 0.
APPEARANCE: dict[int, dict[str, int]] = {
    1: {"picnum": 2528, "cstat": 128, "x_repeat": 64, "y_repeat": 64, "status": 0, "pal": 0},
    2: {"picnum": 2522, "cstat": 128, "x_repeat": 64, "y_repeat": 64, "status": 0, "pal": 5},
    9: {"picnum": 2332, "cstat": 128, "x_repeat": 64, "y_repeat": 64, "status": 0},
    10: {"picnum": 2331, "cstat": 128, "x_repeat": 64, "y_repeat": 64, "status": 0},
    21: {"picnum": 1070, "cstat": 464, "x_repeat": 64, "y_repeat": 40, "status": 0, "pal": 0},
    30: {"picnum": 560, "cstat": 385, "x_repeat": 64, "y_repeat": 64, "status": 0, "pal": 0},
    41: {"picnum": 559, "cstat": 128, "x_repeat": 48, "y_repeat": 48, "status": 3},
    42: {"picnum": 558, "cstat": 128, "x_repeat": 48, "y_repeat": 48, "status": 3},
    43: {"picnum": 524, "cstat": 128, "x_repeat": 48, "y_repeat": 48, "status": 3},
    45: {"picnum": 539, "cstat": 128, "x_repeat": 48, "y_repeat": 48, "status": 3},
    46: {"picnum": 526, "cstat": 128, "x_repeat": 48, "y_repeat": 48, "status": 3},
    60: {"picnum": 618, "cstat": 384, "x_repeat": 40, "y_repeat": 40, "status": 3},
    67: {"picnum": 619, "cstat": 128, "x_repeat": 48, "y_repeat": 48, "status": 3},
    68: {"picnum": 812, "cstat": 128, "x_repeat": 48, "y_repeat": 48, "status": 3},
    69: {"picnum": 813, "cstat": 128, "x_repeat": 48, "y_repeat": 48, "status": 3},
    72: {"picnum": 817, "cstat": 128, "x_repeat": 48, "y_repeat": 48, "status": 3},
    73: {"picnum": 548, "cstat": 128, "x_repeat": 24, "y_repeat": 24, "status": 3},
    76: {"picnum": 816, "cstat": 128, "x_repeat": 48, "y_repeat": 48, "status": 3},
    100: {"picnum": 2552, "cstat": 128, "x_repeat": 32, "y_repeat": 32, "status": 3},
    101: {"picnum": 2553, "cstat": 128, "x_repeat": 32, "y_repeat": 32, "status": 3},
    102: {"picnum": 2554, "cstat": 128, "x_repeat": 32, "y_repeat": 32, "status": 3},
    107: {"picnum": 519, "cstat": 128, "x_repeat": 48, "y_repeat": 48, "status": 3},
    113: {"picnum": 896, "cstat": 128, "x_repeat": 40, "y_repeat": 40, "status": 3},
    117: {"picnum": 829, "cstat": 128, "x_repeat": 40, "y_repeat": 40, "status": 3},
    140: {"picnum": 2628, "cstat": 128, "x_repeat": 64, "y_repeat": 64, "status": 3},
    144: {"picnum": 2594, "cstat": 128, "x_repeat": 64, "y_repeat": 64, "status": 3},
    145: {"picnum": 753, "cstat": 384, "x_repeat": 64, "y_repeat": 64, "status": 3},
    146: {"picnum": 753, "cstat": 384, "x_repeat": 64, "y_repeat": 64, "status": 3},
    201: {"picnum": 2820, "cstat": 384, "x_repeat": 40, "y_repeat": 40, "status": 6, "pal": 3},
}

# Native Blood liquid floor family (ART picanm 1120-1126). Tile 90 is mixed-use
# masonry/unknown and does not read as water. Underwater looks up at 1120.
WATER_FLOOR_PICNUM = 1120
WATER_CEILING_PICNUM = 1120
UNDERWATER_FLOOR_PICNUM = 568


def sprite_appearance(type_id: int, **overrides: Any) -> dict[str, Any]:
    """Return type plus campaign-modal display fields, with optional overrides."""
    payload: dict[str, Any] = {"type": int(type_id)}
    payload.update(APPEARANCE.get(int(type_id), {"picnum": 0}))
    payload.update(overrides)
    return payload
