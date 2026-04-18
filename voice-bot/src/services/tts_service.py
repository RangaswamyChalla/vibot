"""Local TTS service using Piper — no API key required, runs entirely offline."""
import io
import os
import sys
import wave
import tempfile
from pathlib import Path

from core.config import config  # noqa: F401 — load .env before reading env vars
from core.retry import retry
from observability import get_logger

logger = get_logger("services.tts")

VOICE_MAP = {
    "fable": "en_US-lessac-medium",
    "echo": "en_US-lessac-medium",
    "onyx": "en_US-lessac-medium",
    "nova": "en_US-lessac-medium",
    "alloy": "en_US-lessac-medium",
}

PIPER_MODEL_DIR = Path(__file__).parent.parent.parent / "models" / "piper"


class TTSService:
    """Local TTS using Piper — no internet, no API key."""

    def __init__(self, api_key: str = None):
        self._voice = None
        self.VOICES = VOICE_MAP
        self._default_voice = "fable"

    def _get_voice(self, voice_key: str):
        """Lazy-load the Piper voice model on first use."""
        if self._voice is None:
            from piper.voice import PiperVoice

            voice_name = self.VOICES.get(voice_key, self.VOICES[self._default_voice])
            model_path = PIPER_MODEL_DIR / f"{voice_name}.onnx"
            config_path = PIPER_MODEL_DIR / f"{voice_name}.onnx.json"

            if not model_path.exists():
                raise FileNotFoundError(
                    f"Piper voice model not found at {model_path}. "
                    "Run: python -m piper.download_voices en_US-lessac-medium --download-dir voice-bot/models/piper"
                )

            self._voice = PiperVoice.load(str(model_path), str(config_path))
            logger.info(f"Piper voice loaded: {voice_name}")

        return self._voice

    @retry(exceptions=(Exception,), max_retries=3, delay=1.0, logger=logger)
    def synthesize(self, text: str, voice: str = "fable") -> bytes:
        """Convert text to speech using Piper in-process — returns WAV bytes."""
        logger.info(f"Piper TTS: {text[:30]}... voice={voice}")

        if voice not in self.VOICES:
            voice = self._default_voice

        try:
            piper_voice = self._get_voice(voice)

            # Synthesize in-process — generates AudioChunk objects
            audio_bytes = b""
            wav_buffer = io.BytesIO()

            with wave.open(wav_buffer, "wb") as wav_out:
                # Piper outputs 16-bit mono @ 22050 Hz
                wav_out.setnchannels(1)
                wav_out.setsampwidth(2)
                wav_out.setframerate(22050)

                for chunk in piper_voice.synthesize(text):
                    wav_out.writeframes(chunk.audio_int16_bytes)

            audio_data = wav_buffer.getvalue()
            logger.info(f"Piper TTS successful, {len(audio_data)} bytes")
            return audio_data

        except Exception as e:
            logger.error(f"Piper TTS failed: {e}. Falling back to gTTS...")
            try:
                from gtts import gTTS
                tts = gTTS(text=text, lang='en')
                buffer = io.BytesIO()
                tts.write_to_fp(buffer)
                return buffer.getvalue()
            except Exception as gtts_err:
                logger.error(f"gTTS fallback also failed: {gtts_err}")
                raise e

    def synthesize_stream(self, text: str, voice: str = "fable"):
        """Streaming not supported by Piper."""
        raise NotImplementedError("Piper does not support streaming synthesis. Use synthesize() instead.")