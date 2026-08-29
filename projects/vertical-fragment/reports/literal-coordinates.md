# Where the author had to write a number they meant as intent

The intent resolver is out of scope for this pilot. The substitute the addendum
asked for is this: author through the existing constructors, and **record every
place a literal coordinate had to stand in for something the author meant**.

That list is the specification for a resolver, if one is ever built. It is short,
which is itself a finding — the level program already removes most coordinate
arithmetic. What remains clusters into six shapes.

---

## 1. A plan is still drawn, not described

`fragment.py` names 14 rectangles and one polygon in absolute units: three
building blocks, the yard, the store, the stairwells, the doorways, the cellar.

**What the author meant:** *three buildings round a yard, with a cellar under
it.* **What they wrote:** `rect(6400 + 512, 0 + 512, 6400 + 512 + 2048, ...)`.

Half of this is already derived — `WELL_DEPTH = LANDING + STAIR_RUN + LANDING`
means the stairwell is *the size of the stair that goes in it*, and `MAIN_H`
follows from that rather than from a drawing. The other half is placement: where
the kiln stands relative to the brewhouse is a number.

**What a resolver would need:** a placement relation (`the kiln stands east of
the brewhouse across a gap`), which `Room.place_against` already offers for
rooms and nothing offers for *blocks*.

## 2. Naming a stretch of a wall by where it is

The most-felt gap, and the one the fragment worked around with a helper.

`Room.face(name, at=..., width=...)` takes a **fraction along the wall**. That is
right for "in the middle" and wrong for "where the door is". A doorway is a
rectangle standing in a wall; it already knows where it is. Converting the one
into the other means writing `at=0.20512820512` and hoping — or, as here, a local
`against(room, face, doorway_plan, side)` that computes the fraction from the
doorway's own midpoint.

Used 8 times. The midpoint rather than a corner, because a face runs whichever
way its outline winds and which corner comes first is not something the author
should have to know.

**Fix shape:** `Room.face` should accept a world segment or an adjacent room, not
only a fraction. This is a small, well-defined addition and the clearest
candidate for the next thing to build.

## 3. `at=0.0` and `at=1.0` as "at that end of the wall"

Four doorways sit at the very end of a wall. `at=1.0` happens to clamp to
exactly the right place, which is correct but reads as arithmetic luck rather
than as intent. `at="start"` / `at="end"` would say it.

## 4. The room-over-room marker position

`room_over_room(..., at=(4864, 7808))` — the point both markers stand at. What
the author meant is *the middle of the hatch*, and the hatch is a rectangle the
program already holds.

**Fix shape:** `at` should accept a region id and default to its centre. The
translation the campaign's water links use is the exception, not the norm.

## 5. The sprite deck's line

`sprite_bridge(start=(WALL, GANTRY_Y), end=(YARD_RIGHT - WALL, GANTRY_Y))`. What
the author meant is *from the west porch to the east porch*, and both are
declared regions a few lines above. The inset is "just inside the yard, so the
endpoints are not on its boundary" — a constructor detail leaking into the call.

**Fix shape:** `sprite_bridge` should take two regions or two faces and inset
itself.

## 6. Light source heights, in the one unit that is not a coordinate

`light_source(height_player_heights=1.6)` is *not* on this list, and is worth
saying why. It is denominated in bodies, so it is a statement about how high a
lamp hangs rather than a z value — which is exactly what the rest of the file
should look like and mostly does. Every vertical number in the fragment is
derived from `CLEAR`, `SLAB` and `STOREY`, and those three come from BB4.

---

## What this list is not

It is not an argument for building the resolver now. Six shapes, three of which
are one small change to `Room.face`, is not the bottleneck this project has.
The bottleneck it does have is the one the ROR bug demonstrated: instruments
that have never touched a map. A resolver built before the constructors beneath
it have been walked in the engine would be one more of those.
