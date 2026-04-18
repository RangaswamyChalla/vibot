"""RAG API endpoints."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel

from services.rag_service import get_rag_service
from observability import get_logger

logger = get_logger("api.rag")

router = APIRouter()


class RAGQueryRequest(BaseModel):
    query: str


from typing import Optional, List, Union

class RAGQueryResponse(BaseModel):
    reply: Optional[str] = None
    source: str
    context_used: bool
    context: Optional[str] = None

class RAGIngestResponse(BaseModel):
    status: str
    chunks: Optional[int] = None
    ids: Optional[List[str]] = None
    error: Optional[str] = None

class RAGSeedResponse(BaseModel):
    status: str
    total_documents: Optional[int] = None
    reason: Optional[str] = None

@router.post("/ingest", response_model=RAGIngestResponse)
async def ingest_file(file: UploadFile = File(...)):
    """Ingest a file into the knowledge base."""
    from api.security import get_max_upload_size
    max_size = get_max_upload_size()
    
    if file.size and file.size > max_size:
        raise HTTPException(status_code=413, detail=f"File too large. Max allowed: {max_size / 1024 / 1024}MB")
        
    try:
        import tempfile
        contents = await file.read()
        suffix = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(contents)
            tmp_path = tmp.name

        try:
            result = await get_rag_service().ingest_file(tmp_path)
            return RAGIngestResponse(
                status=result.get("status"),
                chunks=result.get("chunks"),
                ids=result.get("ids"),
            )
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/search", response_model=RAGQueryResponse)
async def search(request: RAGQueryRequest):
    """Search the knowledge base."""
    try:
        result = await get_rag_service().query(request.query)
        return RAGQueryResponse(
            reply=result.get("reply"),
            source=result.get("source", "unknown"),
            context_used=result.get("context_used", False),
            context=result.get("context"),
        )
    except Exception as e:
        logger.error(f"Search error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/seed", response_model=RAGSeedResponse)
async def seed():
    """Seed the knowledge base from responses.json."""
    try:
        result = await get_rag_service().seed_from_responses()
        return RAGSeedResponse(
            status=result.get("status"),
            total_documents=result.get("total_documents"),
            reason=result.get("reason"),
        )
    except Exception as e:
        logger.error(f"Seed error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
