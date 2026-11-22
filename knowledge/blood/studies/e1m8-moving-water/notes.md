# Moving water in E1M8

## What I want to build

Make Gravesend's shallow currents and inlets read as moving water, and furnish
its E3M3 towpaths under the existing vaults.

## Where Blood built it

The moving 1120 floors in E1M8 are sectors 142-242, 248 and 389: 103 of 110
uses of this tile. Their palette is always 0. All 103 have XSECTOR
`pan_floor=1`, `pan_always=1`, and `drag=1`. Angles below are the stored
Build angles, with east 0, south 512, west 1024, north 1536. Stat bit 64 makes
angle 0 follow the first wall's local frame. From catalog records and the
campaign map's records:

| Place and records | Surface, light and current | Sides and other motion |
| --- | --- | --- |
| E1M8 River Ride, sectors 142-156, 389 | 1120/0, north at 60 (142-148), then 255 (149-156). 389 is west at 60. Most of the first run has floor and ceiling shade 61, wave 5 amplitude -48, frequencies 7 or 30. 389 uses 28/36 and no wave. | Ordinary walls 230/487, with flesh and machinery in 389 (230-235 and 22), palette 0. These records have no moving water on the corridor sides. |
| E1M8 bends and chutes, sectors 157-241 | 1120/0. Most use first-wall-relative panning, typically 255 at local angle 0. Sections 165-180 step through 100, 125, 150, 175, 200, 225 and 255. 213/214 switch to absolute 1280/1536 at speed 80. 223-225 use relative angle 1024 at 140/225/180. 157 is shade 61/61 with wave 5, -48, frequency 20. 213 and 214 are 28/36 without a wave. | Wall 230 with 231 panels and 487 braces, palette 0. Animated blood spray 775 in sprites 612-614 and 647-648 hangs 7,168-13,330 units above the water. These are type-0 wall sprites, with no moving or floating object behavior. Mines, spikes and chains are attachment or hazard sprites. |
| E1M8 intake and lower pool, 242/243 and 248-251 | Sector 242 pans south at 30, floor shade 28, ceiling 36. Sector 248 pans at 75 with relative alignment. The connected lower pool's 249 and 251 both use still 1120/0, floor shade 28 and 36. | Falls 1309 (243 facing 242) and 1361 (249 facing 251) use 1120/0, shade 28, repeats 16/8, always-on Y pan -85. Their neighbours wear flesh 232. Reverse wall 1386 uses 232/0, shade 34, Y pan -128. Farther away, flesh 232 moves sideways at +5 (walls 52-54) or -4 (1392/1396/1404 and 2067/2068). Pipe sprites 327-330 use animated 977/4 at the water, shade -8 and repeats 64/64. Sprites 566-568 in 243 are separate blood drip generators. |
| E3M6 factory, sectors 74, 262, 318 and 348 | Blue tile 1005/0 on the floor, always-on and first-wall-relative. Speed 40 at 74/262, 255 at 318, 100 at 348, all with drag. Floor/ceiling shades 39/36 in 74 and 32/39 in 318. Depth 2 in 0/79, depth 3 in 21. | Stationary concrete and stone 369/411. Wall 450 between 74 and 262 is 1005/0 at shade 41, Y pan -75. Walls 2424/2437 pan -120. Sprites 157-159 and 244 put translucent, animated 1037 at the waterline beside the falls (shade -33 or -23). |
| E4M3 sluice, sectors 213, 219 and 220 | 1005/0 with always-on panning and drag, speed 129, stored angles 512, 512 and 256. Floor/ceiling shade 45/53 at 219 and 53/53 at 213. All three have depth 0 and underwater clear. | Stone 281/421/379 around 1005. Walls 1480 and 1506 carry always-on Y pan -120, shade 52 and 47. No foam in this sluice group. |

E1M8's sound records include running stream 13 at the chute (sprite 363,
range 250-600, volume 80) and at 242's fall (374, 75-300, volume 50). The ride
also uses underwater-sounding 37 (156 in 389 and 357-362 in 143-148,
75-300, volume 80). Sprite 563 adds heavy breathing 706 at 242. The
comparisons use running stream 13 (E3M6 sprite 256, 200-500/50; E4M3 sprite
217, 300-450/100) and water sound 12 (E3M6 sprite 270 and E4M3 sprite 235).

The 103 E1M8 current floors all have depth and underwater clear. The lower
pool is attached via a normal stack pair (sprites 280/281, group 20),
alongside the separate up-water/low-water pair (279/282, group 21) from
250 into flagged-underwater 245. The
other water pair (265/397, group 24) leads from 123 to 401, with the
underwater flag in 401-403 and kelp/bubbles sent by sprites such as 394.
The ride itself has no swim-layer marker, and the chosen E3M6 and E4M3
races also have underwater clear and no link markers. The E1M8 moving
sectors contain no 1037 foam and show no verified floating decoration.

## What makes it read as that

The 389 frames show a green floor ribbon between dark flesh courses and
uprights. The 251 frames show distinct falling strips meeting a continuous
pool. The steepest ride poses come out mostly black in the observer. The
readable views in `work/water/e1m8-reference` at 213 and 242 show the green
surface and the close, dark corridor walls. E3M6's 74 frame shows a
narrow bright line where each blue sheet meets the pool. E4M3's 219 frame
has a single tall blue sheet against solid stone. The frames show layout
and colour. Motion, drag and sound are read from records.

## Sizes

E1M8:157 is roughly 2,048 by 826 in plan with 32,768 base clearance.
The 242 chute is 2,048 by 8,192 with 65,536 clearance. E3M6 wall 450
has a 45,056-unit drop between 262 and 74. E4M3:219 is approximately
1,536 by 2,560, 131,072 high. E3M3's walk/channel/walk section is
512/1,024/512. The original wall drip in E3M3 sprite 82 is 20,480 units
(1.21 bodies) over the floor. The pair on the example towpath itself,
270/271 in 117/118, is 8,448 units above the floor; shade -8, repeat 64,
translucent. Moss 793 has palette 9 and sprite 2 is 16,384 above the
floor. The owner names 795 "flat round light." E3M3 sprites 77 and 278
sit exactly at a flat ceiling, at repeats 32/48, cstat 160 and shade -128.

## What I will transcribe

Gravesend already has animated 1120, floor panning, E3M3's shade wave,
drag at the manhole landings and Stockyard Drain, and vertical falls at
the Stockyard and Settling Hall. Give the west end of Graves Brook a raised
culvert feeder with a 1120/-85 drop as in E1M8 wall 1309. Put E3M6-style
1037 foam on its splash line and on the existing Settling Hall fall's foot.
Double the outfall's travel speed from 12 to 24, clearing drag there as on
E3M3's fast sector 134 (32, no drag). Fit E3M3 drips and moss to the true
ceiling beneath the vault. Small round ceiling lamps sit on the flat
channel crown, where the whole light has a seat.

## What I will not do, and why

Keep masonry fixed along the runs because the reference maps concentrate
water on floors and drop faces. Keep the circulation walks shallow and reserve
strong player drag for the already established landings and blood race.
The ride's strong light pulses, flesh and animated blood spray belong to its
attraction. The existing sewer ambience and waterfall sound already give
the sound layer its own treatment.

## What I still do not know

How readable the speed change is in motion at player height, and how the
brook's new intake feels when arriving from the manhole. Both need a
walk in Blood. The 1037 foam is blue in the campaign. Check how its
colour reads against Gravesend's green water at the same time.
