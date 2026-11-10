"""Orchestrate Gemini proposal generation and GPT adversarial review.

This coordinator stops at a validated handoff packet. It never runs a backtest,
never approves an experiment, and never submits orders.
"""
from __future__ import annotations
import json
from typing import Any
from .research_workflow import (
    canonical_hash, validate_research_proposal, validate_adversarial_review,
    create_research_packet,
)

RESEARCHER_SYSTEM = """You are a quantitative futures research analyst.
Return exactly one JSON object matching the research_proposal contract.
Do not claim any backtest performance, win rate, profitability, or empirical edge.
Create falsifiable rules with observable inputs and explicit invalidation.
Every parameter must have a type and a finite, explicit values list.
Do not invent data availability. If uncertain, state it in data_requirements or known_risks.
Use artifact_type=research_proposal and status=ready_for_adversarial_review."""

REVIEWER_SYSTEM = """You are an adversarial reviewer for an intraday futures strategy.
Return exactly one JSON object matching the adversarial_review contract.
You must review the supplied proposal exactly as written and repeat its experiment_id and proposal_sha256.
Look for look-ahead bias, survivorship/sample-selection bias, overfitting, multiple testing,
cost/slippage realism, execution ambiguity, session leakage, contract-roll artifacts,
and missing invalidation conditions.
Each finding must include issue, evidence_or_test, and severity (low/medium/high/critical).
Use verdict accept_for_test only if the proposal is sufficiently falsifiable for controlled testing.
accept_for_test does not mean profitable or validated."""

def run_research_cycle(*, researcher: Any, reviewer: Any, experiment_spec: dict,
                       research_question: str, data_context: dict | None = None) -> dict:
    """Call each model once, validate provenance, and return a review-gated packet."""
    if not isinstance(experiment_spec, dict) or not experiment_spec.get("experiment_id"):
        raise ValueError("a registered experiment specification is required")
    if not isinstance(research_question, str) or not research_question.strip():
        raise ValueError("research_question must be non-empty")
    context = data_context or {}
    prompt = json.dumps({
        "task": research_question.strip(),
        "experiment_id": experiment_spec["experiment_id"],
        "strategy_id": experiment_spec.get("strategy_id"),
        "strategy_version": experiment_spec.get("strategy_version"),
        "dataset": {
            "dataset_id": experiment_spec.get("dataset_id"),
            "product_id": experiment_spec.get("dataset_product_id"),
            "timeframe": experiment_spec.get("dataset_timeframe"),
            "dataset_sha256": experiment_spec.get("dataset_sha256"),
        },
        "known_data_context": context,
        "required_output_fields": [
            "artifact_type", "experiment_id", "strategy_id", "strategy_version", "status",
            "hypothesis", "market_mechanism", "entry_rules", "exit_rules",
            "invalidation_rules", "parameter_search_space",
        ],
    }, ensure_ascii=False, allow_nan=False)
    proposal = researcher.generate_json(system_instruction=RESEARCHER_SYSTEM, prompt=prompt)
    proposal_meta = validate_research_proposal(proposal)
    if proposal["experiment_id"] != experiment_spec["experiment_id"]:
        raise ValueError("researcher returned a different experiment_id")
    if proposal["strategy_id"] != experiment_spec.get("strategy_id"):
        raise ValueError("researcher returned a different strategy_id")
    review_prompt = json.dumps({
        "proposal": proposal,
        "experiment_context": {
            "experiment_id": experiment_spec["experiment_id"],
            "dataset_id": experiment_spec.get("dataset_id"),
            "dataset_sha256": experiment_spec.get("dataset_sha256"),
            "cost_model": experiment_spec.get("cost_model"),
            "execution_model": experiment_spec.get("execution_model"),
        },
        "proposal_sha256": proposal_meta["artifact_sha256"],
        "required_output_fields": [
            "artifact_type", "reviewer_model", "experiment_id", "proposal_sha256",
            "verdict", "findings",
        ],
    }, ensure_ascii=False, allow_nan=False)
    review = reviewer.generate_json(system_instruction=REVIEWER_SYSTEM, prompt=review_prompt)
    review_meta = validate_adversarial_review(review, proposal)
    packet = create_research_packet(proposal, review, experiment_spec)
    return {
        "cycle_version": "1.0.0",
        "experiment_id": experiment_spec["experiment_id"],
        "proposal": proposal,
        "proposal_sha256": proposal_meta["artifact_sha256"],
        "review": review,
        "review_sha256": review_meta["artifact_sha256"],
        "handoff_packet": packet,
        "next_action": "human_review" if review_meta["verdict"] == "accept_for_test" else "revise_or_stop",
        "backtest_executed": False,
        "formal_result_created": False,
    }