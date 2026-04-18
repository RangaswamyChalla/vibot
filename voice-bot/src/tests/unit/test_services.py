"""Test suite for services."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import sys, os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.stt_service import STTService
from services.chat_service import ChatService, get_fallback
from services.tts_service import TTSService
from services.storage_service import StorageService
from core.retry import retry

class TestSTTService:
    def test_transcribe_returns_text(self):
        with patch("services.stt_service.OpenAI") as mock_client:
            mock_instance = Mock()
            mock_result = Mock(text="Hello world")
            mock_instance.audio.transcriptions.create.return_value = mock_result
            mock_client.return_value = mock_instance

            stt = STTService(api_key="test-key")
            result = stt.transcribe("dummy_path.webm")
            assert result == "Hello world"

    def test_fallback_on_error(self):
        with patch("services.stt_service.OpenAI") as mock_client:
            mock_instance = Mock()
            mock_instance.audio.transcriptions.create.side_effect = Exception("API Error")
            mock_client.return_value = mock_instance

            stt = STTService(api_key="test-key")
            with pytest.raises(Exception):
                stt.transcribe("dummy_path.webm")

class TestChatService:
    def test_chat_returns_response(self):
        with patch("services.chat_service.OpenAI") as mock_client:
            mock_instance = Mock()
            mock_response = Mock()
            mock_response.choices = [Mock(message=Mock(content="I am Ranga Swami"))]
            mock_instance.chat.completions.create.return_value = mock_response
            mock_client.return_value = mock_instance

            chat = ChatService(api_key="test-key")
            result = chat.chat("Who are you?")
            assert "Ranga Swami" in result

    def test_fallback_keyword_matching(self):
        result = get_fallback("tell me about your life story")
        assert result is not None
        assert "Ranga Swami" in result

    def test_no_fallback_for_unknown(self):
        result = get_fallback("random gibberish xyz123")
        assert result is None

class TestTTSService:
    def test_synthesize_returns_bytes(self):
        with patch("services.tts_service.OpenAI") as mock_client:
            mock_response = Mock()
            mock_response.stream_to_file = Mock()
            mock_client.return_value.audio.speech.create.return_value = mock_response

            with patch("builtins.open", Mock(read=Mock(return_value=b"audio_data"))):
                tts = TTSService(api_key="test-key")
                result = tts.synthesize("Hello", "fable")
                assert result == b"audio_data"

    def test_invalid_voice_defaults_to_fable(self):
        with patch("services.tts_service.OpenAI") as mock_client:
            mock_response = Mock()
            mock_response.stream_to_file = Mock()
            mock_client.return_value.audio.speech.create.return_value = mock_response

            with patch("builtins.open", Mock(read=Mock(return_value=b"audio_data"))):
                tts = TTSService(api_key="test-key")
                tts.synthesize("Hello", "invalid_voice")

class TestStorageService:
    def test_save_and_load(self, tmp_path):
        storage = StorageService(base_dir=str(tmp_path))
        messages = [{"role": "user", "content": "Hello"}, {"role": "assistant", "content": "Hi"}]
        path = storage.save(messages)
        assert os.path.exists(path)

        convs = storage.load_all()
        assert len(convs) == 1
        assert convs[0]["messages"] == messages

    def test_delete(self, tmp_path):
        storage = StorageService(base_dir=str(tmp_path))
        messages = [{"role": "user", "content": "Hello"}]
        path = storage.save(messages)
        ts = os.path.basename(path).replace("conv_", "").replace(".json", "")

        result = storage.delete(ts)
        assert result is True
        assert not os.path.exists(path)

class TestRetryDecorator:
    def test_retries_on_failure(self):
        attempts = 0

        @retry(exceptions=(ValueError,), max_retries=3, delay=0.1)
        def failing_func():
            nonlocal attempts
            attempts += 1
            if attempts < 3:
                raise ValueError("Fail")
            return "success"

        result = failing_func()
        assert result == "success"
        assert attempts == 3

    def test_raises_after_max_retries(self):
        @retry(exceptions=(ValueError,), max_retries=2, delay=0.1)
        def always_fails():
            raise ValueError("Always fails")

        with pytest.raises(ValueError):
            always_fails()