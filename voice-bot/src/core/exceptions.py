"""Custom exceptions for the voice bot."""


class VoiceBotError(Exception):
    """Base exception for voice bot errors."""
    pass


class OllamaUnavailableError(VoiceBotError):
    """Raised when Ollama server is not available."""
    pass


class OllamaTimeoutError(VoiceBotError):
    """Raised when Ollama request times out."""
    pass


class IntentClassificationError(VoiceBotError):
    """Raised when intent classification fails."""
    pass


class RAGError(VoiceBotError):
    """Raised when RAG operations fail."""
    pass


class STTError(VoiceBotError):
    """Raised when speech-to-text fails."""
    pass


class TTSError(VoiceBotError):
    """Raised when text-to-speech fails."""
    pass


class StorageError(VoiceBotError):
    """Raised when storage operations fail."""
    pass


class QueueFullError(VoiceBotError):
    """Raised when the job queue is at capacity."""
    pass
