"""Campaign-modal appearance for Blood decoration tiles.

``item_display.sprite_appearance`` covers sprites that carry a gameplay
*type*.  A decoration has type 0, so nothing there applies to it, and the
only other help the vocabulary offers is ``sprite_repeats``, which asks the
author how many player heights tall the thing should be.

The campaign says that is the wrong question.  Of the 3159 visible untyped
sprites in reachable sectors, 60% are drawn at ``y_repeat`` 64 -- the tile's
natural size -- and 73% at a power of two, from only 53 distinct repeats in
the whole game.  29 of the 60 well-attested tiles are never resized at all, and
only 11 genuinely scale with the room they sit in.  The drawn height is a
consequence of choosing the tile, not an input.

Size and mounting are separate questions and are answered separately.  Tile
641 is drawn at the same size in 96% of its 71 uses but hung several
different ways; asking one question about both would throw its size away.
``height_p10``/``height_p90`` bound what the campaign ever draws a tile at,
in player heights, so a caller that must depart from the canonical size can
still stay inside the range the game uses.

Regenerate with::

    python -m tools.mine_decoration --art reference/blood --min-uses 12 \
        -o knowledge/blood/design/decoration-v1.json
"""

from __future__ import annotations

from typing import Any

#: How settled a mode has to be before it is worth inheriting rather than
#: deciding.  Below this the campaign itself is not consistent.
CONFIDENT_SHARE = 0.6

#: picnum -> the campaign's usual drawing of that decoration.
#: ``uses``/``maps`` are the evidence; ``*_share`` is how settled each mode is;
#: ``height_min``/``height_max`` are the player heights this tile is *ever*
#: drawn at, and ``height_p10``/``height_p90`` where it usually is. The two are
#: not interchangeable: 6% of the campaign's own decorations sit outside their
#: tile's p10..p90, so the percentile band describes a habit and only the bounds
#: can be used as a limit. Tile 1044 has p10 1.69 and a true minimum of 1.21.
DECORATION: dict[int, dict[str, Any]] = {
    795: {"x_repeat": 64, "y_repeat": 64, "cstat": 224, "shade": -8,
        "uses": 159, "maps": 18, "size_share": 0.604, "cstat_share": 0.358,
        "height_min": 0.06, "height_max": 0.48,
        "height_p10": 0.24, "height_median": 0.48, "height_p90": 0.48,
        "scales_with_room": False},
    2915: {"x_repeat": 64, "y_repeat": 64, "cstat": 224, "shade": -8,
        "uses": 147, "maps": 5, "size_share": 0.837, "cstat_share": 0.973,
        "height_min": 0.97, "height_max": 1.93,
        "height_p10": 0.97, "height_median": 0.97, "height_p90": 1.45,
        "scales_with_room": False},
    506: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -128,
        "uses": 138, "maps": 15, "size_share": 0.971, "cstat_share": 0.464,
        "height_min": 0.49, "height_max": 0.65,
        "height_p10": 0.65, "height_median": 0.65, "height_p90": 0.65,
        "scales_with_room": False},
    68: {"x_repeat": 64, "y_repeat": 64, "cstat": 465, "shade": -8,
        "uses": 111, "maps": 13, "size_share": 0.45, "cstat_share": 0.36,
        "height_min": 0.03, "height_max": 0.26,
        "height_p10": 0.06, "height_median": 0.12, "height_p90": 0.24,
        "scales_with_room": False},
    2101: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -128,
        "uses": 91, "maps": 19, "size_share": 0.527, "cstat_share": 0.857,
        "height_min": 0.14, "height_max": 1.33,
        "height_p10": 0.42, "height_median": 0.56, "height_p90": 0.84,
        "scales_with_room": True},
    660: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -8,
        "uses": 86, "maps": 12, "size_share": 0.674, "cstat_share": 0.965,
        "height_min": 0.36, "height_max": 1.15,
        "height_p10": 0.48, "height_median": 0.48, "height_p90": 0.91,
        "scales_with_room": False},
    641: {"x_repeat": 64, "y_repeat": 64, "cstat": 129, "shade": -128,
        "uses": 71, "maps": 11, "size_share": 0.958, "cstat_share": 0.338,
        "height_min": 1.45, "height_max": 2.42,
        "height_p10": 1.93, "height_median": 1.93, "height_p90": 1.93,
        "scales_with_room": False},
    2540: {"x_repeat": 32, "y_repeat": 32, "cstat": 464, "shade": -8,
        "uses": 69, "maps": 29, "size_share": 0.899, "cstat_share": 0.565,
        "height_min": 0.33, "height_max": 0.88,
        "height_p10": 0.44, "height_median": 0.44, "height_p90": 0.44,
        "scales_with_room": False},
    664: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -8,
        "uses": 68, "maps": 12, "size_share": 0.868, "cstat_share": 0.956,
        "height_min": 0.95, "height_max": 2.38,
        "height_p10": 1.43, "height_median": 1.9, "height_p90": 1.9,
        "scales_with_room": False},
    3566: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -128,
        "uses": 65, "maps": 23, "size_share": 0.492, "cstat_share": 0.938,
        "height_min": 0.26, "height_max": 3.12,
        "height_p10": 0.78, "height_median": 1.04, "height_p90": 2.08,
        "scales_with_room": False},
    1044: {"x_repeat": 64, "y_repeat": 64, "cstat": 401, "shade": -8,
        "uses": 63, "maps": 18, "size_share": 0.397, "cstat_share": 0.365,
        "height_min": 1.21, "height_max": 4.11,
        "height_p10": 1.69, "height_median": 1.93, "height_p90": 2.66,
        "scales_with_room": True},
    580: {"x_repeat": 64, "y_repeat": 64, "cstat": 129, "shade": -128,
        "uses": 59, "maps": 8, "size_share": 0.983, "cstat_share": 0.492,
        "height_min": 1.07, "height_max": 1.22,
        "height_p10": 1.22, "height_median": 1.22, "height_p90": 1.22,
        "scales_with_room": False},
    915: {"x_repeat": 64, "y_repeat": 64, "cstat": 208, "shade": -8,
        "uses": 56, "maps": 20, "size_share": 0.518, "cstat_share": 0.482,
        "height_min": 0.5, "height_max": 1.49,
        "height_p10": 0.83, "height_median": 1.33, "height_p90": 1.33,
        "scales_with_room": False},
    256: {"x_repeat": 48, "y_repeat": 64, "cstat": 417, "shade": -8,
        "uses": 55, "maps": 8, "size_share": 0.709, "cstat_share": 0.636,
        "height_min": 0.97, "height_max": 3.86,
        "height_p10": 0.97, "height_median": 1.93, "height_p90": 1.93,
        "scales_with_room": False},
    1701: {"x_repeat": 48, "y_repeat": 48, "cstat": 384, "shade": -128,
        "uses": 53, "maps": 11, "size_share": 0.509, "cstat_share": 0.377,
        "height_min": 0.67, "height_max": 1.8,
        "height_p10": 1.35, "height_median": 1.35, "height_p90": 1.8,
        "scales_with_room": False},
    191: {"x_repeat": 32, "y_repeat": 32, "cstat": 417, "shade": 0,
        "uses": 49, "maps": 4, "size_share": 0.51, "cstat_share": 0.918,
        "height_min": 0.97, "height_max": 1.93,
        "height_p10": 0.97, "height_median": 0.97, "height_p90": 1.93,
        "scales_with_room": False},
    2493: {"x_repeat": 64, "y_repeat": 64, "cstat": 385, "shade": -128,
        "uses": 43, "maps": 4, "size_share": 1.0, "cstat_share": 0.605,
        "height_min": 1.16, "height_max": 1.16,
        "height_p10": 1.16, "height_median": 1.16, "height_p90": 1.16,
        "scales_with_room": False},
    713: {"x_repeat": 64, "y_repeat": 64, "cstat": 160, "shade": -8,
        "uses": 41, "maps": 18, "size_share": 0.732, "cstat_share": 0.171,
        "height_min": 0.36, "height_max": 0.97,
        "height_p10": 0.48, "height_median": 0.97, "height_p90": 0.97,
        "scales_with_room": False},
    668: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -8,
        "uses": 41, "maps": 6, "size_share": 0.976, "cstat_share": 1.0,
        "height_min": 1.93, "height_max": 2.42,
        "height_p10": 1.93, "height_median": 1.93, "height_p90": 1.93,
        "scales_with_room": False},
    732: {"x_repeat": 64, "y_repeat": 64, "cstat": 224, "shade": -8,
        "uses": 38, "maps": 17, "size_share": 0.658, "cstat_share": 0.342,
        "height_min": 0.24, "height_max": 0.97,
        "height_p10": 0.6, "height_median": 0.97, "height_p90": 0.97,
        "scales_with_room": False},
    6: {"x_repeat": 64, "y_repeat": 64, "cstat": 465, "shade": 16,
        "uses": 35, "maps": 5, "size_share": 0.857, "cstat_share": 0.686,
        "height_min": 0.03, "height_max": 0.12,
        "height_p10": 0.06, "height_median": 0.12, "height_p90": 0.12,
        "scales_with_room": False},
    470: {"x_repeat": 64, "y_repeat": 64, "cstat": 481, "shade": -6,
        "uses": 35, "maps": 3, "size_share": 0.857, "cstat_share": 0.457,
        "height_min": 0.6, "height_max": 0.97,
        "height_p10": 0.85, "height_median": 0.97, "height_p90": 0.97,
        "scales_with_room": False},
    754: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -8,
        "uses": 31, "maps": 9, "size_share": 0.226, "cstat_share": 1.0,
        "height_min": 0.12, "height_max": 3.3,
        "height_p10": 0.47, "height_median": 1.18, "height_p90": 1.89,
        "scales_with_room": True},
    2542: {"x_repeat": 32, "y_repeat": 32, "cstat": 464, "shade": -8,
        "uses": 31, "maps": 15, "size_share": 0.581, "cstat_share": 0.645,
        "height_min": 0.33, "height_max": 0.77,
        "height_p10": 0.33, "height_median": 0.44, "height_p90": 0.55,
        "scales_with_room": False},
    2545: {"x_repeat": 32, "y_repeat": 32, "cstat": 464, "shade": -8,
        "uses": 30, "maps": 15, "size_share": 0.567, "cstat_share": 0.8,
        "height_min": 0.33, "height_max": 0.88,
        "height_p10": 0.33, "height_median": 0.44, "height_p90": 0.77,
        "scales_with_room": False},
    502: {"x_repeat": 64, "y_repeat": 64, "cstat": 417, "shade": -8,
        "uses": 29, "maps": 6, "size_share": 0.724, "cstat_share": 0.897,
        "height_min": 0.3, "height_max": 1.57,
        "height_p10": 0.6, "height_median": 0.97, "height_p90": 1.09,
        "scales_with_room": True},
    511: {"x_repeat": 64, "y_repeat": 64, "cstat": 144, "shade": -128,
        "uses": 29, "maps": 6, "size_share": 1.0, "cstat_share": 0.621,
        "height_min": 0.06, "height_max": 0.06,
        "height_p10": 0.06, "height_median": 0.06, "height_p90": 0.06,
        "scales_with_room": False},
    510: {"x_repeat": 64, "y_repeat": 64, "cstat": 208, "shade": -128,
        "uses": 28, "maps": 6, "size_share": 1.0, "cstat_share": 0.571,
        "height_min": 0.48, "height_max": 0.48,
        "height_p10": 0.48, "height_median": 0.48, "height_p90": 0.48,
        "scales_with_room": False},
    1: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": 2,
        "uses": 28, "maps": 4, "size_share": 1.0, "cstat_share": 0.429,
        "height_min": 0.24, "height_max": 0.24,
        "height_p10": 0.24, "height_median": 0.24, "height_p90": 0.24,
        "scales_with_room": False},
    371: {"x_repeat": 64, "y_repeat": 64, "cstat": 481, "shade": 24,
        "uses": 28, "maps": 1, "size_share": 0.571, "cstat_share": 0.964,
        "height_min": 0.48, "height_max": 0.97,
        "height_p10": 0.48, "height_median": 0.97, "height_p90": 0.97,
        "scales_with_room": True},
    2541: {"x_repeat": 32, "y_repeat": 32, "cstat": 464, "shade": -8,
        "uses": 27, "maps": 13, "size_share": 0.63, "cstat_share": 0.556,
        "height_min": 0.33, "height_max": 0.88,
        "height_p10": 0.44, "height_median": 0.44, "height_p90": 0.77,
        "scales_with_room": False},
    2543: {"x_repeat": 32, "y_repeat": 32, "cstat": 464, "shade": -8,
        "uses": 26, "maps": 9, "size_share": 0.923, "cstat_share": 0.731,
        "height_min": 0.33, "height_max": 0.44,
        "height_p10": 0.44, "height_median": 0.44, "height_p90": 0.44,
        "scales_with_room": False},
    929: {"x_repeat": 64, "y_repeat": 64, "cstat": 464, "shade": -8,
        "uses": 24, "maps": 16, "size_share": 0.708, "cstat_share": 0.5,
        "height_min": 0.5, "height_max": 0.8,
        "height_p10": 0.6, "height_median": 0.8, "height_p90": 0.8,
        "scales_with_room": False},
    515: {"x_repeat": 64, "y_repeat": 64, "cstat": 224, "shade": -8,
        "uses": 23, "maps": 6, "size_share": 0.609, "cstat_share": 0.783,
        "height_min": 0.6, "height_max": 2.17,
        "height_p10": 0.72, "height_median": 0.97, "height_p90": 1.09,
        "scales_with_room": False},
    0: {"x_repeat": 64, "y_repeat": 64, "cstat": 481, "shade": 12,
        "uses": 23, "maps": 5, "size_share": 1.0, "cstat_share": 0.348,
        "height_min": 0.97, "height_max": 0.97,
        "height_p10": 0.97, "height_median": 0.97, "height_p90": 0.97,
        "scales_with_room": False},
    672: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -8,
        "uses": 20, "maps": 9, "size_share": 0.5, "cstat_share": 1.0,
        "height_min": 0.7, "height_max": 3.98,
        "height_p10": 1.17, "height_median": 1.87, "height_p90": 3.04,
        "scales_with_room": False},
    838: {"x_repeat": 16, "y_repeat": 16, "cstat": 208, "shade": -8,
        "uses": 18, "maps": 1, "size_share": 1.0, "cstat_share": 0.944,
        "height_min": 0.11, "height_max": 0.11,
        "height_p10": 0.11, "height_median": 0.11, "height_p90": 0.11,
        "scales_with_room": False},
    384: {"x_repeat": 64, "y_repeat": 64, "cstat": 209, "shade": 31,
        "uses": 18, "maps": 1, "size_share": 1.0, "cstat_share": 1.0,
        "height_min": 1.93, "height_max": 1.93,
        "height_p10": 1.93, "height_median": 1.93, "height_p90": 1.93,
        "scales_with_room": False},
    381: {"x_repeat": 64, "y_repeat": 64, "cstat": 209, "shade": 45,
        "uses": 18, "maps": 1, "size_share": 1.0, "cstat_share": 1.0,
        "height_min": 1.93, "height_max": 1.93,
        "height_p10": 1.93, "height_median": 1.93, "height_p90": 1.93,
        "scales_with_room": False},
    69: {"x_repeat": 64, "y_repeat": 64, "cstat": 464, "shade": -4,
        "uses": 18, "maps": 4, "size_share": 0.722, "cstat_share": 0.611,
        "height_min": 0.12, "height_max": 0.27,
        "height_p10": 0.24, "height_median": 0.24, "height_p90": 0.27,
        "scales_with_room": False},
    3812: {"x_repeat": 48, "y_repeat": 48, "cstat": 208, "shade": -8,
        "uses": 17, "maps": 4, "size_share": 0.471, "cstat_share": 1.0,
        "height_min": 0.12, "height_max": 0.58,
        "height_p10": 0.12, "height_median": 0.17, "height_p90": 0.25,
        "scales_with_room": False},
    731: {"x_repeat": 64, "y_repeat": 64, "cstat": 224, "shade": -8,
        "uses": 17, "maps": 8, "size_share": 0.765, "cstat_share": 0.353,
        "height_min": 0.36, "height_max": 0.97,
        "height_p10": 0.48, "height_median": 0.97, "height_p90": 0.97,
        "scales_with_room": False},
    58: {"x_repeat": 64, "y_repeat": 32, "cstat": 145, "shade": -8,
        "uses": 16, "maps": 4, "size_share": 0.562, "cstat_share": 0.562,
        "height_min": 0.48, "height_max": 0.97,
        "height_p10": 0.48, "height_median": 0.48, "height_p90": 0.97,
        "scales_with_room": False},
    2544: {"x_repeat": 32, "y_repeat": 32, "cstat": 208, "shade": -8,
        "uses": 16, "maps": 8, "size_share": 0.625, "cstat_share": 0.562,
        "height_min": 0.33, "height_max": 0.88,
        "height_p10": 0.4, "height_median": 0.44, "height_p90": 0.44,
        "scales_with_room": False},
    363: {"x_repeat": 64, "y_repeat": 64, "cstat": 481, "shade": 46,
        "uses": 16, "maps": 1, "size_share": 1.0, "cstat_share": 1.0,
        "height_min": 0.97, "height_max": 0.97,
        "height_p10": 0.97, "height_median": 0.97, "height_p90": 0.97,
        "scales_with_room": False},
    730: {"x_repeat": 64, "y_repeat": 64, "cstat": 224, "shade": -8,
        "uses": 15, "maps": 5, "size_share": 1.0, "cstat_share": 0.4,
        "height_min": 0.48, "height_max": 0.48,
        "height_p10": 0.48, "height_median": 0.48, "height_p90": 0.48,
        "scales_with_room": False},
    20: {"x_repeat": 64, "y_repeat": 64, "cstat": 225, "shade": -2,
        "uses": 15, "maps": 3, "size_share": 0.933, "cstat_share": 0.533,
        "height_min": 0.48, "height_max": 0.97,
        "height_p10": 0.97, "height_median": 0.97, "height_p90": 0.97,
        "scales_with_room": True},
    640: {"x_repeat": 64, "y_repeat": 64, "cstat": 385, "shade": -8,
        "uses": 14, "maps": 3, "size_share": 1.0, "cstat_share": 0.571,
        "height_min": 1.13, "height_max": 1.13,
        "height_p10": 1.13, "height_median": 1.13, "height_p90": 1.13,
        "scales_with_room": False},
    632: {"x_repeat": 96, "y_repeat": 112, "cstat": 385, "shade": -8,
        "uses": 14, "maps": 2, "size_share": 0.571, "cstat_share": 0.929,
        "height_min": 0.8, "height_max": 1.4,
        "height_p10": 0.8, "height_median": 1.4, "height_p90": 1.4,
        "scales_with_room": False},
    1050: {"x_repeat": 32, "y_repeat": 32, "cstat": 208, "shade": 0,
        "uses": 13, "maps": 4, "size_share": 0.692, "cstat_share": 0.846,
        "height_min": 0.24, "height_max": 0.3,
        "height_p10": 0.24, "height_median": 0.24, "height_p90": 0.3,
        "scales_with_room": True},
    252: {"x_repeat": 158, "y_repeat": 98, "cstat": 464, "shade": 38,
        "uses": 13, "maps": 2, "size_share": 0.308, "cstat_share": 0.923,
        "height_min": 0.97, "height_max": 1.48,
        "height_p10": 1.09, "height_median": 1.18, "height_p90": 1.48,
        "scales_with_room": True},
    1067: {"x_repeat": 96, "y_repeat": 80, "cstat": 144, "shade": 11,
        "uses": 13, "maps": 2, "size_share": 0.538, "cstat_share": 1.0,
        "height_min": 1.42, "height_max": 2.42,
        "height_p10": 1.45, "height_median": 2.42, "height_p90": 2.42,
        "scales_with_room": False},
    436: {"x_repeat": 64, "y_repeat": 64, "cstat": 465, "shade": 0,
        "uses": 13, "maps": 2, "size_share": 0.923, "cstat_share": 0.615,
        "height_min": 0.09, "height_max": 0.24,
        "height_p10": 0.24, "height_median": 0.24, "height_p90": 0.24,
        "scales_with_room": True},
    3808: {"x_repeat": 64, "y_repeat": 64, "cstat": 208, "shade": -8,
        "uses": 12, "maps": 5, "size_share": 0.25, "cstat_share": 1.0,
        "height_min": 0.12, "height_max": 0.58,
        "height_p10": 0.12, "height_median": 0.25, "height_p90": 0.27,
        "scales_with_room": False},
    708: {"x_repeat": 64, "y_repeat": 64, "cstat": 208, "shade": 41,
        "uses": 12, "maps": 2, "size_share": 0.667, "cstat_share": 1.0,
        "height_min": 0.46, "height_max": 0.74,
        "height_p10": 0.46, "height_median": 0.74, "height_p90": 0.74,
        "scales_with_room": True},
    694: {"x_repeat": 64, "y_repeat": 64, "cstat": 129, "shade": -8,
        "uses": 12, "maps": 4, "size_share": 0.5, "cstat_share": 0.333,
        "height_min": 1.45, "height_max": 1.93,
        "height_p10": 1.45, "height_median": 1.69, "height_p90": 1.93,
        "scales_with_room": False},
    469: {"x_repeat": 48, "y_repeat": 48, "cstat": 385, "shade": -8,
        "uses": 12, "maps": 7, "size_share": 0.417, "cstat_share": 0.667,
        "height_min": 0.7, "height_max": 1.62,
        "height_p10": 0.7, "height_median": 1.28, "height_p90": 1.39,
        "scales_with_room": False},
    54: {"x_repeat": 64, "y_repeat": 64, "cstat": 144, "shade": -8,
        "uses": 12, "maps": 2, "size_share": 1.0, "cstat_share": 0.75,
        "height_min": 0.97, "height_max": 0.97,
        "height_p10": 0.97, "height_median": 0.97, "height_p90": 0.97,
        "scales_with_room": False},
    2580: {"x_repeat": 64, "y_repeat": 64, "cstat": 129, "shade": 18,
        "uses": 12, "maps": 1, "size_share": 0.917, "cstat_share": 0.5,
        "height_min": 1.93, "height_max": 2.05,
        "height_p10": 1.93, "height_median": 1.93, "height_p90": 1.93,
        "scales_with_room": False},
    692: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -8,
        "uses": 12, "maps": 3, "size_share": 0.333, "cstat_share": 0.5,
        "height_min": 1.21, "height_max": 1.93,
        "height_p10": 1.21, "height_median": 1.57, "height_p90": 1.93,
        "scales_with_room": True},
}


def decoration_appearance(picnum: int, **overrides: Any) -> dict[str, Any]:
    """Display fields for a decoration tile, as the campaign usually draws it.

    Unknown tiles get the natural size and a plain centred mounting, which is
    what most of the corpus uses; that is a fallback, not evidence.
    """
    record = DECORATION.get(int(picnum))
    payload: dict[str, Any] = {"type": 0, "picnum": int(picnum)}
    if record is None:
        payload.update(x_repeat=64, y_repeat=64, cstat=128, shade=0)
    else:
        payload.update(
            x_repeat=record["x_repeat"], y_repeat=record["y_repeat"],
            cstat=record["cstat"], shade=record["shade"],
        )
    payload.update(overrides)
    return payload


def is_confident_size(picnum: int) -> bool:
    """Whether the campaign draws this tile at one size often enough to copy."""
    record = DECORATION.get(int(picnum))
    return bool(record and record["size_share"] >= CONFIDENT_SHARE)


def is_confident_mounting(picnum: int) -> bool:
    """Whether the campaign hangs this tile one way often enough to copy.

    Separate from the size: a tile can have a settled size and an unsettled
    mounting, and 641 does.
    """
    record = DECORATION.get(int(picnum))
    return bool(record and record["cstat_share"] >= CONFIDENT_SHARE)


def height_range(picnum: int) -> tuple[float, float] | None:
    """Player heights this tile is *usually* drawn at (p10..p90).

    Guidance, not a limit: 6% of the campaign's decorations fall outside their
    own tile's band. Use `height_bounds` to ask whether a size is one Blood
    would ever draw.
    """
    record = DECORATION.get(int(picnum))
    if record is None:
        return None
    return (record["height_p10"], record["height_p90"])


def height_bounds(picnum: int) -> tuple[float, float] | None:
    """Player heights this tile is ever drawn at, or None if unattested."""
    record = DECORATION.get(int(picnum))
    if record is None or "height_min" not in record:
        return None
    return (record["height_min"], record["height_max"])
