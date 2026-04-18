"""Configuration module - loads from environment variables."""
import os

# Force-load from project's .env to override any corrupted system env
_dotenv_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
if os.path.exists(_dotenv_path):
    with open(_dotenv_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

class Config:
    # Engine Configuration (Local-First defaults)
    USE_LEGACY_OPENAI = os.getenv("USE_LEGACY_OPENAI", "false").lower() == "true"
    DEFAULT_LLM_ENGINE = "axiom"  # axiom or legacy
    
    # Model Residency Performance
    KEEP_MODELS_IN_MEMORY = os.getenv("KEEP_MODELS_IN_MEMORY", "true").lower() == "true"
    
    # Security & Guards
    VOICEBOT_API_KEY = os.getenv("VOICEBOT_API_KEY", "axiom-dev-key")
    MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))
    
    # OpenAI (legacy mode)
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

    # Mode selection
    USE_LEGACY_OPENAI = os.getenv("USE_LEGACY_OPENAI", "false").lower() == "true"

    # Ollama (AXIOM mode)
    OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    OLLAMA_CHAT_MODEL = os.getenv("OLLAMA_CHAT_MODEL", "llama3.2")
    OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    OLLAMA_REQUEST_TIMEOUT = float(os.getenv("OLLAMA_REQUEST_TIMEOUT", "60"))
    OLLAMA_EMBED_TIMEOUT = float(os.getenv("OLLAMA_EMBED_TIMEOUT", "30"))

    # STT Model
    STT_MODEL = os.getenv("STT_MODEL", "whisper-1")
    LLM_MODEL = os.getenv("LLM_MODEL", "gpt-3.5-turbo")

    # TTS
    TTS_MODEL = os.getenv("TTS_MODEL", "tts-1")
    TTS_VOICE = os.getenv("TTS_VOICE", "fable")

    # Retry settings
    MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_DELAY = float(os.getenv("RETRY_DELAY", "1.0"))
    TIMEOUT_SECONDS = int(os.getenv("TIMEOUT_SECONDS", "60"))

    # Logging
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Metrics
    ENABLE_METRICS = os.getenv("ENABLE_METRICS", "true").lower() == "true"

    # Queue
    QUEUE_SIZE = int(os.getenv("QUEUE_SIZE", "100"))
    WORKER_COUNT = int(os.getenv("WORKER_COUNT", "4"))
    QUEUE_PERSIST_PATH = os.getenv("QUEUE_PERSIST_PATH", "data/queue_state.json")

    # Storage
    CONVERSATION_DIR = os.getenv("CONVERSATION_DIR", "conversations")
    MAX_AUDIO_DURATION_SEC = int(os.getenv("MAX_AUDIO_DURATION_SEC", "60"))
    MIN_AUDIO_DURATION_SEC = float(os.getenv("MIN_AUDIO_DURATION_SEC", "0.3"))

    # RAG settings
    RAG_VECTOR_STORE = os.getenv("RAG_VECTOR_STORE", "chroma")
    RAG_PERSIST_DIR = os.getenv("RAG_PERSIST_DIR", "data/chroma_db")
    RAG_COLLECTION_NAME = os.getenv("RAG_COLLECTION_NAME", "voicebot_kb")
    RAG_TOP_K = int(os.getenv("RAG_TOP_K", "4"))
    RAG_CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "500"))
    RAG_CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "50"))
    RAG_RESPONSES_PATH = os.getenv("RAG_RESPONSES_PATH", "data/responses.json")

    # Intent
    INTENT_THRESHOLD = float(os.getenv("INTENT_THRESHOLD", "0.7"))

    # Fallback
    USE_FALLBACK_ON_ERROR = os.getenv("USE_FALLBACK_ON_ERROR", "true").lower() == "true"

    # CORS — comma-separated list of allowed origins; empty string disables CORS middleware
    CORS_ALLOWED_ORIGINS = os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:3000,http://localhost:8501")

    # Conversation history — token budget guard (OOM prevention)
    MAX_TOKEN_BUDGET = int(os.getenv("MAX_TOKEN_BUDGET", "4096"))
    MAX_HISTORY_MESSAGES = int(os.getenv("MAX_HISTORY_MESSAGES", "20"))

config = Config()
Config = Config  # alias for backwards compat
