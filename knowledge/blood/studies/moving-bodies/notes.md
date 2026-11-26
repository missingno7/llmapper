# Moving bodies

Build one with `bloodmap.mechanism.rigid_body` (members, host, travel) and
`carry_fittings`; read one with `motion_sim.rigid_bodies` and `body_health`.
Gravesend's Phantom Terminus rides a body of some seventy sectors built by
`projects/blood-city/level/carriage.py`.

**What hangs outside** a body stands in the host's space, where the body's own
sectors cannot carry it. E1M2 makes the host itself a mover: s34 is type 614
with the train's markers, time and wire, and its wheel sprites 66, 67, 70 and
71 (tile 847) carry bit 8192. A 614 moves only flagged walls: s34's outline
is unflagged and stays put, while walls on two of its holes (386-390, 396,
397) carry 16384 and move with the sprites. None of the campaign's 306
carried sprites stands outside its sector; 15 of Death Wish's do.

## Corpus and measurement

The supplied `experiments/moving_bodies/scan.py` compared connected horizontal mechanisms
on the same nonzero receive channel across 1,773 maps. Its 469 candidates
contain 2,215 sectors, including marked slides and rotations that share a
channel for reasons other than common translation. All members have Drag in
108 candidates. All ceilings have bit 64 in 51, and at least one has it in
117. These counts include parallaxed and closed surfaces.

Re-reading the same corpus with `motion_sim.rigid_bodies` found 208 bodies
and 1,101 member sectors. Four bodies are in the campaign, 30 in curated
maps, 172 in bulk community maps and two in tutorials. Two bulk maps could
not be parsed. The narrower sample still includes doors and machinery, so
the counts describe rigid slides. `experiments/moving_bodies/measure.py` records the
sector, wall and sprite measurements and the selection rules.

| Property | Measurement | Precedent |
| --- | --- | --- |
| Drag | 81/208 bodies have Drag on every member. | MACHINERY-1WAYVEHICLE s2–10, DWE1M2 s225–228 and s418–423, E1M2 s7–9 |
| Relative flats | 102/594 non-parallax ceilings with vertical clearance have bit 64. All eligible ceilings are relative in 23/123 bodies that have one. The corresponding floor count is 623/1,053. | DWE1M9 s475–480 and s789–790 have both bits throughout. E2M1 s87 and s91–93 use relative floors beneath a parallax sky. |
| Hull solids | 26/208 bodies have equal floor and ceiling Z in at least one member, for 47 such sectors. Their minimum enclosing rectangle's short side is 128–3,328 XY units, median 256. Ten bodies use one-sided walls on interior holes, for 199 wall records. | Tutorial s2–5 are four 256 × 256 closed posts. DWE1M2 s418/419/421/422 are closed hull corners. DWE1M9 s475/790 have 16 one-sided edges around real voids. |
| Windows | 20/208 bodies have masked or one-way walls between members. For the 54 masked wall sides with the member outline entirely on one side of the wall line, perpendicular bay depth is 64–6,528 XY units, median 128. This measures each side's sector depth. | DWE1M2 s226/227 are two 128-deep bays around a 1,024-wide tile-266 pane on w2428 and its partner. Tutorial s6–8 use open 256-deep sill-and-head bays. |
| Deck relative to host | 174/208 bodies have at least one perimeter floor above its external neighbour's base floor Z. This includes rims and checks base Z before slopes. | E1M2 s7–9 are 16,384 Z above s34. DWE1M2 s225, level with saloon s228, is 5,120 above s334. E2M1's rim s87 is 5,120 above water s125, while the wells s91/93 are 5,120 below that water surface. PHANTOWN s88 is flush with road s69. |
| Payload | 533 visible sprites have the carry flag in the body's direction and 59 meet the grounded face-sprite rule. The reader counted 111 without a ride and four flagged to move opposite their sector's walls. It exempted 976 invisible/artless or control sprites. | DWE1M9 s475 carries 14 tile-463/464 grates, and s790 carries four fixtures and two grounded cultists. E1M2 s7–9 carries all ten visible sprites, including the Phantom lettering. |
| Hanging lamps | The chain-lamp tile 641 occurs three times across two bodies. Other light tiles and built-in panels fall outside that count. | DWE1M9 s790 sprites 1283/1284 hang under its roof. DWE2M1 s128 sprite 119 carries the other. DWE1M2 s228 uses fluorescent tile 2290 on diagonal corner walls w2440 and w2456. DWE3M4 s60/63 put tile 501 into the front corner walls. |

XY widths use the Blood player width of 384. Z heights use the Blood
standing height of 16,960. Both are from `bloodmap.player_space.PLAYER_PROFILES`.
The median closed-sector width of 256 is two-thirds of a player width.
The median window half-bay of 128 is a third of a player width.

## What reads as solid

The XMapEdit observer photographed local copies in the saved pose with
enemies and pickups hidden. The tool was `tools.look_at` through
`experiments/moving_bodies/look.py`, which points at the headless binary in the main
worktree. The frame references are relative to `work/movers/`.

| Body | Frames | What gives it depth |
| --- | --- | --- |
| MACHINERY-1WAYVEHICLE s2–10 | `tutorial/frames/round_00.png`, `round_01.png`, `round_03.png` | The oblique view shows the post turning the corner and the metal bands wrapping it. Deck s10 has 28,672 Z of headroom (1.69 standing heights). The side bays s6–8 raise the sill 8,192 above the deck and put the head 5,120 below its ceiling. Doorway s9 drops the sill to deck height. |
| DWE1M2 s225–228 and s418–423 | `dwe1m2/frames/round_00.png`, `round_01.png`, `round_03.png` | The recessed opening has a visible jamb, lit inner panel and deep sill from the side. The 256-deep glazed bay gives a separate plane for the glass. Inside, s228 has its own 25,600 Z headroom (1.51 heights), a ceiling 9,216 below the host s334 ceiling, and bright diagonal corners. The 512-wide closed corners give the silhouette mass. |
| DWE1M9 s475–480 and s789–790 | `dwe1m9/frames/round_00.png`, `round_01.png`, `round_03.png` | A pointed wooden bow, tall raised hull, real roof and a band of carried grates read as separate layers. Sectors 476/478 are each 2,816 × 256 and stand 4,096 Z above the interior floor of s790, a built-in ledge under the sides. The lamps sit behind the grates under the 36,864-Z-high interior. |
| E2M1 s87 and s91–93 | `e2m1/frames/round_00.png`, `round_01.png`, `round_03.png` | A continuous gunwale casts the silhouette. The two wells s91/93 step down inside it and the bench-like transverse strip s92 stands 6,144 Z above them (0.36 heights). The wood step faces are visible from both bow and stern. Sky above the open boat needs no relative texture. |
| PHANTOWN s88–108 | `phantown/frames/round_00.png`, `round_01.png`, `round_03.png` | A flush perimeter hides the contact seam with the road. The 64-wide quarter panels s95/97, raised bodywork and real cabin floor make room for the wheels and lights as decals. Seats s92/93 are 512 × 512 and stand 3,072 Z over cabin s94. Their 128-deep backs s90/91 rise another 8,704. |
| DWE3M4 s57–70 | `dwe3m4/frames/round_00.png`, `round_01.png` | Slopes and steps sit inside a wide, layered skirt. The front lamps are in shaped corners s60/63 beside the grille, so shape and texture support each other. The 1,024-wide central deck s62 is bounded by 256-wide strips s61/64. |

The observer produced 52 frames across nine examples. Its rings for E1M2
s7–9, DWE2M1's s105 group and CULTBASE s615–632 included obstructed or
close views. On the Phantom Express, s7/8 are
1,024-wide side sectors joined by a 512-deep s9 crosspiece, while linked
marked slides s10/34 change only selected boundaries and stay outside the
rigid body. DWE2M1 s105 has a 512-deep sloped edge and s106–109 put
256-wide strips at the sides. HOS-E1M5 s275–281 uses the two-member glass
seam between s278/279 and has 26 one-sided walls on its interior voids.

## Travel and clearance

NBlood `TranslateSector` and `trInit` use separate marker origins and
per-sector wall bases. Match marker displacement, zero both marker angles,
and match the receive channel, both busy times, both waves and starting
state. For a 616 the geometry travels in the marker direction. A 614
qualifies when every wall takes the same flagged movement branch. The
saved geometry is the ON pose for these zero-angle slides.

For positive ON times, marker distance divided by the busy time in tenths
of a second gives the nominal mean speed. Across the strict sample the
range was 27–35,328 XY units/s, with median 3,765. E2M1 s87 travels 23,790
units diagonally in 18 s (1,322 units/s), tutorial s2 travels 11,776 in
10 s (1,178), DWE1M9 s475 travels 37,376 in 25 s (1,495), and E1M2 s7
travels 24,064 in 12 s (2,005). DWE1M2 s228 travels 101,632 in 15 s
going ON and 10 s going OFF (6,775 and 10,163). PHANTOWN s88 uses the
15 s OFF leg to travel 66,688 (4,446). These are means over the whole
leg. Wave, integer busy increments and event logic determine the actual
position at a tick.

Every map below was read at 16 steps both before and after. The `passed`
and problem counts include the existing sweeps of individual mechanisms.

| Population | Maps | Mechanisms | Maps passed before → after | Problem lines before → after | Bodies healthy / found |
| --- | ---: | ---: | ---: | ---: | ---: |
| Campaign | 43 | 648 | 11 → 11 | 892 → 892 | 4/4 |
| BloodBath | 9 | 48 | 5 → 5 | 43 → 43 | 0/0 |
| Curated | 46 | 847 | 14 → 14 | 516 → 497 | 24/30 |
| Tutorials | 171 | 452 | 155 → 155 | 119 → 119 | 2/2 |
| Total | 269 | 1,995 | 185 → 185 | 1,570 → 1,551 | 30/36 |

The four campaign bodies are E1M2 s7–9, E2M1 s87/91/92/93 and E3M2
s6–10 plus s11–15. The tutorials are ENVIRONMENT-SLIDETRICKS s1–3 and
MACHINERY-1WAYVEHICLE s2–10. All six pass the body sweep. The curated
reports retain XY clearance findings for DWE1M1's s81 group, DWE1M2's
s47 and s50 groups, DWE2M1's s350 group, DWE2M2's s87 group and
DWE2M5's s199 group. For example, the DWE2M2 body crosses its host
s193 at step 10 of 16. DWE2M1's s350 group exceeds host s569's XY
outline. Several wall hits are against s129, which also illustrates
overlapping geometry at different elevations. These reports are sampled
geometry checks. Gameplay timing and traversal of the six curated bodies
were not verified. The DWE1M2 s225 car in the study is a separate, healthy
body. Full reports are in `work/movers/before-*.jsonl` and `after-*.jsonl`.

## Authoring a car

1. Draw a host big enough for the entire outside outline at both endpoints
   and through the travel. Split the car into two or more portal-connected
   sectors. Give them type 616, a shared receiver from one `wiring.Circuit`,
   and matched motion fields. Copy the delta between marker pairs and
   sweep the body at load and throughout the leg.
2. Start with the tutorial's 256-wide posts and side bays. Use a closed
   sector for each solid corner or use a genuine one-sided hole where a
   separate slab or post needs a cutout. Keep each sector that holds moving
   architecture in the body. Shared vertices can move the walls of a static
   island while leaving its contents behind.
3. Give the deck a ceiling plane and a clear boarding edge. Use the
   25,600–28,672 Z interior heights of DWE1M2 s228 and tutorial s10 as
   references. Set bit 64 on visible textured floors and ceilings. Recess
   glazing between two 128-deep sectors, and use their upper and lower
   steps for the head and sill. Check boarding against the dock at the
   served pose. The standing step allowance is 4,096 Z.
4. Shape seats and hood lines as raised floor sectors. Place a wall lamp on
   a solid corner or a chain lamp under the ceiling, and use sprite bit
   8192 for fixtures on a 616. Set Drag on every walking member so
   grounded face sprites and players can ride between pieces.
5. Measure the movement in whole-body lengths per second as well as
   travel time. As starting precedents, the tutorial covers 11,776 in
   10 s, or 0.58 of its 2,048-unit length each second, and the E2M1 boat
   traverses its diagonal in 18 s. Photograph the side and an oblique
   angle to see jambs, ledges and the boarding seam.
