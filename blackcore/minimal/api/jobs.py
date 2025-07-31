"""Job queue system for async transcript processing."""

import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List
import logging

import redis.asyncio as redis

from .models import ProcessingJob, JobStatus
from ..models import TranscriptInput, ProcessingResult
from ..transcript_processor import TranscriptProcessor
from ..config import Config


logger = logging.getLogger(__name__)


class JobQueue:
    """Redis-based job queue for async processing."""

    def __init__(
        self,
        redis_url: str = "redis://localhost:6379",
        queue_name: str = "transcript_processing",
        result_ttl: int = 3600,  # 1 hour
    ):
        self.redis_url = redis_url
        self.queue_name = queue_name
        self.result_ttl = result_ttl
        self._redis: Optional[redis.Redis] = None

    async def connect(self):
        """Connect to Redis."""
        if not self._redis:
            self._redis = await redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )

    async def disconnect(self):
        """Disconnect from Redis."""
        if self._redis:
            await self._redis.close()
            self._redis = None

    async def enqueue_job(
        self,
        transcript: TranscriptInput,
        options: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProcessingJob:
        """Add a job to the queue."""
        await self.connect()

        job_id = str(uuid.uuid4())
        now = datetime.utcnow()

        job = ProcessingJob(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

        # Store job data
        job_data = {
            "job": job.model_dump_json(),
            "transcript": transcript.model_dump_json(),
            "options": json.dumps(options),
        }

        # Save to Redis
        await self._redis.hset(f"job:{job_id}", mapping=job_data)

        # Add to queue
        await self._redis.lpush(self.queue_name, job_id)

        # Set expiration
        await self._redis.expire(f"job:{job_id}", self.result_ttl)

        logger.info(f"Enqueued job {job_id}")

        return job

    async def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Get job status."""
        await self.connect()

        job_data = await self._redis.hget(f"job:{job_id}", "job")

        if not job_data:
            return None

        return ProcessingJob.model_validate_json(job_data)

    async def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        error: Optional[str] = None,
        result: Optional[ProcessingResult] = None,
    ):
        """Update job status."""
        await self.connect()

        job = await self.get_job(job_id)
        if not job:
            return

        # Update fields
        job.updated_at = datetime.utcnow()

        if status:
            job.status = status

            if status == JobStatus.PROCESSING and not job.started_at:
                job.started_at = job.updated_at
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED] and not job.completed_at:
                job.completed_at = job.updated_at

        if progress is not None:
            job.progress = progress

        if error:
            job.error = error

        if result:
            # Store result separately
            await self._redis.hset(f"job:{job_id}", "result", result.model_dump_json())
            job.result_url = f"/jobs/{job_id}/result"

        # Save updated job
        await self._redis.hset(f"job:{job_id}", "job", job.model_dump_json())

        logger.info(f"Updated job {job_id}: status={status}, progress={progress}")

    async def get_result(self, job_id: str) -> Optional[ProcessingResult]:
        """Get job result."""
        await self.connect()

        result_data = await self._redis.hget(f"job:{job_id}", "result")

        if not result_data:
            return None

        return ProcessingResult.model_validate_json(result_data)

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a pending job."""
        await self.connect()

        job = await self.get_job(job_id)
        if not job or job.status != JobStatus.PENDING:
            return False

        await self.update_job(job_id, status=JobStatus.CANCELLED)

        # Remove from queue
        await self._redis.lrem(self.queue_name, 0, job_id)

        return True

    async def get_pending_jobs(self, limit: int = 100) -> List[str]:
        """Get pending job IDs."""
        await self.connect()

        job_ids = await self._redis.lrange(self.queue_name, 0, limit - 1)
        return job_ids


class JobWorker:
    """Worker to process jobs from the queue."""

    def __init__(self, job_queue: JobQueue, config: Config, max_concurrent_jobs: int = 5):
        self.job_queue = job_queue
        self.config = config
        self.max_concurrent_jobs = max_concurrent_jobs
        self._running = False
        self._tasks: List[asyncio.Task] = []

    async def start(self):
        """Start the worker."""
        self._running = True
        logger.info("Job worker started")

        while self._running:
            try:
                # Get pending jobs
                pending_jobs = await self.job_queue.get_pending_jobs(
                    limit=self.max_concurrent_jobs - len(self._tasks)
                )

                # Clean completed tasks
                self._tasks = [t for t in self._tasks if not t.done()]

                # Process new jobs
                for job_id in pending_jobs:
                    if len(self._tasks) >= self.max_concurrent_jobs:
                        break

                    task = asyncio.create_task(self._process_job(job_id))
                    self._tasks.append(task)

                # Wait a bit before checking again
                await asyncio.sleep(1)

            except Exception as e:
                logger.error(f"Worker error: {e}")
                await asyncio.sleep(5)

    async def stop(self):
        """Stop the worker."""
        self._running = False

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        # Wait for tasks to complete
        await asyncio.gather(*self._tasks, return_exceptions=True)

        logger.info("Job worker stopped")

    async def _process_job(self, job_id: str):
        """Process a single job."""
        try:
            # Get job details
            job_data = await self.job_queue._redis.hgetall(f"job:{job_id}")

            if not job_data:
                logger.error(f"Job {job_id} not found")
                return

            # Parse data
            transcript = TranscriptInput.model_validate_json(job_data["transcript"])
            options = json.loads(job_data["options"])

            # Update status
            await self.job_queue.update_job(job_id, status=JobStatus.PROCESSING, progress=0)

            # Create processor
            processor = TranscriptProcessor(config=self.config)

            # Apply options
            processor.config.processing.dry_run = options.get("dry_run", False)
            processor.config.processing.enable_deduplication = options.get(
                "enable_deduplication", True
            )
            processor.config.processing.deduplication_threshold = options.get(
                "deduplication_threshold", 90.0
            )

            # Process transcript
            logger.info(f"Processing job {job_id}: {transcript.title}")

            result = processor.process_transcript(transcript)

            # Update job with result
            await self.job_queue.update_job(
                job_id,
                status=JobStatus.COMPLETED if result.success else JobStatus.FAILED,
                progress=100,
                result=result,
                error=str(result.errors[0]) if result.errors else None,
            )

            logger.info(f"Completed job {job_id}: success={result.success}")

        except Exception as e:
            logger.error(f"Error processing job {job_id}: {e}")

            await self.job_queue.update_job(job_id, status=JobStatus.FAILED, error=str(e))

        finally:
            # Remove from queue
            await self.job_queue._redis.lpop(self.job_queue.queue_name)


# In-memory fallback for development/testing
class InMemoryJobQueue(JobQueue):
    """In-memory job queue for when Redis is not available."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._queue: List[str] = []

    async def connect(self):
        """No-op for in-memory queue."""
        pass

    async def disconnect(self):
        """No-op for in-memory queue."""
        pass

    async def enqueue_job(
        self,
        transcript: TranscriptInput,
        options: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ProcessingJob:
        """Add a job to the in-memory queue."""
        job_id = str(uuid.uuid4())
        now = datetime.utcnow()

        job = ProcessingJob(
            job_id=job_id,
            status=JobStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )

        self._jobs[job_id] = {
            "job": job,
            "transcript": transcript,
            "options": options,
            "result": None,
        }

        self._queue.append(job_id)

        return job

    async def get_job(self, job_id: str) -> Optional[ProcessingJob]:
        """Get job from memory."""
        job_data = self._jobs.get(job_id)
        return job_data["job"] if job_data else None

    async def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        error: Optional[str] = None,
        result: Optional[ProcessingResult] = None,
    ):
        """Update job in memory."""
        if job_id not in self._jobs:
            return

        job = self._jobs[job_id]["job"]
        job.updated_at = datetime.utcnow()

        if status:
            job.status = status

            if status == JobStatus.PROCESSING and not job.started_at:
                job.started_at = job.updated_at
            elif status in [JobStatus.COMPLETED, JobStatus.FAILED] and not job.completed_at:
                job.completed_at = job.updated_at

        if progress is not None:
            job.progress = progress

        if error:
            job.error = error

        if result:
            self._jobs[job_id]["result"] = result
            job.result_url = f"/jobs/{job_id}/result"

    async def get_result(self, job_id: str) -> Optional[ProcessingResult]:
        """Get result from memory."""
        job_data = self._jobs.get(job_id)
        return job_data["result"] if job_data else None

    async def cancel_job(self, job_id: str) -> bool:
        """Cancel a job in memory."""
        if job_id not in self._jobs:
            return False

        job = self._jobs[job_id]["job"]
        if job.status != JobStatus.PENDING:
            return False

        job.status = JobStatus.CANCELLED
        job.updated_at = datetime.utcnow()

        if job_id in self._queue:
            self._queue.remove(job_id)

        return True

    async def get_pending_jobs(self, limit: int = 100) -> List[str]:
        """Get pending jobs from memory."""
        return self._queue[:limit]
