import asyncio
import time
import statistics
import os
import sys
from typing import List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from pipeline.orchestrator import VoiceBotPipeline
from pipeline.queue import JobStatus
from unittest.mock import MagicMock, AsyncMock

async def simulate_pipeline_run(pipeline, concurrent_users: int):
    """Simulate N users hitting the pipeline at once."""
    
    # Mock services to respond with realistic-ish latencies
    async def mock_processor(data):
        # Transcribe (500ms)
        await asyncio.sleep(0.5)
        # Chat (1.5s)
        await asyncio.sleep(1.5)
        # TTS (800ms)
        await asyncio.sleep(0.8)
        return {"text": "hello", "reply": "good day", "audio": b"data"}

    # Re-wrap a fresh pipeline for this test
    p = VoiceBotPipeline(
        stt_service=MagicMock(),
        chat_service=MagicMock(),
        tts_service=MagicMock(),
        storage_service=MagicMock(),
        worker_count=min(concurrent_users, 20) # Max 20 workers
    )
    p.queue._pending = asyncio.Queue() # fresh queue
    await p.start(custom_process_fn=mock_processor)

    start_time = time.perf_counter()
    
    tasks = []
    for i in range(concurrent_users):
        tasks.append(p.submit_and_wait(f"audio_{i}.wav", timeout=60.0))
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    end_time = time.perf_counter()
    duration = end_time - start_time
    
    # Analyze results
    latencies = []
    successes = 0
    errors = 0
    
    for r in results:
        if isinstance(r, dict):
            successes += 1
            # In a real scenario we'd measure individual job times
        else:
            errors += 1

    await p.stop()
    
    return {
        "users": concurrent_users,
        "duration": duration,
        "throughput": successes / duration,
        "successes": successes,
        "errors": errors,
    }

async def main():
    print("=== AXIOM STRESS TEST ===")
    for users in [10, 50, 100]:
        print(f"Testing {users} concurrent users...")
        stats = await simulate_pipeline_run(None, users)
        print(f"  Duration: {stats['duration']:.2f}s")
        print(f"  Throughput: {stats['throughput']:.2f} RPS")
        print(f"  Success: {stats['successes']} | Errors: {stats['errors']}")
        print("-" * 30)

if __name__ == "__main__":
    asyncio.run(main())
