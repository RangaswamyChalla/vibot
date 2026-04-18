"""Dependency injection for FastAPI."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from core.ollama_client import get_ollama_client
from core.intent_classifier import get_intent_classifier
from services.rag_service import get_rag_service
from services.stt_service import STTService
from services.tts_service import TTSService


def get_stt_service() -> STTService:
    return STTService()


def get_tts_service() -> TTSService:
    return TTSService()
