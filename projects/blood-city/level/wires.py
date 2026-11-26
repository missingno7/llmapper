"""The city's wires: every one named, with what it is for. The order here is the numbering.

A wire used to be a number typed into the module that needed one: 262 in the
church, 340 in the theatre, 30 in the foundry -- which is the engine's own
channel, and nobody could have known without reading all six modules. This
is the one table. A module asks for a wire by name, declares what sends on it
and what answers (`bloodmap.wiring.Wire.when` / `.then`), and never sees a
number it chose: `channel(name)` is the wire's place in `PLAN`.

    python projects/blood-city/level/status.py --wires

prints the built level's wiring from this table and the declarations.

To add a wire, add a line to `PLAN` AT THE END (a line in the middle
renumbers every wire after it, which changes the map), then declare its ends
where its sender and its answers are built. A wire in the plan that nothing
declares an end of is left out of the build and named in its log.
"""

from __future__ import annotations

from bloodmap import wiring

#: (name, what the author wants of it). Append only.
PLAN: tuple[tuple[str, str], ...] = (
    ("foundry:staged-moment",
     "stepping onto the yard grate, once, fires the cart's two charges and a "
     "sound cue"),
    ("theatre:curtain",
     "the conductor and fly levers raise the house cloth; the prize relay drops it"),
    ("theatre:stage-light",
     "the stage's light follows the curtain as it travels: dark shut, lit open"),
    ("church:breach",
     "blowing the crack in the crypt wall, from either side, once, opens the "
     "way between crypt and sewer and fires three charges"),
    ("arcade:cache",
     "shooting the extinguisher in the service corridor, once, blows open the "
     "wall behind it onto a hidden cache"),
    ("pump:belt",
     "the console lever stops and starts the belt's open stretches, which "
     "carry whatever stands on them only while on, and tells the presses"),
    ("pump:presses",
     "when the level starts both presses begin slamming; the console lever stops them shut, and the belt "
     "under them, and starts them again"),
    ("station:car-door",
     "six seconds after the signal box's lever the carriage's door sinks into its floor"),
    ("station:gate",
     "the signal box's lever raises the roll-up gate in the tunnel's mouth, and the carriage opens after it"),
    ("sewer:plague-pit",
     "blowing the crack in Graves Brook's south wall by the churchyard, once, "
     "opens the bricked-up plague pit and fires three charges"),
    ("foundry:loading-shutter",
     "pushing either freight leaf from either approach parts both leaves "
     "to open onto the mirror"),
    ("theatre:fire-doors",
     "pushing either of the Aldermack's stage doors from either room toggles both "
     "leaves, which stay where they stop until pushed again"),
    # (the settling hall's service lift was this wire until 2026-11-25)
    ("sewer:stockyard-armor",
     "taking the spirit armor across the blood brings two gill beasts up "
     "out of it, between you and the stair"),
    ("sewer:stockyard-trolley",
     "each dry berth calls the sampling deck to its own stop and the carried "
     "button sends the boarded rider across the blood channel"),
    ("ghost:dial-matches",
     "each maintenance dial adds a match when it reaches its setting and "
     "subtracts it when turned past"),
    ("ghost:all-matched",
     "three simultaneous matches set the service hatch's latch"),
    ("ghost:hatch-open",
     "the first match opens the sliding hatch and sounds the latch once"),
    ("caleb:opening",
     "half a second after the level starts, Caleb says he will paint the town red"),
    ("caleb:spider-mother",
     "killing the Weaver's Cellars' spider mother prompts Caleb's spider rhyme once"),
    ("caleb:ghost-tunnel",
     "the Phantom car reaching the bricked-up stop prompts Caleb"),
    ("theatre:show-latch",
     "the Aldermack stage light reaching its ON stop sets the show latch"),
    ("theatre:show",
     "the first curtain opening plays Caleb's line and raises two patrons"),
    ("theatre:pit-piano",
     "playing the keys in the Aldermack's orchestra pit sounds the organ riff"),
    ("theatre:prize",
     "taking the fire armour drops the house cloth, blacks out the beam and opens the wings"),
    ("theatre:box-curtain",
     "pushing the second west box's cloth draws it aside or shuts it again"),
    ("phantom:departure",
     "the first departure blacks out the platform, sounds the whistle and wakes the Phantasms"),
    ("phantom:car",
     "send the car to the brick stop or call it back to the platform"),
    ("phantom:prize", "picking up the Tommy gun starts the outbound run"),
    ("phantom:arm", "the first outbound command sets the departure effects latch"),
    ("phantom:coach-state", "the coach announces the state of each berth it stops at"),
    ("phantom:car-light",
     "the light that falls from the coach's windows goes as the coach goes and comes back with it"),
    ("phantom:first-platform", "entering the platform puts out the near lamp and sounds the distant whistle"),
    ("key:skull", "taking the skull key in the crypt raises the buried out of its earth"),
    ("key:eye", "taking the eye key in the arcade raises the gun shop's shutter, and the Cabal come out of it and up behind you"),
    ("key:flame", "taking the flame key off the belt brings the dead into the machine hall"),
    ("key:dagger", "taking the dagger key behind the rose puts phantoms between it and the way out"),
    ("key:spider", "taking the spider key out of the nest wakes the brood"),
    ("station:keys", "each key turned in its lock by the station's arches is counted"),
    ("station:unlock", "the sixth key raises the station's gates, and the guard behind them"),
    ("cabal:entered", "stepping onto the chamber's gallery is answered once: give me a sacrifice"),
    ("cabal:broken",
     "the stone beast's death breaks the rite: the earth shakes, the well goes down, some of the audience get up, "
     "the blasts climb, and the relays that put out the fires and burst the window start"),
    ("cabal:fires-1", "the two fires by the runner go out, and the chant stops"),
    ("cabal:fires-2", "a moment later the two at the sides go out, and the room goes dark"),
    ("cabal:fires-3", "and then the two by the altar"),
    ("cabal:burst", "a second after the beast falls the horned thing bursts, and the light in its hands with it"),
    ("cabal:flare-1", "fire flies up from where it stood, hurting nobody"),
    ("cabal:flare-2", "fire flies higher, a fifth of a second after"),
    ("cabal:flare-3", "fire flies higher still, to where the blasts take over"),
    ("cabal:says", "when the last of them has gone off Caleb says what he thinks of it"),
    ("cabal:deep", "the emptied well's bottom goes up, and the earth shakes again"),
    ("cabal:window", "seven seconds after the beast falls the rose bursts, what was behind it comes through, and the beasts in the niches wake"),
    ("cabal:heart", "shooting the heart ends it: a cry, the earth shakes, and the flesh opens on what it had swallowed"),
    ("cabal:silent", "the heart's beat stops with it"),
    ("cabal:shut", "stepping down onto the kerb round the sign turns the stone beast and shuts the mouth behind you; the bursting window, or forty seconds, opens it"),
    ("cabal:disarm", "once the beast is dead the kerb shuts nothing"),
    ("market:cold-store", "the lever in the clerk's gallery raises the steel door of the market's cold store, once"),
    ("market:armor", "taking the armor at the back of the cold store wakes two of the hung and a butcher"),
    ("harbour:boarded", "taking the flare pistol in the Demeter's hold brings three gill beasts up onto her deck"),
    ("underpass:pram",
     "leaving the shut ticket hall for the first time puts out the tunnel's bulb and brings the pram down to the bars"),
    ("theatre:side-door", "pushing either face of the Aldermack's avenue door slides it into the wall, and back"),
    ("theatre:front-doors", "pushing either leaf of the Aldermack's forecourt doors swings both"),
    ("church:slab",
     "the skull switch carried on the crypt's slab sends it down and back; the one at either stop calls it"),
    *((f"underpass:tube-{cell}", f"shooting the underpass's tube in {cell} puts it out, and its light with it")
      for cell in ("north", "bay_1", "bay_2", "bay_4", "mirror")),
    ("sewer:stash-bars", "the valve wheel in the riser by the junction lifts the bars off the stash"),
    ("sewer:shrine-hands",
     "pushing the bloody hands on the bleeding floor's wall presses their slab and opens the pipe to the Rat King's shrine"),
    ("fair:hits", "each smiling face and each bullseye hit at the shooting gallery is counted"),
    ("gallery:beast", "taking what lies at the stone beast's feet in the gallery brings it down off its platform"),
    ("fair:prize", "the last of them rings the bell and brings the prize up through the gallery's counter"),
)

#: Wires one end of which is the engine. They take the engine's channel and
#: no number of the city's, so adding one renumbers nothing.
ENGINE_PLAN: tuple[tuple[str, str, str], ...] = (
    ("station:way-out",
     "pushing the emblem at the forward end of the carriage, whose door the "
     "signal box's lever opens, ends the level",
     "kChannelLevelExitNormal"),
    ("fair:carousel", "when the level starts the fair's carousel turns, and goes on turning", "kChannelLevelStart"),
    ("pump:engine", "when the level starts the pump station's three rods go up and down, and go on", "kChannelLevelStart"),
    ("fair:targets", "when the level starts the shooting gallery's ducks and faces run to and fro, and go on", "kChannelLevelStart"),
)

_NAMES = [name for name, _says in PLAN]
_CIRCUIT: wiring.Circuit | None = None


def channel(name: str) -> int:
    """The number of a planned wire: its place in the plan, from 100."""
    return wiring.USER_CHANNELS_FROM + _NAMES.index(name)


def begin() -> wiring.Circuit:
    """A new circuit holding the plan. Called once, as the build starts."""
    global _CIRCUIT
    _CIRCUIT = wiring.Circuit.from_plan(PLAN, ENGINE_PLAN)
    return _CIRCUIT


def circuit() -> wiring.Circuit:
    """The build's circuit; begun here if a module is being used on its own.

    A module of the city can be exercised without the build (a test hangs
    one curtain in an empty hall). Its declarations then go to a circuit
    nobody applies, and the fields its constructors wrote still carry the
    plan's numbers.
    """
    return _CIRCUIT if _CIRCUIT is not None else begin()


def wire(name: str) -> wiring.Wire:
    """A planned wire, to declare an end of."""
    try:
        return circuit().named(name)
    except wiring.WireError:
        raise wiring.WireError(f"no wire called {name!r} in projects/blood-city/level/wires.py") from None


def shot(index: int, what: str) -> wiring.Wire:
    """The wire of one clock or mirror that smashes when it is shot; these come after the plan, one a face."""
    return circuit().wire(f"shot:{what}", f"shooting {what} throws its glass, once",
                          channel=wiring.USER_CHANNELS_FROM + len(PLAN) + int(index))


def by_channel(number: int) -> wiring.Wire:
    for made in circuit().wires:
        if made.channel == int(number):
            return made
    raise wiring.WireError(f"no wire on channel {number}")


def close() -> list[str]:
    """Leave out every planned wire nothing declared an end of; say which."""
    return circuit().drop_idle()
