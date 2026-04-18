"""Document loader for RAG ingestion."""
import os
import json
import re
from typing import Optional
from dataclasses import dataclass

from observability import get_logger
from core.config import config

logger = get_logger("rag.loader")


@dataclass
class LoadedDocument:
    content: str
    metadata: dict


class DocumentLoader:
    """Load documents from various formats."""

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
    ):
        self.chunk_size = chunk_size or config.RAG_CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or config.RAG_CHUNK_OVERLAP

    def load_file(self, file_path: str) -> list[LoadedDocument]:
        """Load a file and return its content as documents."""
        ext = os.path.splitext(file_path)[1].lower()

        if ext == ".txt":
            return self._load_txt(file_path)
        elif ext == ".md":
            return self._load_md(file_path)
        elif ext == ".json":
            return self._load_json(file_path)
        else:
            logger.warning(f"Unsupported file type: {ext}")
            return []

    def _load_txt(self, file_path: str) -> list[LoadedDocument]:
        """Load a text file."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return [LoadedDocument(
            content=content,
            metadata={"source": os.path.basename(file_path), "type": "txt"},
        )]

    def _load_md(self, file_path: str) -> list[LoadedDocument]:
        """Load a markdown file."""
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return [LoadedDocument(
            content=content,
            metadata={"source": os.path.basename(file_path), "type": "md"},
        )]

    def _load_json(self, file_path: str) -> list[LoadedDocument]:
        """Load a JSON file (expects array of objects or object with text fields)."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        documents = []
        if isinstance(data, list):
            for i, item in enumerate(data):
                if isinstance(item, dict):
                    text = self._extract_text_from_dict(item)
                    if text:
                        documents.append(LoadedDocument(
                            content=text,
                            metadata={"source": os.path.basename(file_path), "type": "json", "index": i},
                        ))
        elif isinstance(data, dict):
            text = self._extract_text_from_dict(data)
            if text:
                documents.append(LoadedDocument(
                    content=text,
                    metadata={"source": os.path.basename(file_path), "type": "json"},
                ))

        return documents

    def _extract_text_from_dict(self, d: dict, prefix: str = "") -> str:
        """Extract all text fields from a dictionary."""
        parts = []
        for key, value in d.items():
            if isinstance(value, str) and len(value) > 10:
                parts.append(f"{key}: {value}")
            elif isinstance(value, dict):
                parts.append(self._extract_text_from_dict(value, f"{prefix}{key}."))
        return "\n".join(parts)

    def chunk_text(self, text: str, metadata: dict = None) -> list[LoadedDocument]:
        """Split text into overlapping chunks."""
        if len(text) <= self.chunk_size:
            return [LoadedDocument(content=text, metadata=metadata or {})]

        chunks = []
        start = 0
        chunk_num = 0

        while start < len(text):
            end = start + self.chunk_size
            chunk_text = text[start:end]

            # Try to break at sentence boundary
            if end < len(text):
                last_period = chunk_text.rfind(".")
                last_newline = chunk_text.rfind("\n")
                break_point = max(last_period, last_newline)
                if break_point > self.chunk_size // 2:
                    chunk_text = chunk_text[:break_point + 1]
                    end = start + break_point + 1

            chunk_metadata = (metadata or {}).copy()
            chunk_metadata["chunk"] = chunk_num

            chunks.append(LoadedDocument(content=chunk_text.strip(), metadata=chunk_metadata))

            start = end - self.chunk_overlap
            chunk_num += 1

        return chunks

    def load_and_chunk(self, file_path: str) -> list[LoadedDocument]:
        """Load a file and chunk it."""
        documents = self.load_file(file_path)
        all_chunks = []
        for doc in documents:
            chunks = self.chunk_text(doc.content, doc.metadata)
            all_chunks.extend(chunks)
        return all_chunks
