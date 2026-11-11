import json
import pytest
from research_engine.ai_providers import GeminiAdapter, OpenAIAdapter, ProviderConfig

def test_openai_adapter_reads_key_from_environment_and_parses_json(monkeypatch):
    import research_engine.ai_providers as module
    monkeypatch.setenv("TEST_OPENAI_KEY", "secret-not-logged")
    captured = {}
    def fake_request(url, headers, payload, timeout):
        captured.update({"url": url, "headers": headers, "payload": payload, "timeout": timeout})
        return {"choices": [{"message": {"content": json.dumps({"artifact_type": "research_proposal"})}}]}
    monkeypatch.setattr(module, "_request_json", fake_request)
    adapter = OpenAIAdapter(ProviderConfig("openai", "test-model", "TEST_OPENAI_KEY", "https://example.test", 3))
    result = adapter.generate_json(system_instruction="Return JSON", prompt="Test")
    assert result["artifact_type"] == "research_proposal"
    assert captured["headers"]["Authorization"] == "Bearer secret-not-logged"
    assert captured["timeout"] == 3

def test_gemini_adapter_parses_json_candidate(monkeypatch):
    import research_engine.ai_providers as module
    monkeypatch.setenv("TEST_GEMINI_KEY", "secret")
    response = {"candidates": [{"content": {"parts": [{"text": json.dumps({"ok": True})}]}}]}
    monkeypatch.setattr(module, "_request_json", lambda *args: response)
    adapter = GeminiAdapter(ProviderConfig("gemini", "model", "TEST_GEMINI_KEY", "https://example.test/models"))
    assert adapter.generate_json(system_instruction="JSON", prompt="Test") == {"ok": True}

def test_missing_key_fails_without_network(monkeypatch):
    monkeypatch.delenv("ABSENT_KEY", raising=False)
    adapter = OpenAIAdapter(ProviderConfig("openai", "model", "ABSENT_KEY", "https://example.test"))
    with pytest.raises(RuntimeError, match="missing API key"):
        adapter.generate_json(system_instruction="JSON", prompt="Test")

def test_adapter_rejects_wrong_provider():
    with pytest.raises(ValueError, match="requires provider"):
        OpenAIAdapter(ProviderConfig("gemini", "model", "KEY", "https://example.test"))