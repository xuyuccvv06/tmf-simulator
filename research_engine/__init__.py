"""TMF deterministic research engine foundation."""
from .models import Bar, Order, Trade
from .validation import validate_bars
from .simulator import simulate
from .performance import PerformanceSummary, summarize_trades
from .csv_loader import load_bars_csv
from .sessions import SessionWindow, classify_session, validate_session_windows
from .audit import DataAudit, audit_bars
from .research_workflow import (
    validate_research_proposal, validate_adversarial_review, create_research_packet,
)
from .research_coordinator import run_research_cycle
from .ai_providers import (
    ProviderConfig, GeminiAdapter, OpenAIAdapter,
    build_gemini_from_env, build_openai_from_env,
)
from .strategy_dsl import CompiledStrategy, compile_strategy, generate_orders, run_dsl_strategy

__all__ = [
    "Bar", "Order", "Trade", "validate_bars", "simulate",
    "PerformanceSummary", "summarize_trades", "load_bars_csv",
    "SessionWindow", "classify_session", "validate_session_windows",
    "DataAudit", "audit_bars", "validate_research_proposal",
    "validate_adversarial_review", "create_research_packet",
    "run_research_cycle", "ProviderConfig", "GeminiAdapter",
    "OpenAIAdapter", "build_gemini_from_env", "build_openai_from_env",
    "CompiledStrategy", "compile_strategy", "generate_orders", "run_dsl_strategy",
]
