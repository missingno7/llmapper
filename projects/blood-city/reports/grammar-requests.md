# Grammar requests — what the city needs that bloodmap cannot yet say

Per the workstream split: this project consumes `bloodmap` improvements and
never edits that tree. Each entry is a concrete case from Blood City work,
with the local workaround in use. The parallel grammar agent owns
disposition.

## 1. Per-area ceiling height inside one E2M6-style region

**Case**: a district's outdoor space is one region with masses carved as
holes (the E2M6 precedent, and this project's L2 skeleton). One region means
one sky height, so canyon ratio can only be set per district — the avenue at
1.71 forces every alley in the same region to read as a deep slot. Phase 2
massing wants the sky (or interim parapet sub-sectors) to vary per street
class within the region.
**Workaround**: accept district-uniform sky at L2; subdivide in Phase 2 by
hand-planned partitions.
**Ask**: partitions or sub-regions that split a region's air without
breaking the one-region containment story.

## 2. Assembly-level deliberate-overlap declaration for true ROR

**Case**: the sewer assembly lies under Foundry Ward's street region
(deliberately — SP contract upgrades Duke's displaced boxes to true ROR).
`declare_stack` is per room pair, so N sewer rooms under one street region
cost N declarations, and a Phase 4 buildout adds one per new room.
**Workaround**: a loop over the sewer assembly's rooms in the generator.
**Ask**: `declare_stack(assembly_a, assembly_b)` or an assembly flag
"overlaps parent plan deliberately".

## 3. Stair landings as a first-class component

**Case**: the works stair descends 45056 z (11 risers); `vocabulary
.staircase` rejects landings by corpus policy, so a switchback needs two
staircase structures and a hand-placed landing room whose floor must repeat
the arithmetic of the flight above it.
**Workaround**: two flights + landing room in the generator, floors computed
from one shared constant.
**Ask**: a switchback/landing composition, or corpus evidence that landings
truly never occur (in which case long descents need a sanctioned pattern —
z-motion platform?).

## 4. Compass face naming on notched hole loops

**Case**: a mass carved with a notch (forecourt, yard, dead-end alley) has
several same-compass edges; `hole_face`'s `_compass_edges` picks one
undocumented winner, so a venue mouth "on the yard face" cannot be named
reliably from the street side.
**Workaround**: connect from the island/interior room's own rectangular face
and use the fact that connections take their geometry from the left anchor
only.
**Ask**: hole faces addressable by edge index or by nearest-to-anchor, and a
documented rule for which same-compass edge wins.

## 5. L3 attachment survival across L2 regeneration (the layer contract)

**Case**: design-layers.md requires L3 attachments (facades, apertures,
venue interiors) to survive an L1 change that regenerates the L2 skeleton.
Region ids derived from node paths survive renames-free regens, but
anchors stated as `at=` fractions along faces shift when a street width
changes upstream.
**Workaround**: none needed yet (no L3 content); flagged before it bites.
**Ask**: anchors addressable by named offsets from face ends (units, not
fractions), so a face that grows keeps its attachments where they were.

## 6. The geometry audit refuses declared partial-overlap stacks

**Case**: the sewer contract (SP) wants the network truly under Foundry
Ward's streets via declared stacks. `declare_stack` satisfies the planar
validator, but `geometry_audit`'s `sub_body_wall_fragment` check flags any
wall whose midpoint lies inside another sector's footprint, with no z
awareness and no declared-specials exemption (its `exact_reversed_coincident`
branch has the exemption; the sub-body branch does not). Result: only
exact-coincident shaft pairs can stack; a corridor partially under a street
cannot exist.
**Workaround**: the skeleton's network runs under the works superblock, and
the manhole pit is a bump of the works hole into the yard so its shaft pair
is exact-coincident. Under-street share is 0.0, recorded as grammar-blocked
in plan-conformance.md.
**Ask**: exempt walls of declared stack/water pairs from
`sub_body_wall_fragment` when the overlapping regions' z-ranges are disjoint
(the corpus's 38 in-place stack pairs all satisfy that test).

## 7. `room_over_room` only builds zero-translation links

**Case**: E3M3 (the Blood sewer precedent) builds its network on water links
whose two mouths are congruent rooms parked apart (corpus median offset 81
player widths). `room_over_room(at=...)` places both markers at one point,
so only in-place stacks are expressible; a displaced dive link needs raw
marker sprites.
**Ask**: an `at_upper`/`at_lower` form (or a `water_link` wrapper) that
places the two markers independently and checks the congruence rules from
`stacks-v1`.

## 8. `roomoverroom.MARKER_STATNUM = 10` deletes every link it builds  (HIGH)

**Case**: `bloodmap/roomoverroom.py` places its link markers on
`MARKER_STATNUM = 10` (`kStatMarker`).  NBlood's map loader deletes them:

```c
// db.cpp:680  PropagateMarkerReferences(), called at the end of dbLoadMap
for (nSprite = headspritestat[kStatMarker]; ...) {
    switch (sprite[nSprite].type) {
        case kMarkerOff: case kMarkerAxis: case kMarkerWarpDest: ... continue;
        case kMarkerOn: ... continue;
    }
    DeleteSprite(nSprite);        // everything else on statnum 10 dies
}
```

`kMarkerUpWater/LowWater (9/10)`, `kMarkerUpStack/LowStack (11/12)` and
`kMarkerUpGoo/LowGoo (13/14)` all fall through to `DeleteSprite`.  It runs
at the end of `dbLoadMap` (db.cpp:1325); `warpInit` only runs later, at
level start (blood.cpp:750), so the markers are gone before any link is
registered.  Result: no `gUpperLink`/`gLowerLink`, `GetZRange` never
extends the floor into the linked sector, the floor stays solid, and the
player cannot cross -- a room-over-room that silently does nothing.

**Evidence in the corpus**: all six stack markers in E3M1 are on statnum
**0** (kStatDecoration) with cstat 128; `warpInit` sets the invisible bit
(32768) itself, so the stored cstat need not.

**Ask**: `MARKER_STATNUM` should be 0 for the water/stack/goo families (and
the `link` family 6/7 as well -- those are also deleted).  Every level the
grammar has built with `room_over_room` has non-functioning links.

### 8b. `MARKER_TILE = 3997` is the wrong tile

Censused over the whole campaign -- 273 link markers, every family (link
6/7, water 9/10, stack 11/12) -- the tile is **2332 on the upper half and
2331 on the lower**, 100% of instances.  This project's own working
example agrees: `reasoned-authoring-v1`'s water links are 2332/2331.
`roomoverroom.MARKER_TILE = 3997` is drawn by XMapEdit as a torch, so a map
built with it shows "a normal sector and a torch sprite" where the link
should be -- which is how this bug was reported.

**Ask**: replace the single `MARKER_TILE` with the upper/lower pair
2332/2331, chosen by which half is being placed.

**Workaround here**: `level/build_skeleton.py` sets statnum 0, cstat 128
and the correct per-half tile on its own hand-built markers, and
`level/conformance.py` now fails the build if any link marker is on
statnum 10, lacks an XSprite, or carries the wrong tile.

### 9. `room_amplitude` sizes a room by wall count, so furniture makes it a hall

`lighting.room_amplitude` picks a room's shade spread from
`wall_count >= LARGE_ROOM_WALLS`.  That reads room size off a number that
also counts furniture: this project builds counters, tables, stage and
display pedestals as *geometry* (which is what the campaign does -- E3M1's
saloon counter is a sector at rise 4096, not a sprite), and every carved
island adds four walls to its host.

Gravesend's pawn shop is 3,584 x 2,560 units -- 3.5 x 2.5 plan units, one
of the smallest rooms in the city -- and has 22 walls because four display
pedestals stand in it.  It was therefore shaded with a hall's amplitude:
its wall shades came out 22 / 35 / 39 / 52 against a room median of 37, and
the whole east wall, the one with the door in it, rendered black.

The campaign's spread is a function of **floor area**, not wall count.
Measured over 1,393 rooms of E3M1 / E3M2 / E6M1 / E1M1 / E4M9:

| area (units^2) | n   | median spread | p75 |
|----------------|-----|---------------|-----|
| < 2M           | 904 | 7             | 15  |
| 2M - 10M       | 305 | 12            | 22  |
| 10M - 40M      | 134 | 19            | 32  |
| > 40M          | 50  | 21            | 32  |

**Ask**: size the room by the shoelace area of its outer loop rather than
by `wall_count`, and band the spread against the table above.  Note that
the target is a *distribution*: capping at the median flattens a level
(tried here -- 102 of 135 rooms compressed, measured contrast fell from
49.5 to 32, which is the failure `lighting`'s own CORPUS_SHADE note already
records).  p75 is the defensible cap.

**Related, lower confidence**: `light_direction` normalises any lamp offset
over 1 unit to a full unit vector, so a lamp at a room's centre still
implies a hard direction.  In 10 of 11 Gravesend rooms with an off-centre
lamp the wall *nearest* the lamp came out darker than the far wall, which
is the opposite of what `light_offset` in the same module does with
distance.  Not filed as a defect because the campaign gives no evidence
either way -- only 2 campaign rooms across seven maps have a lamp far
enough off-centre to test -- but the two functions disagreeing is worth a
look.

**Workaround here**: `level/lightpools.py` carries `settle_room_spread`
(caps each room at its area band's p75) and `settle_door_shading` (pulls
door-facing walls back to their room's median, which is where the campaign
puts them: +0.0 across 720 walls in five maps).

## #9 — an object scale below the prefab layer

`bloodmap.prefab` stops at rooms (alcoves, breakables). The furniture Blood
is actually made of lives a scale below that, and this project has had to
build it locally as `projects/blood-city/level/setpieces.py`:

    raised_solid   one block above its host floor (counter, table, plinth)
    stepped_solid  tiers side by side (E1M1's piano: body + two keyboards)
    basin          concentric tiers descending to water (fountain, pool)
    inset          a hollow behind a low mouth (E1M1's furnace)
    canopy         a lowered ceiling over a footprint (stall, bier)

with class constructors (`counter`, `altar`, `stall`) whose proportion
defaults come from `knowledge/blood/design/set-pieces-v1.json`, mined by
`tools/mine_set_pieces.py` from 7,014 pieces across the campaign.

Two things belong in the grammar rather than here:

1. **The idioms themselves.** Every one of them is carve-then-fill-then-rim
   on all four faces, which is a rule the compiler already enforces and
   which every project re-implements by hand.
2. **A rectangular room's face segment.** `props.face_segment` and
   `setpieces` both need "the wall segment of face F of this room", and
   getting it wrong is silent: insetting perpendicular to the face as well
   as along it puts the segment inside the room, and anchors resolved
   against it land on arbitrary walls including portals.

Owned by the grammar agent; nothing here patches `bloodmap`.

## #10 — rooms that are not rectangles

Gravesend measures **11% diagonal walls** after chamfering its street
masses, against E3M1's 35%, DukCity's 23-34% and TEDE1M2's 32%. The
remaining gap is not in the massing any more — it is that **every interior
room this project builds is an axis-aligned rectangle**, because
`Assembly.room` joins rooms on named compass faces (`north`, `east`,
`south`, `west`) and a face is a side of a rectangle.

Every idiom built on top inherits it: `props.face_segment`,
`setpieces.raised_solid`, `signage`, `doorswitch.lever_segment` all take a
rect and a compass name. A canted or splayed room has no face to name.

What would close it: a face identified by an edge index or a label on an
arbitrary polygon, so a room can be traced as a polygon and still expose
joinable, nameable edges. Everything above would then follow, since they
all want "the wall segment of face F" and nothing more.

Owned by the grammar agent; nothing here patches `bloodmap`.

## Reconciliation, after the grammar workstream landed

Checked against the tree as it stands, not as it was when these were filed.

**Answered:**

- **#7 — non-zero stack translation.** `bloodmap/roomoverroom.py` now
  documents the boundary as "a translation at a plane" and states that a
  non-zero offset is legal. The city's parked sewer no longer needs its
  hand-built justification, though it still uses its own builder (see #8).
- **#9 — an object scale below the prefab layer.** `set-pieces-v1.json` is
  in `knowledge/blood/design/`, and `bloodmap.prefab` carries thirteen
  constructors. `projects/blood-city/level/setpieces.py` should now be
  folded into it rather than maintained alongside.

**Still open, and now more urgent than when filed:**

- **#8 / #8b — `roomoverroom` still builds dead links.** The module has
  `MARKER_STATNUM = 10` and `MARKER_TILE = 3997` at lines 65 and 67, and
  writes both at line 139. Both are wrong, and the evidence has not
  changed: `db.cpp PropagateMarkerReferences()` **deletes** every sprite on
  `kStatMarker` (10) whose type is not off/axis/warpdest/on — which
  includes stack types 11 and 12 — and it runs at the end of `dbLoadMap`,
  before `warpInit` ever sees them. All 273 campaign stack markers sit on
  **statnum 0** with tiles **2332** (upper) and **2331** (lower); 3997 is a
  torch, which is what XMapEdit draws where the link should be.
  This matters more now: `docs/authoring-toolkit.md` routes authors to
  `roomoverroom` for linked volumes, so the next map to follow the guide
  gets links that silently do nothing. Blood City hand-builds its three
  stack pairs for exactly this reason and they work.

**New:**

## #11 — a face cannot report its free spans

`Assembly.connect(room.face(a), room.face(b))` produces a connection with
no explicit span, so nothing downstream can ask *which stretches of this
wall are free*. `props.solid_faces` can only answer per whole face, which
is too coarse: every leg of the sewer ring has a chamber or a corner on all
four of its faces, so a per-face test rejects all of them while in fact
each leg has ten or more plan units of bare wall.

This blocks the run layer (`projects/blood-city/level/runs.py`) on exactly
the spaces it exists for. Deriving the spans from the calling module's own
tables got the failure count from twelve hanging sprites to four and no
further; tightening the margins until it reached zero would have been luck,
not knowledge, so the four ring legs ship bare and say so.

What would close it: a face-declared connection recording the span it
occupies, or `PlanarLayout` exposing `free_spans(region_id, face)`.
Everything a run generator needs follows from that one answer.
