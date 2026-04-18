"""Configuration module - loads from environment variables."""
import os

# Force-load from project's .env to override any corrupted system env
_dotenv_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".env")
if os.path.exists(_dotenv_path):
    with open(_dotenv_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

class Config:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
    STT_MODEL = os.getenv("STT_MODEL", "whisper-1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    TTS_MODEL = os.getenv("TTS_MODEL", "tts-1")
    TTS_VOICE = os.getenv("TTS_VOICE", "fable")
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))
    TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "60"))
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"
    QUEUE_SIZE = int(os.getenv("QUEUE_SIZE", "100"))
    WORKER_COUNT = int(os.getenv("WORKER_COUNT", "4"))
    CONVERSATION_DIR = os.getenv("CONVERSATION_DIR", "conversations")
    MAX_AUDIO_DURATION_SEC = int(os.getenv("MAX_AUDIO_DURATION_SEC", "60"))
    MIN_AUDIO_DURATION_SEC = float(os.getenv("MIN_AUDIO_DURATION_SEC", "0.3"))

config = Config()
Config = Config  # alias for backwards compat