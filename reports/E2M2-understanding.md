# E2M2 understanding

Frozen from `reports/E2M2-understanding.json`. Original polygons are not
repeated here. This is a campaign single-player microscope, not a
reconstruction brief.

## Level identity

Blood v7 campaign map on a ~367 × 373 player-width board. 290 sectors, 2267
walls, 427 sprites. Native validation 0 errors. 101 XSECTORs, 384 XSPRITEs,
25 XWALLs. 46 parallax ceilings. Two keys (fire and moon), 10 weapons, 12
health, 6 armor, 63 enemies.

It is a **large initially-open exploration volume** with additional
state-dependent wings, not a chain of five locked rooms. 204 of 290 sectors
are already rest-walkable from the single-player start (sector 17). 177
portals are blocked or state-dependent. After grounded keys, push-motion, and
TX in reached sectors, 221 sectors are reachable and the normal exit channel
(4) can fire.

## What the old rest-walkability layer missed

`analyze-space` could say “204 reachable, 177 gated portals”. It could not
say:

- the fire key (type 102 → key 3) is collected on the witness;
- moon-key locks (sectors 123/124, key 6) are never collected on that witness;
- a fire-key lock (sector 177) exists;
- channel 110 is a one-to-many motion fan-out that adds space but is not a
  unique exit cut;
- physical traversal and allowed progress must stay separate graphs.

Those are new representations. They are still incomplete: destruction and
one-shot walls are unmodeled, and opening a motion sector treats all of its
gated portals as walkable.

## Progression

Start is already inside a huge connected component (204 sectors, ~8792
player-areas, median clear height ~7.5 player-heights, sky exposure 0.22).
The witness then:

1. takes the fire key (still 204);
2. push-opens two adjacent motion sectors (205, then 206);
3. activates many TX already in that volume (most add no new sectors);
4. grows through optional fan-out channels to 217–221;
5. fires exit channel 4 once the exit sprite’s sector is in the reached set.

Counterfactual re-solve: **no single activated channel and no collected key
is a unique cut for the exit**. Several channels (110, 147–151, …) are
`optional_space`. Many TX never appear on the witness (61 counted). The moon
key is unused.

That does **not** mean E2M2 has no gating in play. It means this model’s
at-rest opening test already treats much of the board as walkable, so the
exit sprite is not behind a unique modeled door. The strongest grounded
claims are: fire key is on the main circuit; moon-key rooms are a separate
lock; fan-out motion adds wings; exit is reachable in the model.

## Mechanism compositions

E2M2 has 42 TX/RX chains with both ends. Recurring campaign signatures
(43 `E*.MAP`):

- `tx1|rx1|motion0|exit0|sprite` — every campaign map
- `tx1|rx2|…` fan-out without motion — 37 maps
- `tx1|rx1|motion1|…` single motion gate — 36 maps
- larger fan-outs (`rx3`, `rx8`, …) including motion — common

E2M2 uses those same shapes (for example channel 110: one TX, eight
receivers, motion). Status **supported** after campaign search, not because
E2M2 contains them once. Do not invent TX/RX wiring when a one-to-many
motion gate is requested.

## Spatial pacing (measured, not labeled)

Spawn-set enclosure is already high laterally (0.99) with mixed sky. Later
witness snapshots change reachable count more than they change the whole-set
median height: this is a wide board that **grows wings**, not a sequence of
tiny rooms that suddenly become cathedrals. Palette evidence for the whole
map: sky sheet 2500 on many ceilings, organic-earth floor 2448 and unfaceted
438, mixed masonry walls, median shade 30 (dark). Covered median height
~5.8 player-heights; sky ~13.

## Vertical rhythm

Covered vs sky height contrast is real. Storey-scale indoor height changes
exist; they are not automatically overlooks. BB3 is the compact vertical
reference, not this map’s DM logic.

## Enemies

63 dudes. Mostly `free_space` floor actors (52), some wall-offset (11).
Types mix 201/202 (cultist family) with 213 and 245. Median wall distance
~1.45 player-widths — not glued to walls, not a switch problem. No combat
simulation.

## What a builder should take

Relations, not E2M2 vertices:

- a large reachable start volume, not a one-room spawn closet
- at least one **hard gate** (key or equivalent) even if E2M2’s exit is not
  a unique cut in this model
- at least one **required side branch** (here: fire key is on the circuit;
  moon-key rooms are optional/unreached)
- world-state changes that add space after the start volume
- fan-out motion as a native way to open several receivers
- material/shade difference between covered masonry and sky
- enemies as floor-supported actors off the walls

and must not copy E2M2 geometry.
