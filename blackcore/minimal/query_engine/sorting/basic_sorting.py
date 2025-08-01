"""High-performance sorting and pagination engine with optimized algorithms."""

from typing import Any, Dict, List, Optional, Tuple, Callable
from datetime import datetime
from functools import cmp_to_key
import logging

from ..interfaces import SortingEngine
from ..models import SortField, SortOrder, QueryError

logger = logging.getLogger(__name__)


class BasicSortingEngine:
    """Memory-efficient sorting engine with multi-field support and cursor pagination.
    
    Performance characteristics:
    - O(n log n) worst case sorting
    - O(n) for pre-sorted data detection
    - Optimized for common sort patterns
    - Memory-efficient cursor-based pagination
    """
    
    def __init__(self):
        """Initialize sorting engine with caches."""
        self._comparator_cache = {}
        self._sort_key_cache = {}
    
    def apply_sorting(self, data: List[Dict[str, Any]], sort_fields: List[SortField]) -> List[Dict[str, Any]]:
        """Apply sorting to data with optimized algorithms.
        
        Performance:
        - O(n) check for pre-sorted data
        - O(n log n) for general sorting
        - Stable sort preserving original order for equal elements
        
        Args:
            data: List of records to sort
            sort_fields: List of fields to sort by with order
            
        Returns:
            Sorted list of records
        """
        if not data or not sort_fields:
            return data
        
        # Check if data is already sorted (common case optimization)
        if self._is_already_sorted(data, sort_fields):
            logger.debug("Data already sorted, skipping sort operation")
            return data
        
        # For single field sorting, use optimized key function
        if len(sort_fields) == 1:
            return self._single_field_sort(data, sort_fields[0])
        
        # For multi-field sorting, use custom comparator
        return self._multi_field_sort(data, sort_fields)
    
    def apply_pagination(self, data: List[Dict[str, Any]], page: int, size: int) -> Tuple[List[Dict[str, Any]], int]:
        """Apply pagination with total count.
        
        Performance: O(1) for slicing, O(1) for count
        
        Args:
            data: Sorted data to paginate
            page: Page number (1-based)
            size: Items per page
            
        Returns:
            Tuple of (paginated data, total count)
        """
        total_count = len(data)
        
        if page < 1:
            page = 1
        
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        
        # Efficient slicing
        paginated = data[start_idx:end_idx]
        
        return paginated, total_count
    
    def apply_cursor_pagination(
        self, 
        data: List[Dict[str, Any]], 
        cursor: Optional[str], 
        size: int,
        sort_fields: List[SortField]
    ) -> Tuple[List[Dict[str, Any]], Optional[str], Optional[str]]:
        """Apply cursor-based pagination for large datasets.
        
        More efficient than offset pagination for large datasets.
        
        Args:
            data: Sorted data to paginate
            cursor: Cursor from previous request
            size: Items per page
            sort_fields: Sort fields for cursor generation
            
        Returns:
            Tuple of (paginated data, next cursor, previous cursor)
        """
        if not data:
            return [], None, None
        
        start_idx = 0
        if cursor:
            start_idx = self._decode_cursor(cursor, data, sort_fields)
        
        end_idx = min(start_idx + size, len(data))
        paginated = data[start_idx:end_idx]
        
        # Generate cursors
        next_cursor = None
        if end_idx < len(data):
            next_cursor = self._encode_cursor(data[end_idx], sort_fields)
        
        prev_cursor = None
        if start_idx > 0:
            prev_cursor = self._encode_cursor(data[max(0, start_idx - size)], sort_fields)
        
        return paginated, next_cursor, prev_cursor
    
    def _is_already_sorted(self, data: List[Dict[str, Any]], sort_fields: List[SortField]) -> bool:
        """Check if data is already sorted to avoid unnecessary work.
        
        Performance: O(n) single pass
        """
        if len(data) <= 1:
            return True
        
        # Build comparator for checking
        comparator = self._build_multi_field_comparator(sort_fields)
        
        # Check if consecutive elements are in order
        for i in range(1, len(data)):
            if comparator(data[i-1], data[i]) > 0:
                return False
        
        return True
    
    def _single_field_sort(self, data: List[Dict[str, Any]], sort_field: SortField) -> List[Dict[str, Any]]:
        """Optimized single-field sorting.
        
        Performance: O(n log n) using Timsort
        """
        field = sort_field.field
        reverse = sort_field.order == SortOrder.DESC
        
        # Build key function
        def sort_key(item):
            value = self._get_field_value(item, field)
            
            # Handle None values (sort last)
            if value is None:
                return (1, None) if not reverse else (-1, None)
            
            # Handle different types
            if isinstance(value, str):
                # Case-insensitive string sorting
                return (0, value.lower())
            elif isinstance(value, (int, float)):
                return (0, value)
            elif isinstance(value, bool):
                return (0, int(value))
            elif isinstance(value, datetime):
                return (0, value)
            else:
                # Convert to string for other types
                return (0, str(value))
        
        return sorted(data, key=sort_key, reverse=reverse)
    
    def _multi_field_sort(self, data: List[Dict[str, Any]], sort_fields: List[SortField]) -> List[Dict[str, Any]]:
        """Multi-field sorting with custom comparator.
        
        Performance: O(n log n) stable sort
        """
        comparator = self._build_multi_field_comparator(sort_fields)
        return sorted(data, key=cmp_to_key(comparator))
    
    def _build_multi_field_comparator(self, sort_fields: List[SortField]) -> Callable:
        """Build a comparator function for multi-field sorting.
        
        Cached for performance.
        """
        # Cache key based on fields and orders
        cache_key = tuple((f.field, f.order) for f in sort_fields)
        
        if cache_key in self._comparator_cache:
            return self._comparator_cache[cache_key]
        
        def comparator(item1: Dict[str, Any], item2: Dict[str, Any]) -> int:
            """Compare two items based on multiple fields."""
            for sort_field in sort_fields:
                field = sort_field.field
                reverse = sort_field.order == SortOrder.DESC
                
                val1 = self._get_field_value(item1, field)
                val2 = self._get_field_value(item2, field)
                
                # Handle None values
                if val1 is None and val2 is None:
                    continue
                elif val1 is None:
                    return 1 if not reverse else -1
                elif val2 is None:
                    return -1 if not reverse else 1
                
                # Compare values
                result = self._compare_values(val1, val2)
                
                if result != 0:
                    return -result if reverse else result
            
            return 0
        
        self._comparator_cache[cache_key] = comparator
        return comparator
    
    def _compare_values(self, val1: Any, val2: Any) -> int:
        """Compare two values of potentially different types.
        
        Returns:
            -1 if val1 < val2
            0 if val1 == val2
            1 if val1 > val2
        """
        # Same type comparison
        if type(val1) == type(val2):
            if isinstance(val1, str):
                # Case-insensitive string comparison
                val1, val2 = val1.lower(), val2.lower()
            
            if val1 < val2:
                return -1
            elif val1 > val2:
                return 1
            else:
                return 0
        
        # Different types - convert to string
        str1, str2 = str(val1), str(val2)
        if str1 < str2:
            return -1
        elif str1 > str2:
            return 1
        else:
            return 0
    
    def _get_field_value(self, record: Dict[str, Any], field: str) -> Any:
        """Get field value with support for nested access.
        
        Supports dot notation: "metadata.priority"
        """
        parts = field.split('.')
        value = record
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        
        return value
    
    def _encode_cursor(self, record: Dict[str, Any], sort_fields: List[SortField]) -> str:
        """Encode cursor from record and sort fields.
        
        Creates a cursor that can be used to resume pagination.
        """
        import base64
        import json
        
        cursor_data = {}
        for sort_field in sort_fields:
            value = self._get_field_value(record, sort_field.field)
            # Convert datetime to ISO format for JSON serialization
            if isinstance(value, datetime):
                value = value.isoformat()
            cursor_data[sort_field.field] = value
        
        cursor_json = json.dumps(cursor_data, sort_keys=True)
        return base64.urlsafe_b64encode(cursor_json.encode()).decode()
    
    def _decode_cursor(self, cursor: str, data: List[Dict[str, Any]], sort_fields: List[SortField]) -> int:
        """Decode cursor and find position in data.
        
        Returns the index where pagination should start.
        """
        import base64
        import json
        
        try:
            cursor_json = base64.urlsafe_b64decode(cursor.encode()).decode()
            cursor_data = json.loads(cursor_json)
        except Exception:
            raise QueryError(f"Invalid cursor: {cursor}")
        
        # Binary search to find position
        comparator = self._build_cursor_comparator(cursor_data, sort_fields)
        
        left, right = 0, len(data) - 1
        result_idx = len(data)
        
        while left <= right:
            mid = (left + right) // 2
            if comparator(data[mid]) >= 0:
                result_idx = mid
                right = mid - 1
            else:
                left = mid + 1
        
        return result_idx
    
    def _build_cursor_comparator(self, cursor_data: Dict[str, Any], sort_fields: List[SortField]) -> Callable:
        """Build comparator for cursor positioning."""
        def comparator(record: Dict[str, Any]) -> int:
            """Compare record against cursor position."""
            for sort_field in sort_fields:
                field = sort_field.field
                reverse = sort_field.order == SortOrder.DESC
                
                record_val = self._get_field_value(record, field)
                cursor_val = cursor_data.get(field)
                
                # Convert ISO datetime strings back to datetime
                if isinstance(cursor_val, str) and 'T' in cursor_val:
                    try:
                        cursor_val = datetime.fromisoformat(cursor_val)
                    except:
                        pass
                
                result = self._compare_values(record_val, cursor_val)
                
                if result != 0:
                    return -result if reverse else result
            
            return 0
        
        return comparator
    
    def get_top_k(self, data: List[Dict[str, Any]], k: int, sort_fields: List[SortField]) -> List[Dict[str, Any]]:
        """Get top K elements efficiently without full sort.
        
        Performance: O(n log k) using heap
        """
        import heapq
        
        if k >= len(data):
            # Need all elements, do full sort
            return self.apply_sorting(data, sort_fields)
        
        # Build comparator
        comparator = self._build_multi_field_comparator(sort_fields)
        
        # Use heap for efficient top-k
        # For ascending order, use max heap (negate comparison)
        # For descending order, use min heap
        heap = []
        
        for item in data:
            if len(heap) < k:
                heapq.heappush(heap, (item, item))
            else:
                # Compare with smallest/largest in heap
                if comparator(item, heap[0][1]) < 0:
                    heapq.heapreplace(heap, (item, item))
        
        # Extract items and sort them
        result = [item[1] for item in heap]
        return sorted(result, key=cmp_to_key(comparator))