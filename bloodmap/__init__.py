"""Verified, dependency-free tooling for Monolith Blood MAP files."""

from .format import BloodMapError, parse_map, read_map, write_map
from .composition import (
    CompositionError, CompositionResult, DestinationMap, connect_portals,
    insert_fragment, transform_fragment,
)
from .fragment import (
    FragmentError, IndexMap, LevelFragment, apply_fragment_in_place, extract_fragment,
)
from .model import DiskMap, LevelIR

__all__ = [
    "BloodMapError",
    "CompositionError",
    "CompositionResult",
    "DestinationMap",
    "DiskMap",
    "FragmentError",
    "IndexMap",
    "LevelIR",
    "LevelFragment",
    "apply_fragment_in_place",
    "connect_portals",
    "extract_fragment",
    "insert_fragment",
    "parse_map",
    "read_map",
    "transform_fragment",
    "write_map",
]

__version__ = "0.3.0"
