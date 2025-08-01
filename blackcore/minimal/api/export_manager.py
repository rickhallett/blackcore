"""Export job management for HTTP API."""

import asyncio
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, field
import tempfile
import structlog

from .query_models import ExportRequest, ExportJob
from ..query_engine.models import StructuredQuery
from ..query_engine.export import StreamingExporter, ExportFormat


logger = structlog.get_logger()


@dataclass
class ExportJobState:
    """Internal state for export jobs."""
    
    job_id: str
    status: str  # pending, running, completed, failed
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    query: Optional[StructuredQuery] = None
    format: str = "csv"
    file_path: Optional[Path] = None
    error_message: Optional[str] = None
    progress: int = 0
    rows_exported: int = 0
    file_size_bytes: int = 0
    user_id: str = ""
    expires_at: Optional[datetime] = None


class ExportJobManager:
    """Manages export jobs and background processing."""
    
    def __init__(self, temp_dir: str = "/tmp/blackcore_exports", retention_hours: int = 24):
        """Initialize export job manager."""
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        self.retention_hours = retention_hours
        self.jobs: Dict[str, ExportJobState] = {}
        self.exporter = StreamingExporter()
        self._cleanup_task = None
        
    async def start(self):
        """Start background tasks."""
        # Start cleanup task
        self._cleanup_task = asyncio.create_task(self._cleanup_expired_jobs())
        
    async def stop(self):
        """Stop background tasks."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
    
    def create_export_job(
        self, 
        request: ExportRequest, 
        user_id: str,
        query_engine
    ) -> ExportJob:
        """Create a new export job."""
        job_id = f"exp_{uuid.uuid4().hex[:12]}"
        
        # Create job state
        job_state = ExportJobState(
            job_id=job_id,
            status="pending",
            created_at=datetime.now(),
            format=request.format.value,
            user_id=user_id,
            expires_at=datetime.now() + timedelta(hours=self.retention_hours)
        )
        
        self.jobs[job_id] = job_state
        
        # Schedule background processing
        asyncio.create_task(self._process_export_job(job_id, request, query_engine))
        
        # Return job info
        return self._job_state_to_api_model(job_state)
    
    def get_job_status(self, job_id: str, user_id: str) -> Optional[ExportJob]:
        """Get export job status."""
        job_state = self.jobs.get(job_id)
        if not job_state or job_state.user_id != user_id:
            return None
        
        return self._job_state_to_api_model(job_state)
    
    async def get_file_stream(self, job_id: str, user_id: str):
        """Get file stream for completed export."""
        job_state = self.jobs.get(job_id)
        if not job_state or job_state.user_id != user_id:
            return None
        
        if job_state.status != "completed" or not job_state.file_path:
            return None
        
        if not job_state.file_path.exists():
            logger.warning(f"Export file not found: {job_state.file_path}")
            return None
        
        # Return async file generator
        async def file_generator():
            with open(job_state.file_path, 'rb') as f:
                while chunk := f.read(8192):  # 8KB chunks
                    yield chunk
        
        return file_generator(), job_state.file_size_bytes
    
    async def _process_export_job(self, job_id: str, request: ExportRequest, query_engine):
        """Process export job in background."""
        job_state = self.jobs[job_id]
        
        try:
            job_state.status = "running"
            job_state.started_at = datetime.now()
            
            logger.info(f"Starting export job {job_id}")
            
            # Convert HTTP request to internal query
            from .query_service import QueryService
            service = QueryService()
            internal_query = service._build_internal_query(request.query)
            
            # Execute query
            result = await query_engine.execute_structured_query_async(internal_query)
            
            # Generate file path
            file_extension = request.format.value
            file_path = self.temp_dir / f"{job_id}.{file_extension}"
            job_state.file_path = file_path
            
            # Export data
            export_result = self.exporter.export_data(
                result.data,
                file_path,
                ExportFormat(request.format.value),
                request.options
            )
            
            # Update job state
            job_state.status = "completed"
            job_state.completed_at = datetime.now()
            job_state.rows_exported = export_result.get('rows_exported', len(result.data))
            job_state.file_size_bytes = export_result.get('file_size_bytes', file_path.stat().st_size)
            job_state.progress = 100
            
            logger.info(f"Export job {job_id} completed: {job_state.rows_exported} rows")
            
        except Exception as e:
            logger.error(f"Export job {job_id} failed: {e}")
            job_state.status = "failed"
            job_state.error_message = str(e)
            job_state.completed_at = datetime.now()
    
    def _job_state_to_api_model(self, job_state: ExportJobState) -> ExportJob:
        """Convert internal job state to API model."""
        return ExportJob(
            job_id=job_state.job_id,
            status=job_state.status,
            created_at=job_state.created_at,
            started_at=job_state.started_at,
            completed_at=job_state.completed_at,
            format=ExportFormat(job_state.format),
            rows_exported=job_state.rows_exported,
            file_size_bytes=job_state.file_size_bytes,
            error_message=job_state.error_message,
            download_url=f"/api/v1/query/export/{job_state.job_id}/download" if job_state.status == "completed" else None,
            expires_at=job_state.expires_at,
            progress=job_state.progress
        )
    
    async def _cleanup_expired_jobs(self):
        """Background task to clean up expired jobs."""
        while True:
            try:
                now = datetime.now()
                expired_jobs = []
                
                for job_id, job_state in self.jobs.items():
                    if job_state.expires_at and now > job_state.expires_at:
                        expired_jobs.append(job_id)
                
                for job_id in expired_jobs:
                    job_state = self.jobs[job_id]
                    
                    # Delete file if exists
                    if job_state.file_path and job_state.file_path.exists():
                        try:
                            job_state.file_path.unlink()
                        except Exception as e:
                            logger.warning(f"Failed to delete export file {job_state.file_path}: {e}")
                    
                    # Remove from jobs dict
                    del self.jobs[job_id]
                    logger.info(f"Cleaned up expired export job {job_id}")
                
                # Sleep for 1 hour before next cleanup
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Error in export cleanup task: {e}")
                await asyncio.sleep(60)  # Retry after 1 minute on error