"""
Async wrapper for the Deduplication Engine

Provides non-blocking operations and progress callbacks for the CLI.
"""

import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import time

from ..core_engine import DeduplicationEngine, DeduplicationResult
from ..review_interface import HumanReviewInterface
from ..audit_system import ReviewTask

logger = logging.getLogger(__name__)


@dataclass
class ProgressUpdate:
    """Progress update information."""
    stage: str
    current: int
    total: int
    message: str = ""
    processing_rate: float = 0.0
    eta_seconds: Optional[float] = None


class AsyncDeduplicationEngine:
    """
    Async wrapper for the DeduplicationEngine.
    
    Provides non-blocking operations, progress tracking, and cancellation support.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None, max_workers: int = 4):
        """Initialize the async engine."""
        # DeduplicationEngine expects a config path, not a dict
        # So we'll initialize it without config and then update
        self.engine = DeduplicationEngine()
        
        # Update config if provided
        if config:
            self.engine.config.update(config)
            
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self._cancelled = False
        self._progress_callback: Optional[Callable] = None
        self._start_time: Optional[float] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.shutdown()
        
    async def shutdown(self):
        """Shutdown the executor."""
        self.executor.shutdown(wait=True)
        
    def cancel(self):
        """Cancel ongoing operations."""
        self._cancelled = True
        logger.info("Cancellation requested")
        
    def update_config(self, config: Dict[str, Any]):
        """Update the engine configuration."""
        if hasattr(self.engine, 'config'):
            self.engine.config.update(config)
        
    async def analyze_database_async(
        self, 
        database_name: str, 
        records: List[Dict[str, Any]],
        enable_ai: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> DeduplicationResult:
        """
        Analyze a database asynchronously with progress tracking.
        
        Args:
            database_name: Name of the database
            records: List of records to analyze
            enable_ai: Whether to enable AI analysis
            progress_callback: Async callback for progress updates
            
        Returns:
            DeduplicationResult with analysis findings
        """
        self._progress_callback = progress_callback
        self._cancelled = False
        self._start_time = time.time()
        
        # Report initial progress
        await self._report_progress("Loading", 0, len(records), "Initializing analysis...")
        
        # Run analysis in thread pool
        loop = asyncio.get_event_loop()
        
        try:
            # Create a wrapper that includes progress tracking
            result = await loop.run_in_executor(
                self.executor,
                self._analyze_with_progress,
                database_name,
                records,
                enable_ai
            )
            
            if self._cancelled:
                logger.info("Analysis cancelled by user")
                return DeduplicationResult(total_entities=len(records))
                
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            raise
            
    def _analyze_with_progress(
        self,
        database_name: str,
        records: List[Dict[str, Any]],
        enable_ai: bool
    ) -> DeduplicationResult:
        """
        Wrapper for engine analysis with progress tracking.
        
        This runs in a thread pool executor.
        """
        # For now, just run the analysis without progress tracking in the thread
        # Progress will be updated before and after
        result = self.engine.analyze_database(database_name, records, enable_ai)
        return result
            
    async def analyze_databases_async(
        self,
        databases: Dict[str, List[Dict[str, Any]]],
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, DeduplicationResult]:
        """
        Analyze multiple databases asynchronously.
        
        Args:
            databases: Dictionary of database names to records
            progress_callback: Async callback for progress updates
            
        Returns:
            Dictionary of database names to results
        """
        self._progress_callback = progress_callback
        self._cancelled = False
        
        results = {}
        total_records = sum(len(records) for records in databases.values())
        processed = 0
        
        for db_name, records in databases.items():
            if self._cancelled:
                break
                
            # Update progress for this database
            await self._report_progress(
                f"Analyzing {db_name}",
                processed,
                total_records,
                f"Processing {len(records)} records..."
            )
            
            # Analyze this database
            result = await self.analyze_database_async(
                db_name,
                records,
                enable_ai=self.engine.config.get("enable_ai_analysis", True)
            )
            
            results[db_name] = result
            processed += len(records)
            
        return results
        
    async def _report_progress(
        self,
        stage: str,
        current: int,
        total: int,
        message: str = ""
    ):
        """Report progress to callback if provided."""
        if not self._progress_callback:
            return
            
        # Calculate processing rate and ETA
        elapsed = time.time() - self._start_time if self._start_time else 0
        rate = current / elapsed if elapsed > 0 and current > 0 else 0
        remaining = total - current
        eta = remaining / rate if rate > 0 else None
        
        update = ProgressUpdate(
            stage=stage,
            current=current,
            total=total,
            message=message,
            processing_rate=rate,
            eta_seconds=eta
        )
        
        await self._progress_callback(update)
        
    async def get_review_tasks_async(
        self,
        results: DeduplicationResult,
        reviewer_id: str
    ) -> List[ReviewTask]:
        """
        Get review tasks asynchronously.
        
        Args:
            results: Deduplication results
            reviewer_id: ID of the reviewer
            
        Returns:
            List of review tasks
        """
        loop = asyncio.get_event_loop()
        
        # Get review interface
        review_interface = HumanReviewInterface(self.engine.audit_system)
        
        # Get tasks in executor
        tasks = await loop.run_in_executor(
            self.executor,
            self._get_review_tasks,
            review_interface,
            results,
            reviewer_id
        )
        
        return tasks
        
    def _get_review_tasks(
        self,
        review_interface: HumanReviewInterface,
        results: DeduplicationResult,
        reviewer_id: str
    ) -> List[ReviewTask]:
        """Get review tasks from results."""
        tasks = []
        
        # Create tasks from medium confidence matches
        for match in results.medium_confidence_matches:
            task = review_interface.create_review_task(
                match["entity_a"],
                match["entity_b"],
                match["entity_type"],
                match["confidence_score"],
                match.get("similarity_scores", {}),
                match.get("ai_analysis")
            )
            tasks.append(task)
            
        return tasks
        
    async def process_in_batches_async(
        self,
        database_name: str,
        all_records: List[Dict[str, Any]],
        batch_size: int = 100,
        progress_callback: Optional[Callable] = None
    ) -> DeduplicationResult:
        """
        Process large datasets in batches asynchronously.
        
        Args:
            database_name: Name of the database
            all_records: All records to process
            batch_size: Size of each batch
            progress_callback: Progress callback
            
        Returns:
            Combined deduplication result
        """
        self._progress_callback = progress_callback
        self._cancelled = False
        
        # Process in batches
        results = []
        
        for i in range(0, len(all_records), batch_size):
            if self._cancelled:
                break
                
            batch = all_records[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (len(all_records) + batch_size - 1) // batch_size
            
            await self._report_progress(
                f"Batch {batch_num}/{total_batches}",
                i,
                len(all_records),
                f"Processing batch of {len(batch)} records..."
            )
            
            result = await self.analyze_database_async(
                database_name,
                batch,
                enable_ai=self.engine.config.get("enable_ai_analysis", True)
            )
            
            results.append(result)
            
        # Combine results
        return self._combine_results(results)
        
    def _combine_results(self, results: List[DeduplicationResult]) -> DeduplicationResult:
        """Combine multiple deduplication results."""
        if not results:
            return DeduplicationResult(total_entities=0)
            
        combined = DeduplicationResult(
            total_entities=sum(r.total_entities for r in results)
        )
        
        # Combine matches
        for result in results:
            combined.high_confidence_matches.extend(result.high_confidence_matches)
            combined.medium_confidence_matches.extend(result.medium_confidence_matches)
            combined.low_confidence_matches.extend(result.low_confidence_matches)
            combined.potential_duplicates += result.potential_duplicates
            combined.auto_merged += result.auto_merged
            combined.flagged_for_review += result.flagged_for_review
            
        return combined
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return self.engine.get_statistics()
        
    def update_config(self, config: Dict[str, Any]):
        """Update engine configuration."""
        self.engine.config.update(config)