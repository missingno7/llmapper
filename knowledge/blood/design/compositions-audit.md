# Campaign composition audit, 24 November 2026

The audit read the native sprite positions and the sector outlines, holes,
portal mates and floor records behind 20 detections in
`compositions-v1.json`. The sample used `random.Random(20261124)` over the
shelf's campaign rows in file order. It took all five rings, seven random
nests and eight random round records. Raw JSON and plan plots are under
`work/composition-audit/`. The host sector and map-local record ID below
identify the rows from this run.

| Kind | Correct / checked | Native geometry |
| --- | --- | --- |
| Ring | 5 / 5 | E2M4:503 #9 has five cultists around the pentagram. E1M4:321 #12 has eight pilaster sprites around the centre cutout. E3M2:231 #5 has ten hanging carcasses at the same z. E2M9:118 #8 has eight cultists around the bonfire. E6M8:0 #1 has six skull panels spaced around the perimeter. |
| Nest | 7 / 7 | E4M3:222 #5, E2M2:120 #4 and E1M5:81 #5 have closed inset rims and drops of 4096, 1024 and 2048 z units. E4M1:144 #5 and E4M6:65 #1 each rise 8192. E3M8:585 #19 rises 4096 and then 26624, with sectors 589 and 595 making the middle band. E2M9:35 #1 has two miniature tiers rising 6144 and 4096. |
| Round | 8 / 8 | E6M9:67 #7, E6M6:54 #0 and E4M3:425 #14 are octagons. The eight wedge sectors in E1M4:352 #15 join into an octagonal boundary. E4M3:408 #11 has 16 sides and E1M6:165 #2 has 26. The outer bands in E2M4:619 #14 and E4M8:53 #3 have 16 and 12 sides. |

The first pass returned four spurious rings in seven checks. E1M1:31 and
E1M6:244 are off-map control closets. E1M6:68 and E6M3:27 had four selected
actors with another of the same kind inside the proposed ring. E1M8:123
also passed the first round test despite having six strong corners and
subdivided edges. A later pass exposed a four-barrel false ring in E3M1:232
and recovered the two off-angle cultists at E2M9:118. The synthetic checks
cover regular and jittered rectangular lattices, consecutive missing slots,
overlapping ring and focus evidence, and radial floor cuts.

The final sample describes precision within these 20 checks. It shares
maps with the tuning runs and provides no estimate of recall.
