# Object placement and spatial anchors

Generated maps used to drop switches as free-standing sprites in the middle of
a room. A Blood control is not `(x, y, z)` in isolation. It has a relationship
to architecture.

## What the corpus actually does

`placement-mine` measures original campaign sprites against their owner sector:

```text
python -m bloodmap placement-mine --maps maps/blood --population blood-campaign \
  -o reports/blood-object-placement.json
```

Campaign `E*.MAP` (43 maps):

| kind | n | dominant sit | median height (player-heights) | median wall distance (player-widths) |
| --- | --- | --- | --- | --- |
| switch (all) | 1396 | mixed floor pads and wall faces | 0.73 | 1.33 |
| switch wall-mounted | 711 | wall_flush 401 / wall_offset 101 | 2.18 | 0.01 |
| switch floor pad | (split) | floor_supported / floor-aligned | ~0 | near |
| pickup | — | floor_supported | 0.0 | — |
| torch | 445 | wall_offset | 0.9 | — |
| enemy | 4370 | free_space / floor actor | — | ~1.3+ |

Do not treat the mixed-switch median 0.73 as “put every switch at that Z”.
That number is the midpoint of two populations: floor pads and wall faces.
Wall-mounted push switches (cstat wall-aligned or sit flush/offset) sit
**flush to a solid wall**, **face into the owner sector** (~70%), and have
sprite origin about **2.18 player-heights** above the floor — the same Z the
scratch first-puzzle room already used (`floor 8192`, `z -4096`).

Construction keeps a small inward offset (0.06–0.12 player-widths) so the
sprite is not embedded in the wall. First-puzzle Use evidence still uses an
~896 unit (2.3 player-width) standing pose in front of the control.

## Anchors

`PlanarLayout` resolves ordinary placement from geometry:

```python
layout.place_on_wall(
    "sw_archive", "region:archive",
    a1=(x0, y0), a2=(x1, y1), t=0.5,
    height_player_heights=2.18,
    offset_player_widths=0.12,
    type=21, picnum=1070, cstat=464,
    behavior={"tx_id": 100, "command": 1, "trigger_on": 1, "trigger_push": 1},
)
layout.place_on_floor("key_skull", "region:crypt", local=(0.55, 0.5), type=100)
layout.place_on_ceiling("chain", "region:nave", local=(0.5, 0.5), type=...)
```

The compiler derives `x, y, z, angle`. Callers should not guess XYZ for
ordinary wall or floor objects. Deliberately floating objects must be declared
(`validate_attachments(..., intended=[{"sprite": n, "allow_free": True}])`).

Anchor kinds: `wall`, `floor`, `ceiling`. That is the whole ontology for now.

## Gates

`validate_attachments` fails unexplained `free_space` switches.

`validate_use_poses` requires wall switches to have a standing Use pose inside
the owner sector at a corpus-supported height (0.35–2.6 player-heights). This
is a short deterministic pose, not AI navigation.

Place wall controls on **solid** edges, not portal spans. Nearest-wall mining
skips portals; a switch authored on a doorway edge looks free-floating.

## What this is not

It is not a furniture catalog. Enemies stay floor-supported actors with
corpus-typical clearance from walls. Combat simulation is out of scope.
