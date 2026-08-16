"""Design Contract: connecting user intent to hard assertions and soft evidence.

A Design Contract is a set of explicit, testable assertions about a level.
It bridges the gap between design intent ("the crypt should feel constrained")
and measurable evidence (area ratio, ceiling delta, visibility delta).

Contract structure:
  - HARD assertions: structural properties that must be true
    (player start exists, blue key is reachable, exit is reachable)
  - SOFT evidence questions: experiential properties that produce evidence
    ("church should feel much larger than crypt" -> transition probe -> measurements)

The contract is serializable and replayable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .probe_schema import DesignProbe, ProbeResult


class ContractError(ValueError):
    """A design contract constraint was violated."""


# ---------------------------------------------------------------------------
# Assertion types
# ---------------------------------------------------------------------------

@dataclass
class HardAssertion:
    """A structural assertion that must be true for the level to be valid.

    Examples:
      - "player_start_exists"
      - "blue_key_reachable_initially"
      - "graveyard_gate_not_traversable_initially"
      - "exit_reachable_after_required_progression"
      - "no_hard_sequence_break"
    """

    assertion_id: str
    description: str = ""
    assertion_type: str = "structural"  # structural, reachability, progression
    expected: bool = True  # True = must be true, False = must be false
    parameters: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "assertion_id": self.assertion_id,
            "description": self.description,
            "assertion_type": self.assertion_type,
            "expected": self.expected,
            "parameters": self.parameters,
        }

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "HardAssertion":
        return cls(
            assertion_id=str(value["assertion_id"]),
            description=str(value.get("description", "")),
            assertion_type=str(value.get("assertion_type", "structural")),
            expected=bool(value.get("expected", True)),
            parameters=dict(value.get("parameters", {})),
        )


@dataclass
class SoftEvidenceQuestion:
    """An experiential question that produces evidence through probes.

    Examples:
      - "crypt_should_feel_spatially_constrained"
        -> transition probe -> area ratio, ceiling delta
      - "church_should_produce_strong_increase_in_perceived_scale"
        -> transition probe -> area ratio, ceiling delta, visibility delta
      - "locked_graveyard_route_should_be_observable_before_key_acquisition"
        -> visibility probe -> first observation point, route fraction
      - "return_through_church_should_expose_a_meaningful_world_state_change"
        -> revisit probe -> new paths, changed mechanisms, new visibility

    The interpretation of whether the evidence satisfies the design intent
    remains the LLM's responsibility.
    """

    question_id: str
    description: str = ""
    probe_type: str = "transition"  # which probe type to run
    probe_parameters: dict[str, Any] = field(default_factory=dict)
    evidence_metrics: list[str] = field(default_factory=list)  # which measurements to extract
    target_direction: str = "higher"  # "higher", "lower", "different", "present"
    threshold: float | None = None  # optional numeric threshold
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


# ---------------------------------------------------------------------------
# Design Contract
# ---------------------------------------------------------------------------

@dataclass
class DesignContract:
    """A set of explicit, testable assertions about a level.

    Schema: llmapper.design-contract
    Version: 1
    """

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
        **parameters: Any,
    ) -> "DesignContract":
        self.hard_assertions.append(HardAssertion(
            assertion_id=assertion_id, description=description,
            assertion_type=assertion_type, expected=expected,
            parameters=parameters,
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


# ---------------------------------------------------------------------------
# Contract evaluation
# ---------------------------------------------------------------------------

@dataclass
class ContractEvaluation:
    """Result of evaluating a design contract against probe results.

    Schema: llmapper.contract-evaluation
    Version: 1
    """

    contract_name: str
    hard_assertion_results: list[dict[str, Any]] = field(default_factory=list)
    soft_evidence_results: list[dict[str, Any]] = field(default_factory=list)
    overall_status: str = "inconclusive"  # "pass", "fail", "inconclusive"
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


def evaluate_contract(
    contract: DesignContract,
    probe_results: dict[str, ProbeResult],
) -> ContractEvaluation:
    """Evaluate a design contract against a set of probe results.

    probe_results maps question_id -> ProbeResult for soft evidence questions.
    Hard assertions are evaluated based on their type and parameters.
    """
    evaluation = ContractEvaluation(contract_name=contract.name)

    # Evaluate hard assertions
    for assertion in contract.hard_assertions:
        result: dict[str, Any] = {
            "assertion_id": assertion.assertion_id,
            "description": assertion.description,
            "expected": assertion.expected,
            "status": "inconclusive",
        }

        if assertion.assertion_type == "structural":
            if assertion.assertion_id == "player_start_exists":
                # Check if player start sector is valid
                actual = assertion.parameters.get("player_start_valid", False)
                result["actual"] = actual
                result["status"] = "pass" if actual == assertion.expected else "fail"
            elif assertion.assertion_id == "exit_reachable":
                actual = assertion.parameters.get("exit_reachable", False)
                result["actual"] = actual
                result["status"] = "pass" if actual == assertion.expected else "fail"
            else:
                result["status"] = "inconclusive"
                result["note"] = "assertion type not automatically evaluated"
        elif assertion.assertion_type == "reachability":
            if assertion.assertion_id == "blue_key_reachable_initially":
                actual = assertion.parameters.get("target_reachable", False)
                result["actual"] = actual
                result["status"] = "pass" if actual == assertion.expected else "fail"
            else:
                result["status"] = "inconclusive"
                result["note"] = "reachability assertion not automatically evaluated"
        else:
            result["status"] = "inconclusive"
            result["note"] = "assertion type not automatically evaluated"

        evaluation.hard_assertion_results.append(result)

    # Evaluate soft evidence questions
    for question in contract.soft_evidence_questions:
        result: dict[str, Any] = {
            "question_id": question.question_id,
            "description": question.description,
            "probe_type": question.probe_type,
            "status": "inconclusive",
        }

        if question.question_id in probe_results:
            probe_result = probe_results[question.question_id]
            result["probe_status"] = probe_result.status
            result["measurements"] = probe_result.measurements

            # Extract requested metrics
            extracted: dict[str, Any] = {}
            for metric in question.evidence_metrics:
                if metric in probe_result.measurements:
                    extracted[metric] = probe_result.measurements[metric]
            result["extracted_metrics"] = extracted

            # Evaluate against threshold if specified
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
                if probe_result.measurements:
                    result["status"] = "pass"
                else:
                    result["status"] = "fail"
        else:
            result["status"] = "not_evaluated"
            result["note"] = "no probe result provided for this question"

        evaluation.soft_evidence_results.append(result)

    # Determine overall status
    hard_pass = all(r["status"] == "pass" for r in evaluation.hard_assertion_results) if evaluation.hard_assertion_results else True
    soft_pass = all(r["status"] == "pass" for r in evaluation.soft_evidence_results) if evaluation.soft_evidence_results else True
    if hard_pass and soft_pass:
        evaluation.overall_status = "pass"
    else:
        evaluation.overall_status = "fail"

    return evaluation
