# Self-destructing briefing recorder

The owner identified the apparent workbench as the **self-destructible tape
player**. It is retained as a Blood-era cabinet recording device. The original
Duke map and baseline Blood map remain intact.

## Source trace

`inspect_briefing.py` records source identities and native read-back against
hashes in `reports/briefing-mechanism.json`. Two original Duke reference views
are under `evidence/duke-source/briefing/source/`; those static views do not execute the sequence.

- Wall **2318**, on sector 405's raised device, is DOORTILE23 (4391), lotag
  **8000**, hitag **327**. EDuke32 `sector.cpp` includes this art in
  `CheckDoorTile`; `P_ActivateSwitch` operates the lotag's MasterSwitches and
  plays the hitag sound. DEFS.CON names 327 DESTRUCT; USER.CON uses
  `detruct2.voc`.
- MasterSwitch sprite **119**, sector 390, listens on 8000 and counts its
  hitag **80** down at 30 Hz, about 2.667 seconds. `actors.cpp` then arms the
  SEENINE in its sector. SEENINE shares arming by hitag **8002**.
- Explosives **114/115/116** have fuses **75/50/25**, counted down by three
  per 30 Hz tick. DETONATE starts the matching SE13 effectors
  **117/118/120**, sectors **390/405/403**.
- The converted map retained three exploders and three Z-motion sectors
  on two receiver channels but had **no sender on either channel**. The
  original tagged door-art control face was lost. This is a converter
  compatibility follow-up: tagged Use surfaces can be controls even when
  their art is outside a small switch whitelist. No conversion was rerun here.

## Native repair, passes 06/07

`briefing.py` declares three wires through `wiring.Circuit`. It reads existing
receiver channels from live records and allocates the missing Use channel
around occupied channels. Numbers are not typed into the declaration.

Using wall 2318 once turns on two hidden plain-sprite relays. Each has rest
state 0, a wait and **Off-only** reporting. NBlood `triggers.cpp`'s default
`OperateSprite` calls `SetSpriteState`; its automatic return posts Off after
`waitTime`, then sends the declared On command. This is a native delay.

- At **2.7 s**, one relay arms the retained exploders. Their converted
  **0.8/0.6/0.3 s** fuses remain unchanged.
- At **3.0 s**, the other starts the retained collapse. Final floors are
  390 → **3072**, 403/405 → **4608**, their existing on endpoints and scaled
  authored Duke heights. Travel parameters were not replaced.
- Stationary desk portion 404 receives one flat ledger. No decoration was
  attached to a moving fragment. The retained device face wears radio-cabinet
  art 2546; wood 34 and drawer fronts 36 distinguish desk and device. The
  original overhead wedge becomes a fluorescent fixture (2290).

Timing is rounded to Blood tenths, preserving the broad sequence with less
than a tenth of a second's rounding per stage. Original speech and exact
intermediate Duke motion are not reproduced. No unrelated Blood voice was
substituted. A suitable briefing recording remains open.

Blood references remain E6M1:79's work furniture and E3M4:153's counter framing.
Radio art 2546 was inspected before use; it is a visual adaptation of the
recording device, not an assertion that Duke's original was a radio.

## Verification and limits

Circuit read-back agrees for all three wires. Same-pose rest/collapsed views
show the recorder disappearing and fragments lowering to their retained
endpoints. Three synthetic regression tests cover reachable listeners,
retained fuses, one-shot Use, Off-only delay relays, posed endpoints and refusal
of mismatched receiver channels.

The native observer sees control wall 2318 from `use-position`. This establishes
visibility; actual Use hit scanning, timers, damage, sound and speech need the
owner's playthrough. The collapsed view is a posed endpoint without explosion
animation, smoke, generated debris or a scorched-material pass. Those effects
were not fabricated into evidence. Neighbouring interiors still need work.


Pass 08 subsequently corrects the inherited SE13 travel duration from its
source velocity. This deliberately changes the old fixed 0.8-second motor
time while retaining endpoints, fuses and the 2.7/3.0-second declared delays.
See the converter mechanism audit; the earlier notes describe passes 06/07.
