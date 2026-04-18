"""Integration tests for the RAGService."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.rag_service import RAGService

@pytest.fixture
def mock_dependencies():
    """Mock vector store and retriever for RAGService."""
    with patch("services.rag_service.RAGService.vector_store", new_callable=MagicMock) as mock_vs, \
         patch("services.rag_service.RAGService.retriever", new_callable=MagicMock) as mock_ret:
        
        mock_vs.add_documents = AsyncMock(return_value=["id1", "id2"])
        mock_vs.count.return_value = 2
        
        mock_ret.get_context_string = AsyncMock(return_value="Ranga Swami is a backend engineer.")
        
        yield mock_vs, mock_ret

@pytest.mark.asyncio
async def test_rag_ingest_text(mock_dependencies):
    """Test text ingestion logic."""
    mock_vs, _ = mock_dependencies
    rag = RAGService()
    
    result = await rag.ingest_text("New knowledge content", metadata={"source": "test"})
    
    assert result["status"] == "success"
    assert result["chunks"] == 1
    assert mock_vs.add_documents.called

@pytest.mark.asyncio
async def test_rag_query_with_context(mock_dependencies):
    """Test RAG query flow with mocked LLM."""
    _, mock_ret = mock_dependencies
    rag = RAGService()
    
    # Mock Ollama client
    from core.ollama_client import get_ollama_client
    with patch("services.rag_service.get_ollama_client") as mock_get_ollama:
        mock_ollama = MagicMock()
        mock_ollama.chat = AsyncMock(return_value=type("Resp", (), {"message": "Ranga is a developer."})())
        mock_get_ollama.return_value = mock_ollama
        
        result = await rag.query("What does Ranga do?")
        
        assert result["reply"] == "Ranga is a developer."
        assert result["source"] == "rag"
        assert result["context_used"] is True
        assert "Ranga Swami" in result["context"]

@pytest.mark.asyncio
async def test_rag_query_no_context(mock_dependencies):
    """Test RAG query flow when no context is found."""
    _, mock_ret = mock_dependencies
    mock_ret.get_context_string.return_value = "" # Empry context
    
    rag = RAGService()
    result = await rag.query("Something obscure")
    
    assert result["reply"] is None
    assert result["source"] == "no_context"
    assert result["context_used"] is False
