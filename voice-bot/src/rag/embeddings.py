"""Ollama embeddings wrapper for RAG."""
from typing import Optional

from observability import get_logger
from core.ollama_client import get_ollama_client
from core.config import config

logger = get_logger("rag.embeddings")


class OllamaEmbeddings:
    """Wrapper around Ollama embeddings API."""

    def __init__(self, model: str = None):
        self.model = model or config.OLLAMA_EMBED_MODEL

    async def embed_query(self, text: str) -> list[float]:
        """Embed a single query text."""
        try:
            client = get_ollama_client()
            embeddings = await client.embeddings(text, model=self.model)
            return embeddings[0]
        except Exception as e:
            logger.error(f"Failed to embed query: {e}")
            raise

    async def embed_documents(self, texts: list[str]) -> list[list[float]]:
        """Embed multiple documents."""
        try:
            client = get_ollama_client()
            embeddings = await client.embeddings(texts, model=self.model)
            if not embeddings or any(not e for e in embeddings):
                raise ValueError(f"Ollama returned empty embeddings for {len(texts)} texts")
            return embeddings
        except Exception as e:
            logger.error(f"Failed to embed documents: {e}")
            raise
