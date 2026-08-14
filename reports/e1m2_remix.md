# E1M2 reordered-room remix

`recipes/e1m2-remix.json` is a replayable LevelIR-level restructuring of E1M2.
It does not distribute original game data; building it requires the developer's
local, legally obtained `E1M2.MAP` under `maps/`.

The design adds a new opening act assembled from four recognizable E1M2 rooms in
a deliberately different order:

1. sector 70 becomes the player-start ambush, rotated one quarter-turn;
2. sector 157 becomes the broader second fight, rotated two quarter-turns;
3. sector 185 becomes a tighter vertical chamber;
4. sector 299 becomes the largest arena and opens directly into E1M2's original
   start room, after which the untouched original progression continues.

The rooms descend in four 6144-Z-unit stages. Three generated stair strips each
contain four sectors and limit every riser to exactly 2048 units. Their collision
checks report no crossings, overlaps, or containment conflicts. Each donor's
behavior closure contains exactly its requested sector and has zero unresolved
gameplay dependencies.

The transformed player start is `(-37872, 65640, -17408)`, angle 1792, in allocated
sector 324. The source-relative recipe operation verifies that this point is
strictly inside the room and within its ceiling/floor span. Static passable-portal
reachability from it covers all 16 added sectors and original sector 237.

The result contains 329 sectors, 2569 walls, and 727 sprites. All 313 original
sectors and all 698 original sprites are identical. Of the original 2469 walls,
only wall 1721 changes, solely to hold the reciprocal portal into the new arena.
The two original normal-exit transmitters on system channel 4 remain unchanged.

Two consecutive recipe builds are byte-identical at 171831 bytes. The generated
MAP SHA-256 is
`0f6e838690d79259d41ab978ea5e99ac5df4401871411d945dc233417c916633`.
NBlood `r14378-fbc5e1186` initialized both the original baseline and the remix and
kept each healthy for the bounded six-second test. See
`reports/nblood_e1m2_remix_oracle.json`.

Build it locally:

```text
python -m bloodmap recipe recipes/e1m2-remix.json \
  --source-dir maps --report work/e1m2-remix-report.json \
  -o work/e1m2-remix.MAP
```
