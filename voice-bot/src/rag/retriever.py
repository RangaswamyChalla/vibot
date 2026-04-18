"""Retriever with MMR reranking for RAG."""
from typing import Optional
from dataclasses import dataclass

from observability import get_logger
from core.config import config
from .vector_store import get_vector_store

logger = get_logger("rag.retriever")


@dataclass
class RetrievedChunk:
    content: str
    metadata: dict
    score: float


class Retriever:
    """Retriever with MMR (Maximal Marginal Relevance) diversity."""

    def __init__(
        self,
        top_k: int = None,
        mmr: bool = True,
    ):
        self.top_k = top_k or config.RAG_TOP_K
        self.mmr = mmr

    async def retrieve(self, query: str, top_k: int = None) -> list[RetrievedChunk]:
        """Retrieve relevant chunks for a query."""
        k = top_k or self.top_k

        try:
            results = await get_vector_store().search(
                query=query,
                n_results=k,
                mmr=self.mmr,
            )

            chunks = []
            docs = results.get("documents", [[]])[0]
            metadatas = results.get("metadatas", [[{}]])[0]
            distances = results.get("distances", [[]])[0]

            for i, doc in enumerate(docs):
                metadata = metadatas[i] if i < len(metadatas) else {}
                score = 1.0 - distances[i] if i < len(distances) else 0.0
                chunks.append(RetrievedChunk(
                    content=doc,
                    metadata=metadata,
                    score=score,
                ))

            logger.debug(f"Retrieved {len(chunks)} chunks for query: {query[:50]}...")
            return chunks

        except Exception as e:
            logger.error(f"Retrieval failed: {e}")
            raise

    async def get_context_string(self, query: str, top_k: int = None) -> str:
        """Get formatted context string from retrieved chunks."""
        chunks = await self.retrieve(query, top_k)
        if not chunks:
            return ""

        context_parts = []
        for chunk in chunks:
            source = chunk.metadata.get("source", "unknown")
            context_parts.append(f"[Source: {source}]\n{chunk.content}")

        return "\n\n".join(context_parts)
