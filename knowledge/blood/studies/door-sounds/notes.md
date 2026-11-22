# Study: door-sounds

## What I want to build

Give Gravesend's moving doors and machinery the feedback Blood authors into
comparable mechanisms. The starting city map has 39 moving sectors and zero
type-709 markers.

## Where Blood built it

The census joins every type-709 sprite to its own sector in 43 campaign maps
and, separately, 171 mechanism tutorials. The columns show sectors with any
marker over total sectors and the most frequent complete four-field tuple.
Counts for tuples are sprite counts. Sectors can have more than one marker.

| Sector type | Campaign marked / total | Leading campaign tuple and count | Tutorial marked / total |
| --- | ---: | --- | ---: |
| 600 Z-motion, ceiling only | 387 / 622 | 106/157/106/157 ×63 | 64 / 87 |
| 600 Z-motion, floor only | 245 / 451 | 106/160/106/160 ×31 | 93 / 125 |
| 600 Z-motion, both planes | 61 / 157 | 358/0/0/0 ×7 | 8 / 25 |
| 600 Z-motion, equal endpoints | 5 / 6 | 0/0/0/0 ×5 | 2 / 3 |
| 602 Z-motion sprite | 23 / 50 | 255/0/256/0 ×4 | 60 / 73 |
| 612 path | 0 / 0 | See waypoint fields below | 8 / 44 |
| 613 step rotate | 5 / 11 | Five distinct tuples, one each | 3 / 6 |
| 614 slide marked | 264 / 308 | 103/0/103/0 ×30 | 168 / 199 |
| 615 rotate marked | 20 / 41 | 113/200/113/200 ×3 | 50 / 77 |
| 616 slide | 43 / 88 | 121/156/121/156 ×5 | 34 / 70 |
| 617 rotate | 136 / 211 | 101/0/100/160 ×24 | 71 / 108 |

The [full census](census.json) preserves every tuple and individual slot
count, example records, and the separate tutorial population. Tutorial type
611 occurs twice and is outside vanilla sector dispatch. Teleport, panning,
and bobbing have separate engine paths from these triggered motions.
Regenerate with `python -m tools.mine_sector_motion_sounds -o knowledge/blood/studies/door-sounds/census.json`.

## What makes it read as that

`NBlood/source/blood/src/triggers.cpp:759–801` scans sprites in the moving
sector for type 709 on decoration stat 0
(`NBlood/source/blood/src/common_game.h:153`). At start it reads
`data_1` from OFF and `data_3` from ON (caller at
`triggers.cpp:1495–1522`). At the endpoint it reads `data_2` on reaching
ON and `data_4` on reaching OFF (for example `triggers.cpp:1351`).
Zero skips playback for that phase. OFF and ON describe engine state,
and a door can be drawn shut at either end. A path sector instead uses
the departed path marker's `data_3` at departure and `data_4` at arrival.
Its own 709 is the sound origin (`triggers.cpp:807–814,1486–1487,1640`).
In the tutorials the leading nonzero path sounds are 113 at departure and
163 at arrival, 21 legs each. The census counts these by following the
waypoint IDs from each audible path sector's start.
The local NBlood source was read from the main checkout.

## Sizes

All 1,247 campaign markers are tile 2520 on stat 0. The common cstat is
32896 (1,175 markers). The remainder add movement attachment or alignment
bits. Use an interior point, the local Z range including a shut leaf's shared
plane, and the invisible bit. The trolley's marker rides the deck. Observer
frames suppress control types 700–712.

## What I will transcribe

| Gravesend mechanism | Data fields | Evidence |
| --- | --- | --- |
| Standard Z-doors and crypt slab | 106/157/106/157 | 63 ceiling and 22 floor markers. E1M5:335 and E1M5:375. |
| Carriage door | 110/150/110/150 | 3 floor markers and 16 ceiling markers. E2M5:86 and :769 are floor examples. |
| Roll-up tunnel gate | 105/153/105/153 | 3 ceiling markers (E6M3:52, :55, :123), 18 floor markers. Also both top-level tutorial elevator sectors. |
| Settling Hall lift | 116/157/116/157 | 4 floor markers, including E3M5:0 and :6. |
| Foundry loading shutter | 103/0/103/0 | 30 marked-slide markers. E2M4:438 is a shutter. |
| Aldermack fire doors | 101/0/100/150 | 5 whole-rotation markers in E4M4, e.g. :146. |
| Aldermack curtain | 0/159/0/159 | 8 marked-slide markers, including curtain E1M1:125. The tutorial population has another 41 matching markers. |
| Stockyard trolley | 115/153/115/153 | E1M2:8, one whole-slide train deck with drag. The tutorial one-way vehicle uses 115/151/115/151 on its audible section. |
| Ghost Station hatch | 111/159/111/159 | E1M3:327, one whole-slide panel. The separate latch cue still fires. |
| Pump presses | 302/309/0/0 | All six E3M5 ceiling presses studied use this tuple. |
| Door and station levers | 203/203 | 40 of 97 pushed type-20 tile-1070 sprites in the campaign use this pair. NBlood reads `data_1` on ON and `data_2` on OFF (`triggers.cpp:441–454`). |
| Fare turnstile | Ambient 21 (near 250, far 700, volume 20) | E1M4:151 and :314 each have one 710 with this envelope and zero 709 markers. Tutorial DOOR-ROTATING:4 has neither. |

E1M1:4 and E1M5:183 provide a door and a lift with complete tuples. E3M5:64
is a marked rotor with a hydraulic start and stop, providing a comparison
for the much longer fare turnstile cycle.

## What I will not do, and why

Keep the three four-piece blast openings on their existing breakage and
charge sounds. The city read-back finds three timed charges on each wire.
Their default sound is 304 (`NBlood/source/blood/src/actor.cpp:5184–5218`).
All 39 campaign type-600 sectors matching the rapid,
one-shot, receiver-driven closed-to-open geometry have zero 709 markers.
The six type-600 sectors in ENVIRONMENT-EXPLODEWALL likewise carry none.
Keep the pump belt on machinery ambience 18. Its panning does not call
sector start and stop sound dispatch. Of 220 panning, dragging type-0
campaign sectors, one contains a 709. E3M5 placed 710s instead, ID 105
in sector 49 and 103 in sector 193.

Use `python projects/blood-city/level/motion_sounds.py` to list the
rebuilt city's sectors, their markers, and the four fields from the MAP.

## What I still do not know

The current check covers authored records and engine dispatch. An in-game
listen will establish relative loudness in the city.

Ronald Allen's [Sector and Ambient Sfx List, updated 6/25/97](https://rtcmsite.neocities.org/knowledge-base/library-online/blood-mapedit-map%20editing%20and%20effectsv2)
(`work/briefs/sector_ambient_sfx.json`) is a 1997 fan listening guide.
It lists 106 as heavy sliding stone, 157 as deep/heavy impact, and 203 as
a door-handle click. Some descriptions and resource names differ:
105 is chain lift in Allen and `ELEVMOVE` in `SOUNDS.RFF`, 153 is a steam
valve opening and `ELSTOP2`, 159 is a closing click and `QPLAT2`, 302 is
repeated door closing and `MGDIE`, and 309 is stomping and `EXPLODUS`.
Allen gives no description for 110 (`QDOORMV1`) or 115 (`QTRAIN1`).
The fan list repeats 720 and assigns two descriptions to 742. There was
no Whisper transcript in the brief. The map records determine which IDs
to play.
