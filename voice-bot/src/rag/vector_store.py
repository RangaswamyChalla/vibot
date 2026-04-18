"""ChromaDB vector store integration for RAG."""
import os
import chromadb
from chromadb.config import Settings
from typing import Optional
import uuid
import math

from observability import get_logger
from core.ollama_client import get_ollama_client
from core.config import config

logger = get_logger("rag.vector_store")


class VectorStore:
    """ChromaDB-backed vector store with Ollama embeddings."""

    def __init__(
        self,
        persist_dir: str = None,
        collection_name: str = None,
    ):
        persist_dir = persist_dir or config.RAG_PERSIST_DIR
        collection_name = collection_name or config.RAG_COLLECTION_NAME

        os.makedirs(persist_dir, exist_ok=True)

        self.client = chromadb.PersistentClient(path=persist_dir)

        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"description": "VoiceBot knowledge base"},
        )

        self._embeddings = None

    @property
    def embeddings(self):
        """Lazy load embeddings client."""
        if self._embeddings is None:
            from .embeddings import OllamaEmbeddings
            self._embeddings = OllamaEmbeddings()
        return self._embeddings

    async def add_documents(
        self,
        documents: list[str],
        metadatas: list[dict] = None,
        ids: list[str] = None,
    ) -> list[str]:
        """Add documents to the vector store."""
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in documents]

        if metadatas is None:
            metadatas = [{} for _ in documents]

        # Filter out empty documents before embedding
        valid_docs = [(doc, meta, id) for doc, meta, id in zip(documents, metadatas, ids) if doc and doc.strip()]
        if not valid_docs:
            logger.warning("No valid documents to add (all empty/whitespace)")
            return []
        documents, metadatas, ids = zip(*valid_docs)
        documents, metadatas, ids = list(documents), list(metadatas), list(ids)

        # Generate embeddings
        embeddings = await self.embeddings.embed_documents(documents)

        # Filter out any documents that got empty embeddings
        valid_triplets = [(d, m, i, e) for d, m, i, e in zip(documents, metadatas, ids, embeddings) if e]
        if not valid_triplets:
            raise ValueError("All documents resulted in empty embeddings")
        documents, metadatas, ids, embeddings = zip(*valid_triplets)
        documents, metadatas, ids, embeddings = list(documents), list(metadatas), list(ids), list(embeddings)

        # Add to ChromaDB
        self.collection.add(
            embeddings=embeddings,
            documents=documents,
            metadatas=metadatas,
            ids=ids,
        )

        logger.info(f"Added {len(documents)} documents to vector store")
        return ids

    async def search(
        self,
        query: str,
        n_results: int = None,
        where: dict = None,
        mmr: bool = False,
    ) -> dict:
        """Search for similar documents."""
        n_results = n_results or config.RAG_TOP_K

        # Embed query
        query_embedding = await self.embeddings.embed_query(query)

        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )

        if mmr and len(results.get("documents", [[]])[0]) > 1:
            results = self._rerank_with_mmr(results, query_embedding)

        return results

    def _rerank_with_mmr(self, results: dict, query_embedding: list[float]) -> dict:
        """Rerank results using Maximal Marginal Relevance."""
        docs = results["documents"][0]
        embeddings = results["embeddings"][0]

        if len(docs) <= 1:
            return results

        # Simple MMR: diversify results
        selected = [0]
        remaining = set(range(1, len(docs)))

        lambda_mult = 0.5

        while remaining and len(selected) < min(3, len(docs)):
            best_score = -float("inf")
            best_idx = None

            for idx in remaining:
                rel = self._cosine_similarity(query_embedding, embeddings[idx])
                div = min(
                    self._cosine_similarity(embeddings[idx], embeddings[s])
                    for s in selected
                ) if selected else 0
                mmr_score = lambda_mult * rel - (1 - lambda_mult) * div

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = idx

            if best_idx is not None:
                selected.append(best_idx)
                remaining.remove(best_idx)

        # Reorder results
        reordered_docs = [docs[i] for i in selected]
        reordered_embeddings = [embeddings[i] for i in selected]
        reordered_metadatas = [results["metadatas"][0][i] for i in selected]
        reordered_ids = [results["ids"][0][i] for i in selected]
        reordered_distances = [results["distances"][0][i] for i in selected]

        return {
            "ids": [reordered_ids],
            "documents": [reordered_docs],
            "embeddings": [reordered_embeddings],
            "metadatas": [reordered_metadatas],
            "distances": [reordered_distances],
        }

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float:
        """Compute cosine similarity between two vectors."""
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def delete(self, ids: list[str]) -> None:
        """Delete documents by IDs."""
        self.collection.delete(ids=ids)
        logger.info(f"Deleted {len(ids)} documents from vector store")

    def clear(self) -> None:
        """Clear all documents from the collection."""
        self.collection.delete(where={})
        logger.info("Cleared all documents from vector store")

    def count(self) -> int:
        """Return the number of documents in the store."""
        return self.collection.count()


_vector_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    """Get or create the singleton vector store."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def reset_vector_store():
    """Reset the singleton (useful for testing)."""
    global _vector_store
    _vector_store = None
