"""Design Contract: connecting user intent to hard assertions and soft evidence.

A Design Contract is a set of explicit, testable assertions about a level.
It bridges the gap between design intent ("the crypt should feel constrained")
and measurable evidence (area ratio, ceiling delta, visibility delta).

Hard assertions are evaluated from the candidate map, probe results, and
authored-layout reports. Caller-supplied booleans are never treated as proof.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .analysis import validate_map
from .geometry_audit import validate_authored_geometry, validate_authored_level
from .model import DiskMap, LevelIR
from .probe_schema import DesignProbe, ProbeResult


class ContractError(ValueError):
    """A design contract constraint was violated."""


@dataclass
class HardAssertion:
    """A structural assertion that must be true for the level to be valid."""

    assertion_id: str
    description: str = ""
    assertion_type: str = "structural"  # structural, reachability, progression, authored
    expected: bool = True
    advisory: bool = False
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assertion_id": self.assertion_id,
            "description": self.description,
            "assertion_type": self.assertion_type,
            "expected": self.expected,
            "advisory": self.advisory,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "HardAssertion":
        return cls(
            assertion_id=str(value["assertion_id"]),
            description=str(value.get("description", "")),
            assertion_type=str(value.get("assertion_type", "structural")),
            expected=bool(value.get("expected", True)),
            advisory=bool(value.get("advisory", False)),
            parameters=dict(value.get("parameters", {})),
        )


@dataclass
class SoftEvidenceQuestion:
    """An experiential question that produces evidence through probes."""

    question_id: str
    description: str = ""
    probe_type: str = "transition"
    probe_parameters: dict[str, Any] = field(default_factory=dict)
    evidence_metrics: list[str] = field(default_factory=list)
    target_direction: str = "higher"
    threshold: float | None = None
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "question_id": self.question_id,
            "description": self.description,
            "probe_type": self.probe_type,
            "probe_parameters": self.probe_parameters,
            "evidence_metrics": self.evidence_metrics,
            "target_direction": self.target_direction,
        }
        if self.threshold is not None:
            result["threshold"] = self.threshold
        if self.notes:
            result["notes"] = self.notes
        return result

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "SoftEvidenceQuestion":
        return cls(
            question_id=str(value["question_id"]),
            description=str(value.get("description", "")),
            probe_type=str(value.get("probe_type", "transition")),
            probe_parameters=dict(value.get("probe_parameters", {})),
            evidence_metrics=list(value.get("evidence_metrics", [])),
            target_direction=str(value.get("target_direction", "higher")),
            threshold=float(value["threshold"]) if "threshold" in value and value["threshold"] is not None else None,
            notes=str(value.get("notes", "")),
        )


@dataclass
class DesignContract:
    """A set of explicit, testable assertions about a level."""

    name: str = ""
    brief: str = ""
    hard_assertions: list[HardAssertion] = field(default_factory=list)
    soft_evidence_questions: list[SoftEvidenceQuestion] = field(default_factory=list)
    schema: str = "llmapper.design-contract"
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": self.schema,
            "schema_version": self.schema_version,
            "name": self.name,
            "brief": self.brief,
            "hard_assertions": [a.to_dict() for a in self.hard_assertions],
            "soft_evidence_questions": [q.to_dict() for q in self.soft_evidence_questions],
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "DesignContract":
        if value.get("$schema") != "llmapper.design-contract":
            raise ContractError(f"not a design contract: {value.get('$schema')}")
        return cls(
            name=str(value.get("name", "")),
            brief=str(value.get("brief", "")),
            hard_assertions=[HardAssertion.from_dict(a) for a in value.get("hard_assertions", [])],
            soft_evidence_questions=[SoftEvidenceQuestion.from_dict(q) for q in value.get("soft_evidence_questions", [])],
        )

    def add_hard_assertion(
        self, assertion_id: str, description: str = "",
        assertion_type: str = "structural", expected: bool = True,
        advisory: bool = False, **parameters: Any,
    ) -> "DesignContract":
        self.hard_assertions.append(HardAssertion(
            assertion_id=assertion_id, description=description,
            assertion_type=assertion_type, expected=expected,
            advisory=advisory, parameters=parameters,
        ))
        return self

    def add_soft_evidence_question(
        self, question_id: str, description: str = "",
        probe_type: str = "transition",
        probe_parameters: dict[str, Any] | None = None,
        evidence_metrics: list[str] | None = None,
        target_direction: str = "higher",
        threshold: float | None = None,
        notes: str = "",
    ) -> "DesignContract":
        self.soft_evidence_questions.append(SoftEvidenceQuestion(
            question_id=question_id, description=description,
            probe_type=probe_type,
            probe_parameters=probe_parameters or {},
            evidence_metrics=evidence_metrics or [],
            target_direction=target_direction,
            threshold=threshold,
            notes=notes,
        ))
        return self


@dataclass
class ContractEvaluation:
    """Result of evaluating a design contract against a candidate and probes."""

    contract_name: str
    hard_assertion_results: list[dict[str, Any]] = field(default_factory=list)
    soft_evidence_results: list[dict[str, Any]] = field(default_factory=list)
    overall_status: str = "inconclusive"
    schema: str = "llmapper.contract-evaluation"
    schema_version: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "$schema": self.schema,
            "schema_version": self.schema_version,
            "contract_name": self.contract_name,
            "hard_assertion_results": self.hard_assertion_results,
            "soft_evidence_results": self.soft_evidence_results,
            "overall_status": self.overall_status,
        }

    def blocking_hard_failures(self) -> list[dict[str, Any]]:
        return [
            item for item in self.hard_assertion_results
            if not item.get("advisory") and item.get("status") != "pass"
        ]

    def archive_admissible(self) -> bool:
        return not self.blocking_hard_failures()


@dataclass
class ContractContext:
    disk: DiskMap | None = None
    level: LevelIR | None = None
    build: Any = None
    authored_report: dict[str, Any] | None = None
    world_state: Any = None
    probe_results: dict[str, ProbeResult] = field(default_factory=dict)
    connection_report: list[dict[str, Any]] | None = None
    allocations: dict[str, int] | None = None


def _candidate_level(ctx: ContractContext) -> LevelIR | None:
    if ctx.level is not None:
        return ctx.level
    if ctx.disk is not None:
        return ctx.disk.to_level_ir()
    if ctx.build is not None and getattr(ctx.build, "source_game", None) == "blood":
        native = (ctx.build.native or {}).get("document")
        if native:
            # BuildIR native document is LevelIR-shaped for blood-level-ir-v1.
            from .model import LevelIR as Level
            if isinstance(native, Level):
                return native
    return None


def _candidate_disk(ctx: ContractContext) -> DiskMap | None:
    if ctx.disk is not None:
        return ctx.disk
    level = _candidate_level(ctx)
    if level is not None:
        return level.to_disk_map()
    return None


def _bool_status(actual: bool | None, expected: bool, *, note: str | None = None) -> dict[str, Any]:
    if actual is None:
        result = {"actual": None, "status": "not_evaluated"}
        if note:
            result["note"] = note
        return result
    return {
        "actual": actual,
        "status": "pass" if actual == expected else "fail",
        **({"note": note} if note else {}),
    }


def _eval_player_start_exists(assertion: HardAssertion, ctx: ContractContext) -> dict[str, Any]:
    disk = _candidate_disk(ctx)
    if disk is not None:
        sector = int(disk.header.get("start_sector", -1))
        actual = 0 <= sector < len(disk.sectors)
        return _bool_status(actual, assertion.expected)
    if ctx.build is not None:
        sector = int(ctx.build.player_start["sector"])
        actual = 0 <= sector < len(ctx.build.sectors)
        return _bool_status(actual, assertion.expected)
    return _bool_status(None, assertion.expected, note="no candidate map was provided")


def _eval_exit_reachable(assertion: HardAssertion, ctx: ContractContext) -> dict[str, Any]:
    for result in ctx.probe_results.values():
        if result.probe_type in {"access", "progression", "route"} and result.status == "pass":
            target = assertion.parameters.get("target_sector")
            if target is None or (result.route and int(result.route[-1]) == int(target)):
                return _bool_status(True, assertion.expected)
    disk = _candidate_disk(ctx)
    if disk is None:
        return _bool_status(None, assertion.expected, note="no candidate map or probe result for exit reachability")
    return _bool_status(False, assertion.expected, note="no passing access/progression probe established an exit route")


def _eval_native_structure_valid(assertion: HardAssertion, ctx: ContractContext) -> dict[str, Any]:
    disk = _candidate_disk(ctx)
    if disk is None:
        return _bool_status(None, assertion.expected, note="no candidate map was provided")
    errors = [item for item in validate_map(disk) if item.severity == "error"]
    return _bool_status(len(errors) == 0, assertion.expected, note=None if not errors else errors[0].code)


def _authored_diagnostics(ctx: ContractContext):
    if ctx.authored_report and "diagnostics" in ctx.authored_report:
        return ctx.authored_report["diagnostics"]
    source = _candidate_level(ctx) or _candidate_disk(ctx)
    if source is None:
        return None
    return [
        {"severity": item.severity, "code": item.code, "message": item.message, "location": item.location}
        for item in validate_authored_level(
            source,
            connection_report=ctx.connection_report,
            allocations=ctx.allocations,
        )
    ]


def _eval_authored_codes(assertion: HardAssertion, ctx: ContractContext, codes: set[str], *, empty_means_true: bool = True) -> dict[str, Any]:
    diagnostics = _authored_diagnostics(ctx)
    if diagnostics is None:
        return _bool_status(None, assertion.expected, note="no candidate map was provided")
    hits = [item for item in diagnostics if item.get("severity") == "error" and item.get("code") in codes]
    actual = not hits if empty_means_true else bool(hits)
    note = None if not hits else hits[0].get("message")
    return _bool_status(actual, assertion.expected, note=note)


def _eval_blue_key_reachable(assertion: HardAssertion, ctx: ContractContext) -> dict[str, Any]:
    for result in ctx.probe_results.values():
        if result.probe_type in {"access", "progression"}:
            return _bool_status(result.status == "pass", assertion.expected)
    return _bool_status(None, assertion.expected, note="no access/progression probe result was provided")


def _eval_no_authored_errors(assertion: HardAssertion, ctx: ContractContext) -> dict[str, Any]:
    source = _candidate_level(ctx) or _candidate_disk(ctx)
    if source is None:
        return _bool_status(None, assertion.expected, note="no candidate map was provided")
    errors = [item for item in validate_authored_geometry(source) if item.severity == "error"]
    return _bool_status(len(errors) == 0, assertion.expected, note=None if not errors else errors[0].code)


def _eval_mechanisms_wired(assertion: HardAssertion, ctx: ContractContext) -> dict[str, Any]:
    disk = _candidate_disk(ctx)
    if disk is None:
        return _bool_status(None, assertion.expected, note="no candidate map was provided")
    required = list(assertion.parameters.get("channels") or [])
    if not required:
        return _bool_status(True, assertion.expected, note="no required channels named")
    from .analysis import channel_graph
    graph = {item["channel"]: item for item in channel_graph(disk)["channels"]}
    missing = [
        channel for channel in required
        if channel not in graph or not graph[channel]["transmitters"] or not graph[channel]["receivers"]
    ]
    return _bool_status(not missing, assertion.expected, note=None if not missing else f"unwired channels {missing}")


EVALUATORS: dict[str, Any] = {
    "player_start_exists": _eval_player_start_exists,
    "exit_reachable": _eval_exit_reachable,
    "native_structure_valid": _eval_native_structure_valid,
    "authored_geometry_valid": _eval_no_authored_errors,
    "no_unintended_xy_overlap": lambda a, c: _eval_authored_codes(
        a, c, {
            "footprint_partial_area_overlap",
            "footprint_full_containment_a_in_b",
            "footprint_full_containment_b_in_a",
        },
    ),
    "no_unresolved_boundary_contacts": lambda a, c: _eval_authored_codes(
        a, c, {"t_junction", "partial_collinear_overlap", "proper_crossing"},
    ),
    "intended_adjacency_realized": lambda a, c: _eval_authored_codes(
        a, c, {"intended_adjacency_missing", "unresolved_intended_connection", "unintended_portal"},
    ),
    "all_dm_starts_reach_main_network": lambda a, c: _eval_authored_codes(
        a, c, {"all_dm_starts_reach_main_network", "isolated_dm_start", "unreachable_start"},
    ),
    "all_required_resources_reachable": lambda a, c: _eval_authored_codes(
        a, c, {"required_resource_unreachable"},
    ),
    "all_required_mechanisms_wired": _eval_mechanisms_wired,
    "blue_key_reachable_initially": _eval_blue_key_reachable,
}


def evaluate_contract(
    contract: DesignContract,
    probe_results: dict[str, ProbeResult],
    *,
    disk: DiskMap | None = None,
    level: LevelIR | None = None,
    build: Any = None,
    authored_report: dict[str, Any] | None = None,
    world_state: Any = None,
    connection_report: list[dict[str, Any]] | None = None,
    allocations: dict[str, int] | None = None,
) -> ContractEvaluation:
    """Evaluate a design contract against a candidate and probe results.

    Hard assertions name evaluators. Parameters such as ``player_start_valid``
    are ignored as evidence.
    """
    ctx = ContractContext(
        disk=disk, level=level, build=build, authored_report=authored_report,
        world_state=world_state, probe_results=probe_results,
        connection_report=connection_report, allocations=allocations,
    )
    evaluation = ContractEvaluation(contract_name=contract.name)

    for assertion in contract.hard_assertions:
        result: dict[str, Any] = {
            "assertion_id": assertion.assertion_id,
            "description": assertion.description,
            "expected": assertion.expected,
            "advisory": assertion.advisory,
            "status": "inconclusive",
        }
        evaluator = EVALUATORS.get(assertion.assertion_id)
        if evaluator is None:
            result["status"] = "not_evaluated"
            result["note"] = "no evaluator is registered for this assertion"
        else:
            result.update(evaluator(assertion, ctx))
        evaluation.hard_assertion_results.append(result)

    for question in contract.soft_evidence_questions:
        result = {
            "question_id": question.question_id,
            "description": question.description,
            "probe_type": question.probe_type,
            "status": "inconclusive",
        }
        if question.question_id in probe_results:
            probe_result = probe_results[question.question_id]
            result["probe_status"] = probe_result.status
            result["measurements"] = probe_result.measurements
            extracted: dict[str, Any] = {}
            for metric in question.evidence_metrics:
                if metric in probe_result.measurements:
                    extracted[metric] = probe_result.measurements[metric]
            result["extracted_metrics"] = extracted
            if question.threshold is not None and question.evidence_metrics:
                metric_name = question.evidence_metrics[0]
                if metric_name in probe_result.measurements:
                    actual_value = probe_result.measurements[metric_name]
                    if isinstance(actual_value, (int, float)):
                        if question.target_direction == "higher":
                            result["status"] = "pass" if actual_value >= question.threshold else "fail"
                        elif question.target_direction == "lower":
                            result["status"] = "pass" if actual_value <= question.threshold else "fail"
                        result["threshold"] = question.threshold
                        result["actual_value"] = actual_value
            elif question.target_direction == "present":
                result["status"] = "pass" if probe_result.measurements else "fail"
        else:
            result["status"] = "not_evaluated"
            result["note"] = "no probe result provided for this question"
        evaluation.soft_evidence_results.append(result)

    hard_ok = not evaluation.blocking_hard_failures()
    soft_results = evaluation.soft_evidence_results
    soft_ok = all(item["status"] == "pass" for item in soft_results) if soft_results else True
    if not contract.hard_assertions and not soft_results:
        evaluation.overall_status = "inconclusive"
    elif hard_ok and soft_ok:
        evaluation.overall_status = "pass"
    else:
        evaluation.overall_status = "fail"
    return evaluation
