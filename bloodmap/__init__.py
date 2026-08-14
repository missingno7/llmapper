"""Verified, dependency-free tooling for Monolith Blood MAP files."""

from .format import BloodMapError, parse_map, read_map, write_map
from .composition import (
    AttachmentResult, CompositionError, CompositionResult, DestinationMap,
    attach_fragment, connect_portals, insert_fragment, transform_fragment,
)
from .fragment import (
    FragmentError, IndexMap, LevelFragment, apply_fragment_in_place, extract_fragment,
)
from .model import DiskMap, LevelIR
from .semantics import ObservationError, observe_level

__all__ = [
    "AttachmentResult",
    "BloodMapError",
    "CompositionError",
    "CompositionResult",
    "DestinationMap",
    "DiskMap",
    "FragmentError",
    "IndexMap",
    "LevelIR",
    "LevelFragment",
    "ObservationError",
    "apply_fragment_in_place",
    "attach_fragment",
    "connect_portals",
    "extract_fragment",
    "insert_fragment",
    "observe_level",
    "parse_map",
    "read_map",
    "transform_fragment",
    "write_map",
]

__version__ = "0.6.0"
