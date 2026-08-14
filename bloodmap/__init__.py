"""Verified, dependency-free tooling for Monolith Blood MAP files."""

from .format import BloodMapError, parse_map, read_map, write_map
from .composition import (
    AttachmentResult, CompositionError, CompositionResult, DestinationMap, PathwayResult,
    attach_fragment, connect_portals, connect_with_pathway, find_layout_conflicts,
    insert_fragment, transform_fragment,
)
from .fragment import (
    BehaviorClosureResult, FragmentError, IndexMap, LevelFragment,
    apply_fragment_in_place, extract_behavior_closed_fragment, extract_fragment,
)
from .model import DiskMap, LevelIR
from .recipe import RecipeError, RecipeResult, build_composition_recipe
from .semantics import ObservationError, observe_level

__all__ = [
    "AttachmentResult",
    "BloodMapError",
    "BehaviorClosureResult",
    "CompositionError",
    "CompositionResult",
    "DestinationMap",
    "DiskMap",
    "FragmentError",
    "IndexMap",
    "LevelIR",
    "LevelFragment",
    "ObservationError",
    "PathwayResult",
    "RecipeError",
    "RecipeResult",
    "apply_fragment_in_place",
    "attach_fragment",
    "build_composition_recipe",
    "connect_portals",
    "connect_with_pathway",
    "extract_fragment",
    "extract_behavior_closed_fragment",
    "find_layout_conflicts",
    "insert_fragment",
    "observe_level",
    "parse_map",
    "read_map",
    "transform_fragment",
    "write_map",
]

__version__ = "0.7.0"
