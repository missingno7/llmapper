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
     "carry whatever stands on them only while on"),
    ("pump:presses",
     "when the level starts both presses begin slamming, and never stop"),
    ("station:car-door",
     "the lever in the station hall sinks the carriage's door into its floor"),
    ("station:gate",
     "the signal box's lever raises the roll-up gate in the tunnel's mouth"),
    ("sewer:plague-pit",
     "blowing the crack in Graves Brook's south wall by the churchyard, once, "
     "opens the bricked-up plague pit and fires three charges"),
    ("foundry:loading-shutter",
     "pushing either freight leaf from either approach parts both leaves "
     "to open the loading alcove"),
    ("theatre:fire-doors",
     "pushing either of the Aldermack's stage doors from either room toggles both "
     "leaves, which stay where they stop until pushed again"),
    ("sewer:settling-hall-lift",
     "the landing buttons recall the deck to their own stop and the rider's "
     "button sends it to the other stop"),
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
     "entering the bricked-up track stub at Ghost Station prompts Caleb once"),
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
)

#: Wires one end of which is the engine. They take the engine's channel and
#: no number of the city's, so adding one renumbers nothing.
ENGINE_PLAN: tuple[tuple[str, str, str], ...] = (
    ("station:way-out",
     "pushing the switch at the end of the tunnel the line leaves by, past "
     "the roll-up gate the signal box's lever raises, ends the level",
     "kChannelLevelExitNormal"),
    ("station:fare-turnstile",
     "when the level starts the station's fare turnstile begins cycling",
     "kChannelLevelStart"),
)

#: Levers beside street doors come after the plan, one wire a door.
LEVER_SAYS = ("the lever beside the {door} door opens it from the street; "
              "pushing the door itself still works")

_NAMES = [name for name, _says in PLAN]
_CIRCUIT: wiring.Circuit | None = None


def channel(name: str) -> int:
    """The number of a planned wire: its place in the plan, from 100."""
    return wiring.USER_CHANNELS_FROM + _NAMES.index(name)


def begin() -> wiring.Circuit:
    """A new circuit holding the plan. Called once, as the build starts."""
    global _CIRCUIT
    _CIRCUIT = wiring.Circuit()
    for name, says in PLAN:
        _CIRCUIT.wire(name, says, channel=channel(name))
    for name, says, engine in ENGINE_PLAN:
        _CIRCUIT.wire(name, says, engine=engine)
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
    for made in circuit().wires:
        if made.name == name:
            return made
    raise wiring.WireError(f"no wire called {name!r} in projects/blood-city/level/wires.py")


def lever(index: int, door: str) -> wiring.Wire:
    """The wire of one street door's lever, made the first time it is asked for."""
    name = f"lever:{door}"
    for made in circuit().wires:
        if made.name == name:
            return made
    return circuit().wire(name, LEVER_SAYS.format(door=door),
                          channel=wiring.USER_CHANNELS_FROM + len(PLAN) + int(index))


def by_channel(number: int) -> wiring.Wire:
    for made in circuit().wires:
        if made.channel == int(number):
            return made
    raise wiring.WireError(f"no wire on channel {number}")


def close() -> list[str]:
    """Leave out every planned wire nothing declared an end of; say which."""
    built = circuit()
    idle = [made.name for made in built.wires if not made.senders and not made.answers]
    built.wires = [made for made in built.wires if made.senders or made.answers]
    return idle
