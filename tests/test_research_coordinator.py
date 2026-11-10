import pytest
from research_engine.research_coordinator import run_research_cycle
from research_engine.research_workflow import canonical_hash

class FakeProvider:
    def __init__(self, response): self.response = response; self.calls = 0
    def generate_json(self, *, system_instruction, prompt):
        self.calls += 1
        return self.response

def make_spec():
    return {"experiment_id":"exp_12345678901234567890","strategy_id":"opening_fvg",
      "strategy_version":"0.1.0","dataset_id":"ds_1234567890abcdef",
      "dataset_sha256":"a"*64,"dataset_product_id":"TMFR1","dataset_timeframe":"5m",
      "cost_model":{"round_trip_cost_points":5.3,"slippage_points":1.0},
      "execution_model":{"model_id":"next_bar_open","version":"1.0"}}

def make_proposal():
    return {"artifact_type":"research_proposal","experiment_id":"exp_12345678901234567890",
      "strategy_id":"opening_fvg","strategy_version":"0.1.0","status":"ready_for_adversarial_review",
      "hypothesis":"Opening imbalance may continue after confirmation",
      "market_mechanism":"Opening displacement followed by directional continuation",
      "entry_rules":"Enter after a completed confirmation bar",
      "exit_rules":"Use fixed stop and target",
      "invalidation_rules":"Close back through the gap invalidates the setup",
      "parameter_search_space":{"min_gap_points":{"type":"integer","values":[5,10,15]}}}

def test_cycle_calls_models_once_and_returns_handoff_without_backtest():
    spec = make_spec(); proposal = make_proposal()
    review = {"artifact_type":"adversarial_review","reviewer_model":"GPT",
      "experiment_id":spec["experiment_id"],"proposal_sha256":canonical_hash(proposal),
      "verdict":"accept_for_test","findings":[{"issue":"Opening volatility confound",
      "evidence_or_test":"Stratify by opening range","severity":"medium"}]}
    gemini = FakeProvider(proposal); gpt = FakeProvider(review)
    result = run_research_cycle(researcher=gemini, reviewer=gpt, experiment_spec=spec,
      research_question="Study opening FVG continuation")
    assert gemini.calls == 1 and gpt.calls == 1
    assert result["handoff_packet"]["handoff_status"] == "ready_for_python_validation"
    assert result["backtest_executed"] is False
    assert result["formal_result_created"] is False
    assert result["next_action"] == "human_review"

def test_revise_review_does_not_create_handoff():
    spec = make_spec(); proposal = make_proposal()
    review = {"artifact_type":"adversarial_review","reviewer_model":"GPT",
      "experiment_id":spec["experiment_id"],"proposal_sha256":canonical_hash(proposal),
      "verdict":"revise","findings":[]}
    with pytest.raises(ValueError, match="accepted for testing"):
      run_research_cycle(researcher=FakeProvider(proposal), reviewer=FakeProvider(review),
        experiment_spec=spec, research_question="Study FVG")

def test_wrong_experiment_id_from_researcher_is_rejected():
    spec = make_spec(); proposal = make_proposal(); proposal["experiment_id"] = "exp_wrong"
    with pytest.raises(ValueError, match="different experiment_id"):
      run_research_cycle(researcher=FakeProvider(proposal), reviewer=FakeProvider({}),
        experiment_spec=spec, research_question="Study FVG")

def test_researcher_cannot_include_performance_claims():
    spec = make_spec(); proposal = make_proposal(); proposal["win_rate"] = 0.9
    with pytest.raises(ValueError, match="performance claims"):
      run_research_cycle(researcher=FakeProvider(proposal), reviewer=FakeProvider({}),
        experiment_spec=spec, research_question="Study FVG")