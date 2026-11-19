# Edge venues: what could stand behind Gravesend's empty edge facades

Date: 2026-11-18. The question, from the owner: the buildings along the city's
outer edge are empty shells, and because they sit outside the city there is
almost unlimited room behind them. Train stations are covered by a separate
study and are not discussed here.

Method: lettering sprites (tiles 3808-3833) were read across the campaign and
curated maps to find named places (FEINMAN MEATS, FORTUNES, RAT DOGS,
GRUDGE FINANCE, HOSPITAL ...). Seven maps were toured with `tools.ideas tour`
(E3M2, E3M4, E1M4, E1M8, DWE1M7, E4M1, E4M3), with views of my own rendered
through `look.as_played` where the automatic poses missed the venue. E4M1 and E4M3
gave nothing venue-like and have no cards. Community maps named BANKJOB and
LIBRARY were planned and dumped: neither is the venue its name promises (a cave
run and an amateur box map), so they were dropped. Every size below is read from
sector fields. Anything marked "not verified" is inferred.

Units: 1,024 units = 1.74 m; a body is 1,060 units tall (16,960 z).

Ranked by how memorable a venue is for what it costs to build.

---

## 1. Freak-show sideshow front (small to medium)

**Card:** `E1M8-414-freak-show-sideshow-frontage-covered-in-`

Most of this venue is the facade, and the facade is the part the city already
has. A sideshow is a wall covered in big painted posters: SLOTH THE HAPPY
MUTANT, JO-JO THE IDIOT CIRCUS BOY, a HOUSE OF HORRORS board, a ticket window
with balloons over it, and wrought-iron fence panels and barrels along the
base. It is the one venue whose identity sits *on* the street wall, so it turns
the edge shell into a landmark before the player even goes in. Nothing in the
city resembles it. The theatre is a civic building with an auditorium, and this
is a cheap fairground front with a dark walk behind it.

- **Exemplar:** E1M8 s414 and s94 (the yard and its facade), ticket booth
  s415/s417/s418.
- **Footprint:** a frontage of 16,896 units (28.7 m) in the exemplar. For us,
  one facade bay of about 8,192 units (14 m) along the street and 6,144 units
  (10.5 m) of depth. That gives two or three rooms: a ticket lobby and a short
  dark "House of Horrors" walk.
- **What the player does:** reads the posters and shoots open the ticket
  booth's lock. Inside, a dark walk with something on show behind glass or bars
  wakes up. The ticket booth can hold a key.
- **Needs:** the facade tile 473 (quilted diamonds with a cornice band) and the
  poster sprites 932 (the SLOTH poster, which the owner has not named; ask) and
  981 (owner: the JO-JO poster). Fence panels 1060/1064 and cobwebs 1067-1069.
  No mechanism is required.
- **Cost:** small for the front alone, medium with the dark walk.

## 2. Lock-up ward: barred cells with a flame trap in each (small)

**Card:** `E3M4-391-lock-up-corridor-of-barred-cells-with-a-`

One low, dark corridor and three cells behind iron bars, each holding a
prisoner and a flame trap. You walk past people you cannot reach, and when the
traps fire they burn. That makes it the strongest single moment per square
metre on this list. Dressed as an asylum's secure ward or as a police station's
cells, it gives the city something it lacks: a place of confinement. The
church crypt is a burial room, and nobody is alive in it.

- **Exemplar:** E3M4 s391 (corridor), cells s340/s346/s348, trap corners
  s364/s366.
- **Footprint:** the corridor is 8,832 x 3,072 units (15.0 x 5.2 m) and
  1.93 bodies high. Each cell is about 1,280 x 2,048 (2.2 x 3.5 m) and
  1.63 bodies high. Behind the street facade we would add a front desk room of
  about 4,096 x 4,096. That makes 2 rooms plus the cells, with a frontage of
  about 5,000 units (8.5 m) and a depth of 9,000 units (15 m).
- **What the player does:** gets through the desk room, finds the cell-block
  key, and walks the corridor. Either a switch or the wrong step lights the
  traps, which is a scene the player watches rather than a fight. A cell can
  hold a secret through its broken grate (466).
- **Needs:** grate tile 465 as the masked bar wall, which the owner has named.
  Prisoners are type 245 (kDudeInnocent, tile 3798). The flame trap is type 452
  (tile 2183). What fires the traps in E3M4 is **not verified**: s365/s367 are
  type 600 sectors, so read them before transcribing. Do we have a trap
  (type 452) emitter in the project yet?
- **Cost:** small.

## 3. Bank with barred teller windows (medium)

**Card:** `E3M2-309-bank-hall-with-barred-teller-windows`

The city has a pawn shop and a saloon, and both have counters. A bank adds two
things to that: the counter is behind bars, and there is a vault, which every
player wants to open. The E3M2 hall reads at once. It has marble walls, a
wooden counter, deep barred teller niches with fretwork over the bars, NOTICE
papers behind them and cultist cashiers standing in them. It is a
self-contained heist objective at the edge of the city.

- **Exemplar:** E3M2 s309 (hall), teller niches s326/s327/s328, tellers' strip
  s408, desk strip s409.
- **Footprint:** the hall is 6,656 x 11,264 units (11.3 x 19.1 m) and
  3.86 bodies high, and the counter zone behind it is 2,560 units deep
  (4.4 m). For us that means a frontage of 6,656 (11.3 m) and a depth of about
  16,000 units (27 m), the vault included. That is 3 to 4 rooms: the hall, the
  staff strip, a manager's office and the vault.
- **What the player does:** fights cashiers who shoot through the bars, gets
  past the counter (staff door or a vault over it), and finds the manager's key
  or combination to open the vault. The vault holds the reward or the level's
  key.
- **Needs:** grate sprites 465/466 and paneling 84 (both named by the owner).
  The marble wall tile 123 is not named; ask the owner. The vault door has no
  exemplar: none was found near the E3M2 hall (searched 6,000 units east). A
  rotating door (type 617) or a lift-slab (type 600) would have to be designed.
  A study of a vault door should come first.
- **Cost:** medium.

## 4. Funeral parlour with a morgue under it (medium)

**Cards:** `E3M4-286-funeral-chapel-pews-facing-a-coffin`,
`E3M4-218-morgue-a-wall-of-body-drawers-and-slab-t`,
`E3M4-252-mortuary-disposal-room-with-a-striped-pr`

The church is public and its crypt is old stone. A funeral parlour is private
and recent. Its chapel of rest has pews facing a coffin between wreaths and
candle banks, and its basement is clinical: a whole wall of steel body
drawers, concrete slabs with corpses on them, and a white-tiled disposal room
with a hazard-striped spiked press. The drawer wall is the image a player will
remember. It is a single tile (311) repeated, so it is cheap.

- **Exemplars:** E3M4 s286+s287 (chapel), s218 (morgue), s252 (disposal room).
- **Footprint:** the chapel is 7,168 x 4,096 (12.2 x 7.0 m). Its exemplar is
  5.8 bodies tall; 3.4 bodies would do here. The morgue is 9,216 square
  (15.6 m) and 2.96 bodies high, though half that is enough. The disposal room
  is 5,120 square (8.7 m). For us that is a frontage of about 7,000 units
  (12 m) and a depth of 8,000 (14 m), with the morgue stacked under it. It
  takes 3 rooms plus a stair or lift.
- **What the player does:** approaches the coffin, which sets off the
  ambush or hides the key under its lid, then goes down to the morgue to search
  the slabs. An opened drawer is a secret or a jump scare. The press in the
  disposal room is a hazard to cross.
- **Needs:** drawer wall tile 311 and the single drawer sprite 325 (neither is
  named by the owner yet), slab concrete 272, and grimy tiles 296 and tiles 297
  (both named). Hazard stripes are tile 309. The press is a damage sector
  (type 618) and does not move in the exemplar. Making a drawer open would
  take a slide (type 616) and is not in the exemplar.
- **Cost:** medium. The project already stacks space (crypt under church), so
  this reuses that.

## 5. Fairground lot: carousel and shooting gallery (large)

**Cards:** `E1M4-321-carousel-a-rotating-platform-of-poles-an`,
`E1M4-69-fairground-shooting-gallery-booth`

This is the venue that uses the edge's "unlimited space" literally: an open-air
lot behind an entrance arch in the edge facade. It has a boardwalk midway with
booths and a carousel as its centrepiece. The carousel is one rotating sector
14.8 m across, with eight poles and winged riders that turn out to be live
gargoyles. The shooting gallery is a 3.9 m booth whose stepped shelves carry
jugs and glasses for the player to shoot. Nothing in the city moves like the
carousel, and nothing invites play like the gallery. The sideshow front (#1)
could be this lot's entrance, which would make the two one venue.

- **Exemplars:** E1M4 s321 (carousel, in yard s352), s66-s69 (gallery booth),
  s320 (midway).
- **Footprint:** a lot of about 20,000 x 16,000 units (34 x 27 m) behind a
  single arch about 2,048 wide. It is mostly outdoor, with 3 to 5 booths and a
  carousel.
- **What the player does:** shoots out the gallery's glassware for a prize on
  the top shelf, then throws the switch that starts the carousel, and the
  "decorative" riders come to life. A key riding on the platform has to be
  grabbed as it comes round.
- **Needs:** a rotating sector (type 617). The project has not built one at
  this size, so check that sprites riding on it rotate as the exemplar implies
  (rx 128 is **not verified**). Pole tile 213 and rider tile 1475 are not
  named. Glass 574 and jug 712 are named by the owner. The boardwalk floor is
  250, and the midway needs a parallax sky.
- **Cost:** large. The gallery alone is small and could stand as a single
  booth set into a street wall.

## 6. Hospital admissions lobby (medium)

**Card:** `E3M4-153-hospital-admissions-lobby`

A big, bright, civic room after a city of dark shops: a chequer floor, red
crosses, benches and potted plants, a planter with a tree, and signs that say
exactly where you are (+HOSPITAL+, HOSPITAL INFORMATION AND ADMISSION,
EAST WING). On its own it is only a hall. It ranks last because its value is
as the front door to #2 (a secure ward) or #4 (a morgue). As the shared
entrance for both, it is a good one.

- **Exemplar:** E3M4 s153.
- **Footprint:** the exemplar is 17,408 square (29.6 m) and 5.8 bodies high. For
  us, about 10,000 x 9,000 units (17 x 15 m) at 3.4 bodies: a frontage of
  10,000 and a depth of 9,000, plus the corridor that leads to the ward.
  That makes 1 hall and 1 corridor.
- **What the player does:** reads the signs, finds a key or a map at the
  reception desk, and takes the wing corridor. The hellhounds in the waiting
  area are the joke.
- **Needs:** sign sprites 151, 695 and 143 (read from their pictures; the owner
  has not named them), potted plant 1009, and hanging lamp 468 (named by the
  owner).
- **Cost:** medium, or small if it only fronts another venue.

---

## Also seen, not shortlisted

- **Open-plan office** (DWE1M7 s753, card
  `DWE1M7-753-open-plan-office-of-cubicles`). A grid ceiling over cubicles
  with partitions 1.33 bodies high gives good cover combat. It is cheap to
  build but does not feel like 1928 Blood.
- **Restaurant kitchen** (E3M2 s450). It has stoves, extractor hoods and a
  chequer floor, but the city already has a canteen.
- **Funhouse "SEEING IS BELIEVING"** (E1M4 s219). Its doorway is good, but the
  interior is a plain brick maze.
- **FEINMAN MEATS** (E3M2 s301). The lettering stands on a street wall and no
  meat-plant interior was found behind it.

## What got in the way

- The automatic tour poses often stand in a corner or face a pillar (E3M2
  s300, E3M4 s40). Each venue above needed its sector dump read, and some
  needed views of my own.
- `tools.ideas tour` only accepts campaign and curated maps, so community maps
  named after venues (BANKJOB, LIBRARY, HOSPITAL, MUSEUM1-4, ZOO, THEVAULT)
  have to be inspected by hand. The two I opened were not what their names
  promised.
- Many signature tiles have no owner name yet: 311 (drawer wall), 325, 932, 123,
  213, 1475, 151, 695 and 143. They belong on the owner's tile sheet before any
  of these is built.
