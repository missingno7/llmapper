# Architect review — how appearance and ownership are represented, and what stands between us and a system that understands a level

Date 2026-09-02. Written after the owner's walk (texture seams, shop glass
on the facade line, cut crate tops, sunken roadways) and after reading the
representation stack end to end: `bloodmap/format.py` (disk) →
`planar_layout.py` (flat regions/connections) → `levelprog.py` (tree:
Assembly/Room/Style/faces) → the city's post-compile passes
(`projects/blood-city/level/build_skeleton.py` main). Companion to
`SUPERVISOR-BRIEF-2026-09-01.md` §6 and prompt P11.

The short version: **auto-alignment is a crutch, as the owner suspects.**
Not because the algorithm is wrong (it is the editor's own), but because it
is applied to a representation that has nothing for it to align — no
object says what a surface is, who owns it, or how a material is projected
on it. The same gap explains the pits, the invisible curtain and the
seams: appearance is decided after compile, by passes over Build wall ids,
each with its own private idea of ownership.

---

## 1. What the representation says about textures today

| layer | what it holds about appearance | what it cannot say |
| --- | --- | --- |
| `Style` (tree, `levelprog.py:177`) | one `wall_picnum`, `floor_picnum`, `ceiling_picnum`, shades, raw `floor_stat`/`ceiling_stat`, inherited by containment | which wall; where the tile starts; scale; that two rooms share one face |
| `RegionSpec` (flat, `planar_layout.py:268`) | the same per region, plus `relative_alignment` and `portal_wall_picnum` | anything per wall |
| `ConnectionSpec` (`:390`) | `face_picnum/over/cstat/x_repeat/scale` for a portal's two faces | the run the portal cuts |
| compiler (`planar_layout.py:2526`) | `x_repeat = length/128`, panning 0 | any phase |
| post-compile passes (city build, 25 of them: facades, headers, facade phase, align runs, align anchor, lintels, glass, signage, …) | picnum per hole loop, world phase from the wall's start coordinate, y anchor from the wall's own sector height, run carry in wall-list order | a global fact; they patch fields in a fixed order and can undo each other |
| reading side (`materials.py` catalog) | per TILE distributions of `x_repeat`, `world_width`, neighbours | a surface; a run; a projection |

Consequences measured on 2026-09-02 (brief §6): the city's largest join
class is `bend portal-portal` (768 pairs) at 55% continuity; y phase
breaks at every step because each wall anchors to its own sector; the zoo
continues 42% of plain bends where the campaign continues 70%; the eleven
crate tops wear cut tiles because a floor has no anchor but the world.

## 2. Who owns a wall, and why it matters

Build's storage answer is "the sector". The project inherited it:

- **Buildings are holes in the street region.** The E2M6 massing makes
  each district one region and its buildings holes; a building's street
  face is therefore owned by the DISTRICT room's hole loop, not by the
  building. `facade_pass.apply` has to rediscover buildings as "loops of
  the district's allocation that are not the largest" and paint them by a
  hash of their position. The building has no node that says "my facade".
- **A portal's face belongs to the connection**, not to either room's
  surface, so a facade that runs solid → door head → solid is three
  owners with three rules (Style, `face_picnum`, `portal_wall_picnum`).
- **A mechanism's walls belong to whichever sector the compiler put them
  in.** The curtain's fin was carved from the house and inherited the
  house's ownership; P1 had to move it into a doorway rect to make the
  fabric its own. The owner's functional-ownership hypothesis (a construct
  is a subgraph crossing sector boundaries) is right and is nowhere in the
  source.
- **Streets are leftovers.** The seam decision exists because a street is
  what remains of a district after the blocks, so a road that crosses a
  seam has no owner at all (brief, seam decision).

The pattern: the source language models SPACES (rooms, holes, portals)
well and SURFACES not at all. Every appearance fault the owner has walked
into is a surface fault: continuity, the glass on the wrong plane, the
crate top, the kerb face, the roadway with no pavement, the fabric drawn
on a two-sided wall.

## 3. The representation change: surfaces, frames, constructs

Introduce one layer between geometry and Build fields. Three objects:

**Surface.** A planar face of a construct: the street face of building X;
the inner wall of room Y; the top of crate Z; the kerb face of run R. A
surface is a chain of coplanar wall segments (or a floor/ceiling polygon)
that may be stored in several sectors. Openings in it are sub-surfaces
(door head, window recess mouth, lintel). A surface has ONE material and
ONE projection frame.

**Frame** (P11's `WallRunFrame` / `SurfaceFrame`). Material tile, u-origin
as a world point, texels per unit, v-origin as a world z, flip; for floors
and ceilings: anchor (world / object corner / first wall), scale, panning.
The compiler derives every Build field in closed form from the frame and
the wall's world coordinates (the editor's `AlignWalls` formula, cited in
P11). Portal cuts and sector splits change nothing, because the frame
does not know about them. Applying the editor's `>` port to a compiled
surface must be a no-op — that is the test.

**One record, one frame (owner, 2026-09-02).** A Build wall record has one
set of texture fields shared by its step bands and its masked middle, so a
material that needs its own scale and phase must sit on a record no other
surface uses, which only a sector boundary (a holder) can give it. Hence
the owner's model: a facade is a surface with HOLES and its own aligned
texture; shopfronts, windows and doors are inserts put into the holes,
owning their sectors and frames. Brief §6d has the audit.

**Construct ownership.** Buildings, streets, mechanisms, furniture are
nodes that OWN surfaces; rooms own interior surfaces; the district owns
only its boundary. `facade_pass` becomes "each building's facade surface
takes a tile from the district set", stated in source, not patched. A
street becomes a construct with a roadway surface, two pavement surfaces
and two kerb-face surfaces (this is also Option C of the seam decision,
and it is why Option C is the right long-term answer).

Reading side: a surface is recoverable from an original map as a chain of
coplanar walls sharing a material whose implied u-origin
(`x_panning − u(start)`) agrees within a tile. That recovery is the
reader half of P11 and the evidence for every surface-level norm (bay
grids, facade shares, kerb tiles) that today is mined per wall.

What this does NOT change: BuildIR, the byte-exact contract, PlanarLayout
as compiler IR. Frames and surfaces are source objects; PlanarLayout
carries them; the compiler resolves them. P11 as assigned builds the
frames and the closed-form resolver; the SURFACE and OWNERSHIP objects are
the part that must not be skipped, or frames will be attached to runs
found post hoc — the crutch again, one level up.

## 4. The other weaknesses on the way to "the AI understands the level"

In order of how much they block understanding, not how hard they are.

1. **Appearance decided by passes, not by source** (above). Rule to adopt:
   a pass may MEASURE; anything that decides a field is either a source
   object or a compiler rule. The city has 25 post-compile passes; each is
   a small representation nobody can read back. `readback.py` (P7) now
   diffs the result against declared sentences, but only for mechanisms;
   surfaces have no sentence to diff against.

2. **Mechanisms are still not citizens of the tree.** P1/P7 gave every
   constructor a `*_spec` dict and a read-back diff; that dict is the
   MechanismDecl in all but type. The three attested fixtures show the
   ceiling: the light Link (P8, a missing verb reader), the stack-linked
   casket (composition across a ROR plane, which a per-sector record cannot
   say), the wall route (fixed). Until declaration and reading share one
   schema, "understanding" is measured by whether two ad-hoc dicts agree.

3. **One attested map.** E1M1 is the only owner-attested ground truth; the
   E1M1 naming cross-cut (8/13 mechanism names not recoverable from
   topology) is one map's evidence. E3M1 (the street), E6M1 (the shop) and
   E2M2 (composition patterns) are already the project's precedents; each
   needs the same field-level attestation E1M1 got, or the norms built on
   them are readings dressed as measurements.

4. **Perception is the owner's job.** Every visual fault so far (dead
   mechanisms, invisible fabric, seams, pits, cut crate tops) passed the
   gates and was found by a walk. The gates measure structure; the
   renderer exists (`tools.render_precedent`) but nothing looks at its
   output. Two cheap moves: (a) geometric proxies for what the eye sees —
   the continuity census by class, the sunken-sector rule, the rendered-
   band law — as build gates (P2, P11, P12 do this); (b) a fixed walk sheet
   of frames rendered on every build, diffed image-to-image against the
   previous build, so a change the owner did not ask for is visible
   before the owner walks.

5. **Units.** Source states raw Build units; the 16:1 z anisotropy and the
   "standing_height moved every wall sprite" incident are the cost. Derived
   units (player heights, steps, bays, tiles) in source, Build units only
   in the compiler. Frames make this natural: a frame's scale is "texels
   per unit", a crate top is "one tile".

6. **Engine semantics are scattered.** `render_slots` (bands), `motion_sim`
   (DragPoint, sweeps), `drag_closure`, `conditional` (blocking), P8's
   verbs, the busy timing: each was ported by a different agent into a
   different module with its own citations. They should be one package
   (`bloodmap/engine/`) that readers AND writers depend on, with the
   citation table as its index. The rule "a law with zero exceptions" is
   only checkable when the law has one home.

7. **Norms are per primitive.** usage-kinds, materials, relations are
   mined per wall/sprite/sector. Surface recovery (above) lets norms be
   mined per surface (bay rhythm, facade share, kerb face, sill height),
   which is the scale at which the owner sees.

8. **The two dialects.** The `*_spec` split has held for turnstile,
   curtain and glass; keep it. Do not migrate the zoo; make surfaces and
   MechanismDecl the shared objects and let both placers consume them.

9. **Process.** Owner walks find what gates miss; the review queue works.
   What is missing is a "changes since your last walk" sheet (item 4b)
   and a standing rule that a new gate is written to fail on the owner's
   last finding before the next wave starts — which P11/P12 now do.

## 5. What to do with P11 as assigned

The agent has the frames and the closed-form resolver. Add, by message or
by a follow-up prompt, the two things §3 insists on: frames attach to
SURFACES owned by constructs (building facade, room wall, crate top, kerb
face), not to runs discovered from wall geometry; and the reader recovers
surfaces from originals so the continuity census is a surface census.
Without that the `>` port is still a pass — a good one — over walls
nobody owns.
