# BB2 semantic revision plan (v2)

Builder inputs (still **no BB2.MAP**):

- `reports/BB2-understanding.md` — target description
- `reports/BB2-reconstruction-understanding.md` — what v1 actually became
- `reports/BB2-semantic-roundtrip.md` — design-space error signal

The builder must not be told “add diagonals” or “make bigger spawn rooms” as
magic instructions. Those are examples of how to read the delta.

---

## Error signal → intended change

### Spawn neighborhoods participate in large open hunting areas

**Target (A):** several outdoor starts occupy 110–455 player-area cells, 5–8
portal choices, max 2D sight ~50–73, still almost no spawn-to-spawn LOS.
Concealment comes from **field geometry and building occlusion**.

**Candidate (B):** spawn cells 32–162 areas, 1–3 portals, median sight ~7
widths. Pairwise LOS is zero because the start sits in a **small grid pocket**.

**Action:** redesign local spawn geometry. Merge/replace alcove cells with
large outdoor yards. Keep occluding masses *between* yards so the 28-pair
matrix stays near zero. Do not restore concealment by shrinking the cell.

### Architecture contains orientation diversity and irregular mass

**Target:** orthogonal fraction ~0.73, orientation diversity ~0.94,
rectangular sector fraction ~0.30, vertex counts to 40, some chamfers and
segmented chains.

**Candidate:** orthogonal 1.00, diversity 0.06, every sector a rectangle.

**Action:** replace some simple rectangles with independently designed
irregular footprints using `LevelBuilder.add_sector` polygons (chamfered
courts, octagonal pavilion, trapezoid water, diagonal occluders). The API
already accepts arbitrary clockwise polygons; no `make_blood_style_building()`.

### Outdoor field is fragmented by buildings, not one courtyard

**Target:** largest connected sky region is only part of the sky footprint;
routes clip cover.

**Candidate:** almost all sky is one connected rectangle ring.

**Action:** place covered masses so sky connectivity and sight break, while
walkability still loops.

### Covered travel along indoor routes

**Target:** indoor start routes spend most samples under cover (sky fraction
~0.3) and may transition more than once.

**Candidate:** one hop onto the ring (sky fraction ~0.7).

**Action:** give west indoor starts a longer covered sequence before the
field, without turning that sequence into a closet.

### Secondary (only if cheap)

- Raise ordinary ammo count toward “abundant” (A: 47; B: 18).
- One outdoor Z-motion floor drop (~6 player-heights) as a distinct mechanism
  role, not a third copy of the item door.
- Keep gated prizes, flags, water Tesla, 20 vs 6 height, square compound.
- Prefer campaign-role tiles already in the kit; outdoor floor may stay earth
  family (270 or 2448) — exact 2448 identity is not the revision’s primary
  lever.

### Explicitly out of scope for this iteration

- Matching 128×128 AABB
- Replicating 13+4+6 movers tag-for-tag
- Lighting sensor / shade painting
- Copying BB2 vertices

---

## Construction primitives

Audit result: `add_sector(points)` already builds arbitrary polygons.
`connect` already pairs reversed coincident edges. v2 should use those.

Do **not** add `make_blood_style_building()` or an auto-chamfer style pack.
If a tiny helper is needed, keep it in the builder script (vertex lists),
not in the package API.

---

## Success check

After v2, independently `Understand(candidate_v2)` without reading this plan’s
target numbers as a script. Then compare to Understanding A.

Ask whether these measured gaps shrank:

- spawn sector area range vs 110–455 outdoor band
- portal choices vs 5–8 on hunting-ground starts
- orientation diversity vs ~0.9
- rectangular fraction vs ~0.3
- pairwise spawn LOS still near zero
- indoor route sky-fraction closer to ~0.3 than ~0.7
