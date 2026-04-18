"""Speech-to-Text service using OpenAI Whisper."""
import os
from openai import OpenAI
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from openai import OpenAI
from core.retry import retry
from observability import get_logger

logger = get_logger("services.stt")

class STTService:
    _model_cache = None

    def __init__(self, api_key: str = None):
        self.client = OpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))

    def _get_model(self):
        """Lazy load and cache the WhisperX model."""
        if STTService._model_cache is None:
            import whisperx
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Loading WhisperX model to {device}...")
            STTService._model_cache = whisperx.load_model("base", device, compute_type="int8")
        return STTService._model_cache

    @retry(exceptions=(Exception,), max_retries=2, delay=1.0, logger=logger)
    def transcribe(self, audio_path: str) -> str:
        """Transcribe audio file to text (Local-First)."""
        logger.info(f"Transcribing audio: {audio_path}")
        
        # 1. Try Local WhisperX
        try:
            import whisperx
            import torch
            model = self._get_model()
            audio = whisperx.load_audio(audio_path)
            result = model.transcribe(audio, batch_size=16)
            text = " ".join([seg["text"] for seg in result["segments"]]).strip()
            if text:
                logger.info(f"Local WhisperX success: {text[:50]}...")
                return text
        except Exception as e:
            logger.warning(f"Local WhisperX failed: {e}. Falling back to OpenAI...")

        # 2. Try OpenAI Fallback
        try:
            if not self.client.api_key:
                raise ValueError("OpenAI API key missing")

            with open(audio_path, "rb") as f:
                result = self.client.audio.transcriptions.create(
                    model="whisper-1",
                    file=f
                )
            text = result.text
            logger.info(f"OpenAI Transcription successful: {text[:50]}...")
            return text
        except Exception as e:
            if "insufficient_quota" in str(e) or "429" in str(e):
                logger.error("STT Failed: OpenAI Quota Exceeded and Local WhisperX unavailable.")
                return "[Transcription unavailable - Cloud Quota Exceeded]"
            logger.error(f"STT complete failure: {e}")
            raise

    def transcribe_bytes(self, audio_bytes: bytes) -> str:
        """Transcribe from bytes (temp file cleanup handled externally)."""
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
            f.write(audio_bytes)
            path = f.name
        try:
            return self.transcribe(path)
        finally:
            if os.path.exists(path):
                os.remove(path)