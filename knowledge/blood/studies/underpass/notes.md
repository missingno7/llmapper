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
