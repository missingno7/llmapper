# The street model — what E3M1 actually builds, what Gravesend builds, and the decisions

Prepared by the supervising architect on 2026-09-02 from the owner's
reading of E3M1 (road sectors 3, 8, 7, 45; pavements 1, 235, 6, 9, 159,
175; kerb face 6) and a re-measurement of the map. Everything here is a
proposal for the owner's batch; the decisions are at the end.

## 1. E3M1's street, measured to the field

| element | E3M1 | source |
| --- | --- | --- |
| roadway floor | tile 352 (cobblestone), z 10240 | s3, s7, s8, s45 |
| pavement floor | tile 4, z 8192 — **2048 above the road**, every kerb | 14 sectors; 11/11 kerb walls |
| kerb face | **picnum 6 on the ROAD-side wall record** (the lower band a body sees from the road); the pavement-side records wear facade tiles that never draw | 11 of 11 |
| plaza floor | tile 379 | s175 and others |
| roadway shape | long strips: s8 7456 × 21504 (north–south), s45 18048 × 4096 (east–west), s7 7328 × 4096, s3 5120 × 5120 at the crossing | bboxes |
| pavement shape | bands along the building faces: 1024 (s1), 2048 (s2, s4, s6, s9, s159), 2560 (s5), **512 (s10, s11)** — even a narrow band exists | bboxes |
| shading | roads and pavements are cut into sectors at SHADOW EDGES: lit floor shade 8, shadow 32–34, penumbra 24; 44 shade boundaries inside the 68-sector street network | floor shades |
| light direction | the shadow edges that are not axis-aligned cluster at 82.9°–86.4° (s7\|s8 and s8\|s45 both 84.2°, 416 units over 4096): one oblique light, about 5° off the north–south axis, casting building shadows across the street | wall angles |
| sky | 33 of 68 street sectors parallax (3491) | ceiling_stat |

So the construct is: **straight road strips between blocks, pavements
hugging the building faces, a 2048 kerb with tile 6 on its face, and the
whole surface cut by one oblique light into lit and shadowed sectors.**
The sector partition is NOT the functional partition: a road strip is
several sectors because the light says so, and it stays one road.

## 2. What Gravesend builds, and why it cannot produce that

The plan (`level/city_plan.py`) is a centreline graph with width classes
and rectangular districts whose seams run down street centrelines. L2
(`build_skeleton.py`) makes **one street region per district with blocks
carved as holes** — the E2M6 form. Consequences, all measured:

- a street is the residue of a district after its blocks; it has no node,
  no faces of its own, and it stops at the district seam (the seam
  decision, 8 of 13 runs blocked);
- the three carriageways laid so far are 4-wall rectangles of tile 352
  inside a tile-352 region, 1024–3072 lower, with brick or glass on the
  drop and **no pavement sector anywhere** (0 sectors wear tile 4);
- shading is uniform per district (30–36) plus nine flush light pools;
  there is no light direction and no shadow;
- roads do not separate blocks and pavements do not run along buildings,
  because neither is a thing the plan or L2 can express.

The wave-1 anatomy constructor was written against the right numbers and
the wrong model: it cuts a rectangle into a residue instead of building a
street.

## 3. The general mechanism the owner asks for

"A sector that casts the building's shadow, and the road passes through
it, part in shade and part in light" is exactly right, and it generalises:

**A Build sector is the intersection of several independent partitions
of the plane, and a surface spans the pieces.** The partitions are:

1. *function* — road strip, pavement band, plaza, kerb line, block face;
2. *height* — where the floor or ceiling changes (the kerb itself);
3. *light* — shadow polygons cast by the masses under one directional
   light, plus the pools of point sources;
4. *mechanism* — what must move together (P1–P3's ownership work).

The compiler overlays them; each resulting piece is a sector; each piece
inherits its floor tile, its kerb and its texture FRAME from the surface it
belongs to, and its shade from the light partition. Nothing is patched
afterwards: the road strip's frame continues across the shadow edge
because the frame is world-anchored (P11/P13), and the shadow edge exists
because the light overlay put it there. This is the same law as "one
record, one frame" (brief §6d) seen from the other side: sectors are
cheap and may be cut for any concern; surfaces and frames are what must
stay whole.

## 4. Decisions

**D1 — Streets become first-class constructs in the plan (the seam
brief's Option C), and blocks are what lies between them.**
Recommended: yes. It is the only model in which a road strip, its
pavements and its kerb faces have an owner, in which a road can cross
what used to be a seam, and in which E3M1's anatomy can be stated rather
than cut. The L1 graph and the block rectangles mostly survive; L2
changes from "district region minus holes" to "street constructs +
block masses + plazas", and the district becomes a grouping for style
and norms only. Cost: the L2 generator, `conformance.py`'s street-loop
row, norm re-baselining. The seam question disappears instead of being
answered.

**D2 — The street construct is E3M1's, to the field.** Roadway 352 as a
continuous strip per graph edge, 2048 below grade; pavement bands of tile
4 along every building face (E3M1's bands: 512, 1024, 2048, 2560 — the
band follows the space available, never zero); kerb face tile 6 on the
road-side record; plazas 379 at pavement level; junctions as road
squares (s3). Recommended: adopt as `bloodmap/street.py`'s definition and
retire the "rectangle in a residue" constructor.

**D3 — One directional light per level, casting mass shadows as a
partition overlay.** Direction measured from E3M1's own shadow edges
(≈5° off the north–south axis; the agent re-measures and states the
convention); lit 8 / shadow 32–34 / penumbra 24 as the starting palette,
re-measured over the campaign's outdoor sectors; LightBomb and pools stay
for point sources. Recommended: yes, as an overlay, never as per-sector
hand values.

**D4 — Overlay partitioning in the compiler, surfaces spanning pieces.**
PlanarLayout gets partition overlays (polygons that split regions without
changing ownership or frames); Surfaces (architect review §3) own tiles,
kerbs and frames across the pieces. Recommended: yes; it is the general
mechanism for "an element passing through several sectors" and it
subsumes the light pools, the kerb, and P12's sunken-sector rule.

**D5 — Stop patching the current city's streets; rebuild L2 under D1–D4.**
The current MAP stays as the "before" for the walk sheet. Wave 1's
`bloodmap/street.py` numbers are kept; its cutting logic is not.

**D6 — Order.** P13 first (texture frames fixed and re-scaled; the
one-record-one-frame gate), because surfaces need frames. Then D4 in the
compiler, then D1/D2/D3 as one L2 rebuild wave with its own review sheet
(west street, the avenue, a junction, a shadow edge, a kerb — before and
after, rendered).

## 5. Owner questions (batched)

1. Light direction convention: state it as an angle in Build's coordinate
   system or as "sun from the north-east"? The agent needs a convention
   to write down; E3M1 only fixes the axis, not the sign.
2. Plazas: E3M1's plaza tile 379 sits at pavement level. Keep plazas as
   pavement-level surfaces (walkable, no kerb) or allow kerbed squares?
3. Lanes and alleys (3072 and 2048 wide): E3M1 has 512 pavements even
   where the road is narrow. Pavement always, or pedestrian lane below a
   width threshold as wave 1 assumed?

## 6. Corrections to earlier project readings

- The kerb face is tile **6 on the road-side record**, not the facade
  tiles 401/400/393 measured on the pavement-side records on 2026-09-02
  (brief §6b); those records do not draw.
- "Kerb = 1024" (the wave-1 brief) was the drain-grate ring; 2048 stands.
- E3M1's road is cut at shadow edges, not at junctions only; a street
  constructor that emits one sector per run cannot match it.

## 7. Owner's refinement, 2026-09-02 (supersedes D1's wording)

- **The hierarchy is: streets → pavement islands on them → buildings on
  the islands → facades with holes → inserts.** The street is the ground
  plane; a pavement is an island standing on it; the kerb is not a thing
  anyone draws but the island's edge showing above the road, and the
  exposed band wears the kerb tile (6). Gravesend gave that band the
  house tiles: wrong, and now explained — the band was a hole's edge in a
  street residue, so it inherited the building's material.
- **Lamps stand on the pavements** (E3M1's street furniture rate), not in
  the road.
- **Our system today can only insert a sector into another where there is
  room.** Level design is about OVERLAPPING relationships: an island lies
  on a street, a shadow lies across both, a building stands on an island,
  a facade run passes a recess. The compiler must resolve overlaps
  (overlay partitioning, D4) instead of refusing them.
- **Light: one sun for the whole level, direction free; E3M1's is fine.**
  Question 1 of §5 is answered: take E3M1's axis and sign as measured
  (the agent states it once, in Build angle units, in resolution.py).

D1 therefore reads: the plan's ground plane is the street network; blocks
are islands; districts group islands for style and norms. D2–D6 stand.

## 8. P14 — the ground-plane city (after P13)

```text
Task: rebuild Gravesend's L2 on the owner's model -- streets are the
ground plane, pavements are islands on it, buildings stand on the
islands, facades carry the holes -- with overlay partitioning in the
compiler and a single sun. E3M1 is the measured template; the numbers
and the decisions are in projects/blood-city/reports/street-model-
decisions-2026-09-02.md. Do not start before P13 has landed (texture
frames at the right scale, one record one frame) and read its status.

Deliverables
1. Compiler: PARTITION OVERLAYS in bloodmap/planar_layout.py. An overlay
   is a set of polygons that split existing regions into pieces without
   changing ownership, material, frames or behaviour. Two overlay kinds
   now: HEIGHT ISLANDS (a pavement island raised 2048 over the street it
   stands on; the exposed edge band takes the island's kerb tile on the
   ROAD-side record -- E3M1 tile 6, 11/11) and LIGHT (shadow polygons).
   Pieces keep the parent surface's frame, so a road strip's cobbles
   continue across a shadow edge (assert with the '>' invariance port).
2. Light: one directional sun per level (direction and sign as measured
   on E3M1's shadow edges, stated once in resolution.py in Build angle
   units); shadows of every mass projected onto the ground plane and cut
   in as the light overlay; floor shade lit / shadow / penumbra from a
   re-measurement of the campaign's outdoor sectors (E3M1: 8 / 32-34 /
   24). LightBomb and pools remain for point sources and interiors.
3. L2: from city_plan.py's graph and blocks, generate (a) the street
   network as ONE ground plane per connected network (roadway tile 352,
   z = grade + 2048), (b) pavement islands: the block footprints grown by
   E3M1's band (512-2560; state the rule you measure) minus the road,
   tile 4 at grade, lamps on them at E3M1's furniture rate, (c) building
   masses standing on the islands with their FACADE surfaces and holes
   (P13's frames and inserts), (d) plazas as pavement-level surfaces
   (tile 379), (e) junctions as road squares. Districts survive only as
   style groups and norm bins; the seam decision is closed by
   construction -- record that in reports/owner-review-queue.md.
4. Gates, each written to FAIL FIRST on the current city: every kerb band
   wears the kerb tile on its road-side record; every building face has
   a pavement between it and the road; no sector is lower than all its
   neighbours without a declared reason (P12's rule); shadow edges share
   the sun's angle; road frames continue across every shadow edge.
5. Read back (bloodmap.readback), render a walk sheet -- west street,
   the avenue, a junction, a kerb from the road, a shadow edge across a
   road, a lamp on a pavement -- before and after; re-run the city norms
   and re-baseline them (rates, not counts). Suite green; report the
   E3M1 comparison table, which gate failed first and on what, what is
   unproven, branch and commits.
```

## 9. From which end to design the city (owner's question, 2026-09-02)

Neither end alone works. Streets first leaves buildings as leftovers;
buildings first leaves streets as leftovers — which is exactly Gravesend
today (streets are the residue of district regions). A city, and a Blood
level, is negotiated between three things with different stiffness:

| element | stiffness | what fixes its size |
| --- | --- | --- |
| landmark interiors (theatre house, church nave, market hall, works) | RIGID | the venue patterns: measured room sizes, clear heights, the mechanism they hold |
| street corridors | SEMI-RIGID | a MINIMUM width per class (E3M1/Duke norms) + pavement bands; may grow, never shrink |
| filler buildings | SOFT | a minimum depth (one room + walls); take what is left along a frontage |
| plazas, park, yards, alleys | SLACK | absorb the rounding; they are where the grid's residue goes on purpose |

So the order of decision is:

1. **The route and its experiences** (the circuit: what the player must
   reach and see, in what order; where the landmarks sit on the vista).
   This is already `city_plan.CIRCUIT` and `VENUES`; keep it.
2. **Rigid interiors → envelopes.** A building's size comes UP from its
   rooms: interior + walls + facade depth (recess 512 for inserts) +
   nothing else. Not down from a block rectangle taken from a norm.
3. **Streets as corridors between envelopes**, each with its class
   minimum and its pavement bands on both sides; junctions where
   corridors meet. Adjacency, not geometry: "the theatre fronts the Row",
   "the church fronts the avenue from inside the cemetery".
4. **Solve the grid.** The plan's running-sum grid (`city_plan.py`:
   column widths, street widths) is the right skeleton; today its cell
   widths come from norms (CN 2 mid mode) — replace them with the
   envelope sums from step 2, and let corridor widths be their minima.
   That is a one-dimensional solve per axis: cells = max(envelope
   demands in that column/row), gutters = class minimum, total = city
   size; if the total is wrong, the SLACK elements (plaza, park, yard)
   change size, never the interiors and never the corridors below
   minimum.
5. **Islands and masses.** Each cell becomes a pavement island (cell +
   band); the envelopes stand on it; leftover frontage on the island is
   filler buildings with a minimum depth, or a yard/alley if below it.
6. **Surfaces, facades, inserts** (P13), then **light** (P14): these are
   consequences of the massing, not inputs to it.

Constraints that bound the whole: the wall budget (7000) fixes total
frontage-with-detail, hence the enterable share (a norm we already
measure); the sky canyon ratio bounds street width against mass height;
E3M1's block pitch (road strip length between junctions ~18–21k, road
width 4096–7456, pavements 512–2560) is the sanity check for step 4's
output, compared as rates.

What changes in the code: L1 gains the envelopes (per venue, from its
pattern) and the corridor minima; a small solver turns them into the
running-sum grid; L2 (P14) builds ground plane, islands and masses from
the solution. The graph, the circuit and the district identities stay.

Two things NOT to do: take building sizes from norms and carve rooms into
them (rooms end up wrong-sized, as the arcade did); and treat a street as
a fixed rectangle — it is a corridor with a floor on its width.

## 10. Owner's composition rule, and P14 rewritten (2026-09-02)

The owner: E3M1 has a main road that needs its width, and between some
houses only a pavement, which can be narrower. So: design the QUARTERS
as pavement islands with their buildings (from the interiors up), then
insert roads BETWEEN islands that simply push them apart by the class
width; where no road runs, islands abut with a pavement-only path
between the houses (E3M1's s10/s11: 512 wide). Roads are spacers,
islands are the designed things. That is the composition rule for P14.

### P14 (final) — the ground-plane city

```text
You are agent P14 on the llmapper repository (D:\Games\DOS\llmapper,
branch blood-city-arcade). Start only after the current P13 work has
landed (bloodmap/surface.py: Surface / Opening / Insert / RecordOwner,
the holder law, the magnitude gate) -- read its status at the end of
09_IMPLEMENTATION_ROADMAP.md first, then AGENT_START_HERE.md,
10_AGENT_EXECUTION_PROTOCOL.md ("Irreplaceable local data"), the
supervisor brief section 6, ARCHITECT-REVIEW-REPRESENTATION-2026-09-02.md
and ALL of projects/blood-city/reports/street-model-decisions-2026-09-02.md
(the decisions D1-D6 are taken; sections 7, 9 and 10 are the model).
Append your status to the roadmap in the protocol's format.

HARD RULES: never delete a directory tree; never create junctions or
symlinks; never launch NBlood or xmapedit; corpus via BLOODMAP_CORPUS=
D:\Games\DOS\llmapper\maps\blood and absolute paths if in a worktree;
engine/editor sources read-only under D:\Games\DOS\llmapper\NBlood and
xmapedit, never staged; commit by file name; never git add -A; never
commit maps/ or reference/. Suite: python -m unittest discover -s tests >
suite.log 2>&1, then grep ^Ran and ^OK/^FAILED; never pipe through tail;
report the Ran line verbatim. Trailer:
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
Every gate is written to FAIL FIRST on the current city. Rates, not
counts, against the campaign. Every engine claim cites file:line. And
the lesson of owner-queue item 17: for every quantity you gate, add ONE
absolute, corpus-anchored magnitude check -- a relative check passes a
uniformly wrong map.

THE MODEL (decided by the owner). Streets are the ground plane.
Pavements are ISLANDS standing on it, 2048 higher; the island's edge
showing above the road is the kerb and its exposed band wears the kerb
tile (E3M1: tile 6 on the ROAD-side record, 11/11). Buildings stand on
the islands; a building has a FACADE surface with holes; shopfronts,
windows and doors are inserts in the holes (P13). Lamps stand on the
pavements. One sun for the whole level, direction as measured on E3M1
(state it once in resolution.py in Build angle units). Sectors are the
INTERSECTION of independent partitions (function, height, light,
mechanism) and surfaces keep their frames across the pieces. Quarters
are designed as islands from the interiors up; roads are spacers
inserted between islands at their class width; where no road runs,
islands abut with a pavement-only path (E3M1 s10/s11, 512 wide).

E3M1, the measured template (re-measure, then cite your numbers):
road 352 at z 10240 in straight strips (s8 7456x21504, s45 18048x4096,
s3 5120x5120 at the crossing); pavements tile 4 at z 8192, bands 512 /
1024 / 2048 / 2560 along the building faces; plazas 379 at pavement
level; kerb face 6 on the road-side record; shade lit 8 / shadow 32-34 /
penumbra 24 with shadow edges cast by one oblique light (about 84
degrees in wall terms, 416 over 4096); 33 of 68 street sectors under
sky 3491.

DELIVERABLES, in this order

1. L1 becomes a constraint program (projects/blood-city/level/city_plan.py
   plus a new solver module). Keep NODES/EDGES (the circuit and the
   street graph), VENUES, DISTRICTS as identities, AREAS (plaza,
   cemetery, yard). Add for each venue its ENVELOPE, derived UP from its
   interior pattern (references/venue-patterns.md and the l3_* modules'
   measured room sizes): rooms + walls + facade depth (512 recess for
   inserts). Add for each edge its corridor MINIMUM by class
   (resolution.WIDTH_UNITS) plus pavement bands on both sides, and a
   "path" class = pavement only. Replace the norm-derived column/row
   widths with a one-dimensional solve per axis: cell = max envelope
   demand in that column/row, gutter = class minimum, slack absorbed ONLY
   by the plaza, the cemetery, the yard and alleys, never by interiors
   and never by corridors below minimum. Print the solved grid beside the
   old one and beside E3M1's block pitch (as rates). Keep the plan free
   of picnums and z, as the layer contract says.

2. Compiler: PARTITION OVERLAYS in bloodmap/planar_layout.py (design them
   with the levelprog tree in mind; the tree is the source). An overlay
   is a set of polygons that split existing regions into pieces without
   changing ownership, surfaces, frames or behaviour; the pieces inherit
   everything from the parent and differ only in what the overlay says.
   Two kinds now: HEIGHT ISLANDS (an island region raised by 2048 over
   the ground plane it stands on; the compiler emits the kerb band on
   the road-side records with the island's kerb tile and pegs it as E3M1
   does) and LIGHT (shadow polygons carrying a floor/wall shade). The
   road surface's frame must continue across an overlay edge: assert
   with the ported auto-align invariance and with texture_frame's world
   u-origin. Refuse overlaps the compiler cannot resolve loudly; do not
   "insert a sector where there is room" -- that idiom is what this
   replaces.

3. Light: one directional sun per level. Project each mass's shadow onto
   the ground plane (mass height from its clear height and the sun's
   elevation: state the convention) and cut it in as the light overlay;
   shade palette re-measured over the campaign's outdoor street sectors,
   E3M1's 8 / 32-34 / 24 as the prior; LightBomb stays for lamps and
   interiors; the light pools become pieces of the light overlay, not
   carved sectors.

4. L2 rebuilt from the solved plan: (a) the street network as one ground
   plane per connected network, tile 352, z = grade + 2048; (b) islands:
   solved cells grown by their pavement band, tile 4 at grade, lamps at
   E3M1's furniture rate at venue mouths, gates and junctions; paths
   between abutting islands; (c) building masses on the islands with
   FACADE surfaces (bloodmap/surface.py) and their holes; inserts through
   P13's holders; (d) plazas and the cemetery as pavement-level surfaces
   (379 / 361), the yard as an island notch; (e) junctions as road
   squares. Districts survive as style groups and norm bins; the seam
   decision is closed by construction -- say so in the owner queue and
   cross out the items it retires. Preserve every mechanism the city
   already has (curtain, turnstiles, doors, sewer stacks, secret
   declaration) by re-placing it through its existing placer, and read
   each back.

5. Gates, fail-first on the current city, each with an absolute check:
   every kerb band wears the kerb tile on its road-side record
   (absolute: tile 6 or a tile the campaign attests in that slot); every
   building face has a pavement between it and a road; no sector lower
   than all its neighbours without a declared reason (P12's rule); shadow
   edges share the sun's angle within tolerance; road frames continue
   across shadow edges and kerb edges; pavement band widths inside E3M1's
   envelope; road widths at or above class minimum; the wall budget.

6. Read back (bloodmap.readback) every construct; render a walk sheet
   with tools.render_precedent -- the west street from the road, the
   avenue, a junction, a kerb seen from the road, a shadow edge across a
   road, a lamp on a pavement, a shopfront in its recess, an arcade run
   -- before (the committed city) and after; re-run and re-baseline the
   city norms as rates; suite green.

REPORT: the solved grid vs the old vs E3M1; every gate's fail-first
result and its absolute check; the E3M1 comparison table after the
rebuild; mechanisms preserved and read back; the Ran line; what is
unproven; branch and commit hashes. Owner questions to
reports/owner-review-queue.md with a recommended default; two are
already answered by assumption -- plazas at pavement level without kerb
(yes), and pavement bands on lanes and alleys (always; E3M1 has 512 even
there).
```

## 11. After P14's first run (2026-09-02): what landed, what it means, P14b

P14 landed layers 1–3 (the envelope solver, partition overlays with an
exact half-plane cut and `HeightIsland`, the sun `SUN_BEARING = 478` at
45° elevation) and did not start the rebuild (commits 7533b9e, c9b664c).
That was the right call: a from-scratch regeneration of a 259-sector map
with every mechanism preserved is a wave of its own.

Two corrections to this document, accepted:

- **Tile 379 is not a plaza tile.** E3M1's 50 sectors wearing it are
  interiors at −90112…−136192. Plazas are pavement-level surfaces of
  tile 4 (or whatever the campaign attests for open ground at grade —
  measure) until a plaza tile is attested.
- **The kerb tile is E3M1's choice, not a law.** Over the campaign's
  1046 outdoor kerb-condition records the band wears 2490 (149), 67 (65),
  110 (51), 2499 (49), 6 (38)… So the rule is "the kerb band wears a
  kerb-class tile attested in that slot and never the material above
  it", with 6 as Gravesend's choice because its template is E3M1. The
  gate becomes exact once a kerb is a record `HeightIsland` declares
  (owner-queue item 18): agreed, and that is why it belongs to P14b.

Budget: E3M1 spends 177 walls (7%) on its 18 street sectors; street
anatomy with kerbs and shadow cuts is cheap. The city's 24% growth on x
costs little in street walls; the budget risk is facades and inserts,
and P14b checks it first.

**The sewer is a layer whose entries are owned.** In the plan the
network runs under the works superblock and its entries (yard grate,
old works pit, pump-station stair) belong to specific masses. Under the
new model the sewer's plan is DERIVED: entries follow the solved
position of their owning mass or yard, tunnels connect the entries by
the SEWER graph under the islands (under a road is fine once stacks may
overlap streets: the layers law only asks that link planes be
congruent), and the network is re-solved whenever the grid is. It is
not a fixed drawing that the buildings must avoid.

### P14b — one road, then the city, in slices

```text
You are agent P14b on the llmapper repository (D:\Games\DOS\llmapper,
branch blood-city-arcade, after commits 7533b9e and c9b664c). Read the
P14 status at the end of 09_IMPLEMENTATION_ROADMAP.md, then
AGENT_START_HERE.md, 10_AGENT_EXECUTION_PROTOCOL.md ("Irreplaceable
local data"), and projects/blood-city/reports/street-model-decisions-
2026-09-02.md in full (sections 10 and 11 are the model and the
corrections). Same hard rules as P14: no directory deletes, no
junctions, never launch NBlood or xmapedit, BLOODMAP_CORPUS and absolute
paths in a worktree, commit by name, suite to a log and report the Ran
line, trailer Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>.
Every gate fails first on the committed city and carries one absolute,
corpus-anchored check.

You have: the envelope solver (solved grid 73728 x 61440, built 72/67%,
corridor 28/33% -- E3M1's road share is 27%), partition overlays with an
exact half-plane cut, HeightIsland (rise 2048, kerb tile on the
road-side record), SUN_BEARING 478 at 45 degrees, bloodmap/surface.py
(Surface/Opening/Insert/RecordOwner), texture frames at natural scale,
readback. You do NOT yet have a single built street on the new model.

Slice 0 -- limits: one line, not a study. The target port is NBlood,
compiled with the V8 limits (NBlood/source/build/include/build.h:48-59:
4096 sectors, 16384 walls, 16384 sprites) and X-object limits of 4096
XSECTOR, 16384 XWALL, 16384 XSPRITE (db.h:25-27). The city is at 259 /
1694 / 430 and 53 / 27 / 110. The 7000-wall cap in project.json and the
512 X-object figures in the manual are vanilla-DOS numbers and are
retired: update project.json to the NBlood limits with a stated reserve,
report the counts after each slice, and never shrink a slack element for
budget unless a real limit is within reach. Map size is the owner's
choice; larger than E3M1 is intended.

Slice 1 -- one road. Emit the west street alone on the new model: the
ground plane (tile 352, z grade+2048), the two islands beside it (tile 4
at grade, bands from the solve), the kerb cut by HeightIsland on the
road-side records, one mass on each island casting its shadow through
the light overlay, two lamps on the pavements, one shopfront insert in a
recess. Prove on this slice: the road frame survives the kerb cut and
the shadow cut (ported auto-align invariance + texture_frame.world_u);
the kerb band wears the declared kerb tile on every road-side record and
never the material above it (the exact rule, now that the kerb is a
declared record -- close owner-queue item 18 with it); shadow edges
share SUN_BEARING; a body walking the road sees the kerb face, not the
house. Render it from the road and from the pavement; read it back.
Commit this slice on its own.

Slice 2 -- all streets and islands. The whole graph as ground planes,
every solved cell as an island with its bands, paths between abutting
islands, junction squares, plazas and the cemetery at pavement level,
the yard as an island notch, lamps at E3M1's rate. No masses yet. Gates
from slice 1 over the whole; the wall count against the slice-0
estimate.

Slice 3 -- masses and interiors. Re-parent every existing L3 module
(l3_theatre, l3_church, l3_market, l3_mall, l3_foundry, l3_sewer,
l3_shed) onto its island with its envelope from the solve; facades as
Surfaces with openings; every existing insert and mechanism re-placed
through its own placer (curtain, turnstiles, doors, glass) and read back;
the secret declaration kept. Continuity and magnitude gates over the
whole city.

Slice 4 -- the sewer, derived. Re-solve the SEWER graph from the solved
positions of its entry owners (yard grate, old works pit, pump-station
stair); tunnels under islands or roads as the graph needs; link planes
congruent (bloodmap.layers law); ROR read back through
reachability.link_pairs. Report what moved relative to the old network.

Slice 5 -- the walk sheet and the norms: before (the committed city) and
after, the frames the owner asked for (west street from the road, the
avenue, a junction, a kerb from the road, a shadow across a road, a lamp,
a shopfront in its recess, an arcade run), norms re-baselined as rates,
the E3M1 comparison table, suite green.

Commit each slice separately; if a later slice cannot land, the earlier
ones still stand and say so. Report per slice: what was built, which
gate failed first and on what, the absolute check, the wall count, what
is unproven. Owner questions to reports/owner-review-queue.md with a
recommended default.
```

## 12. The owner walked slice 1 (2026-09-02): two defects, both constructs

The one road reads right: kerb from the road, shadows across it, lamps
on the pavement. Two things are wrong, and both are things the model had
not named yet.

**Sky.** Slice 1's street and island ceilings wear the FLOOR tiles (352,
4) with the parallax bit set. The street sky is 3491 (E3M1: 33 of 68
street sectors, all 3491). The project's own law "a parallax ceiling
wears a sky-family tile {2500, 3491, 3678}" exists as a usage gate and
did not fire because the slice map never went through the city's gate
set. Rule: a slice map runs every gate the city runs, or it is not a
slice.

**Road terminations.** Slice 1 ends the road at a wall shared with the
houses, and the kerb tile bled onto it. E3M1 never ends a road at a
house. Its road is a T, and each of the three ends is an END WALL —
sectors 0, 339, 343 — measured:

| | s0 | s339 | s343 |
| --- | --- | --- | --- |
| floor (wall top) tile | 379 | 379 | 379 |
| wall top above the road | 5.8 player heights (98304) | 3.9 (65536) | 5.8 |
| top below the sky line | 5.8 | 7.7 | 5.8 |
| ceiling | sky 3491, parallax | same | same |
| faces to road and pavements | two-sided, **cstat 1 blocking**, facade stone 400 / 401 / 108, y_repeat 8 | | |
| far side | one-sided brick 181, or zero-height closed sectors (s340, s338: floor = ceiling = 8192) as solid backing | | |

So an end wall is a raised sector whose floor is the wall top, high
enough that no body reaches it (≥ 3.9 player heights) and lower than
the houses (its top sits 5.8–7.7 player heights under the sky line, so
it reads as a wall against sky, not as a building), with blocking
two-sided faces that draw the wall in facade stone from the road, and a
solid backing behind. The "inner edge" the owner describes is exactly
that: the road-side record's lower band, from the road floor up to the
raised floor, is the wall you see.

Correction to §11: **tile 379 is E3M1's roof and wall-top tile**, not a
plaza tile and not an interior — 37 of its 50 sectors sit 1–8.6 player
heights above the road (roofs, parapets, the end walls). Plazas stay
tile 4 at pavement level.

Rule for the model: **every road end is a declared TERMINATION
construct** — an end wall (E3M1's dialect), a gate, or an off-map arch —
never the wall of a building and never a kerb. Terminations are inserts
on the street ground plane the way shopfronts are inserts in a facade:
they own their sectors and their frames.

### Addendum for slice 2

```text
Before the whole graph, add to slice 1 and re-prove it:
(a) sky: street and island ceilings wear 3491 with the parallax bit, from
    a STREET sky material, never a floor tile; run the slice map through
    every gate the city build runs (usage laws, magnitude, continuity,
    read-back) -- the parallax law would have caught this;
(b) terminations: bloodmap/street.py gains `end_wall`, E3M1's dialect
    (sectors 0, 339, 343): a raised sector at the road end whose floor is
    the wall top wearing 379, 3.9-5.8 player heights above the road and
    5.8-7.7 under the sky line, sky ceiling, blocking (cstat 1)
    two-sided faces to the road and its pavements in the district's
    facade stone at y_repeat 8, a solid backing behind (one-sided brick
    or a zero-height closed sector); every road end in the graph that
    does not continue into a junction or a gate must be a declared
    termination, and a road end that meets a building or a kerb is a
    gate failure (fail-first on slice 1 as committed). The end wall's
    faces carry their own frame: they are inserts on the ground plane,
    not part of any facade run.
Then the whole graph as specified.
```

## 13. The join grammar (owner, 2026-09-02): things are one table, joins are the other

The owner: a kerb is not an object. It is what the join road|pavement
looks like — the texture on the inner face of the road record — and it
may or may not be a physical sector. Different pairs join differently:
road|road simply continues; road|pavement makes a kerb; a termination
cuts the road; and so on. The principle is the one Wave Function
Collapse uses: not only the pieces but the rules for how pieces may
meet. That is the representation the compiler has been missing, and it
subsumes §6d (holders), the kerb (P14), the terminations (§12) and
continuity across cuts (P11/P13).

**JoinRule.** Keyed by the ordered pair of SURFACE KINDS meeting at an
edge (and the height relation between them). It says, for each side's
wall record: which band shows and what tile class it wears, which cstat
bits (blocking, masked, one-way, cstat 4 pegging), whether the surface
frame CONTINUES across the edge or the edge is a frame boundary, and
whether the join needs a holder sector to exist at all. The compiler
applies the table at every shared edge after overlay partitioning; a
pair with no rule is a loud failure, never a default.

Seed table, from E3M1 to the field:

| A \| B | height | A's record shows | continuity | note |
| --- | --- | --- | --- | --- |
| road \| road (shadow or junction cut) | equal | nothing | road frame continues | s3\|s8, s7\|s8, s8\|s45 |
| road \| pavement | B +2048 | lower band = kerb class (E3M1 tile 6; campaign 2490/67/110/2499/6…) | frames independent | 11/11 kerbs |
| pavement \| pavement (path, shadow cut) | equal | nothing | pavement frame continues | s10/s11 paths, shadow splits |
| pavement \| building (facade) | one-sided | facade run | facade frame world-anchored | facade_pass |
| road \| end wall | B +65536…98304 | lower band = facade stone, **blocking** | frame boundary; the wall's own frame | s0, s339, s343 |
| pavement \| end wall | same | same | same | |
| facade \| opening (recess mouth) | holder inside | upper band pegged cstat 4 continues the facade; holder records carry the insert's frame | facade frame continues over the mouth | E6M1 s4/s64 |
| road \| kerb-less edge (a road ending at a wall) | — | **forbidden** | — | the slice-1 fault |

Joins are mined, not invented: over the campaign, classify both sides of
every shared wall by surface kind and height relation and tabulate what
the records wear; E3M1 seeds the outdoor rows, E6M1 the shopfront row,
the curtain and door precedents the mechanism rows. The reader half is
the same table read backwards: a two-sided wall whose records match a
rule is evidence of that join, which is how surfaces are recovered from
originals.

Where the WFC analogy stops: the PIECES here are chosen by the plan and
its solver, deterministically; the grammar decides only the seams. The
same socket table can later drive generative filling (filler buildings,
Phase 15 diversity), but that is not what it is for now.

### Addendum for slice 2, revised (replaces the `end_wall` special case)

```text
Before the whole graph, add to slice 1 and re-prove it:
(a) sky: street and island ceilings wear 3491 with the parallax bit,
    from a STREET sky material, never a floor tile; run the slice map
    through every gate the city build runs.
(b) bloodmap/joins.py: a JoinRule table keyed by (surface kind A,
    surface kind B, height relation) that states, per side, the band
    and tile class shown, the cstat bits, whether the frame continues
    or the edge is a frame boundary, and whether a holder is required.
    Seed it with the E3M1 rows in decisions section 13 and the E6M1
    shopfront row; a pair with no rule is a loud compile failure. The
    compiler applies it at every shared edge after overlay partitioning,
    and HeightIsland's kerb, P13's holders and the terminations below
    become rows of it rather than special cases. Mine the campaign for
    the table's evidence (tools/join_census.py: both sides classified by
    surface kind and height relation, what the records wear, as rates)
    and put the table beside the census.
(c) terminations as a surface kind: an END WALL (E3M1 s0/s339/s343: a
    raised sector whose floor is the wall top wearing 379, 3.9-5.8
    player heights above the road and 5.8-7.7 under the sky line, sky
    ceiling, solid backing) with the road|end wall row: lower band in
    facade stone, blocking, frame boundary. Every road end that is not a
    junction or a gate must meet a termination; a road ending at a
    building or a kerb is a gate failure (fail-first on slice 1 as
    committed).
Then the whole graph as specified.
```

## 14. The edge of the map is a family, not an end wall (owner, 2026-09-02)

An end wall is one kind of what interrupts a path. The general thing is
the MAP EDGE: how the playable city meets its real termination. The
owner names the family; three members are measured:

| edge kind | precedent | what it is, to the field |
| --- | --- | --- |
| **end wall** | E3M1 s0 / s339 / s343 | raised sector, floor = wall top (379) 3.9–5.8 player heights above the road, 5.8–7.7 under the sky line, sky ceiling, blocking two-sided faces in facade stone, solid backing (one-sided brick 181 or zero-height sectors s338/s340); E3M1's outermost skin is 8 sectors of tile 0 at 8192 — the backing nobody sees |
| **chasm** | DWE3M1 | 15 outermost sectors at z 526336 wearing rock (274, 411, 283, 270); the walkable rim sits 26–28 player heights above it (rim floors 82944 / 53248); the city also ends in its own building masses |
| **horizon over water** | DWE3M10 s404 (29 walls), s201, s202 | a sector whose FLOOR and CEILING are both the sky tile 3678 with the parallax bit on both (floorstat 1, ceilingstat 1): the sea meets the sky; its neighbours are the quay sectors (tile 2490 — a kerb-class tile — at the same z 21504) |
| **enclosure with backdrop** | owner's description (not yet located in the corpus) | the city ringed by walls, and beyond them fake masses with no interiors so the city reads larger; `reachability.classify_offmap` is the reader that should find backdrop masses (unreachable one-sided loops beyond the skin) — it currently raises `TypeError: unhashable type: 'dict'` on every map and needs fixing before it can |
| **the buildings themselves** | DWE3M1 | solid masses on the boundary, no gap behind them |

In the join grammar (§13) each is a surface kind with its own rows:
road|end wall (blocking facade stone, frame boundary), pavement|chasm
(a drop, a rim record showing rock, no kerb), quay|horizon (equal z,
nothing drawn, the horizon's own sky frames), street|enclosure (like
end wall, then backdrop beyond). A road may only end at a junction, a
gate, or an edge kind; ending at a building or a kerb is the slice-1
fault. The plan should say, per side of the city, which edge kind it
uses — Gravesend's quay side wants the horizon over water, the others
end walls or enclosure with backdrop — and the L2 builds that edge as an
insert on the ground plane.

### Addendum for slice 2 (edge family)

```text
(d) the map edge is a surface-kind family in bloodmap/joins.py, with
    three measured members and one to locate: END WALL (E3M1 s0/s339/
    s343), CHASM (DWE3M1: outermost sectors 26-28 player heights below
    the rim, rock tiles), HORIZON OVER WATER (DWE3M10 s404: floor and
    ceiling both sky 3678 with parallax on both; neighbours the quay at
    equal z), and ENCLOSURE WITH BACKDROP (walls ringing the city, fake
    masses beyond, no interiors -- find a corpus precedent; fix
    reachability.classify_offmap, which raises TypeError on every map,
    so backdrop masses can be read). The plan states the edge kind per
    side of the city (quay side: horizon over water; the others: end
    walls or enclosure with backdrop); L2 builds each edge as an insert
    on the ground plane with its own frames; the join rows road|edge and
    pavement|edge come from the precedents, as rates; a road end that is
    not a junction, a gate or an edge kind is a gate failure.
```

## 15. How the edges fit together (owner, 2026-09-02): the boundary is a chain, and buildings may be links in it

### 15a. The waterfront, measured on DWE3M10

| band, from the city outward | DWE3M10 | to the field |
| --- | --- | --- |
| shore | s402 concrete 416, s403 sand 433, s121 a deck at −14336 (2.1 player heights above the sea) wearing 255 | walkable, at the sea's z or raised as a pier |
| sea | s399, s400, s401, s452 (97280 × 177152) | **tile 2490 with `pan_floor` + `pan_always`, velocity 10, angle 900, and `drag` on** — a flowing water surface that pushes a body; at z 21504, level with the shore; water links type 9/10 (4 pairs) where the sea is enterable |
| horizon | s404 (98304 × 179200) | floor AND ceiling sky 3678, parallax on both; shore-side walls two-sided into the sea; far-side walls one-sided (177, 130) at the map's rim, never seen |

**Correction, and it matters for the kerb gate: tile 2490 is water, not
a kerb.** The campaign kerb-condition census (P14 status) put 2490 first
with 149 records because a sea meeting a shore is a two-sided step with
a floor below — the same geometry as a kerb. The kerb rule must exclude
panning/drag water sectors, which is one more reason the population
must be DECLARED (an island's kerb) rather than guessed from steps.

### 15b. The boundary is a chain of edge segments

The city's ground plane is bounded, and the boundary is a closed chain
whose segments each have an edge kind (§14): building back, end wall,
enclosure with backdrop, waterfront (shore → sea → horizon), chasm,
gate. Adjacent segments join by the join grammar (§13), so a waterfront
meeting an end wall, or a building back meeting a chasm, is a rule, not
an accident.

**A building may be a link in the chain.** A full building — facade,
interior, mechanisms — can stand on the boundary and terminate the
city. From outside it is a flat wall of one-sided records against the
void; nobody stands outside, so nothing is drawn there and no sector is
spent. Such a building is not a rectangle floating in the street plane:
it is a half-open island whose outer edge IS the boundary. DWE3M1 does
this with its masses. Consequences for the solver and L2:

- perimeter lanes (`city_plan.LANE` on all four sides) exist only where
  the edge kind needs a street behind the buildings (enclosure with
  backdrop, or a gate); on a building-back side the outer cells' outer
  edges are void and the lane is dropped;
- a street that reaches the boundary ends in the edge kind of that side:
  an end wall (E3M1's T), a gate through an enclosure, or the shore;
- an edge building's outer walls carry no facade frame (never seen) and
  its interior is entered from the street side only; its roof, if it is
  visible from anywhere, wears the roof tile (379 in E3M1);
- the boundary chain is stated in the plan, per side, as a list of
  segments with kinds, and L2 builds each segment as an insert on the
  ground plane or as the outer edge of an island.

### 15c. Gravesend's edges, proposed

| side | today | proposed |
| --- | --- | --- |
| south (the quay, Market Slip) | a ROW-class street "the quay" with nothing beyond | **waterfront**: the quay as shore (quay stone, a pier or two as raised decks), the sea as a panning 2490 surface with drag, water links only where the player may enter, the horizon sector beyond; the avenue and the spurs end at the shore |
| north (Theatre Row, Foundry) | the north lane and the district boundary | **buildings as edge** along most of it (the Aldermack superblock's back and the works' back are void), with **end walls** where the avenue and the rail spur reach the boundary; an enclosure-with-backdrop stretch only if a side needs a street behind |
| west (Old Crossing) | the west lane | mixed: building backs, an end wall at the west street's T |
| east (Foundry Ward) | the spur and the works | the works' back as building edge; the rail spur ends at a gate or an end wall |

Nothing here is a plan change the solver cannot absorb: the perimeter
lanes become optional per side, the edge kinds become inserts, and the
quay side gains three surfaces (shore, sea, horizon) whose depths are
free (DWE3M10's sea is ~97k deep; the horizon is a backdrop and costs
one sector).

### Addendum for slice 2 (edges, final)

```text
(e) the boundary chain: city_plan.py states, per side of the city, a
    list of edge segments with kinds (building_back, end_wall,
    enclosure_backdrop, waterfront, chasm, gate); the solver drops the
    perimeter lane on building_back sides; L2 builds each segment as an
    insert on the ground plane or as the outer (void) edge of an island.
    Waterfront per DWE3M10: shore surfaces at the sea's z (quay stone,
    concrete 416, sand 433; a pier as a raised deck), the sea as a
    surface wearing 2490 with pan_floor + pan_always (velocity 10, angle
    per the sun-free convention you state) and drag, water links only
    where the player may enter, then a horizon sector with floor and
    ceiling both sky 3678 and the parallax bit on both. Gravesend's
    south side is the waterfront; north and east are building backs
    with end walls where the avenue and the spur reach the boundary;
    west is building backs with an end wall at the west street's T.
    Join rows: shore|sea (equal z, nothing drawn, the sea's own frame),
    sea|horizon (nothing drawn), building_back|void (one-sided, no
    facade frame), street|end_wall as in (c). Correct the kerb census:
    2490 is water, and the kerb rule excludes panning/drag sectors.
```

## 16. After the join-grammar run (2026-09-02): decisions the supervisor took, and what waits for the owner

Landed (4221670): `bloodmap/joins.py` with eleven evidenced rows and a
loud failure for a pair with no rule; `city_plan.BOUNDARY` per side;
`building_back_sides()` dropping perimeter lanes; the waterfront measured
(18 sea sectors; the horizon is a ZERO-HEIGHT sector, floor_z ==
ceiling_z == 21504, sky 3678 on both, parallax on both). Corrections
accepted:

- **2490 is stone that Blood palettises into water** (25 of its 34
  campaign sectors carry floor palette 10 and pan; 8 are palette 0 and
  still). `joins.is_water` tests palette and behaviour, not the tile.
  Excluding water removes 13% of the outdoor step records and 2490 still
  tops the rest as stone — so the kerb census was wrong because surface
  kinds are not readable from tiles, which is what declared surfaces and
  the join table fix. Section 15a's "2490 is water" is withdrawn.
- **The chasm reference frame** is the city's median floor, not the
  immediate neighbours (DWE3M1: 26.9 player heights below the median).
- `reachability.classify_offmap` does not raise; the TypeError was the
  supervisor's own call with the wrong argument. Withdrawn.

Decided by the supervisor (no owner input needed):

1. **`enclosure_backdrop` stays a named, countable gap.** No corpus
   precedent was found; the family has three measured members. Nobody
   invents a row; if the owner knows a map that rings its city with
   walls and fake masses, it becomes the fourth (owner-queue item 20,
   default accepted).
2. **Junction squares are pieces of the ground plane, not regions.** The
   slice-2 emitter fails `zero_exit_gameplay_sector` at three junction
   squares because it emits the squares as separate regions joined by
   connections. The model says otherwise: the street network is ONE
   ground-plane region per connected network, cut into pieces by the
   overlays (shadows) and by the joins (kerbs); a junction is where two
   strips' cuts meet, and it has no exits of its own to declare. Emit
   the plane whole, then cut.
3. **The compiler applies the join table** at every shared edge after
   overlay partitioning; that is the first deliverable of the next run,
   before the whole graph, proved on the slice-1 map (every existing
   kerb, end wall and pane record must come out identical under the
   table, and the table must refuse a pair it has no row for).
4. **Editor autosaves are never corpus, anywhere.** XMapEdit drops
   `ASAVE<n>.map` into whichever directory it was opened from; the owner
   opens the editor daily ("ignore them"). `bloodmap.patterns._admitted`
   now quarantines `is_editor_autosave` files in every population —
   before this, `curated/` accepted them as maps (47 for 46) — and
   agents keep not touching `maps/`.

Waiting for the owner (optional, nothing blocks):

- a corpus map with an enclosure-and-backdrop edge, if one exists;
- a walk of slice 2 when it lands (the same two-minute look that caught
  the sky and the road ends in slice 1);
- if the autosaves annoy: XMapEdit's `[AUTOSAVE]` setting in
  `XMAPEDIT.INI` can point them at a directory outside the corpus.

### Continue prompt — slice 2b

```text
Continue as P14b, slice 2b, from commit 4221670. Read your own status
at the end of 09_IMPLEMENTATION_ROADMAP.md and sections 13-16 of
projects/blood-city/reports/street-model-decisions-2026-09-02.md. Same
hard rules (no directory deletes, no junctions, never launch NBlood or
xmapedit, BLOODMAP_CORPUS and absolute paths in a worktree, commit by
file name, suite to a log and the Ran line verbatim, trailer
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>). Editor
autosaves in maps/ are quarantined by the registry now; ignore them.

1. The compiler applies bloodmap/joins.py at every shared edge after
   overlay partitioning. Prove it on the committed slice-1 map: rebuild
   it through the table and diff record by record -- every kerb, end
   wall and pane record identical; a synthetic pair with no row must
   refuse loudly. Fail-first: a map with an undeclared pair.
2. Junction squares are pieces of ONE ground-plane region per connected
   street network, cut by the overlays and the joins, not separate
   regions joined by connections (decision 16.2); that removes the
   zero_exit_gameplay_sector failure by construction. Prove on a T and
   on a crossing.
3. Then the whole graph, no masses, as specified in section 10/11
   (slice 2): every edge as ground plane at its class width, islands
   with bands, paths between abutting islands, junctions, plaza and
   cemetery at pavement level, the yard notch, lamps, the south
   waterfront (shore, sea with palette-10 stone + pan + drag, horizon
   as a zero-height sky sector), end walls where the avenue, the spur
   and the west street reach the boundary, building backs elsewhere
   (void, no lane). Every gate from slice 1 over the whole map, each
   with its absolute check; counts against the NBlood limits.
4. Read back, render four frames (a street from the road, a junction, a
   path between islands, the quay with the horizon), suite green,
   commit. Stop and report: what the table refused, what the compiler
   refused, what slice 3 must answer first.
```

## 17. Overlays, systemically (2026-09-02): domain, geometry, order, and what a cut may never touch

Slice 2b landed the join table in the compiler (32f31ec) and the ground
plane as one concave region per network with junctions as the uncovered
part (0a4b13e). It then stopped: a shadow cannot cut the plane, because
`overlay.split_convex` refuses concave polygons by design, and
`apply_overlay` clips by the shadow's bounding RECTANGLE and cuts EVERY
region the rectangle touches — interiors and mechanism sectors included.
Owner-queue item 21 asks for a simple-polygon splitter. That is
necessary and not sufficient; the owner's worry is the right one: an
outdoor shadow must never reach an interior, and a cut must never break
what the rest of the system relies on. Four rules make overlays safe.

**Rule 1 — every overlay has a DOMAIN.** An overlay is (polygons, what it
sets, and a predicate saying WHICH surfaces it may cut). LIGHT applies to
outdoor ground surfaces only: the street plane, islands, plazas, the
shore, visible roofs — regions under a parallax sky ceiling. Interiors
are lit by LightBomb from their declared sources and by their own
INTERIOR LIGHT overlays (a window's pool is one), never by the sun's
shadows. HEIGHT ISLAND applies only to the region it is declared on.
A shadow crossing a region outside its domain is not applied there, and
the compiler says so in the manifest, not as an error.

**Rule 2 — a cut never touches an insert or a mechanism.** Regions that
carry a sector type, a moving wall, a stack marker, a holder role or an
insert are EXCLUDED from every overlay: cutting a mover changes its
DragPoint closure (P3), cutting a holder breaks the one-record-one-frame
law (§6d), cutting a curtain fin changes what its motion set is. Gate:
`motion_set` and `closure_health` of every mechanism are identical before
and after overlays are applied — fail-first by placing a shadow over the
slice-1 shopfront and over a curtain.

**Rule 3 — the geometry is a real clipper, on the pieces the overlay
actually covers, with re-merge.** Accept item 21's default (a simple-
polygon half-plane splitter, exact in integers, area-conserving) and
add three things it needs to be usable on a lattice: (a) a region is a
polygon WITH HOLES (the plane's islands are its holes), so the even-odd
chord pairing runs over all rings; (b) a shadow polygon is convex, so a
shadow is a sequence of half-plane cuts applied only to pieces whose
outline actually overlaps the shadow, never to the whole plane; (c) after
one shadow's cuts, adjacent OUTSIDE pieces are merged back along the
chords they share, so a shadow adds exactly its own boundary and nothing
else — otherwise every shadow line would run to the map's edge and the
sector count would explode. Slivers under MIN_PIECE_AREA are absorbed
into the neighbouring piece by snapping the chord to the nearest vertex,
deterministically, not refused. Intersections snap to integers; the
gate is area conservation within a stated tolerance per cut plus loop
validity through the existing compiler checks.

**Rule 4 — shadows are a FIELD, cut once.** Union all mass shadows of a
ground plane into one shadow field before cutting (E3M1: 44 shade
boundaries over 68 street sectors — broad zones, not one polygon per
house), then cut the plane and its islands by the field. Pieces inside
are shadow, outside are lit; penumbra only where the corpus measurement
says so.

**Order of operations, fixed:**

1. ground planes and islands (height);
2. inserts and mechanisms declared (holders, terminations, movers) —
   these are now excluded from cutting;
3. LIGHT overlay on its domain (outdoor ground surfaces minus inserts);
4. joins applied at every shared edge (32f31ec);
5. frames resolved (P11/P13) — surfaces keep one frame across all pieces.

Reading side, unchanged: shade boundaries at the sun's bearing recover
the field from an original (E3M1's 20 oblique edges at 84°), and a
mechanism inside a shadow is a finding about the original, not a cut.

### Continue prompt — slice 2c

```text
Continue as P14b, slice 2c, from commit 0a4b13e. Read your status at the
end of 09_IMPLEMENTATION_ROADMAP.md and sections 16-17 of
projects/blood-city/reports/street-model-decisions-2026-09-02.md.
Same hard rules (no directory deletes, no junctions or symlinks, never
launch NBlood or xmapedit, BLOODMAP_CORPUS and absolute paths in a
worktree, commit by file name, never git add -A, suite to a log and the
Ran line verbatim, trailer Co-Authored-By: Claude Opus 5
<noreply@anthropic.com>); every gate fails first and carries one
absolute check; commit each deliverable on its own.

1. Overlay DOMAINS in bloodmap/overlay.py: an overlay declares the
   predicate over regions it may cut. LIGHT: regions under a parallax
   sky ceiling that are ground/island/plaza/shore/roof surfaces. HEIGHT
   ISLAND: its own region only. Regions carrying a sector type, a moving
   wall (cstat 0x4000/0x8000), a stack or path marker, a holder role or
   an insert are excluded from every overlay. Out-of-domain crossings
   are reported in the manifest, not applied. Fail-first: a shadow laid
   over a house with an interior must leave every interior sector's
   shade untouched; a shadow over the slice-1 shopfront and over a
   curtain must leave their motion_set / closure_health identical.
2. The clipper: implement owner-queue item 21's simple-polygon
   half-plane splitter exact in integers on polygons WITH HOLES
   (even-odd chord pairing over all rings), apply a convex shadow as a
   sequence of half-plane cuts only to pieces whose outline overlaps the
   shadow, re-merge adjacent outside pieces along shared chords after
   each shadow so nothing but the shadow's own boundary is added, absorb
   slivers under MIN_PIECE_AREA into the neighbour by snapping the chord
   to the nearest vertex (deterministic, reported), and gate on area
   conservation per cut within a stated integer tolerance plus the
   compiler's loop validity. Do NOT decompose the plane into convex
   pieces (item 21's rejected option). Tests: a concave lattice plane
   with two island holes cut by one oblique shadow; a shadow that
   crosses a junction; a shadow that covers a whole island; a sliver
   case.
3. Shadow FIELD: union the mass shadows of a plane into one field before
   cutting; cut the plane and its islands once; lit / shadow shade from
   the campaign measurement (E3M1 8 / 32-34), penumbra only if measured.
   Every shadow edge shares SUN_BEARING (gate), road and island frames
   continue across every edge (auto-align invariance + world_u).
4. Order of operations fixed and asserted in the compiler: planes and
   islands -> inserts and mechanisms declared -> LIGHT on its domain ->
   joins at every shared edge -> frames. A pass that runs out of order
   raises.
5. Rewrite the emitter around overlay.ground_plane (the per-edge
   rectangles and junction squares are retired) and re-run deliverable
   3 of slice 2b: the whole graph, no masses, placeholder masses at the
   solved envelopes' heights for the shadows, the south waterfront,
   end walls, building backs, lamps, every gate, counts against the
   NBlood limits; read back; render four frames; suite green; commit.

Stop and report: cuts refused and why, slivers absorbed (count), sector
and wall counts before/after the field, which gate failed first, what
remains unproven, and what slice 3 must answer first.
```

## 18. Two kinds of channel, and no more (owner, 2026-09-02)

A lamp under a shadow gives less light; a thing cannot open and close at
once. The owner asks for one simple, smart rule rather than a solver.
The rule: every overlay or source writes to CHANNELS, and a channel is
one of two kinds.

- **Additive** (light): every source contributes a delta and the deltas
  sum. The sun is a directional source occluded by masses; a lamp is a
  point source with a range; LightBomb already sums point sources, so
  the sun joins it. The SHADOW is then not an overlay of its own but an
  ISO-LINE of the light field: sun + lamps summed, quantised to a few
  levels (E3M1 uses three: 8 / 24 / 34), sectors cut where the level
  changes. A lamp inside a shadow resolves itself: shadow plus lamp.
- **Exclusive** (floor z, sector type and mechanism state, a surface's
  frame, a holder role): one owner; a second writer raises. "Opens and
  closes at once" is one channel with two writers, refused. P13's
  RecordOwner ledger does this for wall records; extend it to region
  channels.

The compiler carries a two-column table, channel -> additive |
exclusive, and nothing else: no priorities, no conflict solver.

Addendum to slice 2c, deliverable 3: the light is a FIELD -- the sun as
a directional LightBomb source occluded by the masses, lamps as point
sources -- quantised to the campaign's levels; the cut set is the
iso-lines of that field over the LIGHT domain. Deliverable 4 adds the
channel table and the region-channel ledger with a fail-first: two
overlays writing floor_z on one region, and a mechanism asked to open
and close, both refused by name.

## 19. Optional effects yield; required functions do not (owner, 2026-09-02)

Not every door must brighten a sector when it opens. If an effect cannot
be accommodated -- it would dominate the space, or it collides on an
exclusive channel -- it is dropped, not fought over, and the build goes
on. The project already has the instrument: `bloodmap.arbiter` ranks
claims as FUNCTION or PRESENTATION (it settled the curtain's rx/tx
collision). Generalise it to channels:

- every declared effect carries a claim kind: FUNCTION (the mechanism
  does its job: the door opens, the curtain draws, the kerb rises) or
  PRESENTATION (a Link-driven light, a pool, a shade wave, a panning, a
  shadow's penumbra);
- on an exclusive-channel conflict a PRESENTATION claim yields and the
  manifest records it by name with the reason ("stage light link dropped:
  channel shade on s24 owned by the sun field"); FUNCTION against FUNCTION
  is an error, as before;
- a dropped PRESENTATION claim is not a gate failure; the read-back
  compares the built map against the sentence AS ARBITRATED, so a dropped
  facet is expected absence, not a diff;
- the owner sees dropped facets in the review sheet as a list, and may
  promote one to FUNCTION when it matters (a landmark's light, say).

Addendum to slice 2c: extend the arbiter to region channels alongside
the two-kind table (section 18); fail-first: a Link-driven light on a
sector inside the sun field yields and is listed; a door asked to open
and close at once is refused. No effect may block the build unless it
is a FUNCTION claim.

## 20. The symmetry rule (owner, 2026-09-02): every writer has a reader, and the reader's census is the writer's evidence

The point of these principles is not only better levels: they must make
existing levels legible, make mining easier, and give the whole context.
The test is symmetry. Every concept the compiler writes must have a
reader that recovers it from an original map, and the reader's census
over the corpus is the only source of the writer's defaults. A principle
without its reader is a convention, not an observation.

| principle | writer | reader | state |
| --- | --- | --- | --- |
| surfaces and frames | frame -> wall fields in closed form | runs from x_panning - u(start) (`texture_frame.world_u`) | reader exists; per-surface norms not yet mined |
| joins | `joins.py` at every shared edge | classify both sides of every shared wall -> join census | table exists; census assigned, not yet run over 43 maps |
| height islands | HeightIsland | 2048 step + kerb row -> island | declared only; the inverse reader is missing |
| light field | sun + lamps -> iso-lines | shade boundaries at the sun's bearing -> field and sources | bearing read (E3M1 84 deg); field and sources not |
| channels and claims | ADDITIVE/EXCLUSIVE, FUNCTION/PRESENTATION | "a door without a light is expected absence" | mechanisms read; arbitrated absence not read |
| map edges | boundary chain per side | classify the perimeter (end wall, chasm, horizon, backs) | partly (`classify_offmap`); family measured by hand |
| envelopes and the solver | interiors -> cells -> grid | recover a city's street graph, islands, blocks and envelopes from an original | missing -- this is the acid test |

Acceptance test for "the system understands a level": decompile E3M1,
DWE3M1 and DWE3M10 into the plan language (street graph, islands with
bands, blocks with envelopes, joins, light field, edge chain), recompile,
and diff STRUCTURE, not bytes. Where it passes, the principle is an
observation; where it fails, the diff names the convention.
Recommended as the first task after slice 2c, before any further
building: until the readers exist, every wave adds conventions.

## 21. Item 22 decided: the light field quantises to a base plus a step, measured over the campaign (2026-09-02)

Domains and the clipper landed (94c1ba0, ee5705b): the LIGHT domain
admits 31 of the city's 259 regions and refuses 228 by name (197
interiors, 14 mechanisms, 13 inserts, 4 stack markers); every mover's
motion set is identical before and after, because the domain never
admitted one. `split_polygon` conserves area exactly on every named
case, including the U whose one side comes back as two pieces.

The agent asked (item 22) whether to quantise to E3M1's three shades.
No -- and the reason is measured, not argued. Over the 37 campaign maps
with outdoor sectors (parallax ceilings):

```text
significant shade levels per outdoor network (>= 5% of area, merged +-2):
   2 levels: 12 maps   3: 9   4: 6   1: 6   5-6: 4
absolute lit base varies per map: 0 (E1M1, E2M2, E3M8 ...), 4, 8 (E3M1, E3M2, E6M1),
   9, 16, 18, 22, 30 -- there is no campaign lit value, only a map's own
shade DELTA across same-z outdoor boundaries (the shadow edges):
   12 x44   16 x30   10 x24   8 x23   2 x22   4 x18   5 x16   15 x15   13 x15
```

Decision: the field is **base + k * STEP**, where the base is the
network's own lit shade (a plan/style value, campaign range 0-30; E3M1
uses 8) and STEP is the campaign's modal shadow step, **12** (envelope
8-16); k is the number of overlapping shadows at a point (additive
channel), capped so that no outdoor network has more than 4 levels;
lamps subtract through LightBomb as before. No penumbra level: the small
deltas (2-5) are a minority and E3M1's 24 is one map's choice. Gates,
absolute: every shadow edge's delta lies in [8, 16]; every outdoor
network has 2-4 significant levels; the lit base is the one the plan
states.

### Continue prompt -- slice 2d (deliverables 3-6)

```text
Continue as P14b, slice 2d, from commit ee5705b. Read your status at the
end of 09_IMPLEMENTATION_ROADMAP.md and sections 17-21 of
projects/blood-city/reports/street-model-decisions-2026-09-02.md
(section 21 decides owner-queue item 22). Same hard rules: no directory
deletes, no junctions or symlinks, never launch NBlood or xmapedit,
BLOODMAP_CORPUS and absolute paths in a worktree, commit by file name,
never git add -A, never commit maps/ or reference/, suite to a log and
the Ran line verbatim, trailer Co-Authored-By: Claude Opus 5
<noreply@anthropic.com>. Every gate fails first and carries one
absolute, corpus-anchored check; commit each deliverable on its own.

Decided (do not reopen): the light field quantises to base + k*12 --
base is the network's own lit shade from the plan (campaign range 0-30,
E3M1 8), 12 is the campaign's modal shadow step (deltas across same-z
outdoor boundaries: 12 x44, 16 x30, 10 x24, 8 x23), k is the count of
overlapping shadows (additive), capped so no network exceeds 4 levels;
no penumbra level. Re-measure the step over the 37 maps yourself and
cite; if your number differs from 12, say so and use yours.

3. The light FIELD. The sun is a directional LightBomb source occluded
   by the masses; lamps are point sources; the field is summed over the
   LIGHT domain and quantised as decided; the cut set is its iso-lines,
   applied with cut_by_convex / cut_region (one field per plane, cut
   once, outside pieces re-merged, slivers absorbed and reported).
   Gates, absolute: every shadow edge shares SUN_BEARING within
   tolerance and its shade delta lies in [8, 16]; every outdoor network
   has 2-4 significant levels; road and island frames continue across
   every edge (auto-align invariance + world_u). Fail-first on the
   slice-1 map with its lit/shadow at E3M1's raw values.

4. Channels and arbitration. One two-column table, channel -> ADDITIVE
   (light) | EXCLUSIVE (floor z, sector type and mechanism state, a
   surface's frame, a holder role); a second writer on an exclusive
   channel raises by name (extend RecordOwner to region channels).
   bloodmap.arbiter's FUNCTION / PRESENTATION claims generalised to
   channels: PRESENTATION yields on conflict and the manifest lists it
   with the reason; FUNCTION vs FUNCTION is an error; a dropped
   PRESENTATION facet is expected absence for readback (compare against
   the sentence as arbitrated), never a gate failure; the review sheet
   lists every dropped facet. Fail-first: two overlays writing floor_z
   on one region; a mechanism asked to open and close at once; a
   Link-driven light on a sector inside the sun field (yields, listed).

5. Order of operations asserted in the compiler: planes and islands ->
   inserts and mechanisms declared (excluded from cutting) -> the light
   field on its domain -> joins at every shared edge -> frames. A pass
   out of order raises.

6. Rewrite the emitter around overlay.ground_plane and run the whole
   graph without masses: placeholder masses at the solved envelopes'
   heights for the shadows; islands with bands; paths; junctions as
   pieces of the plane; the plaza and the cemetery at pavement level;
   the yard notch; lamps at E3M1's furniture rate; the south waterfront
   (shore at the sea's z; sea as stone 2490 under palette 10 with
   pan_floor + pan_always + drag; the horizon as a zero-height sky
   sector); end walls where the avenue, the spur and the west street
   reach the boundary; building backs elsewhere as void. Every gate
   from slice 1 over the whole map with its absolute check; counts
   against the NBlood limits; readback; four rendered frames (a street
   from the road, a junction, a path between islands, the quay with
   the horizon); suite green; commit.

Stop and report: the measured step; cuts refused; slivers absorbed;
sector and wall counts before and after the field; dropped PRESENTATION
facets by name; which gate failed first; what remains unproven; what
slice 3 must answer first. Owner questions to
reports/owner-review-queue.md with a recommended default.
```

## 22. Three kinds of claim, the populations' roles, item 23, and the freeze (2026-09-02)

Deliverable 3 landed (2cc83c3, 763b978): the field on a crossing plane
gives 5 pieces, levels [0, 1], every iso-line at the sun's bearing, area
conserved; the oblique cut exposed a clipper bug (crossings re-derived
after integer rounding) that axis-aligned and 45-degree tests could not
see -- fixed by recording crossings, with a regression at the sun's own
bearing. Corrections accepted: 12 is the MEDIAN of a flat distribution,
the gate is [8, 16]; four levels at the tenth-of-sectors floor; the lit
base spans -128..37 per map, 0 commonest.

**Three kinds of claim, and only the first is proved.**
- Engine laws (what a wall band draws, DragPoint, busy, Link): the
  source decides; cite the line. Proved.
- Envelopes (shadow step 8-16, 2-4 levels per network, kerb 2048,
  pavement bands 512-2560): measured over the originals, never proved
  universal. A flat distribution is a finding that the quantity is a
  per-map CHOICE, not a failed proof. An envelope is a gate: our choice
  must lie inside it.
- Choices (lit base, kerb tile, sky tile, road tile): parameters of OUR
  level, stated in the plan and the style; checked only for lying
  inside the envelope and for being recoverable by the reader.

**The populations' roles (standing, restated):** campaign = defaults and
envelopes (Blood's own language); curated community = PRECEDENT for
constructs the campaign lacks (the horizon over water, the chasm) and a
wider variety envelope, never a default; bulk community = existence
queries only ("does anyone do this"), never a rate. "Every level is
different" is handled by not explaining every level: we say which
envelope our choice lies in and what attests it.

**Item 23 decided:** floor_shade is an ADDITIVE channel with LightBomb
as its single summing owner; sun, lamps, flicker waves, pools and
Link-driven waves are deltas; direct writes are deleted. Exclusive
would silently drop the 146 Link lights P8 counted.

**Principle freeze.** No new principle, gate or overlay kind until the
city stands (slices 2d and 3). Sections 17-21 are the whole model.

**Milestones.** A: "Gravesend v2 stands" -- slice 2d (channels, order,
emitter, whole graph without masses), slice 3 (masses and interiors
through their own placers, every mechanism read back), waterfront and
edges, walk sheet; fixed scope. B: "the system understands" -- the
section-20 acceptance test (E3M1, DWE3M1, DWE3M10 decompiled into the
plan language, recompiled, structure diffed) plus the missing readers
(islands from steps, the light field from shadows, arbitrated absence,
envelopes from an original); runs in PARALLEL on a second Opus agent
with P4/P5/P8/P9, since none of it touches the city build. C: quality
-- facades, inserts, interiors, the harbor with its pier; then the zoo
and the novelty frontier.

## 23. Owner's experiment for later: decompile ONE original level completely (2026-09-02)

`projects/e2m3-decompiled` already exists: E2M3 as a tree (assembly ->
areas -> rooms), structures, assets and names, byte-exact IR, with the
refactoring history stage by stage. It is a GEOMETRIC decompilation
from before surfaces, joins, mechanism sentences, the light field and
the edge chain. The experiment is milestone B done on one map, with a
RESIDUE LEDGER as the measure of understanding.

- Level: E1M1 first (155 sectors, 1498 walls; the only owner-attested
  mechanisms and names -- 8 of 13 names not recoverable from topology --
  so it shows where the machine stops); E3M1 second (the city language).
- Layers, each with its own reader and its own residue: (1) the space
  tree (exists), (2) surfaces and frames from u-origins, (3) joins
  (every shared wall classified; unknown pairs are residue), (4)
  overlays (islands from steps, the light field from shade edges, the
  sun's bearing from the field), (5) mechanisms as sentences (readback,
  effects, conditional), (6) the edge chain, (7) the plan (street graph,
  islands, blocks, envelopes: the solver's inverse), (8) intent (the
  function taxonomy per mechanism and room, against the owner's names).
- Understanding = 100% minus residue, per layer: the records and sectors
  no layer explains. Recompile and diff structure as the gate; what does
  not come back is copied, not understood.
- When: after milestone A, or in parallel on a second Opus agent now,
  since E1M1 needs nothing from the street work. Frozen until the owner
  says go.

## 24. Item 24 decided: the field contributes k*12 and nothing else, and two numbers are read off the built map (2026-09-02)

Deliverables 4 and 5 landed (346d936, d9a1ed5): the channel table
(shade additive; floor_z, ceiling_z, sector_type, mechanism_state,
frame, holder_role exclusive; an unknown channel raises), RegionLedger
as RecordOwner at region scope, PRESENTATION yielding with its reason,
order-independent arbitration, `lightbomb.apply_shade_channel` as the
single summing owner, and the fixed pass order asserted with reasons.

Decision on item 24: a piece at field depth k contributes exactly k*12
to the additive shade channel; the base is the region's own lit shade
from the plan; nothing else converts depth to shade. And the absolute
gate the agent asks for is adopted as a standing rule, not only here:
**every gate that checks a field's shape also reads at least one
absolute value off the BUILT map.** For light: a sector in full sun ends
at the plan's stated base; one in a single shadow at base + 12; one
under two overlapping shadows at base + 24; one under a lamp in full sun
at base minus the lamp's delta. Four numbers read from the compiled
sectors, asserted before the whole graph is built. This is the check
the 8x regression should have had, applied to the next quantity.

## 25. Item 26 decided: weld by edge identity, and a question the system could have answered itself (2026-09-02)

Steps 1 and 2 of slice 2f landed (d880435, 9cffb66): the partition
assertion (area, pairwise non-overlap, every sampled point claimed once,
boundary test first), the phantom "absorbed" notes gone, the clockwise
shadow normalised, and the cause captured in
`tests/fixtures/overlay_partition_regression.json`: `_crossing` rounds
each cut's crossing to the integer grid independently, so a later cut
that crosses an earlier chord puts a vertex 0.05 units off the
neighbour's edge, and `PlanarLayout`, which splits T-junctions only on
EXACT integer collinearity, reads it as `partial_area_overlap`.

**Decision: weld, but by identity, not by distance.** The agent's weld
searches for edges "within half a unit" of a crossing; that is a
tolerance wearing a different coat. The crossing was computed FROM a
known edge (`here`, `nxt`), so the weld is a lookup: record
(undirected edge key -> crossing) as every cut is made, and after all
cuts of all surfaces insert each recorded crossing into every ring of
every piece that still carries that edge whole, ordered by `_param`
along the edge. Exact, deterministic, no search radius, and it works
ACROSS surfaces too (the plane's hole ring and the island's outer ring
are the same edges, wound the other way). Two companions: `_crossing`
must round the same point whichever way the edge is given (canonical
endpoint order; test both orders over a battery of oblique pairs), and
each weld adds exactly one wall per side, which Build requires anyway
(a red wall needs matching endpoints), so the added walls are counted
and reported, not treated as overhead.

**The larger point, now a standing rule.** Item 26 asked the owner to
choose between weld and snap. The system already knew the answer: a
snap moves solver-placed vertices by up to half the grid, and "no
solver-placed vertex moves" is an invariant this project has stated
twice (the 8x scale, the junction squares). Two gates decide it without
a human: (G1) vertex fidelity, every vertex of every declared surface
appears unmoved in the compiled map, exact set inclusion; (G2) the
partition assertion plus `PlanarLayout` accepting the build. Snap fails
G1 by construction. **An A/B implementation question goes to the owner
queue only when no invariant separates A from B.** Otherwise the agent
writes the gate that separates them, runs it, and reports which side it
chose and why. The queue is for precedent, taste and unknown corpus
facts, not for questions the invariants answer.

## 26. Item 27 decided: edges have a genealogy, and a gate does separate A from B (2026-09-02)

Slice 2g landed G1 and G2 (77964e0), the canonical `_crossing`
(7d9a688) and the weld by edge identity (f6247f5). G1 settled item 26
by itself: snapping to 8 moves 2 of slice-1's 11 points. The graph run
now fails one level deeper: an island edge (p, q) abutted by three plane
pieces whose endpoints were crossings recorded against a DIFFERENT key,
because the plane's copy of that edge had already been split by an
earlier cut into (p, r1) and (r1, q), and the later crossing r2 was
recorded against {r1, q}. The island still carries {p, q} whole and the
registry never connects the two.

**Decision: neither A nor B as stated. Edges have a genealogy.** When a
cut splits an edge (p, q) at r, the cut knows that at the moment it
happens and exactly: record child -> parent, {p, r} -> {p, q} and
{r, q} -> {p, q}. A crossing recorded against any key is then owed to
every ring that carries that key OR ANY OF ITS ANCESTORS whole, in
`_param` order along the ancestor. This is B's exactness ("record at
cut time, where the geometry is still exact") without B's cost: the
record is local to the cut, two dictionary entries, and nothing consults
the whole piece set. No tolerance exists anywhere in the weld.

**A gate does separate A from B.** A crossing is rounded per coordinate,
so it can sit up to 0.5 * sqrt(2) = 0.707 units off the oblique edge it
was computed from. Option A's half-unit containment misses every
crossing rounded toward the far corner of its unit cell; the genealogy
never does. Fail-first fixture: a cut whose crossing rounds 0.6 to 0.7
units off its edge, and a neighbour that must receive it. That is the
invariant the agent said did not exist, and it is the same one as
before: a crossing computed from an edge is welded into every carrier
of that edge, always. The standing rule from section 25 stands, with
one addition: "no invariant separates them" must be shown by a fixture
both options pass, not asserted.

## 27. Item 27 closed: the genealogy built, and the bound measured (P14b, 2026-09-02)

`overlay.CutRegistry` holds both halves of the decision: `record(a, b, p)`
files a crossing under the undirected key of the edge it came from, and
`split(p, q, r)` files `{p,r} -> {p,q}` and `{r,q} -> {p,q}` at the moment
the cut makes them. `by_edge()` then offers every child's points to every
ancestor, and `weld` inserts each into any ring carrying that key or an
ancestor of it, ordered along the edge. No tolerance constant exists in
`overlay.py`, and a test asserts that by reading the source.

**The bound is tight and it is reached.** Searched over 20000 random
oblique edges, the worst distance from a rounded crossing to the true
intersection is **0.702** units against the stated ceiling of
`0.5*sqrt(2) = 0.707`. So option A's half-unit containment does miss real
crossings, and my claim that no invariant separated A from B was wrong in
the way the owner said it was. The fixture is
`tests/test_overlay.EdgesHaveAGenealogy.test_a_half_unit_containment_would_miss_a_real_crossing`,
and it asserts both halves: that some crossing exceeds half a unit (so
containment is not a fair option) and that none exceeds the bound (so the
bound is the right one to have cited).

**It was the whole of the remaining failure.** With the genealogy the
street graph builds end to end for the first time: one ground plane of ten
rings, 104 sectors, 534 walls, 46 welded vertices, 0 slivers, 253 joins
with no unknown pairs, and the light field's four levels reading 8 / 20 /
32 / 44 off real city sectors.

**Still unproven, and named as such:** the waterfront, the end walls, the
plaza and cemetery, the yard notch, the pavement-only paths, the lamps and
the read-back are not emitted -- the emitter builds roads and islands and
stops. Nothing in the model blocks them; they are the next run's work.

## 27. The city builds (2026-09-02): two systemic findings, and the half that is missing

Slice 2h (07f862b, 8db3321, 7f1e685): the genealogy closed the last
refusal, the graph builds, and every gate is green on real sectors:
depth 0 -> 8 (40 sectors), 1 -> 20 (33), 2 -> 32 (24), 3 -> 44 (6), one
lamp-lit piece at 2; G1 178 declared / 0 missing; partition silent on
104 surfaces; the kerb [6] seen from all 38 road pieces; light domain
104 admitted / 0 refused. The 0.707 bound is tight (worst found 0.702
over 20 000 edges).

Two findings the report understates:

1. **The frames gate failed because the emitter never ran
   `frame_map`, and the pass-order assertion did not notice.** The
   order assertion (d9a1ed5) checks the order of passes that ran, not
   that every mandatory pass ran. Decision: the compiler owns the
   pipeline. An emitter declares surfaces, overlays, joins and frames;
   it never calls passes. `PlanarLayout.compile` (or the city's build
   entry) runs planes -> declare -> light -> joins -> frames itself and
   raises if any of the five is skipped. A gate that reads "the editor
   would change nothing" must be unreachable without frames having run.
2. **The light domain refuses nothing because the map has nothing to
   refuse.** That is a true zero, not evidence. Rule 2's first real
   test comes with slice 3 when L3 is re-parented; the gate exists.

**Deliverable 6 is half done.** Roads and islands are in the map; the
waterfront, end walls, plaza, cemetery, yard notch, pavement-only paths,
lamps, read-back and the four renders are not, and nothing in the model
blocks them (the plan states them all). Slice 2i finishes deliverable 6
before slice 3 starts, because the owner's walk of the city needs its
edges: slice 1's two findings (sky, road ends) came from that walk.

## 28. Slice 2i: the pipeline inverted, the edge finished, and two corrections (P14b, 2026-09-02)

**Decision 1 landed.** `bloodmap/pipeline.py` owns the five passes; an
emitter returns an `Emission` and calls none of them. An omission is
refused before any pass runs, naming the pass. The fail-first is slice
2h's own defect and it is now impossible: an emitter with `frames=None`
is told about frames, not about 191 walls.
`Compilation.require_complete` makes the order assertion a completeness
assertion too.

**Decision 2 landed, and reads UNTESTED.** The manifest line is now
`light domain: admits 179, refuses 0 of 0 eligible (mechanisms,
inserts, holders) -- UNTESTED`. Nothing in this map carries a sector
type, a moving wall, a stack marker, a holder role or an insert, so the
rule has never been asked. It stops being zero the moment slice 3
re-parents L3.

### The city, built

179 sectors, 866 walls, 15 sprites -- 4%, 5% and 0% of the NBlood
limits. 20 surfaces, 179 pieces, 16 seeded vertices, 80 welded, 0
slivers. 846 join records with no unknown pairs: 242 kerb, 278
pavement-only path, 112 shore. Partition faults 0, G1 0 missing, the
editor would change 0 walls, both absolute rules 0 violations, no
dropped PRESENTATION facets.

Map: `projects/blood-city/level/slice2-streets.MAP`. Start: sector 0 at
(15481, 23722, 10240), angle 0 -- on Theatre Row, west of the avenue,
facing east down the row.

### Two corrections, both from the corpus

**"The shore at pavement level" is not attested.** DWE3M10's shore never
meets its landward neighbour at equal z: seven records step 35840 (a
quay wall) and one steps 3072 (walkable, inside Blood's 4096 autostep).
The row added is SHORE|PAVEMENT B_ABOVE with the band on the shore's own
side; PAVEMENT|SHORE at EQUAL still raises.

**"Lamps at E3M1's rate" has no rate to take.** E3M1's 45 bright outdoor
sprites carry cstat 32896 -- `0x8000` is INVISIBLE -- statnum 12, and
types 708/710, which are `kGenSound` and Ambient SFX. They are sound
generators wearing an editor icon. Across all 43 campaign maps and
51,277,134,846 square units of outdoor ground there are **0 visible
outdoor lamps**. Blood lights its streets with the sun and nothing else.
The city's 15 lamps are placed at Blood's INDOOR density (per-map median
one per 187,624,103 square units) and their shade delta is ours, declared
as ours, because the campaign attests none.

**A question for the owner, not a decision I took:** should Gravesend
have street lamps at all? The corpus says Blood's streets have none, and
the plan's `AREAS.furnish` asks for them at three places. I built them
because both the plan and the brief asked; if the answer is that the
city should read like Blood, they come out and the sun does all the work.

### What is unproven

The renders are plan views. The observer is XMapEdit and this run does
not launch it, so **nothing has walked this map** -- the owner's walk is
the first. `bloodmap.readback` still has nothing to compare, because the
emitter declares no constructs. And the buildings are still placeholder
masses casting shadows, not shells with facades.

### 23a. Unfrozen (owner, 2026-09-02 evening): E3M1 first, in parallel

The owner starts the experiment now, on a second Opus agent, and picks
E3M1 first, not E1M1: the city language is what the street work is
writing, so E3M1's readers are the writer's evidence directly (section
20). E1M1 follows for the mechanism and naming layers. Project directory
`projects/e3m1-decompiled`, shaped like `projects/e2m3-decompiled`,
with the residue ledger as the deliverable. Readers land in `bloodmap`
as modules, never inside the project, so the census can run over the
corpus; the agent adds readers and never edits the writer side
(overlay, light_field, joins, surface, planar_layout) -- a disagreement
between what a reader recovers and what the writer assumes is a finding
for the owner queue, not a patch.

## 28. Overlapping layers, systemically: records, aspects, channels, links (owner question, 2026-09-02)

The owner's worry: E3M1 already has doors of several dialects, stairs,
a collapsing house, cracking walls, a falling ceiling, 61 light waves
over the sun's shadows; a Death Wish map has an order of magnitude more
detail, mechanism and linkage. Many layers overlap on the same sectors.
A single hierarchy cannot hold that, and it must not try.

**The model: one set of records, many aspects, one ledger.**

1. **Records are the only truth.** Sectors, walls, sprites and their
   X-structs, as the map stores them. Nothing else is authoritative.
2. **An aspect is a partial reading of records.** The space tree is one
   aspect. Surfaces/frames, joins, islands, the light field,
   mechanisms, edges, the plan, intent: each is another. An aspect never
   owns a record; it CLAIMS FIELDS of records (this wall's picnum and
   x_repeat belong to surface S; this sector's floor_z to island I;
   this sector's shade to sun depth 2 plus light wave W). Aspects are
   the decompiler's "primary hierarchy plus overlapping alternatives",
   made precise at field level.
3. **Overlap is resolved per channel, exactly as the writer does it.**
   The channel table (section 18) already says which fields are
   additive (shade) and which exclusive (floor_z, sector type, frame,
   holder role). Reading is the inverse: on an additive channel several
   aspects may each explain a contribution, and the sum must equal the
   record (shade = base + k*12 + wave); on an exclusive channel exactly
   one aspect may claim the field, and two claimants are a FINDING, not
   an error to hide. This is the symmetry rule at field level.
4. **Links are a graph, not a tree.** tx/rx chains, markers, stack
   links, keys, conditions form relations over records; a mechanism
   "sentence" is a subgraph pattern with roles, and the conditional
   topology is derived from the graph. Links never sit in a hierarchy;
   they reference records and nodes of any aspect.
5. **The ledger is the deliverable, and it is the writer's ledger.**
   RegionLedger / RecordOwner is the format: (record, field) ->
   claimant aspect(s) with evidence. Residue = fields no aspect claims;
   conflict = exclusive fields with two claimants. Understanding is a
   percentage of FIELDS, not of sectors, so a sector that is "half
   understood" (its geometry read, its trigger not) counts as half.
6. **Reading order comes from the ledger.** The next thing to read is
   the largest unclaimed mass, like a profiler; nobody reads a Death
   Wish map front to back. A vocabulary saturates when a new map's
   residue under the existing readers is small; the residue tail names
   the new vocabulary. E3M1 first; DWE3M1 measured against E3M1's
   readers before anyone writes a reader for it.
7. **Browsing is the ledger by aspect.** The review pack shows one
   aspect at a time with the others dimmed; a record's fact panel lists
   every claim on it and every unclaimed field. The owner marks a
   claim, not a sector.

Consequence for P15: the residue ledger is `(record, field) -> claims`,
every layer writes into the same ledger, and a layer's report is its
share of claimed fields plus the conflicts it raised on exclusive
channels. The order of layers is unchanged.

## 29. Slice 2i landed; lamps are a stated choice; slice 3 scope (2026-09-02)

Deliverable 6 is complete (2ee6c2f..684aac9): 179 sectors / 866 walls /
15 sprites, 846 join records with 0 unknown, 80 welded vertices, 0
slivers, G1 66/0, sun bearing read back at 84.02 degrees, the four
shades plus lamp deltas read off real sectors with 0 misread, end walls
and waterfront gated on built records. The compiler owns the pipeline
(`pipeline.py`, `Compilation.require_complete`); the light-domain
denominator is reported as UNTESTED at 0 of 0. The map to walk is
`projects/blood-city/level/slice2-streets.MAP`, start sector 0 at
(15481, 23722, 10240), angle 0, on Theatre Row facing east.

Two corpus corrections accepted: a shore never meets land at equal z
(DWE3M10: seven quay-wall steps of 35840, one walkable step of 3072),
so the join row is SHORE|PAVEMENT B_ABOVE and EQUAL raises; and Blood
has ZERO visible outdoor lamps in 43 campaign maps (E3M1's 45 bright
outdoor sprites are invisible kGenSound / ambient SFX emitters). Blood
lights its streets with the sun alone.

**Decision on lamps (owner's taste, supervisor's default):** Gravesend
keeps its street lamps. The plan's identity for Theatre Row is
"gas-lit"; the owner asked for lamps on pavements; and section 22
allows a stated CHOICE where the corpus has no law. The lamp density
is therefore recorded as a choice claim (Blood's indoor sconce rate
applied outdoors), never as an envelope, and the sun remains the only
source of the shade FIELD; lamps stay PRESENTATION deltas. If the
owner wants the city to read as Blood does, the lamps come out with
one declaration and nothing else changes.

**Read-back gaps are findings about Blood, not about us:** field depth
k and lamp authorship are not on disk because Blood sums shade at write
time. A reader cannot recover them from a map alone; the fact store the
compiler will write from slice 3 (section 2 of the research document)
records them beside the map, and E3M1's reader will report the same
gap honestly.

**Slice 3 scope:** the owner's walk of slice2-streets.MAP first (its
findings arrive as review marks or a message and are treated like
slice 1's); then building masses as real shells with L3 interiors
re-parented under their islands, facades as surfaces with openings and
inserts in their own sectors (section 6d), the light domain's first
real refusals, the fact store, the LoD invariance gate, and the
declared mission graph. Eye-level renders remain unproven until an
observer exists; plan views must use XMapEdit's orientation (+Y down).

### 22a. Norms are conditional (external review point 7, adopted 2026-09-02)

Every norm the readers produce is conditioned on a context (surface
kind, join class, LoD, function, population), never a global average
over a map or the campaign: "slopes | outdoor sewer", "detail density
| storefront", "dead ends | optional venue". A global rate is an alarm
at most, never a target; matching a campaign median by adding things
is statistical cosplay, and the discriminator is not allowed to ask
for it. Each conditional norm carries the examples where Blood did NOT
use the thing in that context.

## 30. Both agents at rest (2026-09-03): decisions on queue items 1-4 (city) and 28-31 (E3M1)

State. P14b finished slice 3 on main (117f733): 184 sectors / 1042 walls
/ 14 sprites, 47 surfaces, 1022 joins with 0 unknown pairs, G1 174/0,
the editor would change 0 walls, 2398 facts over 14 predicates, LoD gate
0, Rule 2 asked for the first time (9 curtains, 0 moved), the four walk
findings each fixed with an absolute gate (111/232/15/1 before, 0
after), the mission graph declared with every link and key honestly
`realised: false`. P15 finished all eight layers of E3M1 (merged in
29cda62): 18 297 facts in 35 predicates, 3.883% of claimable fields
claimed, 136 mechanism sentences, the plan recovered in plan units,
eight review packs with 22 owner questions, and a list of what the
writer assumes that E3M1 does not do.

Decisions, each the supervisor's unless marked owner:

- **City 1, lamps:** stays as decided (choice claim, sconces 510, -6).
- **City 2, doors A/B:** A. They are doors; slice 4 realises them
  (switch on the facade beside each, keys on the circuit). The fixture
  separated the options correctly: eligibility for Rule 2 is the
  invariant.
- **City 3, the circuit's grid:** legs become sequences of SURFACE IDS
  ("the avenue between Theatre Row and Market Street"), never plan
  coordinates; a leg survives a re-solve, a coordinate does not. Plan
  change, supervisor's call, owner may veto.
- **City 4, behind the doors:** re-parent the L3 interiors one at a
  time, each under its island's shell, each with its own read-back
  sentence. This IS slice 4.
- **31, two fact stores:** unify on the READER's shape
  (`read_store`: per-row provenance, declared predicate table with a
  description per predicate, the ledger's four extra predicates), with
  `lod` as an attribute. `facts.py` becomes the compiler's writer INTO
  that shape; the LoD gate becomes a query. P14b makes the change; P15
  freezes the row shape meanwhile. The diff of the two stores is the
  symmetry test of section 20 from now on.
- **29a, the shade step:** the step is a per-project CHOICE (Gravesend
  keeps 12; the owner liked the slice-2 shadows) checked against a
  CAMPAIGN envelope whose network definition the gate names: the
  largest outdoor component, the definition that matches "a city's
  street". The envelope is a READER census (P15 provides
  `shade_step_envelope(network=...)`; P14b's gate calls it, never a
  constant). E3M1's own 24-26 is recorded as the precedent's value.
- **29b, `kerb_records` claims 81 where E3M1 makes 11:** writer bug,
  P14b fixes: use the `ground_outline` it already takes; fail-first on
  E3M1's three islands replayed through the reader (11 expected).
- **29c, `is_water` blind on a LevelIR:** writer bug, P14b fixes with
  the `_x` accessor; test on DWE3M10's 22 panning sectors.
- **28a:** fix the evidence string (s10/s11 are masses); the row stays.
- **28b, 28d, 28e:** three censuses for P15's readers over the 43
  campaign maps before the writer changes anything: end-wall tiles by
  join pair; u-continuity by bend class (collinear / bend / reflex,
  solid-solid / solid-portal); interior|interior pair classes by floor
  and ceiling kind. P14b consumes the results in slice 5, not before.
- **28c, 30b, 30e, 30g:** reader-side, P15: a raised outdoor mass with
  a sector type is a mechanism at rest, named apart; a block is cut at
  its street frontages; the stack-fault text says "256 below, as all
  three of E3M1's are"; the prop reader is wired into layer 8.
- **30a, width class means FULL width** (carriageway plus pavements):
  E3M1's east arm is then a ROW with residual exactly 0, and the plan's
  grid already sums streets that way. Stated in `city_plan.py`, applied
  in slice 4 as its own first commit with counts before and after.
- **30f, a chain is one sentence with fan-out as a parameter:** adopted
  for the writer; slice 4's switches use it.
- **30c, 30d, 30h:** recorded; no action.

Next for P15: the sleep phase needs a residue curve, so the readers run
as a CENSUS over all 43 campaign maps first (they are pure functions),
per map per layer; that table picks the second map to decompile fully
by the largest claimed share under E3M1's readers among maps with a
street network (default if ambiguous: E1M2), and then the refactoring
pass promotes what both maps needed. E1M1 stays third, for mechanisms
and the owner's names.

Owner: eight review packs wait in `projects/e3m1-decompiled/review/`
with 22 questions; the four city questions above are decided with
defaults and need only a veto.

## 31. One trunk, and decisions on queue items 32-37 (2026-09-03)

Landed: P14b's slice 4 on main (ff8da12: one fact store on the reader's
shape, full-width classes, the circuit as surface ids, nine switches
and five keys realised, a Z-motion shutter that needs no slot) and
P15's census, E1M2 and E4M8 decompiled by the same program, the residue
curve and five macro proposals (merged in cf97a39). The protocol now
says one trunk: every agent rebases onto origin/main and pushes to main
after every step; no agent branch is merged by anyone again.

- **32a withdrawn, 32b:** shutters stay Z-motion; a marked-slide
  constructor arrives when something slides.
- **32c:** P15 adds `facade` and `opening` to `read_joins.surface_kinds`;
  the city's 296 unnamed joins are the fail-first.
- **32e / 37f:** the unit is the BOUNDARY (a sector pair once). P15's
  `shade_step_envelope` counts boundaries and states its population;
  the gate uses the quartile envelope of the network it names, [8, 18]
  on the largest outdoor component until the recount says otherwise.
- **32f:** interiors one per slice, church first, each with its
  read-back sentence. **32g:** the sewer legs stay `built: false` until
  the sewer's slice.
- **36a:** keep all three decompilations. **36b-36d:** `dressing`
  first, `stair` second (a SURFACE owner), then `channel`, `self_lit`,
  `breakable`; P14b builds them in `bloodmap/city.py`, P15's readers
  must read each back, and a macro that does not lower residue on two
  maps after landing is removed. **36e:** every roadmap item quoting a
  residue number states the split (surface representation 46%, indoor
  rows 31%, macros 16%); the eleven rows are one law and the cheapest
  win; the surface representation is the largest and is the
  architect's item, not a constructor.
- **37a:** keep the end-wall criterion, report the split at two player
  heights. **37b:** 400 stays Gravesend's CHOICE inside the attested
  class; the campaign distribution is the envelope. **37c:** drop
  `cstat=1` from the road|end_wall row; blocking is a per-project
  choice. **37d:** no change; E3M1 is the outlier. **37e:** one indoor
  row keyed on the height relation (the kerb's law indoors) with a
  tile class per context, plus a `masked` row; P14b consumes it now.

Owner: walk `projects/blood-city/level/slice2-streets.MAP` again (nine
doors that shut, switches beside them, keys on the circuit); the review
packs of three maps wait under `projects/*-decompiled/review/`.
