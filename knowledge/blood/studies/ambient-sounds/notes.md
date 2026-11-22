# Gravesend ambient sounds

## What I want to build

Give each place a sound with a campaign precedent. Set the sound's range and volume from the same kind of room.

## Where Blood built it

The census read all 43 maps from `bloodmap.corpus.campaign_maps()` and joined type-710 sprites to their sectors with `record_fields` and `record_extra`. Of 1,778 emitters, 1,582 start on stat 12 with `state=1` and `data_1 < data_2`. Room counts below use that active population. The place IDs group adjacent sectors through `tools.catalog.sector_places()`. Sprite and sector numbers are given separately.

| Context | Active emitters and room evidence | Gravesend ID and near / far / volume |
| --- | --- | --- |
| Town streets | E3M1's outdoor streets in place `E3M1:8` have 22 of 27 emitters on 8 `AMB8` (distant machinery throb) and five on 18 `AMB18` (louder wind). Nineteen of the 22 throb emitters are clustered in sector 175. Sprite 593 in the main street sector 8 has the wider envelope. | 8 at 150 / 350 / 50 |
| General interior | E1M1 has four active 32 `QAMB5` emitters in sectors 38, 54 and 122 with torch tile 570. E1M5 has seven 32s, including sectors with torches and braziers. E1M2 has six 2 `AMB2` emitters in enclosed rooms, five in the station building group `E1M2:92`. Five of the six use the same envelope. The catalogue hears a humming or violin sound. | 32 → 2 at 300 / 600 / 50 |
| Sewers | E3M3 has 21 dripping 30 `QAMB3` emitters out of 40 active. All 21 have 100 / 300 radii. Fourteen use volume 50 in the later channels and walkways, and seven use 70 in the earlier passages. | 30 at 100 / 300 / 50 |
| Church | Six of the seven active E1M5 emitters on 50 `TORCH` share their sector with a flame fixture (570 or 1701). The 1997 list calls it intermittent steam. The filename and placement tie it to local fire. The E1M5 temple seed sector 104 has none. E1M5's 59 `CHANT` appears once in the cult crypt at 394 and once in the flesh shrine at 414. E3M4's chapel place `E3M4:286` has one emitter, sprite 244 in sector 287, on 1 `AMB1` (haunted wind). | 50 → 1, one emitter in the nave at 400 / 800 / 40 |
| Crypt | E1M1's crypt place `E1M1:150` has one 17 `AMB17` low wind in sector 150 and one 32 fire in its torch sector 38. Two more 17s are in E1M5's subterranean place `E1M5:409`, sectors 238 and 253. | One local 17 at 200 / 500 / 50 |
| Fare rotor | Both E1M4 fare rotors have 21 `AMB21`; sprites 727 and 760 in sectors 151 and 314 have identical fields. The catalogue calls it a swinging hum. | 21 at 250 / 700 / 20 |
| Machine hall | E3M6 uses 20 `AMB20` (conveyor hum) 12 times, all with the same envelope, with five within the factory place `E3M6:413`. E1M4 has two more in factory place `E1M4:331`. E3M1's five 18s are all outdoors. Four of E1M5's five 18s are outdoors. | 18 → 20, three emitters in the pump machine hall at 200 / 400 / 50 |
| Mall | Five E4M9 emitters play 65 `MUZAK22` in five sectors of the shopping complex `E4M9:95`. This is all five campaign ambient uses and five of E4M9's 11 emitters. All share the same envelope. | 65 at 900 / 1500 / 50 |

## What makes it read as that

`asound.cpp` reads the near and far radii from `data_1` and `data_2`, the sound ID from `data_3`, and volume from `data_4`. `db.cpp:1281` sets `busy` to `state << 16` when the map loads, so starting emitters play at their configured volume. The engine loops the RAW sample for ambient playback regardless of the SFX header loop flag. Multiple emitters with the same ID contribute to the same ambient channel. Sound 65 supplies the mall's deliberately jaunty background music. Sound 30 gives the sewers a drip distinct from the two flowing-water outlets.

## Sizes

The most common active campaign envelope is 75 / 150 / 50 (202 emitters). The old city used 100 / 300 / 50 across contexts (30 active campaign emitters). Volume 50 is common, with quieter use of 20 at the fare rotors and 40 in the chapel. The engine scales XY distances by 16 and Z by 256 before applying these radii.

## What I will transcribe

Use the table above in `ambience.py`. The map uses invisible tile 2521 on stat 12, with the ambient state on. Use `python -m tools.sound_readback` for every named SFX slot, including both switch positions, moving-sector markers, pathway markers, gib objects, and implicit breakable glass. XSECTOR has zero direct SFX fields in this map format.

Four drain covers change from 370 `RECSCRAP` (Broken Record, copied from E4M9's vent grates) to 314 `RENMETAL` (Opening Steel Door). The census finds 314 on 46 instances of tile 201 metal grates, starting with E3M4 sprite 304, and on three campaign tile 218 grates. The matching sample fits the metal covers' break event. The remaining gib sounds have matching prop precedents. The catalogue calls 312 `SPLNTWOD` Scratched Record, but its filename and the stool exemplar DWE3M1 sprite 539 both support the existing wooden break. The crypt plaques' 502 comes from E1M1 sprite 185, and the 315 `SHRED1` and 2205 `PODDIE3` fields occur on the same breakable prop tiles in the campaign.

The three Caleb lines use invisible type 711 and separate one-shot causes. E3M1 relay 78 sends 4509 to sprite 757 after half a second at level start. E2M8 mother 73 sends its death through relays to sprite 144 for 4537. E1M3 uses 3034 for the end of the train and gives another line to sector 320's one-shot entry trigger. Gravesend combines those two train precedents where the Ghost Station track reaches its brick end. The triggered tunnel and its track share a single portal segment after lighting, where they previously had a collinear split. The opening has the same endpoints and height.

## What I will not do, and why

The existing pours use 56 `GRGLNG`. The catalogue describes underwater swimming, and E3M3 places two of the six campaign emitters in receiving pools above the surface, in sectors 174 and 247 with no underwater flag. Both Gravesend pours follow that water precedent. Keep the checked sector-motion sounds and switch cues.

## What I still do not know

These are compiled-map and engine-source checks. Live mix levels, speech timing and perceived sound bleed across adjoining rooms need listening in the owner's playthrough. The study scaffold could not render its seed because the worktree lacks `xmapedit-observe.exe`.
