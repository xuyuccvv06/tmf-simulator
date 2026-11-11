import copy
import pytest

from research_engine.research_workflow import (
    create_research_packet, validate_adversarial_review, validate_research_proposal,
)


@pytest.fixture
def proposal():
    return {
        "artifact_type": "research_proposal",
        "experiment_id": "exp_12345678901234567890",
        "strategy_id": "opening_fvg",
        "strategy_version": "0.1.0",
        "status": "ready_for_adversarial_review",
        "hypothesis": "Opening imbalance continuation may have positive expectancy",
        "market_mechanism": "Opening price displacement followed by continuation",
        "entry_rules": "Enter only after a completed confirmation bar",
        "exit_rules": "Use predefined stop and target",
        "invalidation_rules": "Invalidate if price closes back through the gap",
        "parameter_search_space": {"min_gap_points": {"type": "integer", "values": [5, 10, 15]}},
    }


@pytest.fixture
def review(proposal):
    from research_engine.research_workflow import canonical_hash
    return {
        "artifact_type": "adversarial_review",
        "reviewer_model": "GPT",
        "experiment_id": proposal["experiment_id"],
        "proposal_sha256": canonical_hash(proposal),
        "verdict": "accept_for_test",
        "findings": [{
            "issue": "Potential opening volatility confound",
            "evidence_or_test": "Stratify results by opening range and volatility regime",
            "severity": "medium",
        }],
    }


def test_proposal_has_stable_hash_and_cannot_claim_results(proposal):
    result = validate_research_proposal(proposal)
    assert len(result["artifact_sha256"]) == 64
    invalid = copy.deepcopy(proposal)
    invalid["win_rate"] = 0.8
    with pytest.raises(ValueError, match="performance claims"):
        validate_research_proposal(invalid)


def test_review_must_reference_exact_proposal_hash(proposal, review):
    assert validate_adversarial_review(review, proposal)["verdict"] == "accept_for_test"
    altered = copy.deepcopy(proposal)
    altered["hypothesis"] = "Changed after review"
    with pytest.raises(ValueError, match="SHA-256"):
        validate_adversarial_review(review, altered)


def test_critical_finding_cannot_be_accepted(proposal, review):
    review["findings"][0]["severity"] = "critical"
    with pytest.raises(ValueError, match="critical"):
        validate_adversarial_review(review, proposal)


def test_packet_handoff_requires_accepted_review_and_matching_experiment(proposal, review):
    spec = {"experiment_id": proposal["experiment_id"], "strategy_id": "opening_fvg"}
    packet = create_research_packet(proposal, review, spec)
    assert packet["handoff_status"] == "ready_for_python_validation"
    assert packet["python_execution_status"] == "not_started"
    assert packet["formal_result_status"] == "not_available"
    assert packet["human_approval_required"] is True


def test_rejected_review_cannot_be_handed_to_python(proposal, review):
    review["verdict"] = "revise"
    with pytest.raises(ValueError, match="accepted for testing"):
        create_research_packet(proposal, review, {"experiment_id": proposal["experiment_id"]})


def test_experiment_mismatch_is_rejected(proposal, review):
    with pytest.raises(ValueError, match="does not match"):
        create_research_packet(proposal, review, {"experiment_id": "exp_other"})
