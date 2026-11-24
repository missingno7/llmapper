# Supplies, keys, gates and secrets: how shipped Blood maps hand them out

For an agent that must place them. Figures: `knowledge/blood/design/supplies.json`
(43 campaign maps, 31 Death Wish maps, read apart). Everything is single player,
difficulty 2, after the engine's lockout bits. Sensor `bloodmap/supplies.py`.

```bash
python -m tools.mine_supplies show DWE1M6 --items     # any name or .MAP path
python -m tools.mine_supplies where "tesla cannon"
python -m tools.mine_supplies keys --wakes            # or --glimpsed, --carried
python -m tools.mine_supplies                         # rewrite supplies.json, 30 s
```

Words. **way**: distance walked at least to stand there, over the exit's
(1.0 = the exit). **foes before**: share of the map's foe health that lies
nearer to the start than the thing; steadier than `way`, use it first.
**C** campaign, **DW** Death Wish. Three figures: lower quartile, median,
upper quartile. `way` figures count only maps whose walk is trusted (32 C, 21
DW). 1 m = 602 units.

## Rules of thumb

### 1. What is in the open, and in what order

Foes met before the FIRST one that is not in a secret:

| supply | C maps | C foes before | C in secrets | DW maps | DW foes before | DW in secrets |
| --- | --- | --- | --- | --- | --- | --- |
| sawed-off | 42/43 | .01 **.12** .33 | 8% | 31/31 | 0 **.03** .05 | 1% |
| TNT box | 41 | .02 **.07** .18 | 6% | 29 | .04 **.21** .39 | 3% |
| tommy gun | 34 | .04 **.14** .52 | 13% | 26 | .07 **.17** .33 | 2% |
| spray can | 32 | .07 **.18** .34 | 5% | 27 | .10 **.30** .73 | 13% |
| tesla cannon | 22 | .04 **.24** .38 | 14% | 25 | .30 **.47** .75 | 26% |
| remote TNT | 31 | .16 **.28** .55 | 3% | 29 | .02 **.06** .28 | 19% |
| napalm launcher | 31 | .25 **.38** .63 | 13% | 24 | .60 **.64** .70 | **66%** |
| proximity TNT | 28 | .25 **.42** .59 | 14% | 27 | .07 **.28** .47 | 9% |
| life leech | 11 | .17 **.35** .56 | 36% | 17 | one case, .97 | **82%** |
| voodoo doll | 30 | .16 **.31** .48 | 27% | 13 | .53 **.81** .83 | 54% |
| guns akimbo | 33 | .14 **.32** .62 | 41% | 17 | .35 **.57** .66 | 4% |

* Order of the first finds, by mean rank: C sawed-off 2.0, tesla 2.4, tommy
  2.8, flare pistol 3.0, napalm 3.2; DW sawed-off 1.3, flare pistol 2.3, tommy
  2.5, tesla 3.4, napalm 4.7. Campaign maps inherit the guns of the map before,
  so for a level that starts with a pitchfork **take Death Wish's order** and
  the openers': sawed-off in the first metres (E2M1 sprite 263 at way 0.00,
  DWE2M1 1030 at 0.00, DWE1M1 82 at 0.01), or the first shotgun cultist (E1M1).
* Two sawed-offs a map (C 2 2 2; DW 1 3 4.5). One or two tommy guns. ONE of each
  big gun, and it is one per map in both populations (1 1 1).
* By 10% of the foe health: one weapon kind. By 25%: two. By half: three (both).
* Keep the four big guns (tesla, napalm, leech, voodoo) after a third of the
  fighting in the open, earlier only in a secret.

### 2. What is in secrets

* Share of items in secrets by tier (1 common .. 4 changes the fight):
  C 5% / 9% / 12% / **45%**; DW 12% / 13% / 41% / **54%**.
* Found ONLY in secrets, where a map has one at all: death mask 8/8 C;
  reflective shots 9/9 DW; cloak 13/16 C, 9/10 DW; super armor 17/29, 9/11;
  life seed 21/40, 19/21; beast vision 7/12; guns akimbo 13/33 C, 4/17 DW;
  napalm 4/31 C, **17/24 DW**; life leech 4/11, **14/17**; body armor 1/33 C,
  **18/20 DW**; doctor's bag 14/41 C.
* Never in secrets only: sawed-off (0/42 C, 2/31 DW), life essence, box of shells.
* Secrets per map: C 3 **5** 6.5; DW 5 **6** 7. Super secrets 8 in 43, 2 in 31.
* Best reward is tier 4 in 116 of 236 (C) and 92 of 171 (DW); tier 3 in 40 and
  30. One item each (1 1 2), DW up to three (1 1 3). A super secret is a hoard:
  E1M6 sector 506 holds ten, DWE1M1 sector 847 eight.
* How they are kept (our categories, both): a place nobody opens, out of the way
  26-30%; a jump or climb 27% C, 21% DW; a door or panel one pushes 12%, 10%; a
  pushed wall 5%, 4%; a switch 5%, 9%; a switch or object that credits itself
  6%, 5%; a crack 4%, 2%; water 7%, 11%. **Half need no mechanism, only a look
  round a corner, up or under water.** A switch pays best (tier 3-4 in 11 of 12
  C, 12 of 15 DW), a crack worst (5 of 10 C).
* Credit is given on entering the sector (157 of 236; 102 of 171) or on taking
  the item itself (48; 61). The pickup form needs no sector of its own.
* Guards: 46% C and 63% DW have none within 4,096; 15% have one INSIDE. A secret
  is a rest, not a fight.
* Where: way .41 **.64** .86 (C), .37 **.57** .88 (DW). Not at the start.

### 3. The budget

| per map | C | DW |
| --- | --- | --- |
| foes | 54 **72** 100 | 74 **89** 146 (of them 17 **30** 45 spawn markers) |
| foe health | 2,511 **3,623** 5,131 | 3,463 **4,490** 6,360 |
| ammo damage / foe health | 5.8 **7.0** 10.0 | 3.8 **4.9** 6.4 |
| the same outside secrets | 5.0 **6.8** 9.1 | 3.2 **3.8** 5.4 |
| with what cultists drop | 6.6 **7.9** 10.9 | 4.3 **5.8** 7.2 |
| health per 100 foe health | 11.9 **14.6** 21.3 | 4.0 **5.0** 7.1 |
| armor per 100 foe health | 16 **20** 37 | 4.9 **8.5** 16 |
| health in secrets / damage in secrets | 24% / 8% | 31% / 16% |
| length of the way (m), foes per 100 m | 91 **169** 233, 43 | 217 **388** 568, 25 |

* `damage` is nominal, one round one target (shell 64, bullet 12, flare 85, TNT
  150, tesla 20, napalm 150; `DAMAGE_PER_ROUND`). Compare maps with it; it is
  not what a player deals.
* Pistol-start maps: E1M1 **2.0** outside secrets (6.7 with), E2M1 8.0, E4M1
  8.8, E6M1 6.4, DWE1M1 3.8, DWE2M1 2.8, DWE3M1 3.6. Under about 3 is DW-hard.
* By ammo: shells 24-27%, bullets 18-19%, flares 11-14%, TNT 11-12%, tesla 10%,
  napalm 8-10%, spray 4-5%, remote and proximity 3% C, 9% DW.
* **Supply runs ahead of the fight.** When 10% of the foe health has been met, the
  ammo passed is 9.1 (C) / 6.7 (DW) per point met; at 25% 7.1 / 5.5; at half 7.6
  / 5.6. Along the way C lays 31% of ammo damage in the first 0.4 against 23% of
  foe health; DW 36% against 29%. It never falls behind after.
* Health stays scarce: by 25% of the foes 80 points C, 20 DW; by half 200 and 80.
* **Health is carried.** 76% of campaign health pickups and 75% of DW's are life
  essences in a dude's `drop_item` (109), a dude in six (15.5% C, 17.8% DW
  carry something). Loose ones are the bag, the seed, the pouch. DW carries guns
  so as well: 48% of its weapons and 18% of its ammo are drops (sawed-off on a
  shotgun cultist, remote TNT on a TNT cultist, shells on anyone). The campaign
  never does that with weapons.
* A finding place of ammo or a weapon comes every 0.9 **2.4** 6.9 m of way (C),
  1.4 **3.8** 13 (DW); 24 **32** 40 places a map (C), 18 **27** 34 (DW).

### 4. Where a supply stands

* Against the fight, by walking distance to the nearest foe: ammo is at it
  (under 3,072 = 5 m) 49%, beside (under 8,192 = 14 m) 35%, between 15-17%, the
  same in C and DW. Weapons 47/35/18 C, 41/31/28 DW. Armor and powerups stand
  off in DW: at 17-22%, between 35-40%.
* 63-68% of ammo lies past or level with its nearest foe on the way: the pickup
  is what you reach after the shot, not before it.
* On: the floor 85-88% C (weapons 64%, ammo 75% DW); DW puts a weapon on
  furniture 15%, on a sprite (table, crate, body) 11%. Niches take powerups
  (27% C, 18% DW), keys (9%, 15%) and health (11%, 16%).
* To the nearest wall or step: ammo 256 **284** 512, weapons 453 **621** 1,042.
  A weapon stands out in the room (a body and a half from the wall); ammo lies
  along the wall.
* By a corpse: DW 23% of weapons, 7% of ammo; campaign under 1%.
* Company within 1,024: C ammo alone 38%, pair 32%, three or more 31%; DW alone
  16%, **three or more 61%**. Two of the same 32%/31%, three or more of the same
  18%/39%. Commonest: two spray cans, two boxes of flares, two tesla charges,
  two proximity, two gasoline cans, two TNT boxes (DW 26), three or four remote
  TNT, gun + its ammo (box of shells + sawed-off 7, tesla + two charges 8, drum
  + tommy 6). A gun has its own ammo beside it in 20% C, 32% DW.
* Weapons alone 70% C, 53% DW. Armor alone 79%.

### 5. Keys and locks

* Per map: C 0 keys 8 maps, 1 9, 2 10, 3 6, 4 7, 5-6 3; **DW 5 keys is the mode
  (8 maps), 4 in 6**. First colour mostly skull, then eye or fire or moon.
* One lock a key (65 of 91; 81 of 109), two in a fifth. A lock works a rising
  door 44/30 sliding/28 swinging/7 lift (C); 42/35/16/24 and the exit 8 (DW). A
  door for the body of the map; DW also puts the key on a SWITCH beside a lift.
* nth key at way: C .48 .54 .73 .79; DW .47 .60 .69 .82 .98 (medians). The first
  key comes at half the shortest way because the way is short without it.
* **The lock is met before the key in 64% (C) and 75% (DW)** of the trusted keys.
  Lock to key is 17 **30** 61 m more of walking (C), 29 **53** 145 (DW); key back
  to lock 28 **43** 63 and 32 **59** 87 m. In a third of them the way back is
  under 0.7 of the way out: a drop, a lift or a door that opens from inside.
* Key visible from well before it can be had (3D line, at rest): 16% C, 14% DW.
* Standing: floor 53% / 50%, on a ledge, shelf or raised sector 23% / 17%, niche
  8% / 14%, dropped by a dude 16% / 9% (always in the place the dude guards).
  Never in a secret (C 0, DW 2 of 109).
* Guards within 4,096: C 1 **2** 4 (19% none), DW 0 **1** 3 (39% none) because
  DW **springs the guard on pickup: 64% of its keys send something, 54% wake or
  spawn dudes (five at the median; spawn markers on the key's channel), 8% open a
  way. C 37% / 20% / 9%.** The form is `trigger_pickup`, `trigger_once`,
  `command` 1 on the key, spawn markers or ambush dudes listening.
* Ammo or health lies within 4,096 of the key in 64% C, 51% DW. Feed the trap.

## Examples worth imitating

1. **DWE1M1 sectors 61 and 64** (way 0.01): sawed-off sprite 82, beast vision 83
   on a raised sector, shells 84 by them; no foe within 13,800 (23 m). Armed
   before the level starts.
2. **DWE1M1 sectors 69 and 70** (0.09): an arsenal, seven together: on a ledge
   sawed-off 96, flare pistol 95, TNT boxes 94 and 1699; three proximity bombs
   97-99 on the floor. Still 0% of the foes met.
3. **DWE1M2 sectors 52 and 54** (0.07 and 0.10): tommy gun 472 alone, then two
   drums 478 and 479 by a corpse at the first fight.
4. **DWE1M4**, a dry start: no gun until sawed-off 525 at 0.31, 4% of foes met
   with the fork; the first secret is under water (sector 397, basic armor); then
   a chest of six at 0.43 (sectors 160-166: tommy 468, drum 204, flares 487 and
   469, shells 200, bag 199). Hunger, then plenty, just before the first lock.
5. **DWE1M4 eye key 510** (sector 416, raised, 3 guards, 0.55): pickup sends
   channel 109 and five more appear; its door, sector 438, was pushed in vain at
   0.43, 12% of the way earlier; 42,000 units back.
6. **DWE1M6, a hub**: three keyed slides side by side at 0.30-0.33 (sectors 325
   eye, 324 spider, 697 dagger), keys at 0.35, 0.42, 0.62 each behind the door
   before it, each trap bigger (4, 5, 5 and six guards). Areas by keys held 273,
   65, 31, 125, 177 sectors. The clearest direction in either population.
7. **DWE1M9, a hub of switches**: sprites 1399, 1401, 1403, 1405 (spider, dagger,
   fire, eye) at 0.154-0.162; keys come back to one place from four parts.
8. **DWE1M6 eye key 393 and DWE1M3 skull key 130**: seen (from sector 267 and
   from sector 69) with 28,000 and 17,000 units still to walk.
9. **E4M4 moon key 236** (sector 64, 0.85): pickup wakes 18. **E3M8 skull 92**
   (sector 249, a tomb top): stepping into its sector, not the key, wakes six.
10. **E1M1**: both keys are dropped by shotgun cultists (544, 546); the skull
    gate (leaf sectors 50 and 51) is met first as a shut gate; eleven small
    secrets (flares, armor) and the napalm launcher as the super secret (sector
    154). 70% of the map's ammo damage is in secrets: the richest example of
    "better weapons hidden".
11. **E2M1**: sawed-off 263 and shells 264 at the feet, tommy gun 331 at 0.13
    with no foe within 15,000; four keys inside 0.26-0.47, locks at 0.40-0.42.
12. **DWE1M1 sector 847**, behind the moon key's door: a super secret that is a
    key's whole reward (napalm, two tesla charges, seed, two armors).
13. **DWE1M4 sector 342**: tesla cannon 408 behind switch sprite 233, way 0.42,
    the earliest big gun there, for who looks.

What the first five minutes (way 0 to about 0.15) of DWE1M1-4 give: DWE1M1 two
sawed-offs, two flare pistols, five explosive pickups and 46 shells, nobody to shoot; DWE1M2 a
tommy gun and 200 rounds with the first three fights; DWE1M3 nothing till a
tommy gun at 0.29 (order not trusted); DWE1M4 nothing at all. Either arm the
player wholly before the first fight, or let him earn one gun; never drip.

## How sure, and what is not

Verified:
* Foes: "enemies by difficulty" on the wiki equal our count at difficulty 2
  (rats, bats and eels left out) in E1M1 18, E1M2 64, E3M1 55, E3M2 86, E4M1 29,
  E4M3 69, E6M1 49, and within 5% to 20% in E1M3, E1M4, E2M1, E2M3, E3M3, E4M2, E6M2.
* Secrets: our count equals the wiki's in 34 of 43; 201 of the 234 rewards the
  wiki names (86%) are in the secrets we read. E1M1 all thirteen, E3M3 all.
* Keys: 84 of 91 campaign keys walked to. Order of pairs against the walkthrough
  text, hand-checked for "grab" and not "door": 43 of 56 agree (77%); two more
  (E2M3, E6M1) are the wiki text's order of first mention, where the walkthrough
  itself agrees with us. `keys_in_route_order` in levels.json counts a key DOOR
  mentioned first as a key; do not use it as an order.
* Records of a dozen of the examples read back (`catalog record`).

Unreliable:
* **`way` is a critical path** and 21 maps read leaky or stuck (list below):
  shorter ways exist for our reader than for a body, so first finds read LATE
  and the last bin ("off past the exit") is fat: 25% of C foes, 10% of DW.
* **`area` (keys needed) holds only where `gates_anything`/`gates` is true**: 64%
  of C and 66% of DW trusted keys. The rest have a way round we believe and a
  body may not (E3M3's ledge needs jump boots; leaps over pits are a 3,000 unit
  guess; blocking railing sprites are not read).
* Jumps: the sum gives 19,600, the bot measured 15,052, shipped ways rise 22,528.
  Ways "taken on trust" are counted (`rescued`) and named in `Walk.believed`.
* A ride or bridge over a pit is read only as a leaf, link, floor sprite or turning sector.
* `fight` counts dudes where placed, asleep or not, and spawn markers; "on pickup" also
  counts what entering the key's own (small) sector sets off.
* 25 of 236 C secrets and 5 of 171 DW hold nothing we read. `stands`: tables and crates of face or wall sprites are not seen; a floor
  reading may be a shelf. Corpses are a hand list of tiles.
* E3M3's eye key, E4M6's skull, E3M5's skull, E2M2's dagger, E1M6's spider keys
  are not reached (the spinning holder and the like).
* Not trusted (no order counted): E1M3 E1M5 E1M7 E2M2 E2M3 E2M7 E2M9 E3M1 E3M6
  E4M8 E6M7; DWE1M10 DWE1M3 DWE1M5 DWE2M3 DWE2M10 DWE3M6 DWE3M7 DWE3M8 DWE3M9
  DWE3M10. Counts, budget, stands and secrets still count for them.

Faults found in readers that were not ours to mend:
* `conditional.rest_state` takes a door drawn open with `state` 0 for open at
  rest; `trInit` moves it to OFF (triggers.cpp:2250). E6M1 sectors 112, 114 and
  121 are keyed doors drawn open. `supplies.Walk._edge_open` reads the state.
* `effects.leaf_blocks` takes the saved pose of a slide or rotate for OFF; it is
  ON (triggers.cpp:2231), which is why 13 of E1M1's 13 swept doors gate nothing.
  `supplies.swept_off_pose` has the load pose; E1M1's skull gate reads shut.
* `available_actions` never offers a door that has a wire AND a push face.
