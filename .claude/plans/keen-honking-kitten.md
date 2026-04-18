# Engineering Plan

## Context
Two issues to fix:
1. Async/await bug in `rag_service.py` query() - context string handling may cause issues when context is empty or not properly guarded
2. Add 30s timeout guard to `/api/chat` endpoint - prevent hanging requests

---

## Fix 1: rag_service.py async/await context guard

**File:** `voice-bot/src/services/rag_service.py`

**Issue:** At line 117-120, context is retrieved and checked, but there could be a race condition or the empty context guard might not handle whitespace-only strings.

**Fix:** Add explicit whitespace check in the empty context guard:

```python
# Line 119, change:
if not context:
# To:
if not context or not context.strip():
```

---

## Fix 2: Add timeout to /api/chat endpoint

**File:** `voice-bot/src/api/routes/chat.py`

**Approach:** Use `asyncio.timeout` (Python 3.11+) or `asyncio.wait_for` with 30s timeout around the entire chat handler or the Ollama call specifically.

**Fix:** Add timeout wrapper to the chat endpoint:

```python
import asyncio

@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Text chat endpoint with intent routing."""
    start = time.time()

    try:
        async with asyncio.timeout(30.0):
            # ... existing logic ...
```

Or apply timeout to the Ollama call specifically at line 103:
```python
response = await asyncio.wait_for(
    client.chat(message=request.message, context=chat_context),
    timeout=30.0
)
```

**Decision:** Apply timeout to the entire handler block for comprehensive latency protection.

---

## Critical Files
- `voice-bot/src/services/rag_service.py` (line 119)
- `voice-bot/src/api/routes/chat.py` (line 63+)

## Verification
1. Run the API server and send test requests
2. Verify RAG queries with empty KB return proper `no_context` responses
3. Confirm timeout triggers and returns proper error response after 30s