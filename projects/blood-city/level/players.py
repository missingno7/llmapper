"""Where players start: eight together on the quay (the first is the game's one), eight apart for Bloodbath.

Every one of the campaign's maps has both (E1M1 and E3M1: eight of type 1, eight of type 2,
pictures 2522 to 2529, the player's number in data 1, z the floor). Type 1's number 0 is
also where a game alone starts (`warp.cpp`: it takes the place of the map's own start),
so it stands on that exactly.
"""

from __future__ import annotations

TOGETHER, APART, FIRST_PICTURE = 1, 2, 2522
#: the seven others, in plan units beside the first
BESIDE = ((-0.9, 0.5), (0.9, 0.5), (-1.8, 0.0), (1.8, 0.0), (-2.7, 0.5), (2.7, 0.5), (0.0, 1.1))
#: Bloodbath: (x, y, floor, the way faced)
BLOODBATH = ((24.0, 51.0, 8192, 1536), (19.0, 36.0, 8192, 0), (28.0, 34.0, 8192, 1536), (21.0, 15.5, 8192, 0),
             (36.5, -1.0, 8192, 512), (53.0, 12.5, 8192, 512), (47.0, 36.0, 8192, 1024), (53.5, 43.5, 8192, 1024))


def place(layout, start: tuple[int, int], region_id: str, angle: int) -> dict:
    """Set both eights down."""
    import gameplay
    floor = layout.regions[region_id].floor_z

    def mark(name, kind, k, region, x, y, z, turn):
        layout.add_sprite(name, region, x=x, y=y, z=z, type=kind, picnum=FIRST_PICTURE + k, cstat=128, status=0, angle=turn,
                          x_repeat=64, y_repeat=64, shade=0, behavior={"data_1": k})
    mark("player:together_0", TOGETHER, 0, region_id, *start, floor, angle)
    for k, (dx, dy) in enumerate(BESIDE, 1):
        region, x, y = gameplay.spot(layout, start[0] / 1024 + dx, start[1] / 1024 + dy, floor, room_for=300)
        mark(f"player:together_{k}", TOGETHER, k, region.region_id, x, y, region.floor_z, angle)
    for k, (bx, by, z, turn) in enumerate(BLOODBATH):
        region, x, y = gameplay.spot(layout, bx, by, z, room_for=300)
        mark(f"player:apart_{k}", APART, k, region.region_id, x, y, region.floor_z, turn)
    if gameplay._REFUSED:
        raise gameplay.GameplayError("; ".join(gameplay._REFUSED))
    return {"together": 1 + len(BESIDE), "apart": len(BLOODBATH)}
