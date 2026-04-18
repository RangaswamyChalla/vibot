"""Integration tests for the VoiceBotPipeline."""
import pytest
import asyncio
import os
import tempfile
from unittest.mock import MagicMock, patch

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pipeline.orchestrator import VoiceBotPipeline
from pipeline.queue import JobStatus

import pytest_asyncio

def test_minimal():
    assert True

@pytest.fixture
def mock_services():
    """Create mock services for the pipeline."""
    stt = MagicMock()
    stt.transcribe.return_value = "Hello, how are you?"
    
    chat = MagicMock()
    chat.chat.return_value = "I am doing well, thank you!"
    
    tts = MagicMock()
    tts.synthesize.return_value = b"fake_audio_data"
    
    storage = MagicMock()
    
    return stt, chat, tts, storage

@pytest_asyncio.fixture
async def pipeline(mock_services):
    """Create and start a pipeline with mock services."""
    stt, chat, tts, storage = mock_services
    
    with patch("pipeline.orchestrator.config") as mock_config:
        mock_config.QUEUE_PERSIST_PATH = None
        mock_config.MAX_TOKEN_BUDGET = 4096
        mock_config.MAX_HISTORY_MESSAGES = 20
        mock_config.USE_LEGACY_OPENAI = False
    
        p = VoiceBotPipeline(
            stt_service=stt,
            chat_service=chat,
            tts_service=tts,
            storage_service=storage,
            queue_size=10,
            worker_count=1
        )
    
        await p.start()
        yield p
        await p.stop()

@pytest.mark.asyncio
async def test_pipeline_full_cycle(pipeline, mock_services):
    """Test a full voice job from submission to completion."""
    stt, chat, tts, storage = mock_services
    
    # Mock intent classifier to return a simple intent
    with patch("pipeline.orchestrator.get_intent_classifier") as mock_get_classifier:
        mock_classifier = MagicMock()
        from unittest.mock import AsyncMock
        mock_classifier.classify = AsyncMock(return_value=type("IntentResult", (), {"intent": "small_talk", "source": "keyword"})())
        mock_get_classifier.return_value = mock_classifier
        
        # Mock Ollama client to avoid external calls
        with patch("pipeline.orchestrator.get_ollama_client") as mock_get_ollama:
            mock_ollama = MagicMock()
            mock_ollama.is_available = AsyncMock(return_value=True)
            mock_ollama.chat = AsyncMock(return_value=type("Response", (), {"message": "I am doing well, thank you!"})())
            mock_get_ollama.return_value = mock_ollama

            # Submit a job
            audio_path = "tests/data/test_audio.webm"
            # Create dummy audio file if it doesn't exist
            os.makedirs("tests/data", exist_ok=True)
            with open(audio_path, "wb") as f:
                f.write(b"dummy audio content")
            
            try:
                result = await pipeline.submit_and_wait(audio_path, timeout=5.0)
                
                # Assertions
                assert result["text"] == "Hello, how are you?"
                assert result["reply"] == "I am doing well, thank you!"
                assert result["audio"] == b"fake_audio_data"
                assert result["intent"] == "small_talk"
                assert storage.save.called
            finally:
                if os.path.exists(audio_path):
                    os.remove(audio_path)

@pytest.mark.asyncio
async def test_pipeline_error_handling(pipeline, mock_services):
    """Test how the pipeline handles STT failure."""
    stt, chat, tts, storage = mock_services
    stt.transcribe.side_effect = Exception("STT Error")
    
    audio_path = "tests/data/test_error.webm"
    os.makedirs("tests/data", exist_ok=True)
    with open(audio_path, "wb") as f:
        f.write(b"dummy")
    
    try:
        with pytest.raises(Exception, match="Job failed: STT Error"):
            await pipeline.submit_and_wait(audio_path, timeout=5.0)
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)
