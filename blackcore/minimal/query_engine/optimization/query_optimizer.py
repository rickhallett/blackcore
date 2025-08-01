"""Cost-based query optimizer for performance improvements."""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import math

from ..models import (
    StructuredQuery, QueryFilter, QueryOperator, 
    SortField, SortOrder, OptimizedQuery
)
from .statistics import QueryStatistics, TableStatistics


@dataclass
class FilterCost:
    """Cost estimation for a filter."""
    
    filter: QueryFilter
    selectivity: float  # Fraction of rows that pass (0-1)
    cpu_cost: float    # Relative CPU cost
    io_cost: float     # Relative I/O cost
    total_cost: float  # Combined cost metric
    
    @property
    def priority(self) -> float:
        """Calculate filter priority (lower is better)."""
        # Apply cheap, selective filters first
        return self.total_cost / max(self.selectivity, 0.001)


@dataclass
class OptimizedQuery(StructuredQuery):
    """Query with optimization metadata."""
    
    estimated_cost: float = 0.0
    optimization_hints: List[str] = None
    suggested_indexes: List[str] = None


class CostBasedOptimizer:
    """Optimize queries based on statistics and cost models."""
    
    def __init__(self):
        """Initialize optimizer."""
        self._statistics_cache: Dict[str, TableStatistics] = {}
        self._query_history: List[Tuple[StructuredQuery, float]] = []
        
    def optimize_query(self, query: StructuredQuery, statistics: Optional[QueryStatistics] = None) -> OptimizedQuery:
        """Optimize query for better performance."""
        # Get table statistics
        table_stats = self._get_table_statistics(query.database)
        
        # Create optimized query
        optimized = OptimizedQuery(**query.model_dump())
        optimized.optimization_hints = []
        
        # Optimize filter order
        if query.filters:
            optimized.filters = self._optimize_filter_order(query.filters, table_stats)
            optimized.optimization_hints.append(f"Reordered {len(query.filters)} filters by selectivity and cost")
        
        # Optimize sort fields
        if query.sort_fields:
            optimized.sort_fields = self._optimize_sort_fields(query.sort_fields, query.filters, table_stats)
        
        # Suggest indexes
        optimized.suggested_indexes = self._suggest_indexes(query, table_stats)
        
        # Estimate total cost
        optimized.estimated_cost = self._estimate_query_cost(optimized, table_stats)
        
        # Track query for learning
        self._query_history.append((query, optimized.estimated_cost))
        
        return optimized
    
    def _optimize_filter_order(self, filters: List[QueryFilter], stats: TableStatistics) -> List[QueryFilter]:
        """Reorder filters by selectivity and cost."""
        filter_costs = []
        
        for filter in filters:
            selectivity = self._estimate_selectivity(filter, stats)
            cpu_cost = self._estimate_filter_cpu_cost(filter)
            io_cost = self._estimate_filter_io_cost(filter, stats)
            
            total_cost = cpu_cost + io_cost
            
            filter_costs.append(FilterCost(
                filter=filter,
                selectivity=selectivity,
                cpu_cost=cpu_cost,
                io_cost=io_cost,
                total_cost=total_cost
            ))
        
        # Sort by priority (lower is better)
        filter_costs.sort(key=lambda fc: fc.priority)
        
        return [fc.filter for fc in filter_costs]
    
    def _estimate_selectivity(self, filter: QueryFilter, stats: TableStatistics) -> float:
        """Estimate fraction of rows that pass filter."""
        field = filter.field
        operator = filter.operator
        value = filter.value
        
        # Use histogram if available
        if field in stats.histograms:
            histogram = stats.histograms[field]
            
            if operator == QueryOperator.EQUALS:
                return histogram.estimate_frequency(value)
            elif operator == QueryOperator.GT:
                return histogram.estimate_range_frequency(value, None)
            elif operator == QueryOperator.LT:
                return histogram.estimate_range_frequency(None, value)
            elif operator == QueryOperator.BETWEEN:
                if isinstance(value, (list, tuple)) and len(value) == 2:
                    return histogram.estimate_range_frequency(value[0], value[1])
        
        # Use distinct values if available
        if field in stats.distinct_values:
            distinct_count = stats.distinct_values[field]
            
            if operator == QueryOperator.EQUALS:
                return 1.0 / max(distinct_count, 1)
            elif operator == QueryOperator.IN:
                if isinstance(value, (list, set)):
                    return min(len(value) / max(distinct_count, 1), 1.0)
        
        # Default selectivity estimates
        selectivity_defaults = {
            QueryOperator.EQUALS: 0.1,
            QueryOperator.NOT_EQUALS: 0.9,
            QueryOperator.CONTAINS: 0.3,
            QueryOperator.NOT_CONTAINS: 0.7,
            QueryOperator.IN: 0.2,
            QueryOperator.NOT_IN: 0.8,
            QueryOperator.GT: 0.3,
            QueryOperator.GTE: 0.35,
            QueryOperator.LT: 0.3,
            QueryOperator.LTE: 0.35,
            QueryOperator.BETWEEN: 0.25,
            QueryOperator.IS_NULL: 0.05,
            QueryOperator.IS_NOT_NULL: 0.95,
            QueryOperator.REGEX: 0.15,
            QueryOperator.FUZZY: 0.2
        }
        
        return selectivity_defaults.get(operator, 0.5)
    
    def _estimate_filter_cpu_cost(self, filter: QueryFilter) -> float:
        """Estimate CPU cost of applying filter."""
        operator = filter.operator
        
        # Relative CPU costs by operator
        cpu_costs = {
            QueryOperator.EQUALS: 1.0,
            QueryOperator.NOT_EQUALS: 1.0,
            QueryOperator.CONTAINS: 5.0,  # String search
            QueryOperator.NOT_CONTAINS: 5.0,
            QueryOperator.IN: 2.0,
            QueryOperator.NOT_IN: 2.0,
            QueryOperator.GT: 1.0,
            QueryOperator.GTE: 1.0,
            QueryOperator.LT: 1.0,
            QueryOperator.LTE: 1.0,
            QueryOperator.BETWEEN: 2.0,
            QueryOperator.IS_NULL: 0.5,
            QueryOperator.IS_NOT_NULL: 0.5,
            QueryOperator.REGEX: 10.0,  # Expensive regex
            QueryOperator.FUZZY: 15.0   # Very expensive fuzzy match
        }
        
        base_cost = cpu_costs.get(operator, 1.0)
        
        # Adjust for case sensitivity
        if hasattr(filter, 'case_sensitive') and not filter.case_sensitive:
            base_cost *= 1.5
        
        return base_cost
    
    def _estimate_filter_io_cost(self, filter: QueryFilter, stats: TableStatistics) -> float:
        """Estimate I/O cost of applying filter."""
        # Simplified model - would be more complex in production
        if filter.field in stats.indexed_fields:
            return 1.0  # Indexed access
        else:
            return 10.0  # Full scan
    
    def _optimize_sort_fields(self, sort_fields: List[SortField], filters: List[QueryFilter], 
                            stats: TableStatistics) -> List[SortField]:
        """Optimize sort fields based on available indexes."""
        # Check if we can use an index for sorting
        for field in sort_fields:
            if field.field in stats.indexed_fields:
                # Move indexed fields to front for better performance
                return [field] + [f for f in sort_fields if f != field]
        
        return sort_fields
    
    def _suggest_indexes(self, query: StructuredQuery, stats: TableStatistics) -> List[str]:
        """Suggest indexes based on query patterns."""
        suggestions = []
        
        # Suggest indexes for frequently filtered fields
        for filter in query.filters:
            if filter.field not in stats.indexed_fields:
                if filter.operator in [QueryOperator.EQUALS, QueryOperator.GT, QueryOperator.LT]:
                    suggestions.append(f"CREATE INDEX idx_{query.database}_{filter.field} ON {query.database}({filter.field})")
        
        # Suggest composite indexes for common filter combinations
        if len(query.filters) > 1:
            filter_fields = [f.field for f in query.filters[:3]]  # Top 3 filters
            composite_key = "_".join(filter_fields)
            suggestions.append(f"CREATE INDEX idx_{query.database}_{composite_key} ON {query.database}({', '.join(filter_fields)})")
        
        # Suggest indexes for sort fields
        for sort_field in query.sort_fields:
            if sort_field.field not in stats.indexed_fields:
                suggestions.append(f"CREATE INDEX idx_{query.database}_{sort_field.field} ON {query.database}({sort_field.field})")
        
        return suggestions[:5]  # Limit suggestions
    
    def _estimate_query_cost(self, query: OptimizedQuery, stats: TableStatistics) -> float:
        """Estimate total query execution cost."""
        base_cost = stats.row_count
        
        # Apply filter selectivity
        for filter in query.filters:
            selectivity = self._estimate_selectivity(filter, stats)
            base_cost *= selectivity
        
        # Add sort cost if needed
        if query.sort_fields:
            sort_cost = base_cost * math.log2(max(base_cost, 2))
            base_cost += sort_cost
        
        # Add pagination overhead
        if query.pagination:
            base_cost += query.pagination.offset
        
        return base_cost
    
    def _get_table_statistics(self, database: str) -> TableStatistics:
        """Get or compute table statistics."""
        if database not in self._statistics_cache:
            # In production, would load from stats table or compute
            self._statistics_cache[database] = TableStatistics(
                database_name=database,
                row_count=10000,  # Default estimate
                distinct_values={},
                indexed_fields=[],
                histograms={}
            )
        
        return self._statistics_cache[database]
    
    def generate_execution_plan(self, query: StructuredQuery) -> Dict[str, Any]:
        """Generate detailed execution plan."""
        optimized = self.optimize_query(query)
        stats = self._get_table_statistics(query.database)
        
        plan = {
            "type": "query_execution_plan",
            "database": query.database,
            "estimated_cost": optimized.estimated_cost,
            "estimated_rows": stats.row_count,
            "steps": []
        }
        
        # Data access step
        plan["steps"].append({
            "operation": "table_scan" if not stats.indexed_fields else "index_scan",
            "table": query.database,
            "estimated_rows": stats.row_count,
            "cost": stats.row_count
        })
        
        # Filter steps
        remaining_rows = stats.row_count
        for i, filter in enumerate(optimized.filters):
            selectivity = self._estimate_selectivity(filter, stats)
            remaining_rows *= selectivity
            
            plan["steps"].append({
                "operation": "filter",
                "condition": f"{filter.field} {filter.operator} {filter.value}",
                "selectivity": selectivity,
                "estimated_rows": int(remaining_rows),
                "cost": self._estimate_filter_cpu_cost(filter)
            })
        
        # Sort step
        if query.sort_fields:
            plan["steps"].append({
                "operation": "sort",
                "fields": [f"{f.field} {f.order}" for f in query.sort_fields],
                "estimated_rows": int(remaining_rows),
                "cost": remaining_rows * math.log2(max(remaining_rows, 2))
            })
        
        # Pagination step
        if query.pagination:
            plan["steps"].append({
                "operation": "limit",
                "offset": query.pagination.offset,
                "limit": query.pagination.size,
                "estimated_rows": min(query.pagination.size, int(remaining_rows))
            })
        
        return plan


class QueryOptimizer(CostBasedOptimizer):
    """Main query optimizer implementing the Protocol interface."""
    
    def optimize_query(self, query: StructuredQuery, statistics: Optional[QueryStatistics] = None) -> StructuredQuery:
        """Optimize query for better performance."""
        optimized = super().optimize_query(query, statistics)
        # Return as base StructuredQuery to match interface
        return StructuredQuery(**optimized.model_dump(exclude={'estimated_cost', 'optimization_hints', 'suggested_indexes'}))
    
    def estimate_cost(self, query: StructuredQuery) -> float:
        """Estimate query execution cost."""
        stats = self._get_table_statistics(query.database)
        return self._estimate_query_cost(query, stats)
    
    def suggest_indexes(self, queries: List[StructuredQuery]) -> List[str]:
        """Suggest indexes based on query patterns."""
        all_suggestions = []
        suggestion_counts = {}
        
        # Collect suggestions from all queries
        for query in queries:
            stats = self._get_table_statistics(query.database)
            suggestions = self._suggest_indexes(query, stats)
            
            for suggestion in suggestions:
                if suggestion in suggestion_counts:
                    suggestion_counts[suggestion] += 1
                else:
                    suggestion_counts[suggestion] = 1
                    all_suggestions.append(suggestion)
        
        # Sort by frequency
        all_suggestions.sort(key=lambda s: suggestion_counts[s], reverse=True)
        
        return all_suggestions[:10]  # Top 10 suggestions