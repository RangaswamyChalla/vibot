"""Async job queue with in-memory storage and worker pool."""
import asyncio
import json
import os
import time
import uuid
from enum import Enum
from typing import Callable, Any, Optional
from dataclasses import dataclass, field
from collections import deque
import threading
import queue as sync_queue

from observability import get_logger

logger = get_logger("pipeline.queue")

class JobStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

@dataclass
class Job:
    id: str
    data: Any
    status: JobStatus = JobStatus.PENDING
    result: Any = None
    error: str = None
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None
    metadata: dict = field(default_factory=dict)

class AsyncQueue:
    """In-memory async job queue with worker pool with disk persistence."""

    def __init__(self, max_size: int = 100, worker_count: int = 4, purge_after_seconds: int = 3600,
                 dead_letter_max: int = 1000, persist_path: str = None):
        self.max_size = max_size
        self.worker_count = worker_count
        self._jobs: dict[str, Job] = {}
        self._pending: asyncio.Queue = asyncio.Queue(maxsize=max_size)
        self._lock = asyncio.Lock()
        self._workers: list[asyncio.Task] = []
        self._running = False
        self._purge_after_seconds = purge_after_seconds
        self._last_purge_at = time.time()
        self._dead_letter: deque = deque(maxlen=dead_letter_max)
        self._persist_path = persist_path
        if persist_path and os.path.exists(persist_path):
            self._load_state()

    def _purge_completed_jobs(self) -> int:
        """Remove completed jobs older than _purge_after_seconds. Returns count purged."""
        if time.time() - self._last_purge_at < 60:
            return 0  # Throttle: only purge once per minute

        cutoff = time.time() - self._purge_after_seconds
        to_remove = [
            job_id for job_id, job in self._jobs.items()
            if job.status == JobStatus.COMPLETED
            and job.completed_at is not None
            and job.completed_at < cutoff
        ]

        for job_id in to_remove:
            del self._jobs[job_id]

        if to_remove:
            logger.info(f"Purged {len(to_remove)} old jobs from queue")

        self._last_purge_at = time.time()
        return len(to_remove)

    async def enqueue(self, job_id: str, data: Any, metadata: dict = None) -> Job:
        """Add a job to the queue."""
        async with self._lock:
            if len(self._jobs) >= self.max_size:
                raise Exception(f"Queue full: {self.max_size} jobs max")

            job = Job(id=job_id, data=data, metadata=metadata or {})
            self._jobs[job_id] = job
            self._pending.put_nowait(job_id)
            logger.info(f"Job enqueued: {job_id}, queue_size={self._pending.qsize()}")
            await self._persist_state()
            return job

    def get_status(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    async def _worker(self, worker_id: int, process_fn: Callable):
        """Worker coroutine that processes jobs from the queue."""
        logger.info(f"Worker {worker_id} started")
        while self._running:
            try:
                job_id = await asyncio.wait_for(self._pending.get(), timeout=1.0)
                job = self._jobs.get(job_id)

                if not job:
                    continue

                job.status = JobStatus.PROCESSING
                logger.info(f"Worker {worker_id} processing job {job_id}")

                try:
                    result = await process_fn(job.data)
                    job.result = result
                    job.status = JobStatus.COMPLETED
                    job.completed_at = time.time()
                    logger.info(f"Job {job_id} completed in {job.completed_at - job.created_at:.2f}s")
                except Exception as e:
                    job.status = JobStatus.FAILED
                    job.error = str(e)
                    job.completed_at = time.time()
                    logger.error(f"Job {job_id} failed: {e}")
                    # Move to dead-letter queue for later inspection/retry
                    self._dead_letter.append(job)
                    logger.info(f"Job {job_id} moved to dead-letter queue ({len(self._dead_letter)} total)")

                # Periodic purge of old completed/failed jobs
                self._purge_completed_jobs()
                async with self._lock:
                    await self._persist_state()

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")

        logger.info(f"Worker {worker_id} stopped")

    async def start(self, process_fn: Callable):
        """Start the worker pool."""
        self._running = True
        self._workers = [
            asyncio.create_task(self._worker(i, process_fn))
            for i in range(self.worker_count)
        ]
        logger.info(f"Started {self.worker_count} workers")

    async def stop(self):
        """Stop all workers gracefully."""
        self._running = False
        for w in self._workers:
            w.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers = []
        logger.info("All workers stopped")

    def get_metrics(self) -> dict:
        """Return queue metrics."""
        total = len(self._jobs)
        pending = sum(1 for j in self._jobs.values() if j.status == JobStatus.PENDING)
        processing = sum(1 for j in self._jobs.values() if j.status == JobStatus.PROCESSING)
        completed = sum(1 for j in self._jobs.values() if j.status == JobStatus.COMPLETED)
        failed = sum(1 for j in self._jobs.values() if j.status == JobStatus.FAILED)

        return {
            "total_jobs": total,
            "pending": pending,
            "processing": processing,
            "completed": completed,
            "failed": failed,
            "dead_letter": len(self._dead_letter),
            "queue_size": self._pending.qsize()
        }

    def get_dead_letter_jobs(self, limit: int = 100) -> list[Job]:
        """Return dead-lettered jobs, newest first."""
        jobs = list(self._dead_letter)
        return sorted(jobs, key=lambda j: j.completed_at or 0, reverse=True)[:limit]

    async def retry_dead_letter_job(self, job_id: str) -> bool:
        """Re-enqueue a dead-lettered job for reprocessing. Returns True if found and re-enqueued."""
        async with self._lock:
            job = None
            for j in self._dead_letter:
                if j.id == job_id:
                    job = j
                    self._dead_letter.remove(j)
                    break
            if not job:
                return False

            # Reset job state
            job.status = JobStatus.PENDING
            job.error = None
            job.completed_at = None
            job.result = None
            job.created_at = time.time()

            self._jobs[job_id] = job
            self._pending.put_nowait(job_id)
            logger.info(f"Job {job_id} re-enqueued from dead-letter queue")
            await self._persist_state()
            return True

    def _job_to_dict(self, job: Job) -> dict:
        """Serialize job to dict (excludes large result field)."""
        return {
            "id": job.id,
            "data": job.data,
            "status": job.status.value,
            "error": job.error,
            "created_at": job.created_at,
            "completed_at": job.completed_at,
            "metadata": job.metadata,
        }

    def _dict_to_job(self, d: dict) -> Job:
        """Reconstruct Job from dict."""
        return Job(
            id=d["id"],
            data=d["data"],
            status=JobStatus(d["status"]),
            error=d.get("error"),
            created_at=d.get("created_at", time.time()),
            completed_at=d.get("completed_at"),
            metadata=d.get("metadata", {}),
        )

    async def _persist_state(self) -> None:
        """Flush PENDING/PROCESSING job state to disk for restart recovery."""
        if not self._persist_path:
            return

        # Note: caller must hold self._lock
        active_jobs = {
            jid: self._job_to_dict(job)
            for jid, job in self._jobs.items()
            if job.status in (JobStatus.PENDING, JobStatus.PROCESSING)
        }
        pending_ids = list(self._pending._queue)

        state = {
            "version": 1,
            "persisted_at": time.time(),
            "jobs": active_jobs,
            "pending_ids": pending_ids,
        }

        def _write():
            tmp = self._persist_path + ".tmp"
            with open(tmp, "w") as f:
                json.dump(state, f)
            os.replace(tmp, self._persist_path)

        start = time.perf_counter()
        try:
            await asyncio.get_event_loop().run_in_executor(None, _write)
        except Exception as e:
            logger.critical("CRITICAL: Failed to persist queue state to disk. System running in volatile mode: %s", e)
            
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.debug(
            "Queue state persisted: active_jobs=%s pending_ids=%s latency_ms=%.2f",
            len(active_jobs),
            len(pending_ids),
            elapsed_ms,
        )

    def _load_state(self) -> int:
        """Rehydrate queue from disk state file. Returns count of re-enqueued jobs."""
        if not self._persist_path or not os.path.exists(self._persist_path):
            return 0

        try:
            with open(self._persist_path) as f:
                state = json.load(f)

            loaded = 0
            for jid, job_dict in state.get("jobs", {}).items():
                job = self._dict_to_job(job_dict)
                if job.status == JobStatus.PENDING:
                    self._jobs[jid] = job
                    self._pending.put_nowait(jid)
                    loaded += 1
                elif job.status == JobStatus.PROCESSING:
                    # Treat PROCESSING jobs as PENDING on restart — they were in-flight
                    # when the server died; safest to reprocess them
                    job.status = JobStatus.PENDING
                    self._jobs[jid] = job
                    self._pending.put_nowait(jid)
                    loaded += 1

            logger.info(f"Queue state reloaded: {loaded} jobs restored from {self._persist_path}")
            return loaded
        except Exception as e:
            logger.warning(f"Failed to load queue state from {self._persist_path}: {e}")
            return 0

    def clear_persist(self) -> None:
        """Delete the on-disk persistence file. Use after a clean shutdown."""
        if self._persist_path and os.path.exists(self._persist_path):
            os.remove(self._persist_path)
            logger.info("Queue persistence file cleared")