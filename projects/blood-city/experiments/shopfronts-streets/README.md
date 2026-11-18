# Experiment: one record, one scale, one origin

2026-11-17, evening. Before/after pairs: [`before-after.png`](before-after.png).
`hypothesis.json` was written before the first edit; two of the owner's three
remarks arrived after it, and are marked so below.

## What the owner said

Walking the afternoon's build in NBlood:

> the glass should sit in a aperure/frame so glass texture scaling won't be
> colliding with facade texture. Also we can decorate city more, it feels bit
> empty, there were roads and sidewalk attempts but it looks poor.

and, an hour in:

> Be careful abount meaningful texture aligment, it seems like a thing that is
> sometimes off. Also these ceiling crates doesn't feel right

Four remarks. Three of them are one fact: a Build wall record has **one**
texture scale and **one** vertical origin, and it is drawn from **one** side.

## 1. Glass

Every shop window was a display box glazed on its street-side wall. That wall
is also the facade's lintel over the pane and the riser under it, and a
record's `x_repeat/y_repeat` scale its masked middle and its step bands alike.

| | before | after |
|---|---|---|
| glazed records that also carry a step band | 24 of 24 | 0 of 20 |
| glazed records that are a street's | 8 | 0 |
| facade band over the market's short pane, texels per unit | 0.25 (the facade is 0.0625) | 0.0625 |
| facade band over its long pane | 0.0357 | 0.0625 |
| `collinear solid-portal` joins that continue in x | 85% | 97% |
| `panes_without_a_recess` | 4 | 0 |

The pane now hangs where there are no bands. From the street inward: a
**reveal**, a **sash pocket** per bay with a solid mullion between two, the
**display box**, the shop; reveal, sashes and box at one floor and one
ceiling. The street-side record is two-sided to the reveal and is the
facade's again. `level/glass.py: shopfront()` gives the rectangles; the
theatre, the market hall and the arcade each build their windows three
different ways and all three took it. Jambs wear the owner's jamb tile (195),
the sill went from 2048 to 4096, a pane's `x_repeat` follows its length
(`bloodmap.glass.glaze(fit=True)`), and a window longer than 2560 is divided.

## 2. Streets

18 planned runs; 3 pieces of carriageway laid, 8 runs refused because a
district seam runs down their centreline. Pavement and carriageway both wore
cobble, so a laid road differed from its pavement by a step and nothing else.

| | before | after |
|---|---|---|
| carriageways | 3 stubs | 11 roads in 22 sectors, on 10 of the 13 runs wide enough for one |
| the avenue, Theatre Row, the market street | none | each has its road down the middle, through its junctions |
| pavement / carriageway / kerb face | 352 / 352 / the facade | 4 / 352 / 6 (owner: stone paving, cobblestone, kerb) |
| street lamps standing | 17 | 40 |
| stalls, fountain rim, monument steps wearing a slice of facade | 32 walls | 0 |

Tile 6 is 64x8: at `y_repeat` 8 it is exactly E3M1's 2048 kerb.

**The campaign does not decorate its streets with sprites.** A census of
every outdoor decoration sprite in the 43 campaign maps (read-only subagent;
scripts in the session scratchpad): E3M1, the campaign's city street, has
**six** in the whole map. It is dressed with geometry: kerb, paving, glass,
porches. Sprite precedent is E1M4 and the E2 winter town. So "emptier" was
answered with street anatomy and lamps, and no props were scattered. Two
standing claims turned out false and are corrected here, not in their files:
tiles 2519-2521 are sound markers, not lamps; and the lamp this city uses
(640) has 14 campaign instances, not 593, and **no owner anchor**. It is on
the list for the owner's next tile sheet, with 560, 547, 1167 and 2497/2498.

### The road and the seam: four attempts

A carriageway was a hole in a district's street; a hole may not touch its
street's outline; Gravesend's district seams are on its main streets'
centrelines. So no road could cross a seam, and the main streets had none.

1. **Two half-roads either side of a 256 raised strip.** Blind reviewer: "a
   grey stripe down the middle of the road ... pavement should never be a
   stripe down the road."
2. **One road on one side, the plan's owning district's.** That put the
   avenue's road where the church tower stands in it; its middle stretch got
   none, and the market street's three runs took three sides.
3. **One road on the side that keeps most road.** Consistent, and not the
   street the plan drew. This is what the owner was shown, and they asked for
   the road in the middle.
4. **The road where the plan puts it; the seam is bookkeeping.** Where a
   carriageway lies on or across a seam, each district gives up its part as
   a **notch in its street's outline**. The parts are rooms of their own
   districts joined across the seam; the five hand-written seam connections
   are gone and `streets.lay`, which runs last, writes one gate for each
   stretch two shapes share (street to street, part to street, part to
   part). `Room.faces` is resolved at compile time, so an outline can be
   replaced after everything else has named its faces.

Two things attempt 4 needed that the earlier ones hid. A guillotine tiling of
"the street minus what stands in it" is not the clear space: the tower in one
side of the avenue left a full-width stretch beyond it that no tile covered,
and the avenue was refused outright. `_clear_rects` enumerates the maximal
clear rectangles and takes the longest. And a run ends at a node, the centre
of a junction, so two roads that stop at their nodes leave the junction to
nobody: a second blind reviewer read the paved band I had left there as "an
error: carts would hit a kerb". Each run now reaches a junction's depth past
its ends; the first road laid owns the square and the others meet its edge.

## 3. Alignment (said after the hypothesis)

`frame_map` took a run's vertical origin from its first wall's peg, which is
an accident of wall order. Tile 2294 is 32x256: plaster over a rail and a
tiled dado. In the market hall the run began on a window head, so the dado
was drawn under the ceiling and never at the floor.

`frame_map(v_anchor="floor")`: one origin per run, the z at which the tile's
bottom row lies on the floor most of the run stands on. Continuity is kept
(`reflex solid-portal` joins continuing in y went from 12% to 100%, `bend
solid-portal` stayed 98%). The dado is on the floor; the avenue facade's
arched ground storey is at the pavement.

It is a city-wide change, and it found a fault by moving it: the market
stalls' edges had always been drawn from the street's record and worn the
district facade. They showed its cornice by accident and, once the facade
stood on its floor, its brick. `skyline.dress_steps(only_from=street
sectors)` now gives every raised thing in a street its own declared tile.

## 4. The crates (said after the hypothesis)

The lintel pass repaints the band over an opening with "the wall it
interrupts", from `tools.mine_apertures.dominant_wall_tile`: the commonest
picnum per wall **record**, portals included. The hall has sixteen crate rims
and five long plaster walls. Crate won, and 24,064 units of band wore it. Now
the facade is the sector's one-sided wall by length.

## The predictions, scored

| | prediction | result |
|---|---|---|
| G1 | no glazed record has a step band | held: 24 of 24 before, 0 of 20 after |
| G2 | no glazed record is a street's | held: 8, then 0 |
| G3 | `panes_without_a_recess` reports 0 | held, after the reader learned that a frame may keep its sill at the front (it reported 20 on the first build: it wanted the sill under the pane, as E6M1 has it) |
| G4 | facade over the pane at the facade's scale | held by measurement (table above). The reviewer: "matches the facade's scale in both sets", with one exception it "can't be sure" of in the *old* set. It did not see the fault the owner saw; the numbers did |
| G5 | reviewer names the shopfronts windows and mentions a frame unprompted | held: "a recess, mullions or posts, a sill ledge and a dark frame" against "one pale, rain-streaked sheet ... laid flat on the wall" |
| S1 | at least 9 pieces; avenue, Row and market street each have one | held: 11 roads, 22 sectors |
| S2 | reviewer tells pavement from road in the three street frames | **partly**: yes on the avenue and the west street ("the clearest street read in either set"); `market_road_level` is the plaza and is one surface in both |
| S3 | lamps from 6 slots to at least 16 | held: 30 slots, 29 stand; 40 lamps in the map |
| S4 | no new rule error, deterministic, load oracle, suite | see the end |
| C1 | church interior frames change by fewer than 500 px | **failed as written**: 0 to 126,373. The floor anchor re-phased every wall in the city. Looked at: the altar steps lost a moulding line they had by accident and the meander frieze moved; nothing is broken, and nothing is the same |
| C2 | arcade floor and theatre interior not retiled | held |

Recorded as could-be-wrong beforehand, and what happened: the centre strip
**did** read as a mistake and is gone; paving wall to wall **is** darker than
the cobble was, in the lanes and on the plaza, and the reviewer still counts
those as "a single surface"; the reveal at 128 **does** read as depth.

## What two strangers saw

Each a fresh reviewer, two unlabelled folders, nothing else
(`critic-first-after.md`, `critic-centre-roads.md`).

**First** (half-roads with a centre strip, against before): new 17, old 1,
neither 1, of 19. Windows: "the glass reads as a window, and R's reads as a
sheet laid on the wall." Streets: "grey flag pavements, raised kerbs, cobble
roads and lamps"; the old set, "you can almost never tell". Against: the
centre strip, and `hall_band`.

**Second** (centred roads, crossings still paved, against before): new 15,
old 1, neither 1, of 17. `kerb_along` "the best street frame". Against:
"Junctions block the road ... carts would hit a kerb"; the avenue's road
"off to the right" beside the tower; `hall_band` again; a broken frieze over
the arcade's first window (`mall_north`), named by both reviewers and not
investigated; vistas that end in "black void".

`hall_band` is the one view both scored against the new build: "isolated red
brick panels of different heights over each opening, with grey plaster
showing between them ... patchy and unfinished"; the old crate frieze "at
least reads as one deliberate band", and is "the wrong material". What they
see is the tile's own dado, standing 1.5 bodies tall on every solid pier
between openings taller than it. The alignment is right. Whether the hall
should wear a wall with a dado that tall is a design question two strangers
have now raised.

The junctions were opened after the second review. **The final build has
not been reviewed blind.**

## Does it run

Rule report 12 errors, 7 warnings (13 and 5 this afternoon; the 12 are
`tile-sits-in-an-attested-slot`). `conformance.py` 12/13: 53 declared, 54
measured, one over (it was four over before `roadways` was counted). NBlood
load oracle on the final build: pass. Two builds from source give the same
sha256. That is a load test. Nobody has walked it. Numbers: `measurements.txt`.

## Not done

- The plaza and the lanes are one paved surface, darker than the cobble was.
- Vistas still end in black; nothing was put at the end of a street.
- No street furniture beyond lamps, and the lamp tile has no owner anchor.
- The avenue's road narrows and sits east of centre beside the church
  tower, which stands in the street; north of Theatre Row it starts only
  where the theatre's porches end.
- The rail spur has no road (its run passes through the gatehouse), nor the
  quay (boardwalk).
- Facades are still one tile from pavement to sky; the ground storey is now
  where the tile puts it, and nothing fits a door or a window to its bays.
- The broken frieze over the arcade's first window.
- `apertures-v1.json` was mined with the old "dominant tile" and not re-run.
- The pawn shop's middle mannequin stands behind a mullion.
