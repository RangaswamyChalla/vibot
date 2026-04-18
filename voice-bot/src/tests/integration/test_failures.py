import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest
import asyncio
from pipeline.orchestrator import VoiceBotPipeline
from pipeline.queue import JobStatus
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def pipeline():
    return VoiceBotPipeline(
        stt_service=MagicMock(),
        chat_service=MagicMock(),
        tts_service=MagicMock(),
        storage_service=MagicMock()
    )

@pytest.mark.asyncio
async def test_recovery_on_processor_crash(pipeline):
    """Test that if a worker crashes, the pipeline stays alive."""
    
    # Processor that fails once, then succeeds
    call_count = 0
    async def flaky_processor(data):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("CRASH")
        return "SUCCESS"

    await pipeline.start(custom_process_fn=flaky_processor)
    
    # 1. Job fails
    try:
        await pipeline.submit_and_wait("err.wav", timeout=2.0)
    except Exception as e:
        assert "Job failed: CRASH" in str(e)
    
    # 2. Next job succeeds (worker still alive)
    res = await pipeline.submit_and_wait("ok.wav", timeout=2.0)
    assert res == "SUCCESS"
    
    await pipeline.stop()

@pytest.mark.asyncio
async def test_dead_letter_manual_retry(pipeline):
    """Test dead-letter re-enqueue."""
    async def fail_proc(data): raise ValueError("FAIL")
    await pipeline.start(custom_process_fn=fail_proc)
    
    # Job 1 goes to dead letter
    try:
        await pipeline.submit_and_wait("1.wav", timeout=1.0)
    except: pass
    
    assert len(pipeline.queue.get_dead_letter_jobs()) == 1
    job_id = pipeline.queue.get_dead_letter_jobs()[0].id
    
    await pipeline.stop()
    
    # Restart with success
    async def ok_proc(data): return "RETRY_OK"
    await pipeline.start(custom_process_fn=ok_proc)
    
    success = await pipeline.queue.retry_dead_letter_job(job_id)
    assert success is True
    
    # Wait for completion
    while True:
        job = pipeline.queue.get_status(job_id)
        if job.status == JobStatus.COMPLETED:
            break
        await asyncio.sleep(0.1)
    
@pytest.mark.asyncio
async def test_persistence_failure_resilience(pipeline, monkeypatch):
    """Test that the system stays alive even if disk persistence fails."""
    # Mock 'open' to raise an error during _persist_state (run_in_executor)
    from builtins import open as builtin_open
    def mock_open(file, *args, **kwargs):
        if "queue_state" in str(file):
            raise IOError("Disk full or permission denied")
        return builtin_open(file, *args, **kwargs)
    
    # We can't easily monkeypatch 'open' inside the executor thread globally, 
    # but we can monkeypatch 'json.dump' which is called inside the executor.
    import json
    def mock_dump(*args, **kwargs):
        raise IOError("DISK_FAILURE")
    
    monkeypatch.setattr(json, "dump", mock_dump)
    
    await pipeline.start()
    
    # Submission should still work (it will log a warning/error in the background)
    job_id = await pipeline.submit("test.wav")
    assert job_id is not None
    
    # Wait a bit for the executor to run and fail
    await asyncio.sleep(1.0)
    
    # The system should NOT crash (it should just log the error)
    stats = pipeline.metrics()
    assert stats["pending"] >= 0
    
    await pipeline.stop()
