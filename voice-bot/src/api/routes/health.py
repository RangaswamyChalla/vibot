"""Health check and Ollama status endpoints."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter

from core.ollama_client import get_ollama_client

router = APIRouter()


@router.get("/health")
async def health_check():
    """Service health check with deep Ollama model validation."""
    client = get_ollama_client()

    # Deep check: server is up AND has loaded models
    if await client.is_available():
        models = await client.list_models()
        if models:
            return {
                "status": "healthy",
                "service": "voicebot-axiom",
                "ollama": {"available": True, "models_loaded": len(models)},
            }
        else:
            return {
                "status": "degraded",
                "service": "voicebot-axiom",
                "ollama": {"available": True, "models_loaded": 0, "error": "No models loaded"},
            }
    else:
        return {
            "status": "unhealthy",
            "service": "voicebot-axiom",
            "ollama": {"available": False},
        }


@router.get("/ollama/status")
async def ollama_status():
    """Check Ollama availability and installed models."""
    client = get_ollama_client()
    available = await client.is_available()

    if available:
        models = await client.list_models()
        return {
            "available": True,
            "models": [m.get("name") for m in models],
            "base_url": client.base_url,
        }
    else:
        return {
            "available": False,
            "models": [],
            "base_url": client.base_url,
            "error": "Ollama server not responding or no models loaded",
        }


@router.get("/ollama/ready")
async def ollama_ready():
    """Deep health probe: validates Ollama has at least one operational model.

    Use this for Kubernetes readiness probes and deployment validation.
    Returns 200 only if Ollama server is up AND has >= 1 model loaded.
    """
    client = get_ollama_client()
    available = await client.is_available()

    if available:
        models = await client.list_models()
        if models:
            return {
                "ready": True,
                "models": [m.get("name") for m in models],
            }
        else:
            return {
                "ready": False,
                "error": "Ollama server is up but no models are loaded",
                "models": [],
            }
    else:
        return {
            "ready": False,
            "error": "Ollama server not available",
            "models": [],
        }
