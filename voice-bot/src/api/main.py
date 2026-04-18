"""FastAPI application entry point."""
import os
import asyncio
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import voice, chat, rag, health, vision
from core.config import config
from observability import get_logger

logger = get_logger("api.main")

from fastapi import FastAPI, Depends
from api.security import verify_api_key

app = FastAPI(
    title="VoiceBot AXIOM",
    version="2.0",
    description="Production-grade voice agent with local LLM, RAG, and intent classification",
)

# Build allowed origins list from config; empty string disables CORS entirely
_origins = [o.strip() for o in config.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
if _origins:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    logger.info("CORS middleware disabled (CORS_ALLOWED_ORIGINS is empty)")

app.include_router(health.router, tags=["Health"]) 
app.include_router(chat.router, prefix="/api", tags=["Chat"], dependencies=[Depends(verify_api_key)])
app.include_router(rag.router, prefix="/api/rag", tags=["RAG"], dependencies=[Depends(verify_api_key)])
app.include_router(vision.router, prefix="/api/vision", tags=["Vision"], dependencies=[Depends(verify_api_key)])
app.include_router(voice.router, prefix="/api", tags=["Voice"]) # WebSocket handles its own auth or is public for now

# Global pipeline instance for metrics and background processing
_pipeline = None

def get_global_pipeline():
    global _pipeline
    if _pipeline is None:
        from pipeline.orchestrator import VoiceBotPipeline
        from services.stt_service import STTService
        from services.tts_service import TTSService
        from services.storage_service import StorageService
        from services.chat_service import ChatService
        
        _pipeline = VoiceBotPipeline(
            stt_service=STTService(),
            chat_service=ChatService(),
            tts_service=TTSService(),
            storage_service=StorageService(),
            queue_size=config.QUEUE_SIZE,
            worker_count=4
        )
    return _pipeline

from api.monitoring import metrics_endpoint, QUEUE_DEPTH, REQUEST_COUNT

app.get("/metrics", tags=["Observability"])(metrics_endpoint)

async def monitor_pipeline():
    """Background task to update Prometheus gauges from the pipeline state."""
    while True:
        try:
            p = get_global_pipeline()
            stats = p.metrics()
            QUEUE_DEPTH.set(stats["pending"])
        except Exception:
            pass
        await asyncio.sleep(5)

@app.get("/api/metrics", tags=["Observability"])
async def get_metrics():
    """Return system metrics including queue depth and job counts."""
    p = get_global_pipeline()
    return {
        "service": "voicebot-axiom",
        "pipeline": p.metrics(),
        "config": {
            "queue_size": config.QUEUE_SIZE,
            "token_budget": config.MAX_TOKEN_BUDGET
        }
    }


@app.on_event("startup")
async def startup_event():
    logger.info("Starting VoiceBot AXIOM API")
    
    # Start background pipeline
    p = get_global_pipeline()
    await p.start()
    
    # Start metrics monitor
    asyncio.create_task(monitor_pipeline())
    
    from core.ollama_client import get_ollama_client
    client = get_ollama_client()
    if await client.is_available():
        models = await client.list_models()
        logger.info(f"Ollama available. Models: {[m.get('name') for m in models]}")

        # Warmup: send a lightweight request to load the model into memory
        try:
            logger.info(f"Warming up LLM ({client.chat_model})...")
            await client.chat(message="hello")
            logger.info("LLM warmup complete")
        except Exception as e:
            logger.warning(f"LLM warmup failed: {e}. First request may be slower.")
    else:
        logger.warning("Ollama not available. Using fallback responses.")


@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down VoiceBot AXIOM API")
    if _pipeline:
        await _pipeline.stop()
