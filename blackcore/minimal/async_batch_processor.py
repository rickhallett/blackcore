"""Async batch processing for Notion operations."""

import asyncio
from dataclasses import dataclass
from typing import Any, Callable, List, Optional, TypeVar, Generic, Dict
from enum import Enum

from .logging_config import get_logger, log_event, log_error, Timer

logger = get_logger(__name__)


class ProcessingError(Exception):
    """Error during batch processing."""
    pass


class BatchStatus(Enum):
    """Status of a batch processing operation."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


T = TypeVar('T')
R = TypeVar('R')


@dataclass
class BatchResult(Generic[T, R]):
    """Result of processing a single item in a batch."""
    item: T
    result: Optional[R] = None
    error: Optional[ProcessingError] = None
    success: bool = True
    retry_count: int = 0


class AsyncBatchProcessor(Generic[T, R]):
    """Process items in batches with async concurrency control."""
    
    def __init__(
        self,
        process_func: Callable[[T], R],
        batch_size: int = 10,
        max_concurrent: int = 3,
        retry_count: int = 0,
        retry_delay: float = 1.0,
        progress_callback: Optional[Callable[[int, int], None]] = None
    ):
        """Initialize batch processor.
        
        Args:
            process_func: Async function to process each item
            batch_size: Number of items per batch
            max_concurrent: Maximum concurrent batches
            retry_count: Number of retries for failed items
            retry_delay: Delay between retries in seconds
            progress_callback: Optional callback for progress updates
        """
        self.process_func = process_func
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.retry_count = retry_count
        self.retry_delay = retry_delay
        self.progress_callback = progress_callback
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._completed_count = 0
        self._total_count = 0
        self._lock = asyncio.Lock()
    
    async def process_all(self, items: List[T]) -> List[BatchResult[T, R]]:
        """Process all items in batches.
        
        Args:
            items: List of items to process
            
        Returns:
            List of BatchResult objects
        """
        self._completed_count = 0
        self._total_count = len(items)
        
        # Split items into batches
        batches = [
            items[i:i + self.batch_size]
            for i in range(0, len(items), self.batch_size)
        ]
        
        log_event(
            __name__,
            "batch_processing_started",
            total_items=len(items),
            batch_count=len(batches),
            batch_size=self.batch_size,
            max_concurrent=self.max_concurrent
        )
        
        # Process batches concurrently
        with Timer() as timer:
            batch_tasks = [
                self._process_batch(batch)
                for batch in batches
            ]
            
            # Gather all results
            batch_results = await asyncio.gather(*batch_tasks)
            
            # Flatten results
            all_results = []
            for batch_result in batch_results:
                all_results.extend(batch_result)
        
        log_event(
            __name__,
            "batch_processing_completed",
            total_items=len(items),
            successful_items=sum(1 for r in all_results if r.success),
            failed_items=sum(1 for r in all_results if not r.success),
            duration_ms=timer.duration_ms
        )
        
        return all_results
    
    async def _process_batch(self, batch: List[T]) -> List[BatchResult[T, R]]:
        """Process a single batch of items.
        
        Args:
            batch: List of items in this batch
            
        Returns:
            List of BatchResult objects for this batch
        """
        async with self._semaphore:
            # Process items in batch concurrently
            tasks = [
                self._process_item_with_retry(item)
                for item in batch
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Convert results to BatchResult objects
            batch_results = []
            for item, result in zip(batch, results):
                if isinstance(result, Exception):
                    batch_results.append(
                        BatchResult(
                            item=item,
                            error=ProcessingError(str(result)),
                            success=False
                        )
                    )
                else:
                    batch_results.append(result)
            
            # Update progress
            async with self._lock:
                self._completed_count += len(batch)
                if self.progress_callback:
                    await self._call_progress_callback(
                        self._completed_count,
                        self._total_count
                    )
            
            return batch_results
    
    async def _process_item_with_retry(self, item: T) -> BatchResult[T, R]:
        """Process a single item with retry logic.
        
        Args:
            item: Item to process
            
        Returns:
            BatchResult object
        """
        last_error = None
        
        for attempt in range(self.retry_count + 1):
            try:
                result = await self.process_func(item)
                return BatchResult(
                    item=item,
                    result=result,
                    success=True,
                    retry_count=attempt
                )
            except Exception as e:
                last_error = e
                
                if attempt < self.retry_count:
                    log_event(
                        __name__,
                        "item_retry",
                        attempt=attempt + 1,
                        max_attempts=self.retry_count + 1,
                        error=str(e)
                    )
                    await asyncio.sleep(self.retry_delay)
        
        # All retries failed
        return BatchResult(
            item=item,
            error=ProcessingError(str(last_error)),
            success=False,
            retry_count=self.retry_count
        )
    
    async def _call_progress_callback(self, completed: int, total: int):
        """Call progress callback if it's async or sync.
        
        Args:
            completed: Number of completed items
            total: Total number of items
        """
        if asyncio.iscoroutinefunction(self.progress_callback):
            await self.progress_callback(completed, total)
        else:
            self.progress_callback(completed, total)


async def batch_create_pages(
    updater: Any,
    pages_data: List[Dict[str, Any]],
    batch_size: int = 10,
    max_concurrent: int = 3,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[BatchResult]:
    """Batch create multiple pages in Notion.
    
    Args:
        updater: NotionUpdater instance
        pages_data: List of page data dicts with 'database_id' and 'properties'
        batch_size: Number of pages per batch
        max_concurrent: Maximum concurrent batches
        progress_callback: Optional progress callback
        
    Returns:
        List of BatchResult objects
    """
    async def create_page_async(page_data: Dict[str, Any]) -> Any:
        """Create a single page asynchronously."""
        # NotionUpdater is sync, so run in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            updater.create_page,
            page_data["database_id"],
            page_data["properties"]
        )
    
    processor = AsyncBatchProcessor(
        process_func=create_page_async,
        batch_size=batch_size,
        max_concurrent=max_concurrent,
        progress_callback=progress_callback
    )
    
    return await processor.process_all(pages_data)


async def batch_update_pages(
    updater: Any,
    updates_data: List[Dict[str, Any]],
    batch_size: int = 10,
    max_concurrent: int = 3,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> List[BatchResult]:
    """Batch update multiple pages in Notion.
    
    Args:
        updater: NotionUpdater instance
        updates_data: List of update data dicts with 'page_id' and 'properties'
        batch_size: Number of pages per batch
        max_concurrent: Maximum concurrent batches
        progress_callback: Optional progress callback
        
    Returns:
        List of BatchResult objects
    """
    async def update_page_async(update_data: Dict[str, Any]) -> Any:
        """Update a single page asynchronously."""
        # NotionUpdater is sync, so run in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            updater.update_page,
            update_data["page_id"],
            update_data["properties"]
        )
    
    processor = AsyncBatchProcessor(
        process_func=update_page_async,
        batch_size=batch_size,
        max_concurrent=max_concurrent,
        progress_callback=progress_callback
    )
    
    return await processor.process_all(updates_data)