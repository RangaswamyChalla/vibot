"""Chat API endpoints."""
import asyncio
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.intent_classifier import get_intent_classifier
from core.ollama_client import get_ollama_client
from core.config import config
from services.rag_service import get_rag_service
from utils import truncate_history, get_fallback as utils_get_fallback
from observability import get_logger

logger = get_logger("api.chat")

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    stream: bool = False
    context: list = []


class ChatResponse(BaseModel):
    reply: str
    intent: str
    source: str
    latency_ms: float



@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Text chat endpoint with intent routing."""
    start = time.time()

    try:
        async with asyncio.timeout(30.0):
            classifier = get_intent_classifier()
            intent_result = await classifier.classify(request.message)

            logger.info(f"Intent: {intent_result.intent} (confidence={intent_result.confidence:.2f})")

            reply = None
            source = "fallback"

            if intent_result.intent == "kb_query":
                rag_result = await get_rag_service().query(request.message)
                if rag_result.get("reply"):
                    reply = rag_result["reply"]
                    source = "rag"

            if reply is None and intent_result.intent in ["small_talk", "about_me"]:
                fallback = utils_get_fallback(request.message)
                if fallback:
                    reply = fallback
                    source = "fallback"

            if reply is None:
                client = get_ollama_client()
                # Skip preflight health-check in hot path and attempt chat directly.
                # This avoids one extra network RTT for every request.
                try:
                    context = truncate_history(
                        request.context,
                        max_tokens=config.MAX_TOKEN_BUDGET,
                        max_messages=config.MAX_HISTORY_MESSAGES,
                    )
                    from core.ollama_client import ChatMessage
                    chat_context = [ChatMessage(role=m["role"], content=m["content"]) for m in context]
                    chat_start = time.perf_counter()
                    response = await client.chat(message=request.message, context=chat_context, timeout=30.0)
                    logger.info("Ollama chat latency_ms=%.2f", (time.perf_counter() - chat_start) * 1000)
                    reply = response.message
                    source = "ollama"
                except Exception as ollama_error:
                    logger.warning(f"Ollama chat unavailable, using fallback: {ollama_error}")
                    fallback = utils_get_fallback(request.message)
                    if fallback:
                        reply = fallback
                        source = "fallback"
                    else:
                        raise HTTPException(status_code=503, detail="Ollama unavailable and no fallback available")

            latency_ms = (time.time() - start) * 1000

            return ChatResponse(
                reply=reply,
                intent=intent_result.intent,
                source=source,
                latency_ms=latency_ms,
            )

    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Request timeout after 30s")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
