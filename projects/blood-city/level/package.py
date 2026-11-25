"""What is given out: GRAVESEND.MAP and README.TXT, and the archive that holds the two.

    python projects/blood-city/level/package.py        # from gravesend.MAP, after the build

The readme is the community's own form: XMAPEDIT's `TEMPLATE-MAPS.txt` (the headings Blood's
maps have carried since 1997), 72 columns, plain ASCII, DOS line ends. What it counts is
counted in the MAP, so it cannot fall behind it; what it says in words agrees with the ModDB
page (`renders/moddb/moddb-page.md`). Spoilers are last.
"""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
LEVEL = Path(__file__).resolve().parent
PLAYED, OUT = LEVEL / "gravesend.MAP", LEVEL.parent / "release"
VERSION, DATE, AUTHOR = "0.1", "25 November 2026", "missingno7"
MAP_NAME, README_NAME = "GRAVESEND.MAP", "README.TXT"
COLUMNS = 72
#: a secret is told to the level on this channel, with this command (E3M1's own)
SECRET = (2, 64)
INNOCENT = 245

TEXT = r"""
======================================================================

                           G R A V E S E N D

            A single-level city for Blood   -   Version {version}

                "The last train leaves from Gravesend."

======================================================================

THIS LEVEL IS NEITHER MADE BY OR SUPPORTED BY MONOLITH PRODUCTIONS,
WARNER BROS, ATARI (FORMERLY INFOGRAMES, GT INTERACTIVE SOFTWARE),
THE WIZARDWORKS GROUP, NIGHTDIVE SOFTWARE OR ANY OF THEIR AFFILIATES
AND SUBSIDIARIES.

* Contents *

-General information
-Installation instructions
-Play information
-Compatibility
-Suggested play
-Construction
-Copyright / Permissions
-Where to get this MAP
-Version history
-Walkthrough and secrets guide (SPOILERS, at the very end)

======================================================================

* General information *

Game                   : Blood
Title                  : Gravesend
Filename               : GRAVESEND.MAP
Version                : {version} (early access)
Date                   : {date}
Author                 : {author}
Contact                : comments on the map's ModDB page

Description            : Gravesend is one very large level: a whole
                         harbour town under a burning sky, with its
                         streets, its interiors and what lies beneath
                         them joined into one map.

                         You come ashore on the quay, beside a
                         travelling fair that should have left town
                         long ago. The only way out is the last
                         train, and the station is locked by six
                         keys. Find them in any order: in the church
                         crypt, the arcade, the Aldermack theatre,
                         the pump station, the spiders' cellars and
                         the Cabal's own chamber. Most of them wake
                         something when you take them.

Additional credits to  : Monolith Productions, for Blood and for the
                         campaign this was learned from.
                         Ken Silverman, for the Build engine.
                         Nuke.YKT and the NBlood contributors.
                         NoOne and the XMAPEDIT contributors.
                         The authors of Death Wish and of the other
                         community maps that were studied for it.

======================================================================

* Installation instructions *

Installation           : 1. Put GRAVESEND.MAP in your NBlood folder,
                            the one with nblood.exe in it.
                         2. Start it with

                              nblood -map GRAVESEND

                            or choose it in the game's menu, under
                            USER MAP, which also asks for the
                            difficulty.

Additional Notes       : From the command line the difficulty is the
                         middle one. For another add -s and a number
                         from 0 (the easiest) to 4 (the hardest):

                              nblood -map GRAVESEND -s 3

                         Nothing of the original game is replaced.
                         To remove the map, delete it.

======================================================================

* Play Information *

Episode and Level #    : N/A (user map)
Single Player          : Yes
BloodBath 2-8 Player   : Starts for 8 players, not yet tested online
Cooperative 2-8 Player : Starts for 8 players, not yet tested online
CTF (Team Play)        : No
Difficulty Settings    : Yes, all five. Enemies, placed and lying in
                         wait, from the easiest to the hardest:
                         {foes}
Pitchfork start        : Yes
Secrets                : {secrets}
Plasma Pak required    : Yes (One Unit Whole Blood includes it)
Cryptic Passage art    : No
New Art                : No
New Music              : No, and the map names no track of its own
New Sound Effects      : No
New Files              : No
Demos Replaced         : None

======================================================================

* Compatibility *

Vanilla Blood          : No. The map is far beyond the limits of the
                         original game.
Fresh Supply           : Not tested
Refreshed Supply       : Not tested
BloodGDX/Related forks : Not tested
nBlood/Related forks   : Yes. Made for NBlood, and played in nothing
                         else.
Raze/Related forks     : Not tested
Additional notes       : {sectors} sectors, {walls} walls, {sprites} sprites. A
                         port has to allow 4096 sectors and 16384
                         walls to load it.

======================================================================

* Suggested play *

Settings               : The default ones. The level is long, so save
                         as you go.
Hints                  : The station at the end of the avenue shows
                         which keys it wants. A key you have is turned
                         in the switch under its sign.
                         Keep some dynamite. Cracked walls and manhole
                         covers give way to it.
                         A wheel, a lever or a hand on a wall is there
                         to be used.

======================================================================

* Construction *

Base                   : From scratch
Level Editor(s) Used   : None in the usual sense. The map is written
                         as code (Python) by AI agents working from
                         the original campaign's own maps, and was
                         directed, walked and corrected by a human
                         over many rounds. The tools are llmapper's.
Art Editor(s) Used     : None
Other Programs Used    : NBlood and XMAPEDIT, to play it and to look
                         at it
Construction Time      : August to November 2026
Known Bugs/Problems    : - Early access: please report anything that
                           is broken, unfair or unreachable.
                         - Co-op and BloodBath have not been played.
                         - There is no music (see New Music).

======================================================================

* Copyright / Permissions *

Anybody may do anything with GRAVESEND.MAP: play it, change it, take
parts of it, build other levels on it and distribute it, in any form
and without asking.

Blood is a trademark of its owners. The map holds none of the game's
files: it needs your own copy of Blood, with the Plasma Pak.

======================================================================

* Where to get this MAP *

WWW                    : ModDB, under the name Gravesend

======================================================================

* Version history *

0.1, {date}: the first public release.

======================================================================




               S P O I L E R S     B E L O W     T H I S




======================================================================

* Walkthrough and secrets guide *

THE WAY OUT

The avenue runs from the quay to Gravesend Station. On the pier between
its two gates hang six key signs, with a switch under each. With all
six keys turned the gates go up. Through the booking hall, over the
platform, up to the signal box: its lever sets the line clear, and
something comes up the platform before the train does. When the
carriage opens, the way out is the emblem at its forward end.

THE KEYS, in any order

Skull   St Gallow's crypt, on the lid of the sarcophagus.

Eye     The arcade, on a plinth on the upper landing. Down the
        escalator into the sunk court, and up the fallen gallery. It
        also opens the service passage behind it.

Moon    The Aldermack theatre, on the stage, in the light.

Flame   The pump station's machine hall, on the belt between the two
        presses. The lever on the console stops the belt, with the
        presses shut.

Spider  The Weaver's Cellars, off the north walk of Graves Brook in
        the sewers: shoot the web across the passage.

Dagger  The Cabal's chamber, behind the toothed mouth on the settling
        hall's south quay, at the foot of the sewer's outfall. Bullets
        and blasts do nothing to the stone beast there. The Tesla
        Cannon lies outside, in line with the falls.

        The sewers are reached by the pump station's spiral stair, by
        three manholes that dynamite opens, or through the cracked
        wall in St Gallow's crypt.

THE SECRETS

 1. The Demeter's hold: a panel at the back is of other planks than
    the rest. Push it.

 2. The arcade's service passage: shoot the fire extinguisher, from a
    distance.

 3. The stash in the sewers, behind bars: the valve wheel in the riser
    by the junction lifts them.

 4. The flooded branch, barred from the walk: dive in the cistern's
    tank and come up at its back.

 5. Old Molly's nest: at the west end of Graves Brook, crouch through
    the ivy in the south wall.

 6. The plague pit: blow open the crack in Graves Brook's south wall,
    under the churchyard.

 7. The Rat King's shrine: push the bloody hands on the wall of the
    stockyard's bleeding floor.

 8. The Phantom Terminus: past the pump spiral's lower landing are
    three dials, and on the east wall an inspection plate that says
    how they stood: A at II, B at IV, C at III.

 9. The Toshers' Den, off the settling hall's west quay: one bed
    stands on two boxes where the others stand on one. Push them.

10. The Cabal's chamber: behind the burst rose, past the dagger, shoot
    the chained eye.

======================================================================
"""


def counts(disk) -> dict:
    """What the readme says in figures."""
    from bloodmap.model import record_extra, record_fields
    foes, secrets = [], 0
    for part in (disk.sectors, disk.walls, disk.sprites):
        for item in part:
            extra = record_extra(item) or {}
            secrets += (int(extra.get("tx_id") or 0), int(extra.get("command") or 0)) == SECRET
    for sprite in disk.sprites:
        kind = int(record_fields(sprite)["type"])
        if 201 <= kind <= 250 and kind != INNOCENT or kind == 18:
            foes.append(int((record_extra(sprite) or {}).get("launch_skill") or 0))
    return {"sectors": len(disk.sectors), "walls": len(disk.walls), "sprites": len(disk.sprites), "secrets": secrets,
            "foes": " / ".join(str(sum(1 for out in foes if not out >> skill & 1)) for skill in range(5))}


def text(disk) -> str:
    """The readme, for this map."""
    return TEXT.lstrip("\n").format(version=VERSION, date=DATE, author=AUTHOR, **counts(disk))


def files(disk=None) -> dict[str, bytes]:
    """The two files as they are given out."""
    from bloodmap.format import read_map
    readme = text(disk or read_map(PLAYED))
    return {MAP_NAME: PLAYED.read_bytes(), README_NAME: readme.replace("\n", "\r\n").encode("ascii")}


def build() -> dict:
    """Write them, and the archive of them: the same bytes for the same map."""
    OUT.mkdir(exist_ok=True)
    made = files()
    archive = OUT / f"gravesend-v{VERSION}.zip"
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data in made.items():
            (OUT / name).write_bytes(data)
            z.writestr(zipfile.ZipInfo(name, (2026, 11, 25, 0, 0, 0)), data, zipfile.ZIP_DEFLATED)
    return {**{name: len(data) for name, data in made.items()}, archive.name: archive.stat().st_size}


if __name__ == "__main__":
    print("packaged:", build())
