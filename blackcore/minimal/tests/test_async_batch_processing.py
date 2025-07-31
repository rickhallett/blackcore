"""Test async batch processing implementation."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from blackcore.minimal.async_batch_processor import (
    AsyncBatchProcessor,
    BatchResult,
    ProcessingError,
    batch_create_pages,
    batch_update_pages,
)


class TestAsyncBatchProcessing:
    """Test suite for async batch processing."""
    
    @pytest.mark.asyncio
    async def test_async_batch_processor_basic(self):
        """Test basic async batch processing."""
        # Define a simple async processor
        async def process_item(item: int) -> int:
            await asyncio.sleep(0.01)  # Simulate async work
            return item * 2
        
        # Create processor
        processor = AsyncBatchProcessor(
            process_func=process_item,
            batch_size=3,
            max_concurrent=2
        )
        
        # Process items
        items = list(range(10))
        results = await processor.process_all(items)
        
        # Check results
        assert len(results) == 10
        assert all(isinstance(r, BatchResult) for r in results)
        
        # Check successful results
        successful = [r for r in results if r.success]
        assert len(successful) == 10
        assert [r.result for r in successful] == [i * 2 for i in range(10)]
    
    @pytest.mark.asyncio
    async def test_async_batch_processor_with_errors(self):
        """Test batch processing with some errors."""
        # Define processor that fails on even numbers
        async def process_item(item: int) -> int:
            await asyncio.sleep(0.01)
            if item % 2 == 0:
                raise ValueError(f"Cannot process even number: {item}")
            return item * 2
        
        # Create processor
        processor = AsyncBatchProcessor(
            process_func=process_item,
            batch_size=2,
            max_concurrent=2
        )
        
        # Process items
        items = list(range(6))
        results = await processor.process_all(items)
        
        # Check results
        assert len(results) == 6
        
        # Check successful results (odd numbers)
        successful = [r for r in results if r.success]
        assert len(successful) == 3
        assert [r.item for r in successful] == [1, 3, 5]
        assert [r.result for r in successful] == [2, 6, 10]
        
        # Check failed results (even numbers)
        failed = [r for r in results if not r.success]
        assert len(failed) == 3
        assert [r.item for r in failed] == [0, 2, 4]
        assert all(isinstance(r.error, ProcessingError) for r in failed)
        assert all("Cannot process even number" in str(r.error) for r in failed)
    
    @pytest.mark.asyncio
    async def test_async_batch_processor_respects_batch_size(self):
        """Test that batch size is respected."""
        call_batches = []
        
        async def process_item(item: int) -> int:
            # Track which batch this item is in
            await asyncio.sleep(0.01)
            current_batch = len(call_batches)
            if not call_batches or len(call_batches[-1]) >= 3:
                call_batches.append([])
            call_batches[-1].append(item)
            return item
        
        # Create processor with batch size 3
        processor = AsyncBatchProcessor(
            process_func=process_item,
            batch_size=3,
            max_concurrent=1  # Process one batch at a time
        )
        
        # Process 10 items
        items = list(range(10))
        await processor.process_all(items)
        
        # Should have 4 batches: [0,1,2], [3,4,5], [6,7,8], [9]
        assert len(call_batches) == 4
        assert call_batches[0] == [0, 1, 2]
        assert call_batches[1] == [3, 4, 5]
        assert call_batches[2] == [6, 7, 8]
        assert call_batches[3] == [9]
    
    @pytest.mark.asyncio
    async def test_async_batch_processor_max_concurrent(self):
        """Test max concurrent batches limit."""
        active_count = 0
        max_active = 0
        
        async def process_item(item: int) -> int:
            nonlocal active_count, max_active
            active_count += 1
            max_active = max(max_active, active_count)
            await asyncio.sleep(0.05)  # Longer delay to ensure overlap
            active_count -= 1
            return item
        
        # Create processor with max_concurrent=2
        processor = AsyncBatchProcessor(
            process_func=process_item,
            batch_size=2,
            max_concurrent=2
        )
        
        # Process 8 items (4 batches)
        items = list(range(8))
        await processor.process_all(items)
        
        # Should never have more than 4 items active (2 batches * 2 items)
        assert max_active <= 4
    
    @pytest.mark.asyncio
    async def test_batch_create_pages(self):
        """Test batch page creation."""
        # Mock NotionUpdater
        mock_updater = MagicMock()
        mock_updater.create_page.return_value = MagicMock(
            id="page-id",
            properties={}
        )
        
        # Create pages
        pages_data = [
            {"database_id": "db1", "properties": {"Title": f"Page {i}"}}
            for i in range(5)
        ]
        
        results = await batch_create_pages(
            updater=mock_updater,
            pages_data=pages_data,
            batch_size=2,
            max_concurrent=2
        )
        
        # Check results
        assert len(results) == 5
        assert all(r.success for r in results)
        assert mock_updater.create_page.call_count == 5
    
    @pytest.mark.asyncio
    async def test_batch_update_pages(self):
        """Test batch page updates."""
        # Mock NotionUpdater
        mock_updater = MagicMock()
        mock_updater.update_page.return_value = MagicMock(
            id="page-id",
            properties={}
        )
        
        # Update pages
        updates_data = [
            {"page_id": f"page-{i}", "properties": {"Status": "Updated"}}
            for i in range(5)
        ]
        
        results = await batch_update_pages(
            updater=mock_updater,
            updates_data=updates_data,
            batch_size=2,
            max_concurrent=2
        )
        
        # Check results
        assert len(results) == 5
        assert all(r.success for r in results)
        assert mock_updater.update_page.call_count == 5
    
    @pytest.mark.asyncio
    async def test_batch_processing_with_retry(self):
        """Test batch processing with retry logic."""
        attempt_count = {}
        
        async def process_item(item: int) -> int:
            # Track attempts
            attempt_count[item] = attempt_count.get(item, 0) + 1
            
            # Fail first attempt for even numbers
            if item % 2 == 0 and attempt_count[item] == 1:
                raise ValueError("Temporary failure")
            
            return item * 2
        
        # Create processor with retry
        processor = AsyncBatchProcessor(
            process_func=process_item,
            batch_size=2,
            max_concurrent=2,
            retry_count=2,
            retry_delay=0.01
        )
        
        # Process items
        items = list(range(6))
        results = await processor.process_all(items)
        
        # All should succeed after retry
        assert all(r.success for r in results)
        assert [r.result for r in results] == [i * 2 for i in range(6)]
        
        # Even numbers should have been tried twice
        for i in range(0, 6, 2):
            assert attempt_count[i] == 2
        # Odd numbers should have been tried once
        for i in range(1, 6, 2):
            assert attempt_count[i] == 1
    
    @pytest.mark.asyncio
    async def test_batch_processing_progress_callback(self):
        """Test progress callback during batch processing."""
        progress_updates = []
        
        async def progress_callback(completed: int, total: int):
            progress_updates.append((completed, total))
        
        async def process_item(item: int) -> int:
            await asyncio.sleep(0.01)
            return item
        
        # Create processor with progress callback
        processor = AsyncBatchProcessor(
            process_func=process_item,
            batch_size=2,
            max_concurrent=2,
            progress_callback=progress_callback
        )
        
        # Process items
        items = list(range(6))
        await processor.process_all(items)
        
        # Should have progress updates
        assert len(progress_updates) > 0
        assert progress_updates[-1] == (6, 6)  # Final update
        
        # Progress should be monotonic
        for i in range(1, len(progress_updates)):
            assert progress_updates[i][0] >= progress_updates[i-1][0]
    
    @pytest.mark.asyncio
    async def test_batch_processing_cancellation(self):
        """Test that batch processing can be cancelled."""
        processed_items = []
        
        async def process_item(item: int) -> int:
            await asyncio.sleep(0.1)  # Slow processing
            processed_items.append(item)
            return item
        
        # Create processor
        processor = AsyncBatchProcessor(
            process_func=process_item,
            batch_size=2,
            max_concurrent=2
        )
        
        # Start processing and cancel after a short time
        items = list(range(20))
        task = asyncio.create_task(processor.process_all(items))
        
        await asyncio.sleep(0.15)  # Let some items process
        task.cancel()
        
        try:
            await task
        except asyncio.CancelledError:
            pass
        
        # Should have processed some but not all items
        assert len(processed_items) > 0
        assert len(processed_items) < 20