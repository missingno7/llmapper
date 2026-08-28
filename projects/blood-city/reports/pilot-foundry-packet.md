# Pilot district packet — Foundry Ward, iteration 1

The first dressed district (owner construction directive). Build:
`level/build_skeleton.py` + `level/l3_foundry.py` →
`level/city-skeleton.MAP`, mirrored to **`level/blood-city-current.MAP`**
(the always-playable build).

## What is in it

- **The parked sewer, per the sewer directive**: network parked at
  +73,728 x (reservation recorded in city_plan `SEWER.park`), connected by
  two hand-built stack pairs (grammar request #7 is the constructor ask):
  the **yard grate** — see-through (mirror 504 both faces; the glimpse
  down sells depth per backdrop logic) — and the **cellar pit** — solid
  (a dark shaft off the works stair; no preview, seams hidden). Forms and
  reasons recorded in city_plan entries. **Wormhole law holds: one shared
  translation, checked every iteration in conformance.** Mouths congruent
  at the plane per stacks-v1; pit landing depth 10240 (standing centre
  stays below the plane — no warp ping-pong — and a jump exits).
- **The works canteen** (venue-patterns `shop`): geometry counter (rise
  4096) and display pedestal (rise 2048, E6M1 module), back room, z-motion
  push door with door-face/jamb tiles attested from E3M1 and a
  marquee-flickered mouth (amplitude −24).
- **Backdrop window** (backdrop-and-weave): a rail-yard scene box behind
  the canteen's back wall — 10 walls, sill 8192, sky-lit, silhouette mass
  carved.
- **Yard furniture** (street-furniture, industrial): loading-dock alcove
  recessed in the works face (the free-standing version breached the CN
  loop ceiling — conformance caught it), barrels on the dock, lamp
  sconces (tile 641) at the stair mouth and canteen door.
- **The staged moment** (destruction reserve, channel 30): stepping onto
  the grate fires two exploders and a sound cue at the dock. One tx (the
  grate sector, trigger-once), three rx.
- **Population at campaign registers**: two cultists holding the yard, a
  zombie in the canteen back, three rats below (E3M3: scavengers, no
  garrison). Breakable barrels ×2 (campaign modal form).
- **Lighting**: directional wall shade (36 rooms / 255 walls, median
  spread 8), corpus shade match (offsets +4 wall / −8 floor), authored
  animated shade in the sewer (junction −16, wet trunk −20 + depth 3) and
  on the door mouth.

## Acceptance

| check | result |
|---|---|
| plan contracts (plan_review) | 16/16 |
| conformance incl. wormhole law | **7/7** |
| budget | pilot ≈ 31 sectors / 182 walls vs ≤1100 cap; city total 36/255 |
| engine load | clean run, no crash (before the no-self-run rule; future runs owner-side) |
| pose renders (XMapEdit observer) | street, canteen, yard/dock, sewer junction — `reports/pilot-views/` |
| bot walk | **not run** — owner: bot is crash-smoke only and nblood is not run from this session; static reachability + stack arithmetic verified instead |

## What the renders say (and iteration-2 notes)

- The street canyon reads as a Blood city under the red night sky; the
  facade tile carries window rows for free — the "windows are texture"
  finding, live.
- The canteen reads as a room with real furniture-height geometry.
  **Iteration 2**: interior walls still wear the facade (windowed) tile;
  interiors need their own wall set from the surface palettes.
- The sewer junction reads as a chamber, not yet a sewer. **Iteration 2 /
  Phase 4**: sewer wall/floor set, the water channel, ledge cross-section.
- The see-through grate cannot be verified from these poses
  (top-down view needed) — owner-check item.

## Judgment calls wanting a verdict (fun-unvalidated, all of them)

1. The grate as a one-way drop with the stair as the only return — is the
   fall acceptable (3.13 standing; landing softened later by water)?
2. The staged moment's trigger (grate step-on → dock explosion behind you)
   — startle vs. cheap?
3. The canteen door as push-to-use z-motion — should it start locked with
   a key on the circuit instead?
