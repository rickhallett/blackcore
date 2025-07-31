"""Run the job worker separately from the API server."""

import asyncio
import os
import signal
import sys
import logging

from .jobs import JobQueue, JobWorker
from ..config import ConfigManager


logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


async def main():
    """Run the job worker."""
    # Load configuration
    config_manager = ConfigManager()
    config = config_manager.load()

    # Initialize job queue
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    job_queue = JobQueue(redis_url=redis_url)

    try:
        await job_queue.connect()
        logger.info(f"Connected to Redis at {redis_url}")
    except Exception as e:
        logger.error(f"Failed to connect to Redis: {e}")
        sys.exit(1)

    # Create worker
    max_concurrent_jobs = int(os.getenv("MAX_CONCURRENT_JOBS", "5"))
    worker = JobWorker(job_queue=job_queue, config=config, max_concurrent_jobs=max_concurrent_jobs)

    # Handle shutdown signals
    stop_event = asyncio.Event()

    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        stop_event.set()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Start worker
    logger.info(f"Starting worker with max {max_concurrent_jobs} concurrent jobs")

    try:
        # Run worker until stop signal
        worker_task = asyncio.create_task(worker.start())
        stop_task = asyncio.create_task(stop_event.wait())

        # Wait for either worker to stop or stop signal
        done, pending = await asyncio.wait(
            [worker_task, stop_task], return_when=asyncio.FIRST_COMPLETED
        )

        # Cancel pending tasks
        for task in pending:
            task.cancel()

        # Stop worker gracefully
        await worker.stop()

    finally:
        await job_queue.disconnect()
        logger.info("Worker stopped")


if __name__ == "__main__":
    asyncio.run(main())
