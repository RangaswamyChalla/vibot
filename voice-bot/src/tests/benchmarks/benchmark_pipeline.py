"""Performance benchmarks for VoiceBot AXIOM components."""
import asyncio
import time
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from services.stt_service import STTService
from services.chat_service import ChatService
from services.tts_service import TTSService
from core.ollama_client import get_ollama_client

async def benchmark_stt(audio_path: str):
    print(f"Benchmarking STT for {audio_path}...")
    stt = STTService()
    start = time.perf_counter()
    text = await stt.transcribe(audio_path)
    end = time.perf_counter()
    print(f"STT Latency: {end - start:.4f}s")
    print(f"Transcript: {text[:50]}...")
    return end - start

async def benchmark_llm(prompt: str):
    print(f"Benchmarking LLM (Ollama)...")
    client = get_ollama_client()
    if not await client.is_available():
        print("Ollama not available, skipping.")
        return None
        
    start = time.perf_counter()
    resp = await client.chat(message=prompt)
    end = time.perf_counter()
    
    latency = end - start
    tokens = len(resp.message) // 4 # Rough estimate
    tps = tokens / latency if latency > 0 else 0
    
    print(f"LLM Latency: {latency:.4f}s")
    print(f"Estimated TPS: {tps:.2f} tokens/sec")
    return latency

async def benchmark_tts(text: str):
    print(f"Benchmarking TTS...")
    tts = TTSService()
    start = time.perf_counter()
    # Mocking run_in_executor since tts.synthesize is sync
    loop = asyncio.get_event_loop()
    audio = await loop.run_in_executor(None, tts.synthesize, text)
    end = time.perf_counter()
    
    latency = end - start
    print(f"TTS Latency: {latency:.4f}s")
    print(f"Audio Generated: {len(audio)} bytes")
    return latency

async def run_all():
    results = {}
    
    # Text for LLM/TTS
    prompt = "Explain why async programming is important for real-time applications."
    
    results["llm"] = await benchmark_llm(prompt)
    results["tts"] = await benchmark_tts("Hello, this is a performance benchmark of the AXIOM voice system.")
    
    print("\n" + "="*40)
    print("BENCHMARK SUMMARY")
    print("="*40)
    for service, latency in results.items():
        if latency:
            print(f"{service.upper():<10}: {latency:.4f}s")
    print("="*40)

if __name__ == "__main__":
    asyncio.run(run_all())
