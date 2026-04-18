"""Prometheus metrics exporter for VoiceBot AXIOM."""
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time

# Metrics definitions
REQUEST_COUNT = Counter(
    "voicebot_requests_total", 
    "Total number of requests", 
    ["method", "endpoint", "http_status"]
)

REQUEST_LATENCY = Histogram(
    "voicebot_request_latency_seconds", 
    "Request latency in seconds", 
    ["endpoint"]
)

QUEUE_DEPTH = Gauge(
    "voicebot_queue_depth", 
    "Current number of pending jobs in the queue"
)

JOB_PROCESS_TIME = Histogram(
    "voicebot_job_process_seconds", 
    "Time taken to process a voice job", 
    ["status"]
)

async def metrics_endpoint():
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

def instrument_pipeline(pipeline):
    """Update metrics based on pipeline state."""
    stats = pipeline.metrics()
    QUEUE_DEPTH.set(stats["pending"])
