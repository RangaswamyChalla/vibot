"""FastAPI wrapper for voice bot services."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import tempfile
import os

from services.stt_service import STTService
from services.chat_service import ChatService
from services.tts_service import TTSService
from services.storage_service import StorageService
from observability import get_logger

logger = get_logger("api")

app = FastAPI(title="Voice Bot API", version="1.0.0")

# Initialize services
stt = STTService()
chat = ChatService()
tts = TTSService()
storage = StorageService()

class ChatRequest(BaseModel):
    text: str
    voice: Optional[str] = "fable"
    context: Optional[list] = None

class ChatResponse(BaseModel):
    reply: str
    audio: Optional[bytes] = None

@app.get("/health")
def health():
    return {"status": "healthy", "service": "voice-bot-api"}

@app.post("/chat/text")
def chat_text(req: ChatRequest):
    """Text → GPT → TTS pipeline."""
    logger.info(f"Text chat request: {req.text[:30]}...")
    reply = chat.chat(req.text, req.context)

    audio = None
    try:
        audio = tts.synthesize(reply, req.voice)
    except Exception as e:
        logger.warning(f"TTS failed, returning text only: {e}")

    storage.save([{"role": "user", "content": req.text}, {"role": "assistant", "content": reply}])

    return {"reply": reply, "audio": audio}

@app.post("/chat/voice")
async def chat_voice(file: UploadFile = File(...), voice: str = "fable"):
    """Audio → STT → GPT → TTS pipeline."""
    logger.info("Voice chat request received")

    # Save uploaded file temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as f:
        content = await file.read()
        f.write(content)
        audio_path = f.name

    try:
        # Pipeline: STT → Chat → TTS
        text = stt.transcribe(audio_path)
        logger.info(f"Transcribed: {text[:30]}...")

        reply = chat.chat(text)
        logger.info(f"GPT replied: {reply[:30]}...")

        audio_data = tts.synthesize(reply, voice)
        logger.info(f"TTS synthesized: {len(audio_data)} bytes")

        return StreamingResponse(
            iter([audio_data]),
            media_type="audio/webm",
            headers={"Content-Disposition": "attachment; filename=reply.webm"}
        )
    except Exception as e:
        logger.error(f"Voice pipeline failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if os.path.exists(audio_path):
            os.remove(audio_path)

@app.get("/conversations")
def list_conversations():
    """List all saved conversations."""
    return storage.load_all()

@app.delete("/conversations/{timestamp}")
def delete_conversation(timestamp: str):
    """Delete a conversation."""
    success = storage.delete(timestamp)
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted", "timestamp": timestamp}

@app.get("/conversations/{timestamp}")
def get_conversation(timestamp: str):
    """Get a specific conversation."""
    conv = storage.load_by_timestamp(timestamp)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv