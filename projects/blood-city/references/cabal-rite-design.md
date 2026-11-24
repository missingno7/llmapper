# The Cabal's rite, under the settling hall

The owner, 2026-11-24: "I would like to focus on that Cabal circle, because it
will need a lot of work to also like make it nice and cool. You check the
existing levels for references on similar things. All of these searches should
improve our catalog and understanding of the level creation."

What was there: six candelabra (580) round a puddle and two cultists on the
settling hall's south quay, two metres from a bare wall. Nothing to see from
anywhere, nothing to do, nothing that answers.

## What the references say (study `ritual-place`)

A ritual place in Blood is four things, and the circle had one of them:

1. **Something the room is arranged round**, made of sectors: E6M6's
   stone-rimmed pool, half a body high (s192/s281), E1M7's hexagonal dais with
   the slab on it, DWE2M4's drum in a moat, SSR3's octagonal blood pool. The
   candles stand ON its rim and not on the floor round it.
2. **People arranged round it**: E6M6 posts ten cultists down both sides,
   facing the pool; E1M7 eight in a ring; DWE1M4 s642 seats a congregation of
   painted robes; DWE1M9 the theatre's dead.
3. **A victim and a thing it is for**: E1M7's Ophelia on the slab with the
   blood run down it; SSR3's winged body hung over the pool; the horned skull
   tapestry (267) over curtains in E6M6; DWE1M4's black figure against a lit
   round window; a mouth of stone teeth (DWE3M6 s840, DWE2M6).
4. **An answer**: E1M7's walls fall, the earth shakes; DWE2M4's stone hand is
   broken and four phantoms come out; E6M8's column lifts its skirt when the
   four beasts fall; E1M5's chant stops when the skull switches are thrown.

And it is seen from above before it is entered (E1M7's stair, E6M6's gallery,
DWE2M6's loft).

## The place

The toshers knew the south quay's wall was younger than the hall. Behind it is
the old storm chamber: a round brick sump the engineers bricked off when the
settling tanks were dug, where every drain of the old city met. The Cabal broke
it open, dressed it out of the Aldermack (the runner carpet, the red drapes,
and the audience), cut its sign into the floor and filled the well.

Plan units; z in Build units, quay 102,400. Centre (27.5, 57.8).

| part | where | level |
|---|---|---|
| the breach: a ragged mouth in the quay's south wall set with stone teeth, the theatre's runner for a tongue | quay (27.5, 50) | quay |
| the gallery: a walk round the whole chamber, its niches hung with the city's dead | ring, radius 5,632 to 6,784 | quay |
| three tiers, seats for the audience; the runner goes down through them | to radius 4,480 | one step (4,096) each |
| the floor, filled by the sign: a pentagram of red sectors and its ring, one point to the door, inside a dark kerb (the owner, 2026-11-24: "large pentagram on the floor out of red sectors") | star 4,032, lines 384, ring to 4,224, kerb to 4,480 | quay + 16,384: a body down |
| the well: a pentagon inside the star, rimmed with ten stone teeth, full to the brim; a horned thing stands out of it to the waist with light in its hands, and a body hangs over it | radius 1,040 | floor |
| the dais (south): altar slab and victim, the book, the priest | the south wall | floor + two steps up |
| the apse behind it: the goat rose (264), whole and 2,048 square, lit from behind | | two steps more |
| two boxes, east and west, high in the drum, hung with the Aldermack's drapes: the Cabal "bought a box at the opera" | gallery + 22,528 | gunmen |
| the vault, in two rings to a black shaft, from which the chain hangs | | 4 bodies over the floor |
| the Gullet, behind the rose: flesh walls, a jaw of teeth, a beating heart on a mound | south of the apse | apse + one step |

## The rite (what happens)

1. The quay: robes on pegs, two sentries, a face over the mouth. From the mouth
   the chamber is seen whole, from above: the sign red in the floor with a
   celebrant on each point, six fires, backs turned (they are deaf and look at
   the well), and over the horned thing's head the priest, black in the rose, on
   the pulpit behind the altar. The sign burns by itself and is the only light
   with no lamp: it goes out with the second pair of fires. Stepping down onto the kerb round it shuts the toothed
   mouth behind you (`cabal:shut`), for forty seconds or until the rose bursts;
   once the priest is dead the kerb shuts nothing (`cabal:disarm`). The chant (59, E1M5's own). A voice, once, at the
   gallery: "Give me a sacrifice" (2367).
2. The priest (kDudeCultistBeast, E6M8) falls: `cabal:broken`. A cry of pain
   (2372), the earth shakes, the blood goes down the well and takes the horned
   thing with it, and the teeth draw back into the rim; the fires go out and smoke, a
   pair at a time (CASTLE23's relays, run backwards), the room's light with the
   second pair, and the chant with the first.
   Four of the audience get up; two stone beasts in their niches wake.
3. Three and a half seconds after, the rose bursts (a kWallGib on the wire: no
   shot breaks it). "I have awaited you" (2356). What was behind it comes
   through: a stone gargoyle, flesh ones for the easy skills.
4. Behind the glass, the Gullet, and a chained column of flesh with an eye in it
   (235): something beats (ambient 60) until the eye is shot or pushed, which is
   Blood's own idiom (E1M5, E6M6). A death cry (2380), the earth shakes, the flesh opens on the hoard. A secret.

The first design put the Gullet under the well and made its floor a lift. A
sector's wall has one neighbour, so a shaft cannot open on a passage below and
on the rim above along the same edge; and a throat behind a window that lights
the room is the better place.

## What is new for the library

* `bloodmap.arrangement`: shapes laid over one another, resolved into regions
  that meet exactly. Rings, stars, wedges, pits; every joint connected and
  painted by one table.
* `bloodmap.compositions` / `tools.mine_compositions`: what is arranged round
  what, in every map we hold.
* `tools.gallery` and `bloodmap.sight.sees`: many places on one sheet, each from
  where it can be seen.
* `bloodmap.posed` shows fires, apparitions (456), bursting glass and lights on a
  wire in their other state, so `mechanism_look` can show the whole rite.
* `PlanarLayout` placements may be `sunk`: half out of a floor on purpose.
* `SECTOR_SOUND_PROFILES`: `flesh_door` (E4M7), `great_stone` (E4M8).
* Engine facts: a torch's flame and a candle's glow follow `state`
  (view.cpp:2922-2938); type 456 does nothing but show and hide its sprite
  (triggers.cpp:393), used twice in all 1,600 maps, both in TUTORIUM.
