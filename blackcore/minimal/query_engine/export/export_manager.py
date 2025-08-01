"""Export job management for async exports."""

import asyncio
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from enum import Enum

from .streaming_exporter import StreamingExporter, ExportFormat


class ExportStatus(str, Enum):
    """Export job status."""
    
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ExportJob:
    """Export job tracking."""
    
    job_id: str
    format: ExportFormat
    output_path: str
    status: ExportStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    progress: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    @property
    def is_running(self) -> bool:
        """Check if job is currently running."""
        return self.status == ExportStatus.RUNNING
    
    @property
    def is_complete(self) -> bool:
        """Check if job has completed (success or failure)."""
        return self.status in [ExportStatus.COMPLETED, ExportStatus.FAILED, ExportStatus.CANCELLED]


class ExportManager:
    """Manage async export jobs."""
    
    def __init__(self, export_dir: str = "exports", max_concurrent_jobs: int = 5):
        """Initialize export manager."""
        self._export_dir = Path(export_dir)
        self._export_dir.mkdir(exist_ok=True)
        
        self._jobs: Dict[str, ExportJob] = {}
        self._active_tasks: Dict[str, asyncio.Task] = {}
        self._max_concurrent_jobs = max_concurrent_jobs
        self._job_semaphore = asyncio.Semaphore(max_concurrent_jobs)
        
        # Export templates
        self._templates: Dict[str, Dict[str, Any]] = {}
    
    async def create_export_job(
        self,
        data_iterator: AsyncIterator[Dict[str, Any]],
        format: ExportFormat,
        filename: Optional[str] = None,
        template_name: Optional[str] = None,
        **export_options
    ) -> str:
        """Create and queue export job."""
        # Generate job ID
        job_id = str(uuid.uuid4())
        
        # Determine filename
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"export_{timestamp}.{format.value}"
        
        output_path = self._export_dir / filename
        
        # Apply template if specified
        if template_name and template_name in self._templates:
            template_options = self._templates[template_name].copy()
            template_options.update(export_options)
            export_options = template_options
        
        # Create job
        job = ExportJob(
            job_id=job_id,
            format=format,
            output_path=str(output_path),
            status=ExportStatus.PENDING,
            created_at=datetime.now(),
            metadata={
                'filename': filename,
                'template': template_name,
                'options': export_options
            }
        )
        
        self._jobs[job_id] = job
        
        # Start export task
        task = asyncio.create_task(
            self._run_export_job(job_id, data_iterator, export_options)
        )
        self._active_tasks[job_id] = task
        
        return job_id
    
    async def _run_export_job(
        self,
        job_id: str,
        data_iterator: AsyncIterator[Dict[str, Any]],
        export_options: Dict[str, Any]
    ):
        """Run export job with progress tracking."""
        job = self._jobs[job_id]
        
        async with self._job_semaphore:
            try:
                # Update job status
                job.status = ExportStatus.RUNNING
                job.started_at = datetime.now()
                
                # Create progress-tracking iterator
                progress_iterator = self._track_progress(job_id, data_iterator)
                
                # Create exporter
                exporter = StreamingExporter()
                
                # Run export
                result = await exporter.export(
                    progress_iterator,
                    job.output_path,
                    job.format,
                    **export_options
                )
                
                # Update job with results
                job.status = ExportStatus.COMPLETED
                job.completed_at = datetime.now()
                job.progress.update(result)
                
            except asyncio.CancelledError:
                job.status = ExportStatus.CANCELLED
                job.completed_at = datetime.now()
                raise
                
            except Exception as e:
                job.status = ExportStatus.FAILED
                job.completed_at = datetime.now()
                job.error_message = str(e)
                
            finally:
                # Clean up task reference
                self._active_tasks.pop(job_id, None)
    
    async def _track_progress(
        self,
        job_id: str,
        data_iterator: AsyncIterator[Dict[str, Any]]
    ) -> AsyncIterator[Dict[str, Any]]:
        """Wrap iterator to track progress."""
        job = self._jobs[job_id]
        rows_processed = 0
        
        async for row in data_iterator:
            rows_processed += 1
            job.progress['rows_processed'] = rows_processed
            
            # Update progress periodically
            if rows_processed % 1000 == 0:
                job.progress['last_update'] = datetime.now().isoformat()
            
            yield row
    
    def get_job_status(self, job_id: str) -> Optional[ExportJob]:
        """Get job status."""
        return self._jobs.get(job_id)
    
    def list_jobs(
        self,
        status: Optional[ExportStatus] = None,
        limit: int = 100
    ) -> List[ExportJob]:
        """List export jobs."""
        jobs = list(self._jobs.values())
        
        # Filter by status if specified
        if status:
            jobs = [j for j in jobs if j.status == status]
        
        # Sort by created time (newest first)
        jobs.sort(key=lambda j: j.created_at, reverse=True)
        
        return jobs[:limit]
    
    async def cancel_job(self, job_id: str) -> bool:
        """Cancel running export job."""
        if job_id not in self._jobs:
            return False
        
        job = self._jobs[job_id]
        
        if job.status != ExportStatus.RUNNING:
            return False
        
        # Cancel task
        task = self._active_tasks.get(job_id)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        return True
    
    def add_template(
        self,
        name: str,
        format: ExportFormat,
        options: Dict[str, Any]
    ):
        """Add export template."""
        self._templates[name] = {
            'format': format,
            'options': options
        }
    
    def get_template(self, name: str) -> Optional[Dict[str, Any]]:
        """Get export template."""
        return self._templates.get(name)
    
    def list_templates(self) -> Dict[str, Dict[str, Any]]:
        """List all templates."""
        return self._templates.copy()
    
    async def cleanup_old_exports(self, days: int = 7):
        """Clean up old export files."""
        import time
        
        cutoff_time = time.time() - (days * 24 * 60 * 60)
        
        for file_path in self._export_dir.iterdir():
            if file_path.is_file():
                if file_path.stat().st_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                    except Exception:
                        pass
    
    def get_export_directory(self) -> Path:
        """Get export directory path."""
        return self._export_dir
    
    def estimate_export_time(
        self,
        row_count: int,
        format: ExportFormat,
        avg_row_size: int = 1000
    ) -> float:
        """Estimate export time in seconds."""
        # Based on empirical measurements
        rows_per_second = {
            ExportFormat.CSV: 100000,
            ExportFormat.JSON: 50000,
            ExportFormat.JSONL: 80000,
            ExportFormat.EXCEL: 10000,
            ExportFormat.PARQUET: 40000,
            ExportFormat.TSV: 100000
        }
        
        rate = rows_per_second.get(format, 50000)
        estimated_seconds = row_count / rate
        
        # Add overhead for large exports
        if row_count > 1000000:
            estimated_seconds *= 1.2
        
        return estimated_seconds