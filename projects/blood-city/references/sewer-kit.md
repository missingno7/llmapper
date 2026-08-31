# Sewer technical kit — original-map evidence

Generated occurrence evidence is in [sewer-kit.json](sewer-kit.json).  The
reference frames were rendered with `tools.render_precedent --hide-dudes`, so
they describe the architecture and fixtures rather than encounter population.

Re-mined 2026-08-31 after an owner correction: pipe tile 468 was wrong (it is
the unlit ceiling light, see `knowledge/blood/design/owner-anchors-v1.json`);
the pipe run is 496–499 with 498.  The corpus scanned is
campaign + curated + conversions (incl. multiplayer subdirs).

## What the corpus says

| Role | Tiles | Strongest source evidence | Construction reading for Gravesend |
|---|---|---|---|
| machinery | 2462, 2463, 2476, 2477 | DWE2M3: 116 uses, all walls; DWBB3: 58 uses; TEDE1M4: 40 uses, mainly walls | Treat them as wall-sized pump consoles and machinery bays in a widened service alcove or pump room.  Do not scatter them as floor sprites along a tunnel. |
| pipe run | 496, 497, 498, 499 | DWE2M10: 395 uses, 393 walls (497×204, 498×92, 499×92); E3M2: 338 uses, 334 walls (497×259, 498×68) | A pipe is a continuous wall run.  Use 497 as the ordinary run, 498/499 at a change of run or junction, and reserve rare 496 for an end, damaged section, or equipment connection. |
| sewer door | 500 | DWE2M3: 127 wall uses; DWE2M10: 60 wall uses | It belongs on a real portal or sealed maintenance mouth, with a surrounding jamb/pier.  It is not a freestanding decorative panel. |
| technical light | 501 | TEDE1M4: 60 uses across wall/surface/sprite; DWE2M2: 28 surface uses | Place it at a repeatable service interval on the ceiling or above equipment, not in every tunnel sector.  It should illuminate a choice, door, ladder, or machinery bay. |
| grate | 502 | TEDE1M4: 149 uses, 140 walls and 9 sprites; TEDE1M5: 37 wall uses | A grate closes or reveals an opening: outfall mouth, side duct, or a guarded service break.  Keep the walkable floor and the grate as separate surfaces. |

## Reusable prefab grammar

1. **Straight trunk:** long `497` wall run; only occasional `501` service
   light.  Avoid mixing every pipe texture in a single short corridor.
2. **Junction/pump bay:** widen by at least one player width, terminate pipe
   runs in one or two `2462/2463/2476/2477` machinery faces, and place a
   `499` transition where the pipe turns into the bay.  This is where the
   starker machinery belongs.
3. **Maintenance branch:** a genuine `500` door set into masonry, with a
   `502` grate used for a neighbouring duct or unreachable drainage opening.
   Door, grate and visible pipe end should not occupy the same wall span.
4. **Light discipline:** `501` marks a technical node or a regularly spaced
   run; it should never compensate for a missing room purpose.

## Representative architecture-only frames

- `DWE2M3` sectors 119/165 — machinery and maintenance-door density.
- `DWE2M10` sectors 38/161 — pipes as a continuous wall register.
- `TEDE1M4` sectors 89/340 — the machinery cluster, light, and grate family.

The current BloodCity sewer can take the first two prefab types at the pump
station, trunk junction, and the two ROR landing bays.  Those are service
destinations; ordinary water channels should retain their simpler stone/pipe
register so the mechanical detail still has contrast.
