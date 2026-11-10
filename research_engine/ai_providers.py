"""Secure, dependency-free HTTP adapters for Gemini and OpenAI-compatible APIs.

API keys are read only from environment variables. This module never logs secrets,
never stores prompts, and does not execute research or approve experiments.
"""
from __future__ import annotations
import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

MAX_RESPONSE_BYTES = 1_000_000

@dataclass(frozen=True)
class ProviderConfig:
    provider: str
    model: str
    api_key_env: str
    endpoint: str
    timeout_seconds: float = 45.0

def _request_json(url: str, headers: dict[str, str], payload: dict, timeout: float) -> dict:
    body = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers={**headers, "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ValueError("provider response exceeds 1 MB safety limit")
            if response.status < 200 or response.status >= 300:
                raise RuntimeError("provider returned HTTP status %s" % response.status)
    except urllib.error.HTTPError as exc:
        raise RuntimeError("provider HTTP error: %s" % exc.code) from None
    except urllib.error.URLError as exc:
        raise RuntimeError("provider connection failed: %s" % exc.reason) from None
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("provider returned invalid UTF-8 JSON") from None
    if not isinstance(parsed, dict):
        raise ValueError("provider response must be a JSON object")
    return parsed

class GeminiAdapter:
    def __init__(self, config: ProviderConfig):
        if config.provider != "gemini":
            raise ValueError("GeminiAdapter requires provider=gemini")
        self.config = config

    def generate_json(self, *, system_instruction: str, prompt: str) -> dict[str, Any]:
        key = os.environ.get(self.config.api_key_env)
        if not key:
            raise RuntimeError("missing API key environment variable: %s" % self.config.api_key_env)
        url = self.config.endpoint.rstrip("/") + "/" + self.config.model + ":generateContent"
        url += "?key=" + urllib.parse.quote(key, safe="")
        payload = {
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"responseMimeType": "application/json"},
        }
        response = _request_json(url, {}, payload, self.config.timeout_seconds)
        try:
            text = response["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(text)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            raise ValueError("Gemini did not return a valid JSON object") from None
        if not isinstance(parsed, dict):
            raise ValueError("Gemini JSON output must be an object")
        return parsed

class OpenAIAdapter:
    def __init__(self, config: ProviderConfig):
        if config.provider != "openai":
            raise ValueError("OpenAIAdapter requires provider=openai")
        self.config = config

    def generate_json(self, *, system_instruction: str, prompt: str) -> dict[str, Any]:
        key = os.environ.get(self.config.api_key_env)
        if not key:
            raise RuntimeError("missing API key environment variable: %s" % self.config.api_key_env)
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        response = _request_json(self.config.endpoint, {"Authorization": "Bearer " + key}, payload, self.config.timeout_seconds)
        try:
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)
        except (KeyError, IndexError, TypeError, json.JSONDecodeError):
            raise ValueError("OpenAI did not return a valid JSON object") from None
        if not isinstance(parsed, dict):
            raise ValueError("OpenAI JSON output must be an object")
        return parsed

def build_gemini_from_env() -> GeminiAdapter:
    model = os.environ.get("TMF_GEMINI_MODEL", "gemini-2.5-flash")
    endpoint = os.environ.get("TMF_GEMINI_ENDPOINT", "https://generativelanguage.googleapis.com/v1beta/models")
    timeout = float(os.environ.get("TMF_AI_TIMEOUT_SECONDS", "45"))
    return GeminiAdapter(ProviderConfig("gemini", model, "GEMINI_API_KEY", endpoint, timeout))

def build_openai_from_env() -> OpenAIAdapter:
    model = os.environ.get("TMF_OPENAI_MODEL", "gpt-4.1-mini")
    endpoint = os.environ.get("TMF_OPENAI_ENDPOINT", "https://api.openai.com/v1/chat/completions")
    timeout = float(os.environ.get("TMF_AI_TIMEOUT_SECONDS", "45"))
    return OpenAIAdapter(ProviderConfig("openai", model, "OPENAI_API_KEY", endpoint, timeout))