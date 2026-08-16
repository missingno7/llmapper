# BB2 semantic reconstruction — design decisions

Blind builder log. The source MAP and `BB2-understanding.json` were not
inspected while these decisions were made. Geometry is an independent
80×80 player-width compound, not a copy of the hidden footprint.

## Isolation

- Allowed input: `reports/BB2-understanding.md` (copied to `work/bb2-recon-blind/SPEC.md`)
- Allowed tools: llmapper construction, contents, sight, inspect-space, ontology v2, NBlood on the candidate
- Hidden until freeze: `BB2.MAP`, `reports/BB2-understanding.json`, BB2 screenshots, sector dumps

## Contract interpretation

VERIFIED facts (8 DM starts, no dudes/keys/exit, flag bases + channels 80/81,
channel 8 sting, gated super armor / cloak / akimbo, water Tesla) were treated
as hard.

DERIVED measurements (outdoor-dominant sky, ~17–23 vs ~5–11 height contrast,
typical ~2.67-width mouths, spawn concealment) were treated as approximate
targets.

INTERPRETED statements (toybox of mover types, “snowy” outdoor, CTF-first
balance) were treated as guidance. Exact brick IDs and wall coordinates were
treated as deliberate bottleneck loss.

---

Intent:
Deathmatch compound with independent geometry.

Decision:
Build an 80×80 player-width square (not 128), ring 12 widths, central 8-width
covered pavilion, west indoor stack, south porch, east water.

Expected effect:
Same bounded-compound character at Blood scale, obviously not a tracing.

Observed:
AABB 80×80 widths; 112 sectors / 448 walls vs source “179 / 1413” in the prose.
Validation 0 errors; NBlood load smoke pass.

Action:
Accepted.

---

Intent:
Most DM starts should not spawn with direct visual contact.

Decision:
Place four outdoor alcove starts (NW, NE, SW, SE/Flag A) and four
covered/indoor starts (porch Flag B, two west rooms). Use solid (non-portal)
building mass and a mid-courtyard N–S sight bar. Evaluate with `sightline
--spawns --multiplayer-only` during construction.

Expected effect:
Immediate spawn-peeking remains rare.

Observed:
First blockout 5/28 clear (straight grid corridors). Hall-to-courtyard garage
opening leaked an indoor start to SE. Porch-mouth column aligned Flag A with
Flag B. After removing those portal streets and adding a three-column sight
bar: **0/28** clear pairs.

Action:
Redesigned geometry rather than accepting the first matrix. Did not target
the source’s 1/28 ratio.

---

Intent:
Interior → exterior should strongly expand perceived space.

Decision:
Outdoor ceiling −20 player heights with sky parallax 2500; indoor −6 heights
with ceiling tile 416. Building mouth 1024 units (2.67 widths) at the west
cluster. Porch mouth also 1024.

Expected effect:
Sky 0→1, height ~6→20, sight lengthens through the mouth.

Observed:
inspect-space: outdoor clear height 20.0, covered 6.0, sky exposure 0→1,
height ratio 3.33. NBlood porch view shows masonry opening onto earth + night
sky. West indoor spawn faces a wall (concealment) until the player turns into
the dogleg.

Action:
Accepted the height contrast. Recorded that a 1024 mouth is easy to miss in
engine view if the spawn faces a solid wall.

---

Intent:
High-value items are gated / high-risk, not free on the field.

Decision:
Type-600 ceiling Z-doors: vault (ch.100, two 1070 switches), akimbo (ch.101),
cloak (ch.102). Tesla in an underwater XSECTOR with paired 9/10 markers.
Napalm on a sky courtyard sector.

Expected effect:
At-rest unreachable item rooms; water as the only non-portal transition.

Observed:
11 sectors unreachable at rest (closed doors + underwater continuation).
2 water-marker links. Channels 100/101/102 have map TX. Super armor, cloak,
akimbo sit behind closed movers.

Action:
Accepted. Did **not** reproduce slide-marked / rotator toybox diversity;
purpose preserved with one verified construction (Z-motion + push switch).

---

Intent:
Gray ground + sky outside; brick/stone interiors; distinct water surface.

Decision:
Ontology v2 kit: floor 270 (organic earth), sky 2500, walls 110 (stone) /
5 (brick), indoor floor 2448, indoor ceiling 416, water floor 90, switch 1070,
masked 330, door 104.

Expected effect:
Readable outdoor/indoor split without copying unannotated source bricks.

Observed:
NBlood: earth courtyard + night sky + brick rooms is Blood-like. Tile 90 does
not read as water (mixed_use, unknown visual material). Tile 104 is
construction-precedent / low-confidence. Indoor floor 2448 is a campaign
floor tile rather than “vertical stone used horizontally.”

Action:
Kept 90 with pal/shade offset as an explicit fallback. Recorded ontology gaps.

---

Intent:
Loop circulation; outdoor is the default connector; bottlenecks at mouths.

Decision:
Ring around the pavilion; west cluster enters through one 1024 mouth; porch
enters through one 1024 mouth; north/east sheds break long sight without
disconnecting walkability.

Expected effect:
One dominant navigation region; closed doors as optional pockets.

Observed:
1 navigation region of 100 sectors; 130 walkable portals; 6 blocked
(state-dependent); 101 reachable from SP at rest.

Action:
Accepted. Some sheds are more “sight mass” than “rooms,” which the prose
allowed (cover from building mass, not blocking-flag clutter).

---

Intent:
Flag bases as opposite-end landmarks near a spawn.

Decision:
Flag A north outdoor, Flag B south covered porch, RX 80/81, no map TX.

Observed:
Opposite sides of the AABB; each has a nearby start; 2D spawn-to-flag sight
not re-measured after the last Flag A cell move (Flag A is adjacent to its
yard; Flag B is in the porch with the covered start).

Action:
Accepted.

---

## Ambiguities resolved independently

| Spec gap | Builder choice |
|---|---|
| Exact courtyard vs building proportions | 12-width ring, 8-width pavilion, west 12-width indoor strip |
| How cover breaks field sight | Solid pavilion E–W + mid-courtyard N–S bar + perimeter sheds |
| Mover vocabulary (Z / slide / rotate) | Z-motion only |
| Outdoor floor-drop lift | Omitted (soft toybox) |
| Water surface look | Tile 90 + pal 1; not a liquid family |
| Lighting / fog | Engine defaults |
| Indoor cluster plan | Single west stack + south porch + east sheds |
| Spawn facing | Toward local exit or mouth after first NBlood pass |

These are information-loss candidates, not proof the builder ignored the spec.
