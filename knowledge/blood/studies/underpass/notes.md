# Study: underpass

Written 2026-11-19, for the owner's rework of Foundry Ward's works yard:
"I would rethink the whole area ... underground passageway for future metro,
service hatch to sewers sounds good." Seeds run through `tools.study`:
`E1M2:104!` and `E1M2:105!` (the passage and stair between the street and the
station's waiting hall) and `maps/blood/community/MISKSTAT.MAP:0!` (a
community station's platform). I looked at the two frame sheets myself; no
blind reader has.

## What I want to build

A pedestrian passage under the rail spur: a stair down from the works yard, a
concourse wider and taller than a corridor, a closed ticket barrier, a barred
tunnel mouth where a metro was begun and never finished, a second stair up on
the far side of the spur, and a service door to the sewer. In the first
second a player should read "a public way under the street", not "cellar"
and not "sewer".

## Where Blood built it

It did not, as a metro. The library has no place, tile or study answering to
"subway", "metro", "underpass" or "turnstile", and the community maps the
station study named (FCZug, MISKSTAT, STATION) spell no such word that
`lettering.read_sign` can read.

The nearest thing in the campaign is **E1M2's passage**: s103/s104, two
halves 2.8 m wide and 14 m long, 7 m high, floor 281 (the owner's "irregular
grey stone masonry"), ceiling 120 ("clay tiles"), walls 417 ("brick wall
with crumbling plaster"), unlit and bare. It runs from the street (s207) to a
stair (s105, 3.5 m by 7 m) and comes out in the waiting hall, where the
light, the notice board and the people are.

## What makes it read as that

From the frames, in the order a player meets them:

- **The passage itself is dark, plain and long.** No sprite stands in it. It
  reads as a way through because of its proportion (five times as long as it
  is wide) and because there is light at its far end.
- **The destination is where the dressing is.** At the passage's end: a
  fluorescent strip lamp over a wooden notice board with bills and wanted
  posters pasted on it, and iron gates with spear heads standing open.
- **Iron railings mean "the public stops here".** MISKSTAT fences its
  platform from its track with a spear-headed iron railing the length of the
  platform; E1M2 uses the same family as gates.

## Sizes

- E1M2's passage: 2.8 m by 14 m, 7.0 m high. Its stair: 3.5 m by 7.0 m.
- MISKSTAT's platform strip: 4.3 m by 31 m, 3.5 m high under its canopy.
- So a passage is about 3 m wide, and a low ceiling (3.5 m, two bodies) is
  attested for a place people stand in. Ours has room for about 1.2 bodies
  between the street's slab and the sewer's, which is LOWER than either
  reference. That is the plan's weakest point and is recorded as such.

## What I will transcribe

- The passage's materials: walls 417, floor 281, ceiling 120.
- The lit notice board at the concourse, under a strip lamp, as the thing a
  player walks toward.
- Iron bars (tile 58, the owner's "iron bars (jail)", a mask on 13 maps)
  across the unfinished tunnel mouth and where a ticket barrier would be.
- The boards the campaign has for tickets (943 'TICKETS', 905 'TICKET
  PRICES'), which it hangs at carnivals and a theatre, on the booth.

## What I will not do, and why

- No turnstiles. Blood has no turnstile here to transcribe, and the city's
  own rotor turnstile is a different mechanism with its own history.
- No "METRO" lettering copied from a community map: none could be read.
  If the passage is named, it is named in the city's own letter sprites.
- No trains, tracks in use or platforms. The metro is unfinished; the player
  sees a barred mouth and a dark bed beyond it.

## What I still do not know

- Whether the headroom reads as a public passage or as a crawl
  space (1.93 bodies under the block: see the last section). Only a frame,
  and the owner walking it, will say.
- Whether the works west face on the avenue can take a second stair head
  (the passage runs under the works to the avenue, not under the spur).
- Whether a breach in the concourse wall onto the unfinished tunnel is
  legible as "the metro" without a platform behind it.

## The owner's own metro: DNE3L6 (added 2026-11-20)

The owner: "I made metro in one of my duke converted maps Rabid." That is
`maps/blood/conversions/DNE3L6.map`, his Blood conversion of Duke's Rabid
Transit, and it outranks everything above: it is a metro built in Blood's
tiles by the person this one is for. Seeds `DNE3L6:0!`, `:165!`, `:371!`;
I looked at the frame sheets for 165 and 371 myself.

**The ticket hall (s371).** 10,752 by 15,360 and 65,536 high: 18 m by 28 m,
3.9 bodies. Floor 287 ("interlocking paving", dark red brick), ceiling 40
("bevelled grey stone slab", coffered), walls 2293 (grey plaster) over a
panelled stone dado with 427 (grey ashlar) on the end walls. What makes it a
ticket hall, in the order the eye finds them:

- a row of barred ticket windows (sprite 1060, "black iron lattice grille",
  six of them) with a clerk behind each, under the board 943 'TICKETS';
- the board 431 'ARRIVALS DEPARTURES', bloodied, high on the same wall;
- the green sign 761 'EXIT' over the doors out;
- two iron ring chandeliers (549) and statues in niches on the end wall.

**The platform (s165 with s0, s90, s92, s20).** One strip 16,896 long, in
bands across its width:

- the platform proper, s165: 3,968 wide, 56,832 high (3.35 bodies), floor
  294 ("chequered green and grey marble"), ceiling 390, walls 102 ("cracked
  brown plaster") with a dark dado rail, hung with tapestries and a banner
  (610, 614, 847), floor shade -8: the brightest place in the map;
- a LIGHT BAND beside it, s0: 768 wide under a ceiling dropped to 25,600
  that wears 2288 ("fluorescent light, vertical tile") at shade -24. It reads
  as a strip light running the whole platform;
- two more low bands, s90 and s92 (864 and 960 wide, ceiling 491 metal
  plating), their walls 321 ("dark ornate iron lattice strip"): the train's
  side, with its doors;
- the edge, s20: 192 wide, floor 208 ("diagonal black-and-yellow hazard
  stripe").

**What this changes in the plan.** The first plan was a brick passage with a
notice board. The owner's metro is a public building: tall, lit, tiled,
with a ticket wall and a named way out. So:

- The concourse is a HALL, not a corridor. The layout below gave it 3 by 5
  plan units at 1.93 bodies; his is 10 by 15 at 3.9. Under the works block
  there is room for about 8 by 8 south of the trunk (x 41..49, y 23..31),
  and no street above it, so it can stand 3 bodies high.
- Its dress is his, tile for tile: floor 287, ceiling 40, walls 2293 over a
  stone dado, ticket windows 1060 under 943, the board 431, 761 over each
  way out, chandeliers 549.
- The unfinished platform beyond the bars is his platform cut short: floor
  294, the 2288 light band dark, the 208 hazard edge, and no train.
- Brick 417 and floor 281 from E1M2 are kept for the stairs and the service
  room only: the parts that are NOT the metro.

## Where it fits in the works block (measured 2026-11-19, not built)

The works block is x 39..53, y 3..35 in plan units (1,024 each); the yard is
its notch at x 49..53, y 15..23. Read off the built map:

- **The sewer lies under most of it** between z 36,864 (its ceiling) and
  61,440 (its floor): a run along the block's west edge (x 39..41), the trunk
  across it at y 20.5..22.5, runs south of that, and the pump hall's part to
  the north.
- **So the underpass floor has to be at 32,768 or higher** (one 4,096 slab
  over the sewer's ceiling). At that height it can cross over any sewer run.
  The street floor is 8,192, so that is six 4,096 steps down.
- **Under the block there is no street sector above**, so the passage's
  ceiling may rise above street level inside the mass: floor 32,768 with a
  ceiling at 0 is 1.93 bodies clear. The "1.2 bodies" in the first plan was
  the headroom under the STREET, which the passage does not have to keep to.
- **The present stair goes deeper than that.** Its top room is x 47..49,
  y 18..20; eight steps run west to a landing at 40,960; three more run north
  to the cellar at 53,248, whose pit is the room-over-room link into the
  sewer. The landing is boxed in by the sewer on three sides at its depth.
- **A straight west-east passage does not fit.** Two top rooms and two
  six-step flights take 10 of the block's 14 units.

The layout that does fit:

1. East stair: the present top room, six steps west to a landing at
   x 42..44, y 18..20, floor 32,768.
2. Concourse: south of that landing, x 41..44, y 20..25, over the trunk.
3. West stair: a top room in the works' west face at x 39..41, y 18..20,
   opening on the avenue; six steps south to a landing at x 39..41,
   y 23..25, which opens east into the concourse. This needs a notch in the
   works' west face in `city_plan.py`.
4. The unfinished metro: bars across the concourse's south end and a short
   dark bore beyond, x 41.5..43.5, y 25..27, its bed half a step lower.
5. Service hatch: a small room off the concourse's east side whose floor
   holds the sewer link, over free ground at about x 44..45, y 22.5..23.5,
   beside the trunk's south face. It replaces the cellar and its pit.
6. The breach: a cracked stretch of the concourse wall beside the bars.

Done so far, on the surface: the yard's grate is a grate (no link, flush,
tile 502 laid as a floor sprite), the low dock is a bay at grade, and the
staged charges are gone. The wire `foundry:staged-moment` is idle until 6.

## What was built (2026-11-20), and how it differs from the layout above

The owner chose the passage over the hall: "you can do your own style as you
described before, there is not that much space ... just do a passageway."
Built in `build_skeleton.py` (stage `works-stair`), in E1M2's passage
materials (brick 417, stone 281, clay tiles 120):

- **Depth 16,384 below the street, not 24,576.** `bloodmap.layers` lets two
  plans share ground only when their height bands are apart, and the
  sewer's band starts at 28,672. The passage is its own layer, `underpass`,
  from 8,192 above its floor's 32,768 clear down to a floor at 24,576.
- **The yard stair keeps its place and its eight treads**, taken at 2,048
  each, and its landing is the passage's level.
- **The old lower flight and the cellar are kept whole** as the service
  stair to the sewer hatch (eight steep treads of 384 by 3,584). The
  cellar's room-over-room pit sits inside the sewer's junction chamber and
  was not worth moving. So the "service room off the concourse" of the
  layout above is the cellar where it always was.
- **The passage** runs south from the landing, 2,048 wide and 5,120 long,
  1.93 bodies clear, over the sewer's trunk.
- **The avenue stair** is half that width, stands a wall's thickness clear
  of the landing and the passage (two rooms that share an edge and no
  doorway are refused), and is reached from the avenue through a porch in
  the works' west face. A flight laid along the block's edge was refused
  too: every tread became a neighbour of the street.
- **The metro bore** is one corridor square behind iron bars (tile 463),
  floored with track 1129 and dark. Its bed is level with the passage,
  because bars hang on a wall whose two sides stand at one floor.

Not built: the breach (the wire `foundry:staged-moment` is still idle), any
door on the service stair, a notice board or a lamp in the passage, and the
second-exit porch's fit to the facade's painted windows, which it cuts.

## Rebuilt long (2026-11-25)

The owner, having played the passage: "I would also rework the underpass, add
there some posters and things, making it look more liminal." Looked at again,
by `tools.gallery` (DNE3L6 s165, s169, s171, s371; E1M2 s92, s104; DWE2M2 s634,
s679; DWE3M4 s118; E3M4 s220; E4M9 s95; DWE2M10 s157):

- **DWE2M2 s634 is the corridor that has it.** 4.5 units wide, 37,888 high and 24 long: plaster over a red tiled
  dado (2294, its dado's top at row 154 of 256, hung so that it stands 0.87 of a body), a plain ceiling (374), two rows of identical tubes
  (2290, 512 by 1024, four-wall sectors at ceiling shade 0 over a floor at 13, the rest at 30), the same board
  (420) at intervals, nothing on the floor but paper and bottles. It reads as it does because every bay is
  the last one again and the far end is a small bright square.
- **DNE3L6 s171 is the owner's own**: the passage from his ticket hall to his platform is grimy tiles (296), interlocking
  paving (287) and bevelled slabs (40), with a stair on one side and black at its end.
- **A dead tube is a tile**: 2289 and 2291 are the lit 2288 and 2290 with the glass broken (E1M2 s92, DWE2M2 s274).
- **The pram** (183) stands once in the campaign: alone, in E3M4 s423.
- **The folding gate** 1060 is what the owner hangs before his ticket windows; floor to ceiling it is a metro's, and one sees through it.
  The jail bars (463) in an opening lower than one tile show their top rail in the middle of it, and hid everything behind them.

Built: `projects/blood-city/level/underpass.py`, intent in `projects/blood-city/references/underpass-design.md`.
A sliding sector's sweep is judged in plan only (`swept_state`), so over the sewer it had to lie where no sewer wall runs:
between the cistern's wall (y 27) and the ring's (x 51).
