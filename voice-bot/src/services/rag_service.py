"""RAG service for knowledge base operations."""
import os
import json
from typing import Optional

from observability import get_logger
from core.config import config
from core.ollama_client import get_ollama_client
from core.exceptions import RAGError

logger = get_logger("services.rag")


class RAGService:
    """High-level RAG service combining retrieval and generation."""

    def __init__(self):
        self._vector_store = None
        self._retriever = None

    @property
    def vector_store(self):
        if self._vector_store is None:
            from rag.vector_store import get_vector_store
            self._vector_store = get_vector_store()
        return self._vector_store

    @property
    def retriever(self):
        if self._retriever is None:
            from rag.retriever import Retriever
            self._retriever = Retriever()
        return self._retriever

    async def ingest_file(self, file_path: str) -> dict:
        """Ingest a file into the knowledge base."""
        logger.info(f"Ingesting file: {file_path}")
        try:
            from rag.document_loader import DocumentLoader
            loader = DocumentLoader()
            chunks = loader.load_and_chunk(file_path)
            documents = [c.content for c in chunks]
            metadatas = [c.metadata for c in chunks]

            ids = await self.vector_store.add_documents(documents, metadatas)
            logger.info(f"Ingested {len(documents)} chunks from {file_path}")
            return {"status": "success", "chunks": len(documents), "ids": ids}
        except Exception as e:
            logger.error(f"Failed to ingest file: {e}")
            raise RAGError(f"Failed to ingest file: {e}")

    async def ingest_text(self, text: str, metadata: dict = None) -> dict:
        """Ingest raw text into the knowledge base."""
        try:
            from rag.document_loader import DocumentLoader
            loader = DocumentLoader()
            chunks = loader.chunk_text(text, metadata)
            documents = [c.content for c in chunks]
            metadatas = [c.metadata for c in chunks]

            ids = await self.vector_store.add_documents(documents, metadatas)
            logger.info(f"Ingested {len(documents)} text chunks")
            return {"status": "success", "chunks": len(documents), "ids": ids}
        except Exception as e:
            logger.error(f"Failed to ingest text: {e}")
            raise RAGError(f"Failed to ingest text: {e}")

    async def seed_from_responses(self, responses_path: str = None) -> dict:
        """Seed the knowledge base from responses.json."""
        if responses_path is None:
            responses_path = config.RAG_RESPONSES_PATH
            # Resolve relative to project root (two levels up from services/)
            if not os.path.isabs(responses_path):
                project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                responses_path = os.path.join(project_root, responses_path)

        if not os.path.exists(responses_path):
            logger.warning(f"Responses file not found: {responses_path}")
            return {"status": "skipped", "reason": "file not found"}

        logger.info(f"Seeding knowledge base from {responses_path}")

        try:
            with open(responses_path, "r", encoding="utf-8") as f:
                responses = json.load(f)

            # Handle nested {"responses": {...}} structure
            if isinstance(responses, dict) and "responses" in responses:
                responses = responses["responses"]

            if isinstance(responses, dict):
                for topic, content in responses.items():
                    if isinstance(content, str):
                        await self.ingest_text(
                            text=content,
                            metadata={"topic": topic, "persona": "ranga", "type": "response"},
                        )
                    elif isinstance(content, list):
                        for item in content:
                            if isinstance(item, str):
                                await self.ingest_text(
                                    text=item,
                                    metadata={"topic": topic, "persona": "ranga", "type": "response"},
                                )

            count = self.vector_store.count()
            
            # Also ingest the ranga_bio.txt if it exists
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            bio_path = os.path.join(project_root, "data", "ranga_bio.txt")
            if os.path.exists(bio_path):
                logger.info("Ingesting professional bio...")
                await self.ingest_file(bio_path)
                
            logger.info(f"Knowledge base seeded. Total documents: {self.vector_store.count()}")
            return {"status": "success", "total_documents": self.vector_store.count()}

        except Exception as e:
            logger.error(f"Failed to seed knowledge base: {e}")
            raise RAGError(f"Failed to seed knowledge base: {e}")

    async def query(self, user_input: str) -> dict:
        """Query the knowledge base and generate a response."""
        try:
            context = await self.retriever.get_context_string(user_input)

            if not context or not context.strip():
                return {"reply": None, "source": "no_context", "context_used": False}

            system_prompt = (
                "You are Ranga Swami, an AI and backend developer. "
                "Answer questions based ONLY on the provided context. "
                "If the context doesn't contain relevant information, say so."
            )

            prompt = f"Context:\n{context}\n\nQuestion: {user_input}\n\nAnswer:"

            client = get_ollama_client()
            response = await client.chat(message=prompt, system_prompt=system_prompt)

            return {
                "reply": response.message,
                "source": "rag",
                "context_used": True,
                "context": context[:200] + "..." if len(context) > 200 else context,
            }

        except Exception as e:
            logger.error(f"RAG query failed: {e}")
            return {"reply": None, "source": "error", "error": str(e)}


_rag_service = None


def get_rag_service() -> RAGService:
    global _rag_service
    if _rag_service is None:
        _rag_service = RAGService()
    return _rag_service
