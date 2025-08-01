"""Main FastAPI application."""

import os
from contextlib import asynccontextmanager
from typing import Dict, Any, List, Optional

from fastapi import FastAPI, HTTPException, Depends, Security, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from .models import (
    HealthResponse,
    TokenRequest,
    TokenResponse,
    TranscriptProcessRequest,
    BatchProcessRequest,
    ProcessingResponse,
    ProcessingJob,
    APIError,
    ConfigResponse,
    DatabaseInfo,
    ValidationRuleUpdate,
)
from .auth import auth_handler, get_current_user, require_admin, rate_limiter
from .jobs import JobQueue, InMemoryJobQueue, JobWorker
from .query_endpoints import router as query_router
from ..config import ConfigManager
from ..models import ProcessingResult
from ..property_validation import ValidationLevel


logger = structlog.get_logger()


# Global instances
job_queue: Optional[JobQueue] = None
job_worker: Optional[JobWorker] = None
config_manager: Optional[ConfigManager] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle."""
    global job_queue, job_worker, config_manager

    # Initialize configuration
    config_manager = ConfigManager()
    config = config_manager.load()

    # Initialize job queue
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")

    try:
        job_queue = JobQueue(redis_url=redis_url)
        await job_queue.connect()
        logger.info("Connected to Redis job queue")
    except Exception as e:
        logger.warning(f"Failed to connect to Redis: {e}. Using in-memory queue.")
        job_queue = InMemoryJobQueue()

    # Start job worker
    job_worker = JobWorker(job_queue=job_queue, config=config)

    # Start worker in background (in production, run separately)
    if os.getenv("RUN_WORKER", "true").lower() == "true":
        import asyncio

        asyncio.create_task(job_worker.start())

    yield

    # Cleanup
    if job_worker:
        await job_worker.stop()

    if job_queue:
        await job_queue.disconnect()


def create_app(title: str = "Blackcore Minimal API", version: str = "1.0.0") -> FastAPI:
    """Create and configure the FastAPI application."""

    app = FastAPI(
        title=title,
        version=version,
        description="HTTP(S) API for Blackcore Minimal Transcript Processor",
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Exception handlers
    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=APIError(
                error_code=f"HTTP_{exc.status_code}",
                message=exc.detail,
                request_id=request.headers.get("X-Request-ID"),
            ).model_dump(mode="json"),
        )

    # Health check
    @app.get("/health", response_model=HealthResponse, tags=["System"], summary="Health check")
    async def health_check():
        """Check system health and component status."""
        checks = {
            "api": {"status": "healthy"},
            "job_queue": {
                "status": "healthy" if job_queue else "unhealthy",
                "type": type(job_queue).__name__ if job_queue else "none",
            },
            "config": {"status": "healthy" if config_manager else "unhealthy"},
        }

        overall_status = (
            "healthy"
            if all(check["status"] == "healthy" for check in checks.values())
            else "unhealthy"
        )

        return HealthResponse(status=overall_status, version="1.0.0", checks=checks)

    # Authentication
    @app.post(
        "/auth/token",
        response_model=TokenResponse,
        tags=["Authentication"],
        summary="Generate access token",
    )
    async def generate_token(request: TokenRequest):
        """Generate JWT access token from API key."""
        # In production, validate API key against database
        # For now, add basic validation

        if not request.api_key or not request.api_key.strip():
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")

        return auth_handler.generate_token_response(
            api_key=request.api_key, expires_in=request.expires_in
        )

    # Transcript processing
    @app.post(
        "/transcripts/process",
        response_model=ProcessingResponse,
        tags=["Transcripts"],
        summary="Process a single transcript",
        dependencies=[Depends(rate_limiter.rate_limit_dependency)],
    )
    async def process_transcript(
        request: TranscriptProcessRequest, current_user: Dict[str, Any] = Security(get_current_user)
    ):
        """Submit a transcript for processing."""
        if not job_queue:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Job queue not available"
            )

        # Enqueue job
        job = await job_queue.enqueue_job(
            transcript=request.transcript,
            options=request.options.model_dump(),
            metadata={"user": current_user.get("sub")},
        )

        # Generate response
        response = ProcessingResponse(
            request_id=f"req_{job.job_id}",
            job=job,
            links={
                "self": f"/jobs/{job.job_id}",
                "result": f"/jobs/{job.job_id}/result",
                "cancel": f"/jobs/{job.job_id}/cancel",
            },
        )

        return response

    @app.post(
        "/transcripts/batch",
        response_model=List[ProcessingResponse],
        tags=["Transcripts"],
        summary="Process multiple transcripts",
        dependencies=[Depends(rate_limiter.rate_limit_dependency)],
    )
    async def process_batch(
        request: BatchProcessRequest, current_user: Dict[str, Any] = Security(get_current_user)
    ):
        """Submit multiple transcripts for processing."""
        if not job_queue:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Job queue not available"
            )

        responses = []

        for transcript in request.transcripts:
            job = await job_queue.enqueue_job(
                transcript=transcript,
                options=request.options.model_dump(),
                metadata={"user": current_user.get("sub"), "batch": True},
            )

            response = ProcessingResponse(
                request_id=f"req_{job.job_id}",
                job=job,
                links={
                    "self": f"/jobs/{job.job_id}",
                    "result": f"/jobs/{job.job_id}/result",
                    "cancel": f"/jobs/{job.job_id}/cancel",
                },
            )

            responses.append(response)

        return responses

    # Job management
    @app.get(
        "/jobs/{job_id}", response_model=ProcessingJob, tags=["Jobs"], summary="Get job status"
    )
    async def get_job_status(
        job_id: str, current_user: Dict[str, Any] = Security(get_current_user)
    ):
        """Get the status of a processing job."""
        if not job_queue:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Job queue not available"
            )

        job = await job_queue.get_job(job_id)

        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        # Check ownership
        if job.metadata.get("user") != current_user.get("sub"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        return job

    @app.get(
        "/jobs/{job_id}/result",
        response_model=ProcessingResult,
        tags=["Jobs"],
        summary="Get job result",
    )
    async def get_job_result(
        job_id: str, current_user: Dict[str, Any] = Security(get_current_user)
    ):
        """Get the result of a completed job."""
        if not job_queue:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Job queue not available"
            )

        job = await job_queue.get_job(job_id)

        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        # Check ownership
        if job.metadata.get("user") != current_user.get("sub"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        if job.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Job not completed. Current status: {job.status}",
            )

        result = await job_queue.get_result(job_id)

        if not result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Result not found")

        return result

    @app.post("/jobs/{job_id}/cancel", tags=["Jobs"], summary="Cancel a pending job")
    async def cancel_job(job_id: str, current_user: Dict[str, Any] = Security(get_current_user)):
        """Cancel a pending job."""
        if not job_queue:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Job queue not available"
            )

        job = await job_queue.get_job(job_id)

        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        # Check ownership
        if job.metadata.get("user") != current_user.get("sub"):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access denied")

        success = await job_queue.cancel_job(job_id)

        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Job cannot be cancelled"
            )

        return {"message": "Job cancelled successfully"}

    # Configuration
    @app.get(
        "/config/databases",
        response_model=ConfigResponse,
        tags=["Configuration"],
        summary="Get database configuration",
    )
    async def get_config(current_user: Dict[str, Any] = Security(get_current_user)):
        """Get current configuration settings."""
        if not config_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Configuration not available",
            )

        config = config_manager.load()

        databases = []
        for db_type, db_config in config.notion.databases.items():
            databases.append(
                DatabaseInfo(
                    id=db_config.id,
                    name=db_config.name,
                    entity_type=db_type,
                    property_count=len(db_config.mappings),
                    is_configured=bool(db_config.id),
                )
            )

        return ConfigResponse(
            databases=databases,
            validation_level=getattr(
                config.processing, "validation_level", ValidationLevel.STANDARD
            ),
            deduplication_enabled=config.processing.enable_deduplication,
            deduplication_threshold=config.processing.deduplication_threshold,
            cache_enabled=bool(config.processing.cache_dir),
        )

    @app.put(
        "/config/validation",
        tags=["Configuration"],
        summary="Update validation settings",
        dependencies=[Depends(require_admin)],
    )
    async def update_validation(
        update: ValidationRuleUpdate, current_user: Dict[str, Any] = Security(get_current_user)
    ):
        """Update validation settings (admin only)."""
        if not config_manager:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Configuration not available",
            )

        # Update configuration
        config = config_manager.load()
        config.processing.validation_level = update.validation_level

        # Save would happen here in production
        # For now, just update in memory

        return {"message": "Validation settings updated"}

    # Include query engine endpoints
    app.include_router(query_router)

    return app


# Create default app instance
app = create_app()
