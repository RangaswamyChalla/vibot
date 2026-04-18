"""WebSocket voice endpoint for real-time audio streaming."""
import asyncio
import base64
import json
import os
import sys
import time
import uuid
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from utils import truncate_history, get_fallback as utils_get_fallback

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from fastapi.websockets import WebSocketState

from core.intent_classifier import get_intent_classifier
from core.ollama_client import get_ollama_client
from core.config import config
from services.rag_service import get_rag_service
from services.storage_service import StorageService
from observability import get_logger

logger = get_logger("api.voice")

router = APIRouter()

AUDIO_BUFFER_THRESHOLD = 16000 * 2  # ~2 seconds of 16kHz audio


class VoiceConnection:
    """Manages a single WebSocket voice connection."""

    def __init__(self, websocket: WebSocket):
        self.ws = websocket
        self.connection_id = str(uuid.uuid4())[:8]
        self.audio_buffer = b""
        self.conversation_history = []
        self.streaming = False
        self.storage = StorageService()

    async def send_json(self, data: dict):
        """Send JSON message to client."""
        if self.ws.client_state == WebSocketState.CONNECTED:
            await self.ws.send_json(data)

    async def send_text(self, data: str):
        """Send text message to client."""
        if self.ws.client_state == WebSocketState.CONNECTED:
            await self.ws.send_text(data)

    async def close(self):
        """Close the connection."""
        if self.ws.client_state == WebSocketState.CONNECTED:
            await self.ws.close()


@router.websocket("/ws/voice")
async def websocket_endpoint(websocket: WebSocket, token: Optional[str] = None):
    """Handle WebSocket voice session with authorization."""
    # Check token from query param or header
    api_key = token or websocket.headers.get("X-API-Key")
    
    if config.VOICEBOT_API_KEY and api_key != config.VOICEBOT_API_KEY:
        await websocket.accept()
        await websocket.send_json({"type": "error", "message": "Unauthorized"})
        await websocket.close(code=1008)
        return

    await websocket.accept()
    connection = VoiceConnection(websocket)
    logger.info(f"Voice WebSocket connected: {connection.connection_id}")

    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                break

            if message["type"] == "websocket.receive":
                # Binary audio data
                if "bytes" in message:
                    if len(connection.audio_buffer) + len(message["bytes"]) > 10 * 1024 * 1024:
                        await connection.send_json({"type": "error", "message": "Buffer limit exceeded"})
                        connection.audio_buffer = b""
                        continue
                    connection.audio_buffer += message["bytes"]

                    # Send partial transcript when buffer is large enough
                    if len(connection.audio_buffer) >= AUDIO_BUFFER_THRESHOLD:
                        text = await transcribe_audio(connection.audio_buffer)
                        if text:
                            await connection.send_json({
                                "type": "transcript",
                                "text": text,
                                "partial": True,
                            })
                            connection.audio_buffer = b""

                # Text control message
                elif "text" in message:
                    try:
                        data = json.loads(message["text"])
                    except json.JSONDecodeError:
                        continue

                    action = data.get("action")

                    if action == "finalize":
                        # Full transcription + intent + reply + TTS
                        await handle_finalize(connection, data)
                    elif action == "clear":
                        connection.conversation_history = []
                        await connection.send_json({"type": "cleared"})
                    elif action == "ping":
                        await connection.send_json({"type": "pong"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: {connection.connection_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await connection.send_json({"type": "error", "message": str(e)})
    finally:
        await connection.close()
        logger.info(f"Voice WebSocket closed: {connection.connection_id}")


async def transcribe_audio(audio_bytes: bytes) -> str | None:
    """Transcribe audio bytes to text."""
    try:
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
            f.write(audio_bytes)
            path = f.name

        try:
            from services.stt_service import STTService
            stt = STTService()
            return stt.transcribe(path)
        finally:
            if os.path.exists(path):
                os.remove(path)
    except Exception as e:
        logger.error(f"STT failed: {e}")
        return None


async def handle_finalize(connection: VoiceConnection, data: dict):
    """Handle finalize action - full STT → Intent → Chat → TTS chain."""
    try:
        # Transcribe full audio (10s timeout)
        await connection.send_json({"type": "status", "message": "Transcribing..."})
        text = await asyncio.wait_for(transcribe_audio(connection.audio_buffer), timeout=10.0)
        connection.audio_buffer = b""

        if not text:
            await connection.send_json({"type": "error", "message": "Could not transcribe audio"})
            return

        await connection.send_json({"type": "transcript", "text": text, "partial": False})

        # Parallel Perception: Classify intent and speculative RAG query in parallel
        classifier = get_intent_classifier()
        rag_service = get_rag_service()
        itask = asyncio.create_task(classifier.classify(text))
        rtask = asyncio.create_task(rag_service.query(text))
        
        # Wait for results (5s max)
        done, _ = await asyncio.wait([itask, rtask], timeout=5.0)
        intent_result = itask.result() if itask in done else type('obj', (object,), {'intent': 'unknown'})()
        rag_result = rtask.result() if rtask in done else {}

        await connection.send_json({"type": "intent", "intent": intent_result.intent})

        # Generate response based on intent
        await connection.send_json({"type": "status", "message": "Generating response..."})

        reply = None
        source = "fallback"

        if intent_result.intent == "kb_query" and rag_result:
            if rag_result.get("reply"):
                reply = rag_result["reply"]
                source = "rag"

        if reply is None and intent_result.intent in ["small_talk", "about_me"]:
            reply = utils_get_fallback(text)
            source = "fallback"

        if reply is None:
            client = get_ollama_client()
            try:
                context = truncate_history(
                    connection.conversation_history,
                    max_tokens=config.MAX_TOKEN_BUDGET,
                    max_messages=config.MAX_HISTORY_MESSAGES,
                )
                from core.ollama_client import ChatMessage
                chat_context = [ChatMessage(role=m["role"], content=m["content"]) for m in context]
                
                # Optimized Stream-to-Sentence Synthesis
                from services.tts_service import TTSService
                tts = TTSService()
                
                full_reply = ""
                sentence_buffer = ""
                
                logger.info("Starting AXIOM streaming chat...")
                async for chunk in client.chat_stream(message=text, context=chat_context):
                    full_reply += chunk
                    sentence_buffer += chunk
                    
                    # If we have a complete sentence break, synthesize immediately
                    if any(punct in sentence_buffer for punct in [". ", "! ", "? ", "\n"]):
                        to_synthesize = sentence_buffer.strip()
                        if to_synthesize:
                            try:
                                # Run TTS in background for this sentence
                                audio_data = await asyncio.wait_for(
                                    asyncio.get_event_loop().run_in_executor(None, tts.synthesize, to_synthesize),
                                    timeout=10.0
                                )
                                if audio_data:
                                    audio_b64 = base64.b64encode(audio_data).decode()
                                    await connection.send_json({
                                        "type": "audio",
                                        "audio_b64": audio_b64,
                                        "partial_text": to_synthesize
                                    })
                            except Exception as e:
                                logger.error(f"Streaming TTS chunk failed: {e}")
                        sentence_buffer = ""

                # Handle leftover buffer
                if sentence_buffer.strip():
                    to_synthesize = sentence_buffer.strip()
                    try:
                        audio_data = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(None, tts.synthesize, to_synthesize),
                            timeout=5.0
                        )
                        if audio_data:
                            audio_b64 = base64.b64encode(audio_data).decode()
                            await connection.send_json({
                                "type": "audio",
                                "audio_b64": audio_b64,
                                "partial_text": to_synthesize
                            })
                    except Exception: pass

                reply = full_reply
                source = "ollama"
            except Exception as ollama_error:
                logger.warning(f"Streaming AXIOM failed: {ollama_error}. Trying OpenAI fallback...")
                
                # Try OpenAI Fallback if enabled
                try:
                    from services.chat_service import ChatService
                    chat = ChatService()
                    reply = chat.chat(text, connection.conversation_history)
                    source = "openai"
                except Exception as e:
                    logger.error(f"OpenAI fallback failed in voice pipeline: {e}")
                    reply = utils_get_fallback(text) or "I'm sorry, I encountered a systemic error."
                    source = "fallback"

        # (Post-processing follows)
        if reply:
            await connection.send_json({
                "type": "reply",
                "text": reply,
                "source": source,
            })

        # Update conversation history with sliding window trim
        connection.conversation_history.append({"role": "user", "content": text})
        connection.conversation_history.append({"role": "assistant", "content": reply})
        connection.conversation_history = truncate_history(
            connection.conversation_history,
            max_tokens=config.MAX_TOKEN_BUDGET,
            max_messages=config.MAX_HISTORY_MESSAGES,
        )

        # Auto-save after each turn so history survives crashes
        connection.storage.save(connection.conversation_history)

        await connection.send_json({"type": "done"})

    except asyncio.TimeoutError:
        logger.error("handle_finalize timed out")
        await connection.send_json({"type": "error", "message": "Request timeout"})
    except Exception as e:
        logger.error(f"Finalize error: {e}")
        await connection.send_json({"type": "error", "message": str(e)})

