"""Verified, dependency-free tooling for Blood and Duke3D Build MAP files."""

from .format import BloodMapError, parse_map, read_map, write_map
from .composition import (
    AttachmentResult, CompositionError, CompositionResult, DestinationMap, PathwayResult,
    attach_fragment, connect_portals, connect_with_pathway, find_layout_conflicts,
    insert_fragment, transform_fragment,
)
from .build_ir import BuildDiagnostic, BuildIR, BuildIRError, validate_build_ir
from .construction import (
    ConstructionError, LevelBuilder, SectorAllocation, new_level, portal_profiles,
)
from .conversion import ConversionError, GAME_PROFILES, convert_build_ir, convert_shade, native_scale
from .design import DesignUnderstandingError, design_fingerprint
from .doom import DoomError, parse_wad, read_wad
from .doom_convert import DoomConversionError, convert_doom_to_blood
from .mechanisms import SemanticLevel, solve_progression
from .semantics import ObservationError, blood_to_semantic_level, observe_level
from .experience import (
    ExperienceProbeError, probe_progression, probe_route, probe_transition, probe_visibility,
)
from .spatial import SpatialAnalysisError, analyze_spatial, spatial_selection_context
from .workspace import (
    WorkspaceError, append_decision, append_episode, append_evidence, initialize_project,
    make_level_slice, store_level_slice,
)
from .designs import DesignedLevel, build_first_puzzle_room
from .differential import compare_e3l1_pair, compare_hand_converted_pair, infer_xy_scale
from .duke import (
    DukeDiskMap, DukeMapError, encode_duke_map, parse_duke_map, read_duke_map, write_duke_map,
)
from .fragment import (
    BehaviorClosureResult, FragmentError, IndexMap, LevelFragment,
    apply_fragment_in_place, extract_behavior_closed_fragment, extract_fragment,
)
from .model import DiskMap, LevelIR
from .oracle import run_eduke32_oracle
from .recipe import RecipeError, RecipeResult, build_composition_recipe

__all__ = [
    "AttachmentResult",
    "BloodMapError",
    "BuildDiagnostic",
    "BuildIR",
    "BuildIRError",
    "BehaviorClosureResult",
    "CompositionError",
    "CompositionResult",
    "ConstructionError",
    "ConversionError",
    "DoomConversionError",
    "DoomError",
    "DesignUnderstandingError",
    "ExperienceProbeError",
    "DestinationMap",
    "DesignedLevel",
    "DiskMap",
    "DukeDiskMap",
    "DukeMapError",
    "FragmentError",
    "IndexMap",
    "LevelIR",
    "LevelBuilder",
    "LevelFragment",
    "ObservationError",
    "SemanticLevel",
    "PathwayResult",
    "RecipeError",
    "RecipeResult",
    "SpatialAnalysisError",
    "WorkspaceError",
    "SectorAllocation",
    "GAME_PROFILES",
    "apply_fragment_in_place",
    "analyze_spatial",
    "blood_to_semantic_level",
    "attach_fragment",
    "append_decision",
    "append_episode",
    "append_evidence",
    "build_composition_recipe",
    "build_first_puzzle_room",
    "compare_e3l1_pair",
    "compare_hand_converted_pair",
    "connect_portals",
    "connect_with_pathway",
    "convert_build_ir",
    "convert_doom_to_blood",
    "convert_shade",
    "design_fingerprint",
    "encode_duke_map",
    "extract_fragment",
    "extract_behavior_closed_fragment",
    "find_layout_conflicts",
    "insert_fragment",
    "infer_xy_scale",
    "initialize_project",
    "new_level",
    "observe_level",
    "native_scale",
    "parse_map",
    "parse_duke_map",
    "parse_wad",
    "portal_profiles",
    "probe_progression",
    "probe_route",
    "probe_transition",
    "probe_visibility",
    "read_map",
    "read_duke_map",
    "read_wad",
    "run_eduke32_oracle",
    "spatial_selection_context",
    "solve_progression",
    "make_level_slice",
    "store_level_slice",
    "transform_fragment",
    "validate_build_ir",
    "write_map",
    "write_duke_map",
]

__version__ = "1.0.0"
