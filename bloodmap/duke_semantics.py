"""Semantic inventory for classic Duke3D mechanisms.

This module deliberately describes runtime intent rather than exposing raw
lotags to a conversion profile.  The mappings are grounded in EDuke32's
``game.h``, ``actors.cpp``, and ``sector.cpp``.  It is small on purpose: a
mechanism is only promoted here once its controller topology is understood.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from .duke import DukeDiskMap


CRACK_TILES = frozenset({546, 547, 548, 549})

# EDuke32 source/duke3d/src/game.h.  Values absent from this table are kept as
# explicit unknowns: an integer tag alone is not conversion evidence.
EFFECTOR_SEMANTICS: dict[int, tuple[str, str]] = {
    0: ("rotating_sector", "faithfully-convertible"),
    1: ("rotation_pivot", "controller"),
    2: ("earthquake", "visual-only-approximation"),
    3: ("shot_out_random_lighting", "visual-only-approximation"),
    4: ("random_lighting", "visual-only-approximation"),
    7: ("teleport_or_water_link", "faithfully-convertible"),
    8: ("door_linked_lighting", "visual-only-approximation"),
    9: ("door_linked_lighting", "visual-only-approximation"),
    10: ("door_autoclose", "unsupported"),
    11: ("swinging_door", "unsupported"),
    12: ("switchable_lighting", "semantically-approximated"),
    13: ("linked_explosion", "semantically-approximated"),
    15: ("sliding_sector", "faithfully-convertible"),
    18: ("incremental_z_motion", "unsupported"),
    19: ("explosion_lowers_ceiling", "unsupported"),
    20: ("stretch_bridge", "unsupported"),
    21: ("drop_floor", "unsupported"),
    22: ("teeth_door", "unsupported"),
    23: ("one_way_teleport", "unsupported"),
    24: ("conveyor", "faithfully-convertible"),
    25: ("piston", "unsupported"),
    26: ("escalator", "unsupported"),
    27: ("demo_camera", "visual-only-approximation"),
    28: ("lightning", "visual-only-approximation"),
    29: ("waves", "visual-only-approximation"),
    30: ("two_way_train", "unsupported"),
    31: ("floor_rise_fall", "faithfully-convertible"),
    32: ("ceiling_rise_fall", "faithfully-convertible"),
    33: ("quake_debris", "visual-only-approximation"),
    34: ("conveyor", "unsupported"),
    36: ("projectile_shooter", "unsupported"),
}


def analyze_duke_mechanisms(duke: DukeDiskMap) -> dict[str, Any]:
    """Return a stable, source-independent behavior inventory for a Duke map.

    Relationships use the Duke tag graph (switch/activator/effectors and
    crack/explosion groups), so callers can use this function on any classic
    v7 board rather than relying on map or object indices.
    """
    effectors = [
        (source_id, sprite)
        for source_id, sprite in enumerate(duke.sprites)
        if sprite.picnum == 1
    ]
    by_hitag: dict[int, list[int]] = defaultdict(list)
    for source_id, sprite in effectors:
        by_hitag[sprite.hitag].append(source_id)

    records: list[dict[str, Any]] = []
    for source_id, sprite in effectors:
        kind, classification = EFFECTOR_SEMANTICS.get(
            sprite.lotag, ("unknown_sector_effector", "unsupported")
        )
        records.append({
            "source_sprite": source_id,
            "source_sector": sprite.sector,
            "lotag": sprite.lotag,
            "hitag": sprite.hitag,
            "kind": kind,
            "classification": classification,
        })

    cracks: list[dict[str, Any]] = []
    explosion_tags = {
        sprite.hitag for _source_id, sprite in effectors if sprite.lotag == 13
    }
    for source_id, sprite in enumerate(duke.sprites):
        if sprite.picnum not in CRACK_TILES:
            continue
        linked = sprite.hitag in explosion_tags
        cracks.append({
            "source_sprite": source_id,
            "source_sector": sprite.sector,
            "tile": sprite.picnum,
            "link": sprite.hitag,
            "kind": "destructible_wall" if linked else "damageable_crack",
            "classification": "semantically-approximated" if linked else "unsupported",
            "linked_effect": "linked_explosion" if linked else None,
        })

    classifications = Counter(record["classification"] for record in records)
    classifications.update(record["classification"] for record in cracks)
    return {
        "$schema": "llmapper.duke-mechanism-inventory",
        "schema_version": 1,
        "counts_by_effector_lotag": dict(sorted(Counter(sprite.lotag for _, sprite in effectors).items())),
        "classifications": dict(sorted(classifications.items())),
        "effectors": records,
        "destructible_walls": cracks,
        "tag_groups": {
            str(tag): sorted(ids) for tag, ids in sorted(by_hitag.items()) if tag
        },
    }
