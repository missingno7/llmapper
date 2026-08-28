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

    python -m tools.mine_decoration --maps maps/blood --art reference/blood \
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
#: can be used as a limit. Tile 1044 has p10 5.09 and a true minimum of 3.64.
DECORATION: dict[int, dict[str, Any]] = {
    795: {"x_repeat": 64, "y_repeat": 64, "cstat": 224, "shade": -8,
        "uses": 159, "maps": 18, "size_share": 0.604, "cstat_share": 0.358,
        "height_min": 0.18, "height_max": 1.45,
        "height_p10": 0.73, "height_median": 1.45, "height_p90": 1.45,
        "scales_with_room": False},
    2915: {"x_repeat": 64, "y_repeat": 64, "cstat": 224, "shade": -8,
        "uses": 147, "maps": 5, "size_share": 0.837, "cstat_share": 0.973,
        "height_min": 2.91, "height_max": 5.82,
        "height_p10": 2.91, "height_median": 2.91, "height_p90": 4.36,
        "scales_with_room": False},
    506: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -128,
        "uses": 138, "maps": 15, "size_share": 0.971, "cstat_share": 0.464,
        "height_min": 1.47, "height_max": 1.95,
        "height_p10": 1.95, "height_median": 1.95, "height_p90": 1.95,
        "scales_with_room": False},
    68: {"x_repeat": 64, "y_repeat": 64, "cstat": 465, "shade": -8,
        "uses": 111, "maps": 13, "size_share": 0.45, "cstat_share": 0.36,
        "height_min": 0.09, "height_max": 0.77,
        "height_p10": 0.18, "height_median": 0.36, "height_p90": 0.73,
        "scales_with_room": False},
    2101: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -128,
        "uses": 91, "maps": 19, "size_share": 0.527, "cstat_share": 0.857,
        "height_min": 0.42, "height_max": 3.99,
        "height_p10": 1.26, "height_median": 1.68, "height_p90": 2.52,
        "scales_with_room": True},
    660: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -8,
        "uses": 86, "maps": 12, "size_share": 0.674, "cstat_share": 0.965,
        "height_min": 1.09, "height_max": 3.45,
        "height_p10": 1.45, "height_median": 1.45, "height_p90": 2.73,
        "scales_with_room": False},
    641: {"x_repeat": 64, "y_repeat": 64, "cstat": 129, "shade": -128,
        "uses": 71, "maps": 11, "size_share": 0.958, "cstat_share": 0.338,
        "height_min": 4.36, "height_max": 7.27,
        "height_p10": 5.82, "height_median": 5.82, "height_p90": 5.82,
        "scales_with_room": False},
    2540: {"x_repeat": 32, "y_repeat": 32, "cstat": 464, "shade": -8,
        "uses": 69, "maps": 29, "size_share": 0.899, "cstat_share": 0.565,
        "height_min": 0.99, "height_max": 2.64,
        "height_p10": 1.32, "height_median": 1.32, "height_p90": 1.32,
        "scales_with_room": False},
    664: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -8,
        "uses": 68, "maps": 12, "size_share": 0.868, "cstat_share": 0.956,
        "height_min": 2.86, "height_max": 7.16,
        "height_p10": 4.3, "height_median": 5.73, "height_p90": 5.73,
        "scales_with_room": False},
    3566: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -128,
        "uses": 65, "maps": 23, "size_share": 0.492, "cstat_share": 0.938,
        "height_min": 0.78, "height_max": 9.41,
        "height_p10": 2.35, "height_median": 3.14, "height_p90": 6.27,
        "scales_with_room": False},
    1044: {"x_repeat": 64, "y_repeat": 64, "cstat": 401, "shade": -8,
        "uses": 63, "maps": 18, "size_share": 0.397, "cstat_share": 0.365,
        "height_min": 3.64, "height_max": 12.36,
        "height_p10": 5.09, "height_median": 5.82, "height_p90": 8.0,
        "scales_with_room": True},
    580: {"x_repeat": 64, "y_repeat": 64, "cstat": 129, "shade": -128,
        "uses": 59, "maps": 8, "size_share": 0.983, "cstat_share": 0.492,
        "height_min": 3.22, "height_max": 3.68,
        "height_p10": 3.68, "height_median": 3.68, "height_p90": 3.68,
        "scales_with_room": False},
    915: {"x_repeat": 64, "y_repeat": 64, "cstat": 208, "shade": -8,
        "uses": 56, "maps": 20, "size_share": 0.518, "cstat_share": 0.482,
        "height_min": 1.5, "height_max": 4.5,
        "height_p10": 2.5, "height_median": 4.0, "height_p90": 4.0,
        "scales_with_room": False},
    256: {"x_repeat": 48, "y_repeat": 64, "cstat": 417, "shade": -8,
        "uses": 55, "maps": 8, "size_share": 0.709, "cstat_share": 0.636,
        "height_min": 2.91, "height_max": 11.64,
        "height_p10": 2.91, "height_median": 5.82, "height_p90": 5.82,
        "scales_with_room": False},
    1701: {"x_repeat": 48, "y_repeat": 48, "cstat": 384, "shade": -128,
        "uses": 53, "maps": 11, "size_share": 0.509, "cstat_share": 0.377,
        "height_min": 2.03, "height_max": 5.41,
        "height_p10": 4.06, "height_median": 4.06, "height_p90": 5.41,
        "scales_with_room": False},
    191: {"x_repeat": 32, "y_repeat": 32, "cstat": 417, "shade": 0,
        "uses": 49, "maps": 4, "size_share": 0.51, "cstat_share": 0.918,
        "height_min": 2.91, "height_max": 5.82,
        "height_p10": 2.91, "height_median": 2.91, "height_p90": 5.82,
        "scales_with_room": False},
    2493: {"x_repeat": 64, "y_repeat": 64, "cstat": 385, "shade": -128,
        "uses": 43, "maps": 4, "size_share": 1.0, "cstat_share": 0.605,
        "height_min": 3.5, "height_max": 3.5,
        "height_p10": 3.5, "height_median": 3.5, "height_p90": 3.5,
        "scales_with_room": False},
    713: {"x_repeat": 64, "y_repeat": 64, "cstat": 160, "shade": -8,
        "uses": 41, "maps": 18, "size_share": 0.732, "cstat_share": 0.171,
        "height_min": 1.09, "height_max": 2.91,
        "height_p10": 1.45, "height_median": 2.91, "height_p90": 2.91,
        "scales_with_room": False},
    668: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -8,
        "uses": 41, "maps": 6, "size_share": 0.976, "cstat_share": 1.0,
        "height_min": 5.82, "height_max": 7.27,
        "height_p10": 5.82, "height_median": 5.82, "height_p90": 5.82,
        "scales_with_room": False},
    732: {"x_repeat": 64, "y_repeat": 64, "cstat": 224, "shade": -8,
        "uses": 38, "maps": 17, "size_share": 0.658, "cstat_share": 0.342,
        "height_min": 0.73, "height_max": 2.91,
        "height_p10": 1.82, "height_median": 2.91, "height_p90": 2.91,
        "scales_with_room": False},
    6: {"x_repeat": 64, "y_repeat": 64, "cstat": 465, "shade": 16,
        "uses": 35, "maps": 5, "size_share": 0.857, "cstat_share": 0.686,
        "height_min": 0.09, "height_max": 0.36,
        "height_p10": 0.18, "height_median": 0.36, "height_p90": 0.36,
        "scales_with_room": False},
    470: {"x_repeat": 64, "y_repeat": 64, "cstat": 481, "shade": -6,
        "uses": 35, "maps": 3, "size_share": 0.857, "cstat_share": 0.457,
        "height_min": 1.82, "height_max": 2.91,
        "height_p10": 2.55, "height_median": 2.91, "height_p90": 2.91,
        "scales_with_room": False},
    754: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -8,
        "uses": 31, "maps": 9, "size_share": 0.226, "cstat_share": 1.0,
        "height_min": 0.36, "height_max": 9.94,
        "height_p10": 1.42, "height_median": 3.55, "height_p90": 5.68,
        "scales_with_room": True},
    2542: {"x_repeat": 32, "y_repeat": 32, "cstat": 464, "shade": -8,
        "uses": 31, "maps": 15, "size_share": 0.581, "cstat_share": 0.645,
        "height_min": 0.99, "height_max": 2.31,
        "height_p10": 0.99, "height_median": 1.32, "height_p90": 1.65,
        "scales_with_room": False},
    2545: {"x_repeat": 32, "y_repeat": 32, "cstat": 464, "shade": -8,
        "uses": 30, "maps": 15, "size_share": 0.567, "cstat_share": 0.8,
        "height_min": 0.99, "height_max": 2.64,
        "height_p10": 0.99, "height_median": 1.32, "height_p90": 2.31,
        "scales_with_room": False},
    502: {"x_repeat": 64, "y_repeat": 64, "cstat": 417, "shade": -8,
        "uses": 29, "maps": 6, "size_share": 0.724, "cstat_share": 0.897,
        "height_min": 0.91, "height_max": 4.73,
        "height_p10": 1.82, "height_median": 2.91, "height_p90": 3.27,
        "scales_with_room": True},
    511: {"x_repeat": 64, "y_repeat": 64, "cstat": 144, "shade": -128,
        "uses": 29, "maps": 6, "size_share": 1.0, "cstat_share": 0.621,
        "height_min": 0.18, "height_max": 0.18,
        "height_p10": 0.18, "height_median": 0.18, "height_p90": 0.18,
        "scales_with_room": False},
    510: {"x_repeat": 64, "y_repeat": 64, "cstat": 208, "shade": -128,
        "uses": 28, "maps": 6, "size_share": 1.0, "cstat_share": 0.571,
        "height_min": 1.45, "height_max": 1.45,
        "height_p10": 1.45, "height_median": 1.45, "height_p90": 1.45,
        "scales_with_room": False},
    1: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": 2,
        "uses": 28, "maps": 4, "size_share": 1.0, "cstat_share": 0.429,
        "height_min": 0.73, "height_max": 0.73,
        "height_p10": 0.73, "height_median": 0.73, "height_p90": 0.73,
        "scales_with_room": False},
    371: {"x_repeat": 64, "y_repeat": 64, "cstat": 481, "shade": 24,
        "uses": 28, "maps": 1, "size_share": 0.571, "cstat_share": 0.964,
        "height_min": 1.45, "height_max": 2.91,
        "height_p10": 1.45, "height_median": 2.91, "height_p90": 2.91,
        "scales_with_room": True},
    2541: {"x_repeat": 32, "y_repeat": 32, "cstat": 464, "shade": -8,
        "uses": 27, "maps": 13, "size_share": 0.63, "cstat_share": 0.556,
        "height_min": 0.99, "height_max": 2.64,
        "height_p10": 1.32, "height_median": 1.32, "height_p90": 2.31,
        "scales_with_room": False},
    2543: {"x_repeat": 32, "y_repeat": 32, "cstat": 464, "shade": -8,
        "uses": 26, "maps": 9, "size_share": 0.923, "cstat_share": 0.731,
        "height_min": 0.99, "height_max": 1.32,
        "height_p10": 1.32, "height_median": 1.32, "height_p90": 1.32,
        "scales_with_room": False},
    929: {"x_repeat": 64, "y_repeat": 64, "cstat": 464, "shade": -8,
        "uses": 24, "maps": 16, "size_share": 0.708, "cstat_share": 0.5,
        "height_min": 1.51, "height_max": 2.41,
        "height_p10": 1.81, "height_median": 2.41, "height_p90": 2.41,
        "scales_with_room": False},
    515: {"x_repeat": 64, "y_repeat": 64, "cstat": 224, "shade": -8,
        "uses": 23, "maps": 6, "size_share": 0.609, "cstat_share": 0.783,
        "height_min": 1.82, "height_max": 6.55,
        "height_p10": 2.18, "height_median": 2.91, "height_p90": 3.27,
        "scales_with_room": False},
    0: {"x_repeat": 64, "y_repeat": 64, "cstat": 481, "shade": 12,
        "uses": 23, "maps": 5, "size_share": 1.0, "cstat_share": 0.348,
        "height_min": 2.91, "height_max": 2.91,
        "height_p10": 2.91, "height_median": 2.91, "height_p90": 2.91,
        "scales_with_room": False},
    672: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -8,
        "uses": 20, "maps": 9, "size_share": 0.5, "cstat_share": 1.0,
        "height_min": 2.11, "height_max": 11.98,
        "height_p10": 3.52, "height_median": 5.64, "height_p90": 9.16,
        "scales_with_room": False},
    838: {"x_repeat": 16, "y_repeat": 16, "cstat": 208, "shade": -8,
        "uses": 18, "maps": 1, "size_share": 1.0, "cstat_share": 0.944,
        "height_min": 0.34, "height_max": 0.34,
        "height_p10": 0.34, "height_median": 0.34, "height_p90": 0.34,
        "scales_with_room": False},
    384: {"x_repeat": 64, "y_repeat": 64, "cstat": 209, "shade": 31,
        "uses": 18, "maps": 1, "size_share": 1.0, "cstat_share": 1.0,
        "height_min": 5.82, "height_max": 5.82,
        "height_p10": 5.82, "height_median": 5.82, "height_p90": 5.82,
        "scales_with_room": False},
    381: {"x_repeat": 64, "y_repeat": 64, "cstat": 209, "shade": 45,
        "uses": 18, "maps": 1, "size_share": 1.0, "cstat_share": 1.0,
        "height_min": 5.82, "height_max": 5.82,
        "height_p10": 5.82, "height_median": 5.82, "height_p90": 5.82,
        "scales_with_room": False},
    69: {"x_repeat": 64, "y_repeat": 64, "cstat": 464, "shade": -4,
        "uses": 18, "maps": 4, "size_share": 0.722, "cstat_share": 0.611,
        "height_min": 0.36, "height_max": 0.82,
        "height_p10": 0.73, "height_median": 0.73, "height_p90": 0.82,
        "scales_with_room": False},
    3812: {"x_repeat": 48, "y_repeat": 48, "cstat": 208, "shade": -8,
        "uses": 17, "maps": 4, "size_share": 0.471, "cstat_share": 1.0,
        "height_min": 0.38, "height_max": 1.75,
        "height_p10": 0.38, "height_median": 0.5, "height_p90": 0.75,
        "scales_with_room": False},
    731: {"x_repeat": 64, "y_repeat": 64, "cstat": 224, "shade": -8,
        "uses": 17, "maps": 8, "size_share": 0.765, "cstat_share": 0.353,
        "height_min": 1.09, "height_max": 2.91,
        "height_p10": 1.45, "height_median": 2.91, "height_p90": 2.91,
        "scales_with_room": False},
    58: {"x_repeat": 64, "y_repeat": 32, "cstat": 145, "shade": -8,
        "uses": 16, "maps": 4, "size_share": 0.562, "cstat_share": 0.562,
        "height_min": 1.45, "height_max": 2.91,
        "height_p10": 1.45, "height_median": 1.45, "height_p90": 2.91,
        "scales_with_room": False},
    2544: {"x_repeat": 32, "y_repeat": 32, "cstat": 208, "shade": -8,
        "uses": 16, "maps": 8, "size_share": 0.625, "cstat_share": 0.562,
        "height_min": 0.99, "height_max": 2.64,
        "height_p10": 1.19, "height_median": 1.32, "height_p90": 1.32,
        "scales_with_room": False},
    363: {"x_repeat": 64, "y_repeat": 64, "cstat": 481, "shade": 46,
        "uses": 16, "maps": 1, "size_share": 1.0, "cstat_share": 1.0,
        "height_min": 2.91, "height_max": 2.91,
        "height_p10": 2.91, "height_median": 2.91, "height_p90": 2.91,
        "scales_with_room": False},
    730: {"x_repeat": 64, "y_repeat": 64, "cstat": 224, "shade": -8,
        "uses": 15, "maps": 5, "size_share": 1.0, "cstat_share": 0.4,
        "height_min": 1.45, "height_max": 1.45,
        "height_p10": 1.45, "height_median": 1.45, "height_p90": 1.45,
        "scales_with_room": False},
    20: {"x_repeat": 64, "y_repeat": 64, "cstat": 225, "shade": -2,
        "uses": 15, "maps": 3, "size_share": 0.933, "cstat_share": 0.533,
        "height_min": 1.45, "height_max": 2.91,
        "height_p10": 2.91, "height_median": 2.91, "height_p90": 2.91,
        "scales_with_room": True},
    640: {"x_repeat": 64, "y_repeat": 64, "cstat": 385, "shade": -8,
        "uses": 14, "maps": 3, "size_share": 1.0, "cstat_share": 0.571,
        "height_min": 3.41, "height_max": 3.41,
        "height_p10": 3.41, "height_median": 3.41, "height_p90": 3.41,
        "scales_with_room": False},
    632: {"x_repeat": 96, "y_repeat": 112, "cstat": 385, "shade": -8,
        "uses": 14, "maps": 2, "size_share": 0.571, "cstat_share": 0.929,
        "height_min": 2.41, "height_max": 4.22,
        "height_p10": 2.41, "height_median": 4.22, "height_p90": 4.22,
        "scales_with_room": False},
    1050: {"x_repeat": 32, "y_repeat": 32, "cstat": 208, "shade": 0,
        "uses": 13, "maps": 4, "size_share": 0.692, "cstat_share": 0.846,
        "height_min": 0.73, "height_max": 0.91,
        "height_p10": 0.73, "height_median": 0.73, "height_p90": 0.91,
        "scales_with_room": True},
    252: {"x_repeat": 158, "y_repeat": 98, "cstat": 464, "shade": 38,
        "uses": 13, "maps": 2, "size_share": 0.308, "cstat_share": 0.923,
        "height_min": 2.91, "height_max": 4.45,
        "height_p10": 3.27, "height_median": 3.55, "height_p90": 4.45,
        "scales_with_room": True},
    1067: {"x_repeat": 96, "y_repeat": 80, "cstat": 144, "shade": 11,
        "uses": 13, "maps": 2, "size_share": 0.538, "cstat_share": 1.0,
        "height_min": 4.27, "height_max": 7.27,
        "height_p10": 4.36, "height_median": 7.27, "height_p90": 7.27,
        "scales_with_room": False},
    436: {"x_repeat": 64, "y_repeat": 64, "cstat": 465, "shade": 0,
        "uses": 13, "maps": 2, "size_share": 0.923, "cstat_share": 0.615,
        "height_min": 0.27, "height_max": 0.73,
        "height_p10": 0.73, "height_median": 0.73, "height_p90": 0.73,
        "scales_with_room": True},
    3808: {"x_repeat": 64, "y_repeat": 64, "cstat": 208, "shade": -8,
        "uses": 12, "maps": 5, "size_share": 0.25, "cstat_share": 1.0,
        "height_min": 0.38, "height_max": 1.75,
        "height_p10": 0.38, "height_median": 0.75, "height_p90": 0.81,
        "scales_with_room": False},
    708: {"x_repeat": 64, "y_repeat": 64, "cstat": 208, "shade": 41,
        "uses": 12, "maps": 2, "size_share": 0.667, "cstat_share": 1.0,
        "height_min": 1.39, "height_max": 2.23,
        "height_p10": 1.39, "height_median": 2.23, "height_p90": 2.23,
        "scales_with_room": True},
    694: {"x_repeat": 64, "y_repeat": 64, "cstat": 129, "shade": -8,
        "uses": 12, "maps": 4, "size_share": 0.5, "cstat_share": 0.333,
        "height_min": 4.36, "height_max": 5.82,
        "height_p10": 4.36, "height_median": 5.09, "height_p90": 5.82,
        "scales_with_room": False},
    469: {"x_repeat": 48, "y_repeat": 48, "cstat": 385, "shade": -8,
        "uses": 12, "maps": 7, "size_share": 0.417, "cstat_share": 0.667,
        "height_min": 2.1, "height_max": 4.89,
        "height_p10": 2.1, "height_median": 3.84, "height_p90": 4.19,
        "scales_with_room": False},
    54: {"x_repeat": 64, "y_repeat": 64, "cstat": 144, "shade": -8,
        "uses": 12, "maps": 2, "size_share": 1.0, "cstat_share": 0.75,
        "height_min": 2.91, "height_max": 2.91,
        "height_p10": 2.91, "height_median": 2.91, "height_p90": 2.91,
        "scales_with_room": False},
    2580: {"x_repeat": 64, "y_repeat": 64, "cstat": 129, "shade": 18,
        "uses": 12, "maps": 1, "size_share": 0.917, "cstat_share": 0.5,
        "height_min": 5.82, "height_max": 6.18,
        "height_p10": 5.82, "height_median": 5.82, "height_p90": 5.82,
        "scales_with_room": False},
    692: {"x_repeat": 64, "y_repeat": 64, "cstat": 128, "shade": -8,
        "uses": 12, "maps": 3, "size_share": 0.333, "cstat_share": 0.5,
        "height_min": 3.64, "height_max": 5.82,
        "height_p10": 3.64, "height_median": 4.73, "height_p90": 5.82,
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
