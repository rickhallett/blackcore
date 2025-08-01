"""High-performance filter engine with optimized algorithms for all query operators."""

import re
from typing import Any, Dict, List, Optional, Union
from datetime import datetime
import numpy as np
from fuzzywuzzy import fuzz
import logging

from ..interfaces import FilterEngine
from ..models import QueryFilter, QueryOperator, QueryValidationError

logger = logging.getLogger(__name__)


class BasicFilterEngine:
    """High-performance filter engine implementing all 15 query operators.
    
    Performance characteristics:
    - O(n) for most operators where n is number of records
    - Optimized filter ordering for early termination
    - Type conversion handling with minimal overhead
    - Support for nested field access via dot notation
    """
    
    def __init__(self):
        """Initialize filter engine with compiled patterns."""
        self._filter_cache = {}
        self._compiled_patterns = {}
        self._operator_functions = {
            QueryOperator.EQUALS: self._filter_equals,
            QueryOperator.NOT_EQUALS: self._filter_not_equals,
            QueryOperator.CONTAINS: self._filter_contains,
            QueryOperator.NOT_CONTAINS: self._filter_not_contains,
            QueryOperator.IN: self._filter_in,
            QueryOperator.NOT_IN: self._filter_not_in,
            QueryOperator.GT: self._filter_gt,
            QueryOperator.GTE: self._filter_gte,
            QueryOperator.LT: self._filter_lt,
            QueryOperator.LTE: self._filter_lte,
            QueryOperator.BETWEEN: self._filter_between,
            QueryOperator.IS_NULL: self._filter_is_null,
            QueryOperator.IS_NOT_NULL: self._filter_is_not_null,
            QueryOperator.REGEX: self._filter_regex,
            QueryOperator.FUZZY: self._filter_fuzzy,
        }
    
    def apply_filters(self, data: List[Dict[str, Any]], filters: List[QueryFilter]) -> List[Dict[str, Any]]:
        """Apply filters to data with optimized execution order.
        
        Performance: O(n*m) where n is records and m is filters
        Optimizations:
        - Early termination for empty results
        - Filter reordering for selectivity
        - Numpy arrays for numeric operations on large datasets
        
        Args:
            data: List of records to filter
            filters: List of filter conditions
            
        Returns:
            Filtered list of records
        """
        if not filters:
            return data
        
        if not data:
            return []
        
        # Optimize filter order for better performance
        optimized_filters = self._optimize_filter_order(filters, data)
        
        result = data
        for filter_condition in optimized_filters:
            if len(result) == 0:
                break  # Early termination
            
            # Use numpy for numeric operations on large datasets
            if (filter_condition.operator in (QueryOperator.GT, QueryOperator.LT, 
                                             QueryOperator.GTE, QueryOperator.LTE) 
                and len(result) > 1000):
                result = self._apply_numeric_filter_numpy(result, filter_condition)
            else:
                filter_func = self._operator_functions[filter_condition.operator]
                result = filter_func(result, filter_condition)
        
        return result
    
    def validate_filter(self, filter_condition: QueryFilter, database_schema: Dict[str, Any]) -> bool:
        """Validate that a filter is applicable to the schema.
        
        Args:
            filter_condition: Filter to validate
            database_schema: Database schema definition
            
        Returns:
            True if filter is valid
            
        Raises:
            QueryValidationError: If filter is invalid
        """
        # Check if field exists in schema
        field_parts = filter_condition.field.split('.')
        current_schema = database_schema
        
        for part in field_parts:
            if not isinstance(current_schema, dict) or part not in current_schema:
                raise QueryValidationError(
                    f"Field '{filter_condition.field}' not found in schema"
                )
            current_schema = current_schema[part]
        
        # Validate operator for field type
        # TODO: Add type-specific validation
        
        return True
    
    def _optimize_filter_order(self, filters: List[QueryFilter], data: List[Dict[str, Any]]) -> List[QueryFilter]:
        """Optimize filter execution order for better performance.
        
        Strategy:
        - Execute most selective filters first
        - Put equality and IN filters before range filters
        - Put regex and fuzzy filters last
        """
        # Group filters by estimated selectivity
        high_selectivity = []  # EQUALS, IN, IS_NULL
        medium_selectivity = []  # GT, LT, CONTAINS
        low_selectivity = []  # REGEX, FUZZY
        
        for f in filters:
            if f.operator in (QueryOperator.EQUALS, QueryOperator.IN, 
                            QueryOperator.IS_NULL, QueryOperator.IS_NOT_NULL):
                high_selectivity.append(f)
            elif f.operator in (QueryOperator.REGEX, QueryOperator.FUZZY):
                low_selectivity.append(f)
            else:
                medium_selectivity.append(f)
        
        return high_selectivity + medium_selectivity + low_selectivity
    
    def _get_field_value(self, record: Dict[str, Any], field: str) -> Any:
        """Get field value with support for nested access.
        
        Supports dot notation: "metadata.category" -> record["metadata"]["category"]
        """
        parts = field.split('.')
        value = record
        
        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return None
        
        return value
    
    def _apply_numeric_filter_numpy(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Apply numeric filters using numpy for better performance."""
        # Extract values as numpy array
        values = np.array([self._get_field_value(item, filter_condition.field) for item in data])
        
        # Handle None values
        mask = ~np.isnan(values.astype(float, errors='ignore'))
        
        # Apply operator
        if filter_condition.operator == QueryOperator.GT:
            mask &= values > filter_condition.value
        elif filter_condition.operator == QueryOperator.GTE:
            mask &= values >= filter_condition.value
        elif filter_condition.operator == QueryOperator.LT:
            mask &= values < filter_condition.value
        elif filter_condition.operator == QueryOperator.LTE:
            mask &= values <= filter_condition.value
        
        # Return filtered data
        return [item for item, include in zip(data, mask) if include]
    
    # Filter implementation methods
    def _filter_equals(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Filter for equality."""
        if filter_condition.case_sensitive or not isinstance(filter_condition.value, str):
            return [
                item for item in data 
                if self._get_field_value(item, filter_condition.field) == filter_condition.value
            ]
        else:
            value_lower = filter_condition.value.lower()
            return [
                item for item in data 
                if isinstance(self._get_field_value(item, filter_condition.field), str) and
                self._get_field_value(item, filter_condition.field).lower() == value_lower
            ]
    
    def _filter_not_equals(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Filter for inequality."""
        if filter_condition.case_sensitive or not isinstance(filter_condition.value, str):
            return [
                item for item in data 
                if self._get_field_value(item, filter_condition.field) != filter_condition.value
            ]
        else:
            value_lower = filter_condition.value.lower()
            return [
                item for item in data 
                if not isinstance(self._get_field_value(item, filter_condition.field), str) or
                self._get_field_value(item, filter_condition.field).lower() != value_lower
            ]
    
    def _filter_contains(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Filter for substring containment."""
        def check_contains(value: Any) -> bool:
            if isinstance(value, str):
                if filter_condition.case_sensitive:
                    return filter_condition.value in value
                else:
                    return filter_condition.value.lower() in value.lower()
            elif isinstance(value, list):
                return filter_condition.value in value
            return False
        
        return [
            item for item in data 
            if check_contains(self._get_field_value(item, filter_condition.field))
        ]
    
    def _filter_not_contains(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Filter for substring non-containment."""
        def check_not_contains(value: Any) -> bool:
            if isinstance(value, str):
                if filter_condition.case_sensitive:
                    return filter_condition.value not in value
                else:
                    return filter_condition.value.lower() not in value.lower()
            elif isinstance(value, list):
                return filter_condition.value not in value
            return True
        
        return [
            item for item in data 
            if check_not_contains(self._get_field_value(item, filter_condition.field))
        ]
    
    def _filter_in(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Filter for membership in list."""
        if not isinstance(filter_condition.value, list):
            raise QueryValidationError("IN operator requires list value")
        
        # Convert to set for O(1) lookup
        value_set = set(filter_condition.value)
        
        if filter_condition.case_sensitive or not all(isinstance(v, str) for v in filter_condition.value):
            return [
                item for item in data 
                if self._get_field_value(item, filter_condition.field) in value_set
            ]
        else:
            value_set_lower = {v.lower() for v in filter_condition.value if isinstance(v, str)}
            return [
                item for item in data 
                if isinstance(self._get_field_value(item, filter_condition.field), str) and
                self._get_field_value(item, filter_condition.field).lower() in value_set_lower
            ]
    
    def _filter_not_in(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Filter for non-membership in list."""
        if not isinstance(filter_condition.value, list):
            raise QueryValidationError("NOT_IN operator requires list value")
        
        # Convert to set for O(1) lookup
        value_set = set(filter_condition.value)
        
        if filter_condition.case_sensitive or not all(isinstance(v, str) for v in filter_condition.value):
            return [
                item for item in data 
                if self._get_field_value(item, filter_condition.field) not in value_set
            ]
        else:
            value_set_lower = {v.lower() for v in filter_condition.value if isinstance(v, str)}
            return [
                item for item in data 
                if not isinstance(self._get_field_value(item, filter_condition.field), str) or
                self._get_field_value(item, filter_condition.field).lower() not in value_set_lower
            ]
    
    def _filter_gt(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Filter for greater than."""
        return [
            item for item in data 
            if self._compare_values(
                self._get_field_value(item, filter_condition.field),
                filter_condition.value,
                lambda a, b: a > b
            )
        ]
    
    def _filter_gte(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Filter for greater than or equal."""
        return [
            item for item in data 
            if self._compare_values(
                self._get_field_value(item, filter_condition.field),
                filter_condition.value,
                lambda a, b: a >= b
            )
        ]
    
    def _filter_lt(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Filter for less than."""
        return [
            item for item in data 
            if self._compare_values(
                self._get_field_value(item, filter_condition.field),
                filter_condition.value,
                lambda a, b: a < b
            )
        ]
    
    def _filter_lte(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Filter for less than or equal."""
        return [
            item for item in data 
            if self._compare_values(
                self._get_field_value(item, filter_condition.field),
                filter_condition.value,
                lambda a, b: a <= b
            )
        ]
    
    def _filter_between(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Filter for range (between two values)."""
        if not isinstance(filter_condition.value, list) or len(filter_condition.value) != 2:
            raise QueryValidationError("BETWEEN operator requires list with exactly 2 values")
        
        min_val, max_val = filter_condition.value
        
        return [
            item for item in data 
            if self._compare_values(
                self._get_field_value(item, filter_condition.field),
                min_val,
                lambda a, b: a >= b
            ) and self._compare_values(
                self._get_field_value(item, filter_condition.field),
                max_val,
                lambda a, b: a <= b
            )
        ]
    
    def _filter_is_null(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Filter for null/None values."""
        return [
            item for item in data 
            if self._get_field_value(item, filter_condition.field) is None
        ]
    
    def _filter_is_not_null(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Filter for non-null values."""
        return [
            item for item in data 
            if self._get_field_value(item, filter_condition.field) is not None
        ]
    
    def _filter_regex(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Filter using regular expressions."""
        # Cache compiled patterns
        pattern_key = (filter_condition.value, filter_condition.case_sensitive)
        if pattern_key not in self._compiled_patterns:
            flags = 0 if filter_condition.case_sensitive else re.IGNORECASE
            self._compiled_patterns[pattern_key] = re.compile(filter_condition.value, flags)
        
        pattern = self._compiled_patterns[pattern_key]
        
        return [
            item for item in data 
            if isinstance(self._get_field_value(item, filter_condition.field), str) and
            pattern.search(self._get_field_value(item, filter_condition.field))
        ]
    
    def _filter_fuzzy(self, data: List[Dict[str, Any]], filter_condition: QueryFilter) -> List[Dict[str, Any]]:
        """Filter using fuzzy string matching."""
        # Expect value to be dict with 'text' and 'threshold'
        if isinstance(filter_condition.value, dict):
            search_text = filter_condition.value.get('text', '')
            threshold = filter_condition.value.get('threshold', 70)
        else:
            search_text = str(filter_condition.value)
            threshold = 70
        
        results = []
        for item in data:
            field_value = self._get_field_value(item, filter_condition.field)
            if isinstance(field_value, str):
                score = fuzz.ratio(search_text.lower(), field_value.lower())
                if score >= threshold:
                    results.append(item)
        
        return results
    
    def _compare_values(self, value1: Any, value2: Any, comparison_func) -> bool:
        """Compare values with type conversion handling."""
        if value1 is None or value2 is None:
            return False
        
        # Try to convert to same type for comparison
        try:
            # Handle date/datetime comparison
            if isinstance(value2, str) and isinstance(value1, str):
                # Try parsing as dates
                try:
                    v1 = datetime.fromisoformat(value1.replace('Z', '+00:00'))
                    v2 = datetime.fromisoformat(value2.replace('Z', '+00:00'))
                    return comparison_func(v1, v2)
                except:
                    pass
            
            # Handle numeric comparison
            if isinstance(value2, (int, float)):
                try:
                    value1 = float(value1)
                    return comparison_func(value1, value2)
                except:
                    return False
            
            # Default comparison
            return comparison_func(value1, value2)
        except:
            return False