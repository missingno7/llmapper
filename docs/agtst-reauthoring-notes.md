# AGTST re-authoring notes

The bot's hand-authored test maps `reference/blood/AGTST1.map` …
`AGTST18.map` were lost on 2026-09-01 (`reports/corpus-recovery-2026-09-01.md`)
and the owner has confirmed no copy exists. This note keeps everything the
repository still knows about them, so that re-authoring can start from a
specification instead of from memory, and states plainly what the surviving
artifacts can and cannot give back.

## What survives, per map

Source: `NBlood/corpus/all-agtst-preservation-after-simple-subset/runs/normal/<MAP>/`
(telemetry + trajectory for AGTST1–13, 15; AGTST14 also has a full
`navmesh.ndjson`), the bot docs (`docs/nblood-autonomous-playtest-bot.md`)
and the audits in `NBlood/extras/`.

| map | intent (docs/audits) | gate result | what the artifacts hold |
| --- | --- | --- | --- |
| AGTST1 | concave starting room whose way on is a wall that must be pushed; 6 sectors → 3 regions | COMPLETED 30 s | 6 sectors, 2 doors (sector_push), 8 wall adjacencies, sprites (type 231 = 3 gargoyle statues at recorded positions), trajectory |
| AGTST2 | crouch passage (38 crouch_posture events) | COMPLETED 73 s | 11 sectors mentioned, 18 wall adjacencies |
| AGTST3 | repeated waypoint jumps; jump input confined to gaps; the leap fixture | COMPLETED 32 s | 11 sectors, 40 wall adjacencies, 22 local_geometry records |
| AGTST4 | reach and operate the crypt continuation/door; thin/transit geometry; sprite 74 is a zero-clip gib | STALLED 376 s | 56 sectors, 97 wall adjacencies, 79 local_geometry (the biggest telemetry set) |
| AGTST5 | pickup vs locked door; ledger identity collision fixture | COMPLETED 57 s | 9 sectors, 26 adjacencies |
| AGTST6 | bridge of floor-aligned sprites across a damaging pit; acute wall spur at (4096,−4096); 35 sectors, 42 support faces → 12 regions | STALLED 342 s | 36 sectors, 23 adjacencies |
| AGTST7 | doorway barred by a pushable sprite panel; 5 sectors → 5 regions | COMPLETED 44 s | 7 sectors, 12 adjacencies |
| AGTST8 | solid sprite as owner of blockage/support; lift and bridges | STALLED 333 s | 7 sectors, 22 adjacencies, 138 jump_traversal events |
| AGTST9 | damage the blocking gib (sprite 5), then continue; stale deferred frontier (wall 24) | COMPLETED 58 s | 10 sectors, 18 adjacencies |
| AGTST10 | jumping and explosive safety | COMPLETED 36 s | 5 sectors, 4 adjacencies |
| AGTST11 | (short run, 17 s game time) | COMPLETED 61 s | 5 sectors, 6 adjacencies |
| AGTST12 | real support-to-support jump (`executeJumpTraversal`) | COMPLETED 338 s* | 3 sectors, 64 jump_airborne events |
| AGTST13 | acquire key 1 from the exit button, return across the support chain to the exit; sector 5 split inbound/outbound | STALLED 332 s | 10 sectors, 46 adjacencies |
| AGTST14 | support identity / two-phase support; physical action scan | STALLED 333 s | **full navmesh**: 896 live cells at revision 1 (256-unit grid), 22 sectors, 8 floor heights, extent x −3712…3712, y −6976…3712, edges with gateways and conditions |
| AGTST15 | — | STALLED 301 s | 1 telemetry run |
| AGTST16 | — | COMPLETED 40 s | none |
| AGTST17 | "the harder ones the model is pushed against"; 8 sectors → 5 regions | COMPLETED 79 s | none |
| AGTST18 | the size at which the model can hide nothing; 155 sectors, 173 faces → 133 regions | NO_KNOWN_ACTION 28 s | none |

\* result differs between runs; the sanitisation table says STALLED, the
preservation run says COMPLETED.

## What the telemetry actually contains

Every event is a `detail` string. The geometry-bearing ones:

- `local_geometry`: `sector, clearance, player_ceiling, player_floor,
  portals, jumpable, max_rise, max_drop, xsector, state, busy` — per
  sector the bot stood in. Heights and mechanism presence, no outline.
- `boundary_clearance_changed` / `discovered_frontier`: `wall, from, to,
  clearance, floor_delta` — the sector adjacency graph with the step at
  each shared wall. Wall ids, no coordinates.
- `local_solid_sprite`: `sprite, type, picnum, pos=(x,y,z), cstat,
  clipdist, top, bottom, push, vector` — every solid sprite met, with its
  exact position and type.
- `discovered_door`: `door (sector), key, locked, wall_push, sector_push,
  direct_use` — the doors and how they are worked.
- `nav_cell_waypoint`: `at=(x,y) sector=` and `player=(x,y)` — walkable
  points with their sector.
- `trajectory.ndjson`: `x, y, z, sector, angle` per sample — the path the
  body took, with sector labels.
- AGTST14 only: `navmesh.ndjson` cells `(x, y, z, sector, clearance)` on a
  256-unit grid plus edges with gateway coordinates and conditions — a
  real walkable-floor plan.

**No wall vertices, no textures, no XSECTOR wiring, no sprite for anything
the bot did not meet.** Exact reconstruction is impossible.

## Verdict on machine reconstruction

What can be rebuilt with `bloodmap` from these records is a **functional
replica** per map: the same sector graph with the same clearances and
floor steps, doors of the same working kind at the same places, the same
solid sprites at their recorded positions, room footprints sized from the
trajectory/waypoint point clouds (and, for AGTST14, from the navmesh
cells). That reproduces what the bot's gate measures — topology, heights,
doors, blocking sprites, jump gaps — but not the maps as the owner drew
them. AGTST16–18 cannot be rebuilt at all; AGTST17/18 are known only by
their sizes and their role.

Recommended: treat the replicas as **AGTST-R** (reconstructed), never as
the originals; keep the originals' names free for the owner's new maps;
gate the bot on the replicas only after the owner has walked them.

## Owner decision, 2026-09-02

Not now. The replicas are parked until work on the bot resumes; the owner
will then author entirely new maps, and this note plus P10 below are the
starting material for that day. Nothing under `projects/agtst-replica/`
should exist before then.

## P10 (parked) — reconstruct the AGTST replicas from telemetry

```text
Task: build functional replicas of the lost AGTST bot test maps from the
surviving telemetry, with bloodmap's authoring stack, and say per map how
much of the original intent the replica can carry.

Inputs: NBlood/corpus/all-agtst-preservation-after-simple-subset/runs/normal/
AGTST*/{telemetry,trajectory}.ndjson (AGTST14 also navmesh.ndjson);
docs/agtst-reauthoring-notes.md (this note); docs/nblood-autonomous-
playtest-bot.md; NBlood/extras/*.md for per-map intent. Read the telemetry
format from the bot source in NBlood/source/blood/src (the llmapper bot
files; grep for the event names) so every field is read as the engine
wrote it.

Deliverables
1. tools/agtst_extract.py: telemetry -> one JSON per map: sectors with
   clearance/floor/ceiling, adjacency (wall from/to, floor_delta), doors
   (kind, key, locked), solid sprites (type, picnum, pos, cstat), walkable
   point cloud per sector (waypoints + trajectory), navmesh cells where
   present. Report coverage: sectors mentioned vs total_sectors.
2. tools/agtst_rebuild.py: JSON -> projects/agtst-replica/level/AGTST-R<n>.MAP
   through PlanarLayout: room outlines from the point cloud (convex hull
   padded to clearance-consistent rectangles; navmesh union for AGTST14),
   portals from the adjacency, floor/ceiling from local_geometry, doors
   from discovered_door via bloodmap.doors / mechanism constructors, solid
   sprites placed as recorded. Validate, roundtrip, read back
   (bloodmap.readback) and render with tools.render_precedent.
3. A per-map report (projects/agtst-replica/reports/replicas.md): what was
   rebuilt, what was guessed, what could not be (AGTST16-18: nothing), and
   the sector-graph diff between replica and telemetry.
4. Do NOT touch reference/blood or maps/; do not name any output
   AGTST<n>.map; never run the game. The owner decides whether a replica
   becomes a gate map.
```
