# Study: stockyard-drain

These notes were rewritten by the integrator on 2026-11-22. The GPT 6.2 Sol worker that built the place wrote the first ones in its worktree, and they were lost when the worktree was removed before they were copied. The frames and measurements were regenerated from the same exemplars (`projects/blood-city/level/character.py`). The decisions are as built in `l3_sewer.py` and recorded in `references/sewer-design.md`.

## What I want to build

The Stockyard Drain: the slaughterhouses' outfall (`references/sewer-design.md`, "the boom"). It is a tiled race of blood that runs north from the east quay into the Foundry Main, carrying a current a body can ride. A blood pipe drips at its intake, and a rack of hung carcasses stands beside it. Its own blast-open manhole cover sits on the quay, far from every other way in.

## Where Blood built it

- **E1M8:389**, the River Ride. Blood's ridable current: a channel with drag. Its walls are 230 (52%) and 487; its sprites are explodable debris (973, 746) and zombies.
- **E1M8:251**. The sewer room with the blood pipe mouths (tile 977, four of them, wall-aligned) and wall 232.
- **TEDE1M4:82** (community-curated). A wash room in glazed tile (424).
- **E3M2:258**. The meat room: six hung carcasses (416 on 1351, gib objects), and the butcher.

## What makes it read as that

- **Blood in the water.** The current is red-brown: 1120 at palette 7, not the sewer's grey water.
- **Tile, not rubble.** Grimy wall tile (296) and bloody floor tile (291) say "abattoir", where the brook says "culvert".
- **The intake.** A pipe mouth dripping blood (E1M8's 977), and hung carcasses on a rack (E3M2's 1351, with E1M8's hook 692), place the slaughterhouse upstream.
- **It moves.** E1M8's current (speed 60, north, drag on) carries the player toward the Foundry Main.

## Sizes

- The race follows the sewer's corridor section (walks 512, channel 1,024 lower by 2,048).
- The carcass rack is a side room of 1.5 by 2.5 plan units at the walk's height.
- The new cover is 16.5 plan units from the market road's cover, the nearest other entrance.

## What I will transcribe

- E1M8's current (speed 60, drag) on the race, the landing and the ford.
- The 977 pipe mouth at the outlet.
- E1M8's 692 hook, and E3M2's 416/1351 carcasses on the rack.

Surfaces: walls 296, the rack's floor 291, and the race's floor 1120 at palette 7.

## What I will not do, and why

- No zombies or butcher. The sewer's population is E3M3's scavengers; a butcher belongs to the canteen's freezer.
- No diving suit or flags from E1M8:251. They are that map's items, not the place's.
- No crushers or machinery. The slaughterhouse is upstream, out of the map; the drain only carries what it sends.

**Since 2026-11-25** the two refusals above are withdrawn: the branch was "the most cramped part of the sewers and not one enemy in it".
A butcher works the bleeding floor (`stockyard_floor.py`), where the rack went, and gill beasts keep the blood below it.

## What I still do not know

- How the current feels to ride, and whether the drop from the quay cover reads as safe. The owner will walk it.

**Since 2026-11-23** the race runs SOUTH, from the Main to its fall into the sampling chamber (the owner: the water went against the fall), green as far as the carcass rack and blood below it; see `projects/blood-city/references/sewer-design.md`.
