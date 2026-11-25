# How Gravesend is played

The owner, 2026-11-24: "I would make this level the way that you will be
collecting keys around the city and will need all of them to unlock station to
get to the exit. So instead of linear order of keys you just pick all of them in
any order and then use them at the end ... We should have some plan on how the
level can be completed, where are pickups, enemies, etc. to have some actuall
meaningful gameplay."

This page is the intent. What the built map really holds (every foe, supply,
key, the order the reader finishes it in) is measured from the MAP by
`python projects/blood-city/level/playthrough.py` into
[../reports/gameplay.md](../reports/gameplay.md). The rows themselves are
`level/gameplay.py`. The numbers behind both are
`knowledge/blood/studies/supplies/notes.md`.

## The shape: one lock, six keys, any order

The quay is the start, and the avenue runs straight from it to **Gravesend
Station** at the far end, its two arches shut by roll-up gates behind four columns.
On the pier between them hang six key signs in a row, a switch
under each. Nothing else in the level says what to do, so it is said once, in the
open, at the end of the first street.

Each switch takes its key once; the sixth raises both gates (DWE1M9's lock:
four keyed switches into one counting switch). Caleb: "Looks like my train's come
in." The guard behind the gates wakes. Up the booking hall's stairs, over the platform,
up to the signal box: its lever sets the line clear. A whistle far off, the ground shakes,
the tunnel's gate rises and what was in the tunnel comes up the platform
(`gameplay.LAST`); six seconds after, the carriage opens half way down it, and the way
out is the emblem at its forward end (`station-design.md`).

| key | where | what stands in the way | what taking it does |
|---|---|---|---|
| **skull** | on the lid of the sarcophagus in St Gallow's crypt | the church's dead and cultists, the slab (the skull it carries sends it) | five of the buried rise out of the crypt's earth |
| **eye** | on a plinth on the arcade's landing, in sight from its street door and across a fallen gallery from it (it also opens the service passage behind it) | the sunk court: the escalator down, the dead in it, the fallen span up | Miguel's shutter goes up and two come out of the gun shop on the gallery opposite, one stands at the street door, one gets up in the draper's |
| **flame** | on the belt in the pump station's machine hall, lit under the hood between the two presses; seen first from the deck the gallery comes out on | the presses slam and the belt carries you into them; the console lever stops both, the presses shut | one rises out of the settling basin, a butcher stands on the deck across the way out, one comes from the south bay |
| **moon** | on the Aldermack's trap, in the light | the house's gunmen; the show | the curtain drops, the light goes, the wings open on the watchers (as it did for the armour) |
| **spider** | in the Weaver's Cellars, on a stone in the north nest, in the one light there | the great web across the nest, the brood, and its mother over the pit | five more spiders |
| **dagger** | the Cabal's chamber, in the throat behind the rose | the stone beast; the rose bursts only when it dies | phantoms between it and the way out |

Underground are the flame's neighbour, the spider and the dagger. The sewers are entered by the pump
station's spiral, or by blowing one of three manholes, or through the crypt's cracked wall: nothing
is a required order, and a player with dynamite has shorter ways.

## The Cabal's chamber: what is meant to happen

1. The toothed mouth in the settling hall's south quay, between fires, under the horned face. Two sentries.
2. The gallery: "Give me a sacrifice." Below, the burning sign, the celebrants facing the well, a horned thing in it,
   and over its head, against the rose, the back of the stone beast. Gunmen in two boxes over the gallery.
3. Stepping down to the kerb round the sign shuts the mouth behind you (forty seconds, or until it is over) and turns the beast.
4. The beast (a stone gargoyle) shrugs off bullets and blasts. The Tesla Cannon lies at the foot of the falls outside, in
   line with the outfall, with three charges; two more are in the chamber's niches.
5. It dies: a cry, the earth shakes, the blood starts down the well and the fires go out pair by pair. Four of the audience get up.
   - 1.2 s: the thing in the well bursts into stone and fire.
   - 1.3 to 2.8 s: fire climbs the hanged one's chain to the crown of the vault.
   - 3.1 to 3.5 s: five blasts run round the crown, and stone falls.
   - 4.6 s: Caleb: "Rest in pieces."
   - 5.8 s: the emptied well's bottom goes up.
   - 7 s: the rose bursts, what was behind it comes through, the beasts in the niches wake, and the mouth opens.
   None of the blasts can reach anybody standing in the room (`bloodmap.blasts.harmless`, and a test).
6. Behind the rose, lit: the dagger key. Past it the chained eye; shooting it opens the flesh on the hoard (a secret).

## The guns

| gun | where | open or secret |
|---|---|---|
| sawed-off | by the dead man at the foot of the avenue, in the first frame | open |
| flare pistol | the Demeter's hold; taking it brings three gill beasts up onto her deck | open |
| dynamite | the smugglers' locker behind the hold's panel | secret |
| tommy gun | the arcade's service passage, behind the eye's door | open, keyed |
| Tesla Cannon | between the fires at the foot of the falls, before the Cabal's mouth | open |
| voodoo doll | the sewer's stash, seen through bars; the wheel in the riser by the junction lifts them | secret |
| napalm launcher | the flooded room | secret |
| life leech | the Phantom Terminus's ride | behind the dials |
| guns akimbo, super armor | the Gullet | secret |
| death mask | the Rat King's shrine, its pipe stopped until the bloody hands on the bleeding floor are pushed | secret |
| body armor | the arcade's cache | secret |
| spirit armor | across the blood by the trolley | off the way; taking it wakes two gill beasts |

Ammunition lies in threes along a wall past the fight it is for; a foe in six carries a life essence; bags and pouches stand where a
fight has just been.

## The sewers

A place to be hunted in, not a place to clear: eight rats and four beasts in three hundred metres of corridor before 2026-11-25. Now the
stockyard branch has a fight of its own (the bleeding floor: a butcher, two axe zombies, rats, gill beasts below and in the sampling chamber),
the ring has something under its south channel and hands in its west leg, and the Cabal keeps a picket where the outfall goes down to the
settling hall. The rest is the Toshers' Den, off that hall: a light, a bag, shells, and a secret under a bed. Rows: `gameplay.SEWERS`, `gameplay.WAKES`.

## Under water

Three places are dived into (`level/underwater.py`, study `underwater`), every swim a breath there and back. **The settling basin** in
the machine hall is the top of a well: at its foot the pumps' wheel, two eels (one on the harder skills), a doctor's bag and a tesla
charge at the screen, and a pipe on to a pool in the junction, which is a second way between the works and the sewers. A diving suit
lies by the basin to say so. **The flooded branch**, the napalm launcher's secret, is barred now: it is looked into from the south
walk and reached from the tank in the cistern, through a crawl under the channel, past the drowned and an eel; stepping onto its bank
counts it. **The slip**, between the quay, the Demeter and the jetty, can be jumped into from any side and walked out of by a ramp;
under her keel a gill beast, and body armor on the box in her sunk boat. The rest of the sea stays shut.

## The meat market

A butcher behind the counter and the clerk (two on the harder skills) in the
gallery over the jar shelves. The lever up there raises the cold store's steel
door; two more butchers were shut in behind it, and the armor lies at its south
end. Taking that brings two dead off their hooks and a butcher in behind
(`market-design.md`).

## The streets

Before this pass nobody walked them. Twenty-one foes do now, in ones and twos, thinnest at the quay and thickest at the station's
front; seven of them only on the harder skills. Three lie in the churchyard's earth.

**Gallows Steps** (`level/gallows.py`), west of the well square, is the one place over them: a stair at the end of a blind alley to a
terrace two and a half bodies up, with the parish's gallows on it and nothing else. Whoever keeps it shoots down into the crossroads; whoever
takes it has the crossroads. No key is there, and nothing needs it.
