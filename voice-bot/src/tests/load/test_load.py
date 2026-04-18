"""Load testing script for VoiceBot AXIOM."""
import asyncio
import time
import json
import uuid
import httpx
from typing import List

# Configuration
BASE_URL = "http://localhost:8000"
WS_URL = "ws://localhost:8000/api/ws/voice" # Note: prefix /api included based on orchestrator route
CONCURRENT_USERS = 10
ROUNDS_PER_USER = 5
TIMEOUT = 30.0

async def simulate_user(user_id: int):
    """Simulates a single user session over WebSocket."""
    stats = {"user_id": user_id, "success": 0, "failure": 0, "latencies": []}
    
    async with httpx.AsyncClient() as client:
        # Note: We'd normally use a websocket library here since httpx's WS 
        # support is sometimes limited in older versions. 
        # For a truly robust test, we'll use 'websockets' library.
        try:
            import websockets
        except ImportError:
            print("Please install 'websockets' library: pip install websockets")
            return stats

        try:
            async with websockets.connect(WS_URL) as ws:
                for r in range(ROUNDS_PER_USER):
                    start = time.time()
                    
                    # 1. Send dummy audio data
                    await ws.send(b"fake_audio_content")
                    
                    # 2. Send finalize signal
                    finalize_msg = {"action": "finalize", "voice": "fable"}
                    await ws.send(json.dumps(finalize_msg))
                    
                    # 3. Listen for completion
                    while True:
                        resp = await asyncio.wait_for(ws.recv(), timeout=TIMEOUT)
                        msg = json.loads(resp)
                        
                        if msg["type"] == "done":
                            latency = (time.time() - start) * 1000
                            stats["latencies"].append(latency)
                            stats["success"] += 1
                            break
                        elif msg["type"] == "error":
                            stats["failure"] += 1
                            break
                            
        except Exception as e:
            print(f"User {user_id} connection failed: {e}")
            stats["failure"] += 1
            
    return stats

async def run_load_test():
    """Runs the full load test concurrency scenario."""
    print(f"Starting load test: {CONCURRENT_USERS} concurrent users, {ROUNDS_PER_USER} rounds each...")
    start_time = time.time()
    
    tasks = [simulate_user(i) for i in range(CONCURRENT_USERS)]
    results = await asyncio.gather(*tasks)
    
    end_time = time.time()
    total_duration = end_time - start_time
    
    # Aggregating results
    total_success = sum(r["success"] for r in results)
    total_failure = sum(r["failure"] for r in results)
    all_latencies = [l for r in results for l in r["latencies"]]
    
    avg_latency = sum(all_latencies) / len(all_latencies) if all_latencies else 0
    p95_latency = sorted(all_latencies)[int(len(all_latencies) * 0.95)] if all_latencies else 0
    
    print("\n" + "="*40)
    print("LOAD TEST RESULTS")
    print("="*40)
    print(f"Total Duration:    {total_duration:.2f}s")
    print(f"Total Requests:    {total_success + total_failure}")
    print(f"Success Count:     {total_success}")
    print(f"Failure Count:     {total_failure}")
    print(f"Avg Latency:       {avg_latency:.2f}ms")
    print(f"p95 Latency:       {p95_latency:.2f}ms")
    print(f"Throughput:        {(total_success + total_failure) / total_duration:.2f} req/s")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_load_test())
