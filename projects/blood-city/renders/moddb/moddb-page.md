# Gravesend: the ModDB page

Version 0.1, 2026-11-25, against `release/GRAVESEND.MAP` (1732 sectors, 14892 walls, 3402 sprites; 166 foes on the middle difficulty, 8 co-op and 8 Bloodbath starts; the counts are `release/README.TXT`'s). `gravesend-logo.png` is a render of that MAP itself (`render/final.py`): the city cut at 1.9 plan units over the streets, every enemy and pickup hidden, nothing that lies under the streets shown; the key emblems stand round the ring in no relation to where the keys are. `gravesend-logo-noversion.png` is the same without "V0.1" (`VERSION` in `render/scene.py`); `gravesend-logo-1917.png` is the same view of the build before the release; `gravesend-logo-gallows.png` is the first logo.

## Summary

Gravesend is a huge single-level city for Blood. You come ashore on the quay under a burning sky, beside a travelling fair that should have left town long ago, and the only way out is the last train. The station is locked by six keys. Find them in any order: in the church crypt, the arcade, the Aldermack theatre, the pump station, the spiders' cellars and the Cabal's own chamber. Most of them wake something when you take them.

In between: open streets and shops, a meat market, a saloon, a ship in the harbour, a gallows over the crossroads, a sewer network, flooded passages, a ghost station and ten secrets. Five difficulties, with starts for co-op and Bloodbath.

Requires Blood with the Plasma Pak, and NBlood: the map is far beyond the original game's limits. This is an early access release, and feedback is welcome. Built with the help of AI agents, directed and playtested by a human.

## Description

**The last train leaves from Gravesend.**

Gravesend is one very large level for Blood: a whole harbour town under a burning sky, with its streets, its interiors and what lies beneath them joined into one map.

From the quay the avenue runs straight to Gravesend Station. Its gates are shut, and six emblems hang between them: skull, eye, flame, dagger, spider, moon. Where you go first is up to you.

**What is in it**

- Six keys in any order, each in a place of its own with its own trap, fight or puzzle
- The fair, St Gallow's church and crypt, the Aldermack theatre, a shopping arcade, the meat market, the saloon, RAT DOGS, the pump station, the harbour and the *Demeter*
- A city under the city: sewers, flooded passages, the Cabal's chamber and an abandoned station with a train still running
- Ten secrets, with the best weapons among them
- Scaled enemy counts on all five difficulties
- Starts for eight players in co-op and Bloodbath (not yet tested online)

**What you need**

- Blood with the Plasma Pak (One Unit Whole Blood includes it)
- NBlood. The map is past the limits of the original DOS game, and other ports have not been tested

**How to play**

1. Put `GRAVESEND.MAP` in your NBlood folder.
2. Start it with `nblood -map GRAVESEND`.

**How it was made**

Gravesend was built with AI agents writing the level as code, working from the original campaign's own maps, and directed, walked and corrected by a human over many rounds. It uses Blood's own textures, sprites and sounds. This is an early access release: please report anything broken, unfair or unreachable.
