"""Typed, deterministic contracts for the Gemini -> GPT -> Python research workflow.

This module validates artifact structure and provenance only. It does not call
AI providers, interpret free-form conclusions, or turn AI opinions into results.
"""
from __future__ import annotations
import hashlib
import json
from typing import Any

PROPOSAL_STATUSES = {"draft", "ready_for_adversarial_review"}
REVIEW_VERDICTS = {"accept_for_test", "revise", "reject"}
RISK_LEVELS = {"low", "medium", "high", "critical"}


def canonical_hash(value: dict[str, Any]) -> str:
    try:
        payload = json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("artifact must contain finite JSON-compatible values") from exc
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _required_text(data: dict, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value.strip()


def validate_research_proposal(proposal: dict) -> dict:
    """Validate a researcher proposal; no performance claims are accepted."""
    if proposal.get("artifact_type") != "research_proposal":
        raise ValueError("artifact_type must be research_proposal")
    _required_text(proposal, "experiment_id")
    _required_text(proposal, "strategy_id")
    _required_text(proposal, "strategy_version")
    _required_text(proposal, "hypothesis")
    _required_text(proposal, "market_mechanism")
    _required_text(proposal, "entry_rules")
    _required_text(proposal, "exit_rules")
    _required_text(proposal, "invalidation_rules")
    if proposal.get("status") not in PROPOSAL_STATUSES:
        raise ValueError("proposal status is not allowed")
    params = proposal.get("parameter_search_space")
    if not isinstance(params, dict) or not params:
        raise ValueError("parameter_search_space must be a non-empty object")
    for name, spec in params.items():
        if not isinstance(name, str) or not name.strip() or not isinstance(spec, dict):
            raise ValueError("each parameter must have a named specification object")
        if not {"type", "values"}.issubset(spec):
            raise ValueError(f"parameter {name} requires type and values")
        if not isinstance(spec["values"], list) or not spec["values"]:
            raise ValueError(f"parameter {name} values must be a non-empty list")
    if "backtest_result" in proposal or "win_rate" in proposal or "net_points" in proposal:
        raise ValueError("research proposal cannot contain backtest performance claims")
    return {"artifact_type": "research_proposal", "artifact_sha256": canonical_hash(proposal),
            "experiment_id": proposal["experiment_id"], "status": proposal["status"]}


def validate_adversarial_review(review: dict, proposal: dict) -> dict:
    """Validate GPT review linkage and required counter-arguments."""
    proposal_meta = validate_research_proposal(proposal)
    if review.get("artifact_type") != "adversarial_review":
        raise ValueError("artifact_type must be adversarial_review")
    _required_text(review, "reviewer_model")
    if review.get("experiment_id") != proposal_meta["experiment_id"]:
        raise ValueError("review experiment_id does not match proposal")
    if review.get("proposal_sha256") != proposal_meta["artifact_sha256"]:
        raise ValueError("review must reference the exact proposal SHA-256")
    if review.get("verdict") not in REVIEW_VERDICTS:
        raise ValueError("review verdict is not allowed")
    findings = review.get("findings")
    if not isinstance(findings, list):
        raise ValueError("findings must be a list")
    for index, finding in enumerate(findings):
        if not isinstance(finding, dict):
            raise ValueError(f"finding {index} must be an object")
        _required_text(finding, "issue")
        _required_text(finding, "evidence_or_test")
        _required_text(finding, "severity")
        if finding["severity"] not in RISK_LEVELS:
            raise ValueError(f"finding {index} has invalid severity")
    if review["verdict"] == "accept_for_test" and any(
        finding["severity"] == "critical" for finding in findings
    ):
        raise ValueError("critical finding prevents accept_for_test verdict")
    return {"artifact_type": "adversarial_review", "artifact_sha256": canonical_hash(review),
            "experiment_id": review["experiment_id"], "verdict": review["verdict"],
            "finding_count": len(findings)}


def create_research_packet(proposal: dict, review: dict, experiment_spec: dict) -> dict:
    """Create a handoff packet; never execute or approve an experiment."""
    proposal_meta = validate_research_proposal(proposal)
    review_meta = validate_adversarial_review(review, proposal)
    if experiment_spec.get("experiment_id") != proposal_meta["experiment_id"]:
        raise ValueError("experiment spec does not match proposal experiment_id")
    if review_meta["verdict"] != "accept_for_test":
        raise ValueError("only proposals accepted for testing can be handed to Python")
    if experiment_spec.get("approval_status") not in (None, "approved"):
        raise ValueError("experiment spec approval status is not approved")
    return {
        "packet_version": "1.0.0",
        "experiment_id": proposal_meta["experiment_id"],
        "proposal_sha256": proposal_meta["artifact_sha256"],
        "review_sha256": review_meta["artifact_sha256"],
        "experiment_spec_sha256": canonical_hash(experiment_spec),
        "handoff_status": "ready_for_python_validation",
        "python_execution_status": "not_started",
        "formal_result_status": "not_available",
        "human_approval_required": True,
    }
