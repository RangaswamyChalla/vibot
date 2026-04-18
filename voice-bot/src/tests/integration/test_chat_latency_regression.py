import sys
import os
import types
import pytest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from api.routes import chat as chat_route


class _StubClassifier:
    async def classify(self, _message: str):
        return types.SimpleNamespace(intent="unknown", confidence=0.99)


class _StubOllamaClient:
    def __init__(self):
        self.is_available_calls = 0
        self.chat_calls = 0

    async def is_available(self):
        self.is_available_calls += 1
        return False

    async def chat(self, **_kwargs):
        self.chat_calls += 1
        raise RuntimeError("ollama unavailable")


@pytest.mark.asyncio
async def test_chat_route_skips_preflight_availability_check(monkeypatch):
    client = _StubOllamaClient()

    monkeypatch.setattr(chat_route, "get_intent_classifier", lambda: _StubClassifier())
    monkeypatch.setattr(chat_route, "get_ollama_client", lambda: client)
    monkeypatch.setattr(chat_route, "utils_get_fallback", lambda _msg: "fallback-reply")

    request = chat_route.ChatRequest(message="hello")
    response = await chat_route.chat(request)

    assert response.reply == "fallback-reply"
    assert response.source == "fallback"
    assert client.chat_calls == 1
    assert client.is_available_calls == 0
    assert response.latency_ms < 500
