"""Ollama API client for local LLM inference."""
import os
import json
import asyncio
import httpx
from typing import Optional, Generator, AsyncGenerator
from dataclasses import dataclass

from core.exceptions import OllamaUnavailableError
from observability import get_logger

from observability import get_logger

logger = get_logger("core.ollama")

DEFAULT_BASE_URL = "http://localhost:11434"
DEFAULT_CHAT_MODEL = "llama3.2"
DEFAULT_EMBED_MODEL = "nomic-embed-text"


@dataclass
class ChatMessage:
    role: str
    content: str


@dataclass
class ChatResponse:
    message: str
    model: str
    done: bool = True
    latency_ms: float = 0.0


@dataclass
class EmbeddingResponse:
    embedding: list[float]
    model: str


class OllamaClient:
    """Async client for Ollama REST API (http://localhost:11434)."""

    # Circuit breaker: open after this many consecutive failures
    CIRCUIT_BREAKER_THRESHOLD = 5
    # Seconds before attempting half-open probe
    CIRCUIT_BREAKER_RESET_SECS = 30.0

    def __init__(
        self,
        base_url: str = None,
        chat_model: str = None,
        embed_model: str = None,
        timeout: float = 60.0,
    ):
        self.base_url = base_url or os.getenv("OLLAMA_BASE_URL", DEFAULT_BASE_URL)
        self.chat_model = chat_model or os.getenv("OLLAMA_CHAT_MODEL", DEFAULT_CHAT_MODEL)
        self.embed_model = embed_model or os.getenv("OLLAMA_EMBED_MODEL", DEFAULT_EMBED_MODEL)
        self.timeout = timeout
        self._client = httpx.AsyncClient(
            timeout=timeout,
            limits=httpx.Limits(max_keepalive_connections=20, max_connections=100),
        )
        self._cb_failures = 0
        self._cb_opened_at = 0.0  # timestamp when circuit last opened

    @property
    def circuit_open(self) -> bool:
        """True if circuit breaker is currently open."""
        if self._cb_failures < self.CIRCUIT_BREAKER_THRESHOLD:
            return False
        import time
        if time.time() - self._cb_opened_at < self.CIRCUIT_BREAKER_RESET_SECS:
            return True
        # Auto-probe: allow one attempt through
        return False

    def _cb_record_success(self):
        self._cb_failures = 0
        self._cb_opened_at = 0.0

    def _cb_record_failure(self):
        import time
        self._cb_failures += 1
        if self._cb_failures == self.CIRCUIT_BREAKER_THRESHOLD:
            self._cb_opened_at = time.time()
            logger.warning(f"Ollama circuit breaker OPENED after {self._cb_failures} consecutive failures")

    async def close(self):
        """Close the async client."""
        await self._client.aclose()

    async def is_available(self) -> bool:
        """Check if Ollama server is running AND has at least one model loaded."""
        try:
            response = await self._client.get(f"{self.base_url}/api/tags")
            if response.status_code != 200:
                return False
            # Server is up - verify at least one model is available
            models = response.json().get("models", [])
            if len(models) == 0:
                logger.warning("Ollama server is up but no models are loaded")
                return False
            return True
        except Exception as e:
            logger.warning(f"Ollama not available: {e}")
            return False

    async def list_models(self) -> list[dict]:
        """List available models."""
        try:
            response = await self._client.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            data = response.json()
            return data.get("models", [])
        except Exception as e:
            logger.error(f"Failed to list models: {e}")
            return []

    async def pull_model(self, model: str) -> dict:
        """Pull a model (download on startup if missing)."""
        logger.info(f"Pulling model: {model}")
        try:
            response = await self._client.post(
                f"{self.base_url}/api/pull",
                json={"name": model},
                timeout=300.0,  # longer timeout for downloads
            )
            response.raise_for_status()
            return {"status": "success", "model": model}
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return {"status": "error", "model": model, "error": str(e)}

    async def chat(
        self,
        message: str,
        model: str = None,
        context: list[ChatMessage] = None,
        system_prompt: str = None,
        stream: bool = False,
        max_retries: int = 3,
        timeout: float = None,
        _wrap_timeout: bool = True,
    ) -> ChatResponse:
        """Send a chat message and get a response with built-in retry + circuit breaker."""
        if self.circuit_open:
            raise OllamaUnavailableError("Ollama circuit breaker is open — service unavailable")
        model = model or self.chat_model

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            messages.extend([{"role": m.role, "content": m.content} for m in context])
        messages.append({"role": "user", "content": message})

        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
        }

        last_exception = None
        for attempt in range(max_retries + 1):
            try:
                effective_timeout = timeout or self.timeout
                async with asyncio.timeout(effective_timeout):
                    response = await self._client.post(
                        f"{self.base_url}/api/chat",
                        json=payload,
                        timeout=effective_timeout,
                    )
                response.raise_for_status()
                data = response.json()

                self._cb_record_success()
                return ChatResponse(
                    message=data["message"]["content"],
                    model=data.get("model", model),
                    done=data.get("done", True),
                    latency_ms=0.0,
                )
            except asyncio.TimeoutError:
                last_exception = TimeoutError(f"Ollama chat timed out after {effective_timeout}s")
                logger.error(f"Ollama chat timed out (attempt {attempt + 1}/{max_retries + 1})")
            except httpx.TimeoutException as e:
                last_exception = e
                logger.error(f"Ollama chat timed out after {self.timeout}s (attempt {attempt + 1}/{max_retries + 1})")
            except httpx.HTTPError as e:
                last_exception = e
                logger.error(f"Ollama chat failed (attempt {attempt + 1}/{max_retries + 1}): {e}")

            if attempt < max_retries:
                sleep_time = 1.0 * (2.0 ** attempt)  # exponential backoff
                logger.warning(f"Retry {attempt + 1}/{max_retries} after {sleep_time:.1f}s")
                await asyncio.sleep(sleep_time)

        logger.error(f"All {max_retries + 1} retries exhausted for chat")
        self._cb_record_failure()
        raise last_exception

    async def chat_stream(
        self,
        message: str,
        model: str = None,
        context: list[ChatMessage] = None,
        system_prompt: str = None,
    ) -> AsyncGenerator[str, None]:
        """Stream chat response tokens."""
        model = model or self.chat_model

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context:
            messages.extend([{"role": m.role, "content": m.content} for m in context])
        messages.append({"role": "user", "content": message})

        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
        }

        try:
            async with self._client.stream("POST", f"{self.base_url}/api/chat", json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        data = json.loads(line)
                        if "message" in data:
                            yield data["message"]["content"]
                        if data.get("done"):
                            break
        except Exception as e:
            logger.error(f"Ollama stream failed: {e}")
            raise

    async def embeddings(self, text: str | list[str], model: str = None) -> list[list[float]]:
        """Generate embeddings for text(s) using Ollama embeddings API — parallelized with semaphore."""
        model = model or self.embed_model

        if isinstance(text, str):
            texts = [text]
        else:
            texts = text

        if not texts:
            return []

        # Parallelize up to 10 concurrent embedding requests
        sem = asyncio.Semaphore(10)

        async def embed_one(t: str) -> list[float]:
            async with sem:
                payload = {"model": model, "prompt": t}
                response = await self._client.post(
                    f"{self.base_url}/api/embeddings",
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                return response.json()["embedding"]

        results = await asyncio.gather(*[embed_one(t) for t in texts], return_exceptions=True)
        failures = [t for t, r in zip(texts, results) if isinstance(r, Exception)]
        if failures:
            logger.error(f"Embedding failed for {len(failures)} texts: {failures[0]}")
            raise failures[0]
        return results

    async def classify_intent(self, user_input: str) -> dict:
        """Classify user intent using LLM."""
        classification_prompt = f"""You are an intent classifier for a voice assistant. Classify the user query into one of:
- small_talk, technical, kb_query, about_me, unknown

Return ONLY valid JSON: {{"intent": "...", "confidence": 0.0-1.0}}
Do not explain. Do not add fields.

Query: "{user_input}" """

        try:
            response = await self.chat(
                message=classification_prompt,
                system_prompt="You are a JSON-only intent classifier. Return only valid JSON.",
            )
            # Parse JSON from response
            result = json.loads(response.message)
            return {
                "intent": result.get("intent", "unknown"),
                "confidence": result.get("confidence", 0.5),
            }
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse intent classification: {response.message}")
            return {"intent": "unknown", "confidence": 0.0}
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return {"intent": "unknown", "confidence": 0.0}


# Singleton instance
_ollama_client: Optional[OllamaClient] = None


def get_ollama_client() -> OllamaClient:
    """Get or create the singleton Ollama client."""
    global _ollama_client
    if _ollama_client is None:
        _ollama_client = OllamaClient()
    return _ollama_client


def reset_ollama_client():
    """Reset the singleton (useful for testing)."""
    global _ollama_client
    _ollama_client = None
