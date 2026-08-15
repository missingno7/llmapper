# E1M2 Crossroads mashup

`recipes/e1m2-crossroads.json` is the first replayable multi-map LevelIR assembly.
It requires the developer's local, legally obtained `E1M1.MAP`, `E1M2.MAP`, and
`E1M3.MAP`; no original map data is stored in this repository.

The recipe preserves E1M2 as the playable backbone and adds a side route directly
from its original player-start sector:

1. E1M3 sector 287 (the start gallery) is behavior-closed, raised by 9216 Z units,
   and attached to E1M2 wall 1720. Its floor exactly matches the E1M2 start sector.
2. E1M1 sector 112 (the tall hall) is behavior-closed, moved west, and raised by
   4096 Z units. Its inserted footprint has no intersection or containment conflict.
3. A generated four-sector passage joins the two donors. Its floor levels are
   17408, 15360, 13312, and 11264: three exact 2048-unit risers/descents.

Both donor closures have zero unresolved trigger, marker, or ownership references.
The passage has 45056–68608 Z units of portal opening and no layout conflicts.
Static passable-portal reachability from the unchanged E1M2 player start reaches
all six added sectors.

The result contains 319 sectors, 2503 walls, and 714 sprites. The original player
start, sky, all 313 base sectors, all 698 base sprites, and 2468 of 2469 base walls
are identical. Base wall 1720 differs only by the reciprocal portal references to
new sector 313/wall 2469. E1M2's original normal-exit transmitters on system channel
4 remain present and unchanged.

The generated MAP SHA-256 is
`b1ec5db182cf45b313e283a4ac930b15b790ffa53556d2a98b46acde2c576b74`.
NBlood `r14378-fbc5e1186` initialized it and remained healthy for the six-second
bounded test, matching the E1M2 baseline result. See
`reports/nblood_mashup_oracle.json`.

Build it locally:

```text
python -m bloodmap recipe recipes/e1m2-crossroads.json \
  --source-dir maps/blood --report work/e1m2-crossroads-report.json \
  -o work/e1m2-crossroads.MAP
```
