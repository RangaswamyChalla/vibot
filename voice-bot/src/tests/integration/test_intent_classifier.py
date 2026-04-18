"""Integration tests for the IntentClassifier."""
import pytest
from unittest.mock import MagicMock, AsyncMock

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from core.intent_classifier import IntentClassifier, IntentResult

@pytest.mark.asyncio
async def test_keyword_fast_path():
    """Test that keywords are caught without LLM."""
    classifier = IntentClassifier(use_llm_fallback=False)
    
    # Test lowercase match
    result = await classifier.classify("hello there")
    assert result.intent == "small_talk"
    assert result.source == "keyword"
    
    # Test phrase match
    result = await classifier.classify("what's your #1 superpower")
    assert result.intent == "about_me"
    assert result.source == "keyword"
    
    # Test RAG keyword
    result = await classifier.classify("explain the project")
    assert result.intent == "kb_query"
    assert result.source == "keyword"

@pytest.mark.asyncio
async def test_llm_fallback(monkeypatch):
    """Test that unknown queries fall back to LLM."""
    classifier = IntentClassifier(use_llm_fallback=True)
    
    # Mock Ollama client
    mock_ollama = MagicMock()
    mock_ollama.classify_intent = AsyncMock(return_value={"intent": "complex_query", "confidence": 0.9})
    
    # Monkeypatch the module-level function
    import core.intent_classifier
    monkeypatch.setattr(core.intent_classifier, "get_ollama_client", lambda: mock_ollama)
    
    result = await classifier.classify("the quick brown fox jumps over the lazy dog")
    assert result.intent == "complex_query"
    assert result.source == "llm"

@pytest.mark.asyncio
async def test_unknown_classification():
    """Test behavior when no keywords match and LLM is disabled."""
    classifier = IntentClassifier(use_llm_fallback=False)
    result = await classifier.classify("xyzzy")
    assert result.intent == "unknown"
    assert result.source == "default"
