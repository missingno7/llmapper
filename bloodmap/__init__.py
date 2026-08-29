"""Verified, dependency-free tooling for Blood and Duke3D Build MAP files."""

from .format import BloodMapError, parse_map, read_map, write_map
from .composition import (
    AttachmentResult, CompositionError, CompositionResult, DestinationMap, PathwayResult,
    attach_fragment, connect_portals, connect_with_pathway, find_layout_conflicts,
    insert_fragment, transform_fragment,
)
from .build_ir import BuildDiagnostic, BuildIR, BuildIRError, validate_build_ir
from .construction import ConstructionError, LevelBuilder, SectorAllocation, new_level, portal_profiles
from .geometry_audit import (
    AuthoredGeometryError, audit_geometry, audit_markdown, audit_svg,
    construction_preflight, validate_authored_geometry, validate_authored_level,
)
from .planar_layout import CompiledLayout, PlanarLayout, PlanarLayoutError
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
from .blood_types import classify as classify_blood_type
from .contents import explain_mechanisms, inventory_map, multiplayer_layout
from .sight import SightError, line_of_sight, spawn_sight_report
from .exposure import ExposureError, route_exposure_report, spawn_neighborhood_report
from .patterns import PatternError, inspect_pattern, load_catalog, mine_directory, query_catalog
from .placement import (
    PlacementError, mine_attachments, observe_sprite_attachment, validate_attachments, validate_use_poses,
)
from .progression import (
    ProgressionError, analyze_progression, classify_mechanisms, completion_witness,
)
from .player_space import (
    PlayerSpaceError, PLAYER_PROFILES, compare_transition, inspect_connection,
    inspect_space, player_profile, present_space,
)
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
from .sector_map import render_sector_map
from .oracle import run_eduke32_oracle
from .recipe import RecipeError, RecipeResult, build_composition_recipe
from .decompiler import DecompilerError, LevelSource, decompile_level, emit_python_source
from .viewpoints import (
    ViewpointError, ViewpointSpec, apply_viewpoint, prepare_viewpoints, resolve_viewpoint,
    viewpoint_manifest, viewpoint_variant_diff,
)
from .authoring_loop import (
    AuthoredAssembly, AuthoredIntent, AuthoredTransition, AuthoringIteration,
    AuthoringLoopError, Candidate, NextAction, ProbeRequest, ReasoningReview, ReviewClaim,
    attach_review, compare_iterations, evaluate_candidate, record_review, resolve_evidence,
)
from .morphology import MorphologyError, analyze_morphology
from .understanding import understand_map
from .structures import StructureError, detect_structures, structure_index
from .vocabulary import (
    Anchor, Decoration, VocabularyError, arc_points, arc_through, outline, recess,
    sprite_repeats, staircase, vocabulary_manifest,
)
from .levelprog import (
    Assembly, Frame, LevelProgram, LevelProgramError, LightSourceDecl, Room, Style,
    ceiling_detail, floor_detail, native_detail, wall_detail,
)

__all__ = [
    "AuthoredAssembly",
    "AuthoredIntent",
    "AuthoredTransition",
    "AuthoringIteration",
    "AuthoringLoopError",
    "Candidate",
    "NextAction",
    "ProbeRequest",
    "ReasoningReview",
    "ReviewClaim",
    "ViewpointError",
    "ViewpointSpec",
    "apply_viewpoint",
    "attach_review",
    "compare_iterations",
    "evaluate_candidate",
    "prepare_viewpoints",
    "record_review",
    "resolve_evidence",
    "resolve_viewpoint",
    "viewpoint_manifest",
    "viewpoint_variant_diff",
    "AttachmentResult",
    "BloodMapError",
    "BuildDiagnostic",
    "BuildIR",
    "BuildIRError",
    "BehaviorClosureResult",
    "CompositionError",
    "CompositionResult",
    "AuthoredGeometryError",
    "CompiledLayout",
    "PlanarLayout",
    "PlanarLayoutError",
    "audit_geometry",
    "construction_preflight",
    "validate_authored_geometry",
    "validate_authored_level",
    "ConversionError",
    "DoomConversionError",
    "DoomError",
    "DesignUnderstandingError",
    "ExperienceProbeError",
    "DestinationMap",
    "DesignedLevel",
    "DecompilerError",
    "DiskMap",
    "DukeDiskMap",
    "DukeMapError",
    "FragmentError",
    "IndexMap",
    "LevelIR",
    "LevelSource",
    "LevelBuilder",
    "LevelFragment",
    "ObservationError",
    "PathwayResult",
    "SemanticLevel",
    "PLAYER_PROFILES",
    "PlayerSpaceError",
    "RecipeError",
    "RecipeResult",
    "SightError",
    "SpatialAnalysisError",
    "ExposureError",
    "MorphologyError",
    "PatternError",
    "PlacementError",
    "ProgressionError",
    "WorkspaceError",
    "SectorAllocation",
    "GAME_PROFILES",
    "apply_fragment_in_place",
    "analyze_spatial",
    "classify_blood_type",
    "explain_mechanisms",
    "inventory_map",
    "line_of_sight",
    "multiplayer_layout",
    "spawn_sight_report",
    "spawn_neighborhood_report",
    "route_exposure_report",
    "analyze_morphology",
    "understand_map",
    "mine_directory",
    "query_catalog",
    "inspect_pattern",
    "load_catalog",
    "mine_attachments",
    "observe_sprite_attachment",
    "validate_attachments",
    "validate_use_poses",
    "analyze_progression",
    "classify_mechanisms",
    "completion_witness",
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
    "Anchor",
    "Assembly",
    "Decoration",
    "Frame",
    "LevelProgram",
    "LevelProgramError",
    "LightSourceDecl",
    "Room",
    "Style",
    "StructureError",
    "VocabularyError",
    "arc_points",
    "arc_through",
    "ceiling_detail",
    "detect_structures",
    "floor_detail",
    "native_detail",
    "outline",
    "recess",
    "sprite_repeats",
    "staircase",
    "structure_index",
    "vocabulary_manifest",
    "wall_detail",
    "decompile_level",
    "emit_python_source",
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
    "player_profile",
    "portal_profiles",
    "present_space",
    "compare_transition",
    "inspect_connection",
    "inspect_space",
    "probe_progression",
    "probe_route",
    "probe_transition",
    "probe_visibility",
    "read_map",
    "read_duke_map",
    "read_wad",
    "render_sector_map",
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
