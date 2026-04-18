"""Async voice bot pipeline with queue-based concurrency and intent routing."""
import asyncio
import uuid
import time
from typing import Optional, Callable

from .queue import AsyncQueue, JobStatus
from observability import get_logger
from core.intent_classifier import get_intent_classifier
from core.ollama_client import get_ollama_client
from core.config import config
from services.rag_service import get_rag_service
from services.chat_service import ChatService

logger = get_logger("pipeline.orchestrator")

FALLBACK_RESPONSES = {
    "life story": "I'm Ranga Swami, someone who has always learned by doing...",
    "superpower": "My superpower is learning and adapting quickly...",
    "grow": "The top 3 areas I'd like to grow in are...",
    "misconception": "People often assume I'm quiet or reserved...",
    "boundaries": "I deliberately take on projects that challenge me...",
    "about me": "I'm Ranga Swami, an AI and backend developer...",
}


def get_fallback(text: str) -> str | None:
    q = text.lower()
    for key in FALLBACK_RESPONSES:
        if key in q:
            return FALLBACK_RESPONSES[key]
    return None


class VoiceBotPipeline:
    """End-to-end voice bot pipeline with intent routing."""

    def __init__(self, stt_service, chat_service, tts_service, storage_service,
                 queue_size: int = 100, worker_count: int = 4):
        self.stt = stt_service
        self.chat = chat_service
        self.tts = tts_service
        self.storage = storage_service

        # Resolve persist path relative to project root
        import os
        persist_path = config.QUEUE_PERSIST_PATH
        if persist_path:
            if not os.path.isabs(persist_path):
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                persist_path = os.path.join(project_root, persist_path)
            os.makedirs(os.path.dirname(persist_path), exist_ok=True)

        self.queue = AsyncQueue(
            max_size=queue_size,
            worker_count=worker_count,
            persist_path=persist_path,
        )
        self._started = False

    async def _process_voice_job(self, job_data: dict) -> dict:
        """Process a single voice job through the pipeline with intent routing."""
        audio_path = job_data.get("audio_path")
        voice = job_data.get("voice", "fable")
        user_id = job_data.get("user_id", "anonymous")

        start = time.time()
        step_metrics = {}

        # Step 1: STT
        step_start = time.time()
        try:
            text = self.stt.transcribe(audio_path)
            step_metrics["stt_ms"] = (time.time() - step_start) * 1000
            logger.info(f"STT done: {text[:40]}...")
        except Exception as e:
            logger.error(f"STT failed: {e}")
            raise

        # Step 2: Intent Classification
        step_start = time.time()
        try:
            classifier = get_intent_classifier()
            intent_result = await classifier.classify(text)
            step_metrics["intent_ms"] = (time.time() - step_start) * 1000
            logger.info(f"Intent: {intent_result.intent} ({intent_result.source})")
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            intent_result = type("IntentResult", (), {"intent": "unknown", "confidence": 0.0, "source": "error"})()
            step_metrics["intent_ms"] = (time.time() - step_start) * 1000

        # Step 3: Route to appropriate handler
        step_start = time.time()
        reply = None
        source = "fallback"

        try:
            # Try RAG for kb_query
            if intent_result.intent == "kb_query":
                rag_result = await get_rag_service().query(text)
                if rag_result.get("reply"):
                    reply = rag_result["reply"]
                    source = "rag"

            # Try fallback for about_me and small_talk
            if reply is None and intent_result.intent in ["small_talk", "about_me"]:
                fallback = get_fallback(text)
                if fallback:
                    reply = fallback
                    source = "fallback"

            # Try Ollama for general queries
            if reply is None:
                client = get_ollama_client()
                if await client.is_available():
                    response = await client.chat(message=text)
                    reply = response.message
                    source = "ollama"
                elif config.USE_LEGACY_OPENAI:
                    # Use injected ChatService when Ollama is unavailable
                    try:
                        reply = self.chat.chat(text)
                        source = "openai"
                    except Exception as e:
                        logger.warning(f"OpenAI fallback failed: {e}")
                        fallback = get_fallback(text)
                        if fallback:
                            reply = fallback
                            source = "fallback"
                else:
                    fallback = get_fallback(text)
                    if fallback:
                        reply = fallback
                        source = "fallback"

            # Ultimate fallback
            if reply is None:
                reply = "I'm sorry, I couldn't process your request right now."
                source = "error"

            step_metrics["chat_ms"] = (time.time() - step_start) * 1000
            logger.info(f"Chat done ({source}): {reply[:40]}...")

        except Exception as e:
            logger.error(f"Chat failed: {e}")
            fallback = get_fallback(text)
            reply = fallback or "I'm sorry, I encountered an error."
            source = "error"
            step_metrics["chat_ms"] = (time.time() - step_start) * 1000

        # Step 4: TTS
        step_start = time.time()
        try:
            audio_data = self.tts.synthesize(reply, voice)
            step_metrics["tts_ms"] = (time.time() - step_start) * 1000
            logger.info(f"TTS done: {len(audio_data) if audio_data else 0} bytes")
        except Exception as e:
            logger.warning(f"TTS failed, returning text only: {e}")
            audio_data = None

        # Save conversation
        self.storage.save([
            {"role": "user", "content": text},
            {"role": "assistant", "content": reply}
        ])

        total_ms = (time.time() - start) * 1000
        step_metrics["total_ms"] = total_ms

        return {
            "text": text,
            "reply": reply,
            "audio": audio_data,
            "intent": intent_result.intent,
            "source": source,
            "metrics": step_metrics,
            "user_id": user_id
        }

    async def start(self, custom_process_fn: Optional[Callable] = None):
        """Start the pipeline workers."""
        if self._started:
            return
        
        process_fn = custom_process_fn or self._process_voice_job
        await self.queue.start(process_fn)
        self._started = True
        logger.info("VoiceBotPipeline started")

    async def stop(self):
        """Stop the pipeline workers."""
        await self.queue.stop()
        self._started = False
        logger.info("VoiceBotPipeline stopped")

    async def submit(self, audio_path: str, voice: str = "fable", user_id: str = "anonymous") -> str:
        """Submit a voice job and return job_id for tracking."""
        job_id = str(uuid.uuid4())[:8]
        await self.queue.enqueue(job_id, {
            "audio_path": audio_path,
            "voice": voice,
            "user_id": user_id
        })
        logger.info(f"Job submitted: {job_id}")
        return job_id

    def get_job(self, job_id: str) -> Optional[dict]:
        """Get job status and result."""
        job = self.queue.get_status(job_id)
        if not job:
            return None

        return {
            "id": job.id,
            "status": job.status.value,
            "result": job.result,
            "error": job.error,
            "created_at": job.created_at,
            "completed_at": job.completed_at
        }

    async def submit_and_wait(self, audio_path: str, voice: str = "fable",
                              user_id: str = "anonymous", timeout: float = 60.0) -> dict:
        """Submit a job and wait for result (blocking)."""
        job_id = await self.submit(audio_path, voice, user_id)

        start = time.time()
        while time.time() - start < timeout:
            job = self.queue.get_status(job_id)
            if not job:
                raise Exception(f"Job {job_id} not found")

            if job.status == JobStatus.COMPLETED:
                return job.result
            elif job.status == JobStatus.FAILED:
                raise Exception(f"Job failed: {job.error}")

            await asyncio.sleep(0.1)

        raise Exception(f"Job {job_id} timed out after {timeout}s")

    def metrics(self) -> dict:
        """Return pipeline metrics."""
        return self.queue.get_metrics()
