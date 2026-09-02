"""Gravesend L1 -- the schematic plan. The city as data, not geometry.

Layer contract (references/design-layers.md): this file contains districts,
the street network as a graph whose edges carry a WIDTH CLASS (never Build
units), blocks with roles, venue slots typed from venue-patterns.md, the
sewer subgraph and its entries, the roof-route stack positions, the main
circuit, and the channel budget. It contains no picnums, no z values, and no
Build units.

Schematic coordinates: 1 pu (plan unit) on an abstract grid, existing only
so the plotter can draw the plan side-by-side with the precedent plans (the
plotting convention renders 1 pu at 1024 Build units; the L2 generator owns
the real resolution, level/resolution.py). Quarter-pu fractions are legal.

Every quantity here traces to a contract: CN = references/city-norms.md,
VP = references/venue-patterns.md, SP = references/sewer-patterns.md,
ID = references/city-identity.md.
"""

from __future__ import annotations

# --- the grid the streets draw (running sums; a width change re-flows all
# --- positions beyond it -- streets are the flexible elements) -------------
LANE = 3        # perimeter service lanes          (CN 1 minor street)
ALLEY = 2       # alleys                           (CN 1 p10 band)
STREET = 5      # standard streets                 (CN 1 DukCity median)
ROW = 6         # Theatre Row street / the quay    (CN 1 Blood town band)
AVENUE = 7      # the avenue                       (CN 1 Blood town median)

COL_A_W, COL_B_W, COL_C_W = 12, 12, 14      # block columns (CN 2 mid mode)
ROW1_D, ROW2_D, ROW3_D = 12, 14, 10         # block rows

X_LANE_W = 0
X_A = X_LANE_W + LANE                        # 3
X_STREET_W = X_A + COL_A_W                   # 15
X_B = X_STREET_W + STREET                    # 20
X_AVENUE = X_B + COL_B_W                     # 32
X_C = X_AVENUE + AVENUE                      # 39
X_SPUR = X_C + COL_C_W                       # 53
CITY_W = X_SPUR + STREET                     # 58

Y_LANE_N = 0
Y_R1 = Y_LANE_N + LANE                       # 3
Y_ROWST = Y_R1 + ROW1_D                      # 15
Y_R2 = Y_ROWST + ROW                         # 21
Y_MARKST = Y_R2 + ROW2_D                     # 35
Y_R3 = Y_MARKST + STREET                     # 40
Y_QUAY = Y_R3 + ROW3_D                       # 50
CITY_D = Y_QUAY + ROW                        # 56

DISTRICTS = {
    # ID gives each its one-line identity; seams follow street centerlines.
    "theatre_row": "gas-lit entertainment street; the Aldermack superblock and the venue cluster",
    "old_crossing": "the pre-boom quarter: narrow lanes, the well square, the parish "
                    "church and its cemetery, the Phase-2 roof route",
    "foundry_ward": "the works, the rail spur, the sewer network below",
    "market_slip": "the river gate: quay, plaza, monument; the start",
}

# --- street graph: centerline nodes and edges; width by class only ---------
NODES = {
    "nw": (1.5, 1.5), "n_ave": (35.5, 1.5), "n_spur": (55.5, 1.5),
    "row_w": (1.5, 18), "row_west": (17.5, 18), "row_ave": (35.5, 18),
    "mkt_w": (1.5, 37.5), "mkt_west": (17.5, 37.5), "mkt_ave": (35.5, 37.5),
    "mkt_spur": (55.5, 37.5),
    "quay_w": (1.5, 53), "quay_ave": (35.5, 53), "quay_spur": (55.5, 53),
}

EDGES = [
    # (a, b, width_class, district, name)
    ("nw", "n_ave", "lane", "theatre_row", "north lane"),
    ("n_ave", "n_spur", "lane", "foundry_ward", "north lane east"),
    ("nw", "row_w", "lane", "theatre_row", "west lane north"),
    ("row_w", "mkt_w", "lane", "old_crossing", "west lane mid"),
    ("mkt_w", "quay_w", "lane", "market_slip", "west lane south"),
    ("row_w", "row_west", "row", "theatre_row", "Theatre Row street west"),
    ("row_west", "row_ave", "row", "theatre_row", "Theatre Row street east"),
    ("row_west", "mkt_west", "street", "old_crossing", "the west street"),
    ("n_ave", "row_ave", "avenue", "theatre_row", "the avenue north"),
    ("row_ave", "mkt_ave", "avenue", "old_crossing", "the avenue mid"),
    ("mkt_ave", "quay_ave", "avenue", "market_slip", "the avenue south"),
    ("n_spur", "mkt_spur", "street", "foundry_ward", "the rail spur"),
    ("mkt_spur", "quay_spur", "street", "market_slip", "spur south"),
    ("mkt_w", "mkt_west", "street", "old_crossing", "market street west"),
    ("mkt_west", "mkt_ave", "street", "market_slip", "market street mid"),
    ("mkt_ave", "mkt_spur", "street", "foundry_ward", "market street east"),
    ("quay_w", "quay_ave", "row", "market_slip", "the quay west"),
    ("quay_ave", "quay_spur", "row", "market_slip", "the quay east"),
]

# --- open areas beyond the graph: one plaza per district (CN 1) ------------
AREAS = [
    {"id": "market_plaza", "district": "market_slip", "kind": "plaza",
     "rect": (X_STREET_W, Y_R3, X_C, Y_QUAY),
     "note": "24-pu open span between the market blocks; the monument holds its loop",
     "furnish": ["fountain@center-offset-west", "stall_run_3@west_edge",
                 "lamps@mouths"]},
    {"id": "theatre_forecourt", "district": "theatre_row", "kind": "forecourt",
     "rect": (X_AVENUE - ROW, Y_ROWST - 4, X_AVENUE, Y_ROWST),
     "note": "notched from the Aldermack's SE corner; the landmark mouth on the vista",
     "furnish": ["kiosk(existing_mass)", "lamps@marquee_rule"]},
    {"id": "well_square", "district": "old_crossing", "kind": "square",
     "rect": (X_STREET_W - 2, Y_R2 + 3, X_B, Y_R2 + 9),
     "note": "the west street widens into the quarter's square",
     "furnish": ["well@center", "bench_pair@south_edge", "lamps"]},
    {"id": "cemetery", "district": "old_crossing", "kind": "cemetery",
     "rect": (X_B, Y_R2, X_AVENUE, Y_MARKST),
     "note": "walled ground on the old block B footprint; the church fronts "
             "the avenue from inside it (church-patterns.md placement)",
     "carved": True,
     # One gate: a second would cut the boundary wall into two arc-masses
     # and push the street-loop census past the CN 2 ceiling (found by the
     # first conformance run -- the check works).
     "gates": [{"edge": "west", "at": 0.5, "name": "lychgate"}],
     "attached_masses": [
         # The mausoleum row rides the church's west face (one merged solid,
         # one street loop -- a wall-attached row would loop on the street
         # side and break the CN 2 ceiling).
         (X_AVENUE - 8, Y_R2 + 1, X_AVENUE - 6, Y_R2 + 3.25),
         (X_AVENUE - 8, Y_R2 + 4.5, X_AVENUE - 6, Y_R2 + 6.75),
     ]},
    {"id": "works_yard", "district": "foundry_ward", "kind": "yard",
     "rect": (X_SPUR - 4, Y_ROWST, X_SPUR, Y_ROWST + 8),
     "note": "notched from the works' east face onto the spur",
     "furnish": ["cart_platform@south", "cargo_sprites", "lamps@stair_and_gatehouse",
                 "no_fountain (industrial; street-furniture.md)"]},
]

# --- blocks: role from CN 2 (superblock / block / free_standing); ----------
# --- notches are street space a mass gives back ----------------------------
BLOCKS = [
    {"id": "aldermack_superblock", "district": "theatre_row", "role": "superblock",
     "rect": (X_A, Y_R1, X_AVENUE, Y_ROWST),          # 29 x 12 pu (CN 2 band)
     "notches": ["theatre_forecourt"]},
    {"id": "works", "district": "foundry_ward", "role": "superblock",
     "rect": (X_C, Y_R1, X_SPUR, Y_MARKST),           # 14 x 32 pu (CN 2 band)
     "notches": ["works_yard"]},
    {"id": "oc_block_a", "district": "old_crossing", "role": "block",
     "rect": (X_A, Y_R2, X_STREET_W, Y_MARKST),
     "notches": ["oc_alley_a", "well_square"]},
    # oc_block_b was replaced by the church-and-cemetery complex
    # (church-patterns.md): the church mass fronts the avenue from inside
    # the walled cemetery ground; the mausoleum row rides the north wall as
    # attached masses so the street-loop count holds.
    {"id": "church_mass", "district": "old_crossing", "role": "block",
     "rect": (X_AVENUE - 6, Y_R2, X_AVENUE, Y_R2 + 10),
     "notches": [], "inside_area": "cemetery"},
    {"id": "market_block_a", "district": "market_slip", "role": "block",
     "rect": (X_A, Y_R3, X_STREET_W, Y_QUAY), "notches": []},
    {"id": "market_block_c", "district": "market_slip", "role": "block",
     "rect": (X_C, Y_R3, X_SPUR, Y_QUAY), "notches": []},
    {"id": "kiosk", "district": "theatre_row", "role": "free_standing",
     "rect": (28.25, 12.25, 29.75, 13.75), "notches": []},    # 1.5 pu (CN 2 small)
    # Widened from 2.0 to 2.375 plan units (2,432) so the composition has a
    # face to carry lettering a player can read from the spawn eleven plan
    # units away.  2.0 was the campaign's MEDIAN monument base
    # (monuments-v1.json: median 2.0, q1 1.5, q3 3.25), so this is between
    # its median and its q3 -- and 2,432 is the top of CN 2's free-standing
    # band, which `plan_review` checks at 700..2,500.
    {"id": "monument", "district": "market_slip", "role": "free_standing",
     "rect": (24.8125, 43.8125, 27.1875, 46.1875), "notches": []},   # 2.375 pu
    {"id": "gatehouse", "district": "foundry_ward", "role": "free_standing",
     "rect": (52, 19, 54.25, 21.25), "notches": []},          # 2.25 pu
]

#: Dead-end alleys bitten into the Old Crossing blocks: texture without a
#: loop (keeps loop count at the CN 2 ceiling, not over it).
DEAD_END_ALLEYS = [
    {"id": "oc_alley_a", "block": "oc_block_a", "edge": "north",
     "at": 0.5, "width_class": "alley", "depth_pu": 8},
]

# --- venue slots: types from VP, placed on named frontages -----------------
# --- (rates checked in reports/plan-contract-check.md) ---------------------
VENUES = [
    {"id": "aldermack", "type": "landmark_complex", "block": "aldermack_superblock",
     "face": "south@forecourt", "doorways": 4,
     "note": "ID landmark and objective; VP complex at the low end (~110 sect/680 walls)"},
    {"id": "saloon", "type": "bar", "block": "aldermack_superblock",
     "face": "south@west", "doorways": 2,
     "note": "VP bar: geometry counter + tables, destruction reserve"},
    {"id": "shooting_parlor", "type": "walk_through", "block": "aldermack_superblock",
     "face": "south@mid", "doorways": 2,
     "note": "VP walk-through: deep plan behind a narrow mouth"},
    {"id": "pawn_shop", "type": "open_front", "block": "aldermack_superblock",
     "face": "east@avenue", "doorways": 2,
     "note": "VP open-front on the avenue"},
    {"id": "market_hall", "type": "retail_row", "block": "market_block_a",
     "face": "east@plaza", "doorways": 2,
     "note": "decision C: E4M9 multi-unit grammar, 2-3 units on one hall"},
    {"id": "church", "type": "church_complex", "block": "church_mass",
     "face": "east@avenue", "doorways": 3,
     "note": "church-patterns.md: monastery chapel grammar; tower on the "
             "vista opposite the Aldermack"},
    # The chandlery slot became the Gravesend Arcade: the owner asked for a
    # shopping mall and E4M9's grammar is a retail row, not an open front.
    # Recording it here rather than leaving L1 and the tree disagreeing --
    # `conformance.py` checks that every venue declared here has a node and
    # that its type matches the template that built it, so a plan left
    # stale now fails a row instead of going unnoticed.
    {"id": "arcade", "type": "retail_row", "block": "market_block_c",
     "face": "west@plaza", "doorways": 2,
     "note": "was 'chandlery/open_front'; E4M9 concourse with six units"},
    {"id": "ferry_office", "type": "open_front", "block": "market_block_a",
     "face": "south@quay", "doorways": 1},
    {"id": "workshop_bar", "type": "bar", "block": "oc_block_a",
     "face": "alley:oc_alley_a", "doorways": 1,
     "note": "the hand-shaped exception district gets the hidden bar"},
    {"id": "works_canteen", "type": "open_front", "block": "works",
     "face": "east@yard", "doorways": 2},
]

# --- the sewer subgraph (SP): under Foundry Ward, its own ring topology ----
SEWER = {
    "district": "foundry_ward",
    "depth_contract": "2.5..4 standing heights below grade (SP); L2 resolves",
    # The network runs under the works superblock: the geometry audit
    # refuses declared partial-overlap stacks (grammar request #6), so
    # under-street placement is grammar-blocked this iteration and the
    # conformance report says so rather than hiding it.
    "nodes": {
        "junction": (41.75, 12), "trunk_west": (39.75, 21.5),
        "manhole_foot": (49.5, 21.5), "cistern": (46, 29),
    },
    "edges": [
        ("junction", "trunk_west", "north riser"),
        ("trunk_west", "manhole_foot", "the trunk under the works"),
        ("manhole_foot", "cistern", "fall to the cistern"),
        ("cistern", "junction", "Phase 4: dive link closes the ring (E3M3 water-link precedent)"),
    ],
    "entries": [
        {"id": "yard_grate", "form": "drop", "link_form": "see_through",
         # Shifted east so a kerb ring clears the loading dock (west) and
         # the gatehouse (east) by half a plan unit each.
         "at": (50.5, 21.5),
         "note": "owner sewer directive: stack link, see-through -- the "
                 "player looks down through the grate into the gallery "
                 "(backdrop-urbanism logic applied downward); one-way fall, "
                 "return is the stair"},
        {"id": "works_stair", "form": "stair", "link_form": "see_through",
         "at": (48.5, 19),
         "note": "flights down to the works cellar; the cellar pit is a "
                 "ROR shaft into the adjacent under-city junction"},
        {"id": "pump_spiral", "form": "spiral", "link_form": "solid",
         "at": (44.5, 5),
         "note": "the pump station's road-level stair reaches a cellar, then "
                 "a physical 270-degree spiral descends into the sewer"},
    ],
    "under_city": {
        "footprint_pu": (27, 2, 57, 39),
        "note": "the sewer lies directly below Foundry Ward; its real spiral "
                "stair stays in the same XY footprint, while the two remaining "
                "ROR links are vertically aligned",
    },
    "roles": {"main_circuit": "required passage once (SP)",
              "secret_branch": "Phase 4, from the cistern (dive link)"},
}

# --- roof route (ID: Old Crossing carries the E3M1-style stacked layer) ----
ROOF_STACKS = [
    {"id": "roof_up", "district": "old_crossing", "at": (14, 22),
     "note": "stair shaft up at oc_block_a's NE corner; Phase 2"},
    {"id": "roof_cross", "district": "old_crossing", "at": (19, 22),
     "note": "plank crossing over the west street toward the cemetery wall; Phase 2"},
    {"id": "crypt_stack", "district": "old_crossing", "at": (24, 22),
     "note": "the crypt under the mausoleum row (church-patterns.md, E1M1 "
             "precedent); built with Old Crossing's district turn"},
]

# --- the main circuit (ID): start -> venues -> objective -------------------
#: THE MAIN CIRCUIT, AS SURFACE IDS (owner queue item 3, decided 2026-09-03).
#:
#: Each leg used to be a coordinate in the 58x56 plan grid. The envelope solve
#: produces 72x60, so no leg could be checked against a built map -- and a
#: coordinate would not survive the next re-solve either. A leg is now the
#: SURFACES a body passes through, in order: "the avenue between Theatre Row
#: and Market Street" survives a re-solve, and (35.5, 25) does not.
#:
#: `at` is kept as provenance, not as a check. `built` is false for a leg
#: whose surfaces this level does not have yet, with the reason, so an absent
#: leg is a row rather than a silence.
CIRCUIT = [
    {"leg": "start on the quay", "at": (33.5, 53),
     "surfaces": ("walk",), "built": True},
    {"leg": "plaza and monument", "at": (26, 45),
     "surfaces": ("plane", "market_plaza"), "built": True},
    {"leg": "the avenue north: the Aldermack vista", "at": (35.5, 37.5),
     "surfaces": ("plane",), "built": True},
    {"leg": "the vista, mid-avenue", "at": (35.5, 25),
     "surfaces": ("plane",), "built": True},
    {"leg": "forecourt and Theatre Row venues", "at": (30, 13.5),
     "surfaces": ("plane", "col_a/row_1"), "built": True},
    {"leg": "the avenue to the north lane", "at": (35.5, 1.5),
     "surfaces": ("plane",), "built": True},
    {"leg": "the north lane east to the spur", "at": (55.5, 1.5),
     "surfaces": ("plane",), "built": True},
    {"leg": "the spur south to the works yard", "at": (55.5, 19),
     "surfaces": ("plane", "col_c/row_3"), "built": True},
    {"leg": "into the yard", "at": (52, 19.5),
     "surfaces": ("works_yard",), "built": True},
    {"leg": "manhole drop at the yard's edge", "at": (49.5, 21.5),
     "surfaces": ("manhole",), "built": False,
     "why": "no sewer is emitted: the manhole, the trunk and the junction "
            "are three legs of one unbuilt district"},
    {"leg": "the trunk west under the works (the sewer leg)", "at": (44, 21.5),
     "surfaces": ("sewer_trunk",), "built": False,
     "why": "no sewer is emitted"},
    {"leg": "the sewer junction", "at": (41.75, 12),
     "surfaces": ("sewer_junction",), "built": False,
     "why": "no sewer is emitted"},
    {"leg": "works stair up to the yard", "at": (48.5, 19),
     "surfaces": ("works_stair",), "built": False,
     "why": "the stair is the sewer's way back up and has nothing to climb "
            "from yet"},
    {"leg": "spur south, market street west", "at": (55.5, 37.5),
     "surfaces": ("plane",), "built": True},
    {"leg": "market street to the avenue", "at": (35.5, 37.5),
     "surfaces": ("plane", "market_plaza"), "built": True},
    {"leg": "north to the forecourt: the objective", "at": (32, 15),
     "surfaces": ("plane", "col_a/row_1"), "built": True},
]

# --- channel budget per district (CN 8: 50..70 user channels) --------------
CHANNELS = {
    "theatre_row": {"doors": 12, "destruction": 6, "switches": 5, "sound_spawn": 4},
    "market_slip": {"doors": 5, "destruction": 1, "switches": 2, "sound_spawn": 2},
    "old_crossing": {"doors": 6, "destruction": 1, "switches": 2, "sound_spawn": 3},
    "foundry_ward_and_sewer": {"doors": 5, "destruction": 2, "switches": 3,
                               "sound_spawn": 2},
    "citywide_circuit": {"keys_gates": 5},
}


def plan() -> dict:
    total_channels = sum(sum(v.values()) for v in CHANNELS.values())
    return {
        "$schema": "llmapper.city-schematic-plan",
        "schema_version": 1,
        "identity": "references/city-identity.md",
        "grid_pu": {"city_w": CITY_W, "city_d": CITY_D},
        "districts": DISTRICTS,
        "nodes": NODES,
        "edges": EDGES,
        "areas": AREAS,
        "blocks": BLOCKS,
        "dead_end_alleys": DEAD_END_ALLEYS,
        "venues": VENUES,
        "sewer": SEWER,
        "roof_stacks": ROOF_STACKS,
        "circuit": CIRCUIT,
        "channels": CHANNELS,
        "channels_total": total_channels,
    }


if __name__ == "__main__":
    import json
    print(json.dumps(plan(), indent=2))


# --- envelopes: what each venue needs, derived UP from its interior --------
#
# The layer contract keeps Build units out of this file, and these are the one
# exception it has to make -- with the reason stated, because an envelope IS a
# size and a schematic cannot carry one. They are measured, not chosen: where
# the tree already builds the venue, the number is that module's own MASS rect
# (`l3_church.MASS` 6144 x 10240, `l3_mall.MASS` 14336 x 10240); where it does
# not, it is the venue pattern's room size for that type.
#
# The point of stating them here rather than in L2 is the order of decision
# (street-model-decisions section 9): a building's size comes up from its
# rooms, and the grid is solved from the envelopes. Taking a block from a norm
# and carving rooms into it is what gave the arcade a concourse the wrong size.
#
# `interior` is the room extent; `city_solve.Envelope` adds the walls and the
# facade depth an insert needs.
ENVELOPES = {
    "church":       {"interior": (6144, 10240), "faced": ("east",),
                     "source": "l3_church.MASS, built"},
    "arcade":       {"interior": (14336, 10240), "faced": ("west",),
                     "source": "l3_mall.MASS, built"},
    "aldermack":    {"interior": (12288, 10240), "faced": ("south",),
                     "source": "VP complex at the low end; the theatre house "
                               "plus its stage and forecourt depth"},
    "market_hall":  {"interior": (10240, 7168), "faced": ("east",),
                     "source": "VP retail_row, E4M9 multi-unit hall"},
    "saloon":       {"interior": (5120, 4096), "faced": ("south",),
                     "source": "VP bar: counter geometry plus tables"},
    "shooting_parlor": {"interior": (3072, 7168), "faced": ("south",),
                        "source": "VP walk_through: deep plan, narrow mouth"},
    "pawn_shop":    {"interior": (4096, 4096), "faced": ("east",),
                     "source": "VP open_front"},
    "ferry_office": {"interior": (4096, 3072), "faced": ("south",),
                     "source": "VP open_front, single doorway"},
    "workshop_bar": {"interior": (4096, 4096), "faced": ("north",),
                     "source": "VP bar in the hand-shaped district"},
    "works_canteen": {"interior": (5120, 4096), "faced": ("east",),
                      "source": "VP open_front onto the yard"},
}

#: Which cells absorb the residue. Named here so the solver never has to guess
#: which parts of the city are allowed to change size: the plaza, the
#: cemetery, the works yard and the alleys, and nothing else.
SLACK_AREAS = ("market_plaza", "cemetery", "works_yard")


# --- the boundary: what the city ends with, side by side ------------------
#
# A city has to stop, and how it stops is a design decision per side rather
# than a fallback. The kinds are `bloodmap.joins`'s edge family, three of
# which are measured in the corpus:
#
#   end_wall            E3M1 s0/s339/s343: a raised mass whose floor is the
#                       wall top (379), sky ceiling, blocking faces
#   waterfront          DWE3M10: shore at the sea's z, the sea panning
#                       (pal 10, pan_floor + pan_always, velocity 10, angle
#                       900, drag), then a horizon sector with floor AND
#                       ceiling both 3678 and the parallax bit on both
#   chasm               DWE3M1: the outermost sectors 26-28 player heights
#                       below the rim, rock tiles
#   enclosure_backdrop  walls ringing the city with fake masses beyond and no
#                       interiors -- NO CORPUS PRECEDENT LOCATED YET, so it is
#                       named here and carries no join row; asking for one
#                       fails loudly rather than guessing
#   building_back       the backs of the perimeter buildings ARE the boundary
#   gate                the way out of the level
#
# `building_back` is the one with a consequence for the solve: where the
# city ends in the backs of its own buildings there is no perimeter lane to
# build, because nothing walks behind them. The solver drops it.
BOUNDARY = {
    "south": [{"kind": "waterfront", "from": "quay_w", "to": "quay_spur",
               "note": "the quay: shore, sea, horizon (DWE3M10's dialect)"}],
    "north": [{"kind": "building_back", "from": "nw", "to": "n_ave"},
              {"kind": "end_wall", "at": "n_ave",
               "note": "the avenue reaches the boundary and stops"},
              {"kind": "building_back", "from": "n_ave", "to": "n_spur"},
              {"kind": "end_wall", "at": "n_spur",
               "note": "the rail spur stops"}],
    "east": [{"kind": "building_back", "from": "n_spur", "to": "quay_spur"}],
    "west": [{"kind": "building_back", "from": "nw", "to": "quay_w"},
             {"kind": "end_wall", "at": "row_west",
              "note": "the west street's T against the perimeter"}],
}

#: Sides whose boundary is the backs of buildings: no perimeter lane is built
#: there, because nothing walks behind them.
def building_back_sides():
    return tuple(side for side, chain in BOUNDARY.items()
                 if all(segment["kind"] in ("building_back", "end_wall")
                        for segment in chain))

# ---------------------------------------------------------------------------
# A WIDTH CLASS IS THE FULL WIDTH (owner queue item 30a, decided 2026-09-03)
# ---------------------------------------------------------------------------

#: `resolution.WIDTH_UNITS` gives a street's width. It means the FULL width --
#: carriageway plus the pavements beside it -- and not the carriageway alone.
#: Read that way E3M1's east arm is a ROW with residual exactly 0, and the
#: plan's own grid already sums its streets that way.
#:
#: So a gutter's solved span is the whole street, and the carriageway is what
#: is left after the pavements are taken out of it. Measured on E3M1: its nine
#: pavement sectors have a median narrow dimension of **2048** and its four
#: road sectors are 4096, 4096, 5120 and 7456 across. A pavement is 2048 wide
#: and a carriageway is never narrower than 2048.
#:
#: Where a gutter cannot afford both bands it gets ONE, on its low-coordinate
#: side, and where it cannot afford one it gets none and is all carriageway.
#: A one-sided pavement is not a compromise: E3M1's east arm is exactly that,
#: 6144 across as 4096 of road and one 2048 pavement.
WIDTH_IS_FULL_WIDTH = True
PAVEMENT_BAND = 2048
MIN_CARRIAGEWAY = 2048


def pavement_bands(full_width: int, *, band: int = PAVEMENT_BAND,
                   floor: int = MIN_CARRIAGEWAY) -> tuple[int, int]:
    """(low-side band, high-side band) for a street of this full width."""
    if full_width - 2 * band >= floor:
        return band, band
    if full_width - band >= floor:
        return band, 0
    return 0, 0

