"""Integration tests for the AsyncQueue with persistence and dead-letter support."""
import pytest
import asyncio
import os
import json
import tempfile
from unittest.mock import MagicMock, AsyncMock

import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pipeline.queue import AsyncQueue, JobStatus

@pytest.mark.asyncio
async def test_queue_persistence_roundtrip():
    """Test that the queue correctly persists and reloads its state."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".json") as tmp:
        persist_path = tmp.name
    
    try:
        # 1. Enqueue some jobs
        queue = AsyncQueue(max_size=10, persist_path=persist_path)
        await queue.enqueue("job-1", {"task": "test-1"})
        await queue.enqueue("job-2", {"task": "test-2"})
        
        # Verify they are in memory
        assert queue.get_status("job-1").status == JobStatus.PENDING
        
        # 2. Shut down and reload from a NEW instance
        # (persistence happens on enqueue automatically)
        new_queue = AsyncQueue(max_size=10, persist_path=persist_path)
        
        # 3. Verify jobs were restored
        assert new_queue.get_status("job-1") is not None
        assert new_queue.get_status("job-2") is not None
        assert new_queue.get_status("job-1").data["task"] == "test-1"
        assert new_queue.get_metrics()["pending"] == 2
        
    finally:
        if os.path.exists(persist_path):
            os.remove(persist_path)

@pytest.mark.asyncio
async def test_dead_letter_recovery():
    """Test that failing jobs go to dead-letter and can be retried."""
    queue = AsyncQueue(max_size=10)
    
    # Define a failing processor
    async def failing_task(data):
        raise ValueError("Simulated failure")
        
    await queue.start(failing_task)
    
    # Enqueue a job
    await queue.enqueue("fail-job", {"x": 1})
    
    # Wait for completion (failure)
    start = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start < 2.0:
        job = queue.get_status("fail-job")
        if job and job.status == JobStatus.FAILED:
            break
        await asyncio.sleep(0.1)
        
    assert queue.get_status("fail-job").status == JobStatus.FAILED
    assert len(queue.get_dead_letter_jobs()) == 1
    
    await queue.stop()
    
    # Now retry it with a successful processor
    async def success_task(data):
        return "success"
        
    await queue.start(success_task)
    
    # Retry from dead-letter
    success = await queue.retry_dead_letter_job("fail-job")
    assert success is True
    
    # Wait for completion (success)
    start = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start < 2.0:
        job = queue.get_status("fail-job")
        if job and job.status == JobStatus.COMPLETED:
            break
        await asyncio.sleep(0.1)
        
    assert queue.get_status("fail-job").status == JobStatus.COMPLETED
    assert len(queue.get_dead_letter_jobs()) == 0
    
    await queue.stop()

@pytest.mark.asyncio
async def test_queue_concurrency():
    """Test that multiple workers process jobs in parallel."""
    queue = AsyncQueue(max_size=10, worker_count=4)
    processed_count = 0
    
    async def fast_task(data):
        nonlocal processed_count
        await asyncio.sleep(0.1)
        processed_count += 1
        return "done"
        
    await queue.start(fast_task)
    
    for i in range(8):
        await queue.enqueue(f"job-{i}", i)
        
    # Wait for all to finish
    start = asyncio.get_event_loop().time()
    while asyncio.get_event_loop().time() - start < 5.0:
        if queue.get_metrics()["completed"] == 8:
            break
        await asyncio.sleep(0.1)
        
    assert processed_count == 8
    await queue.stop()
