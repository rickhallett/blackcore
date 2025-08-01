"""Query execution planning and visualization."""

from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
import json

from ..models import StructuredQuery, QueryFilter


@dataclass
class ExecutionStep:
    """Single step in execution plan."""
    
    operation: str
    description: str
    estimated_rows: int
    estimated_cost: float
    actual_rows: Optional[int] = None
    actual_time_ms: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def row_reduction(self) -> float:
        """Calculate row reduction percentage."""
        if 'input_rows' in self.metadata and self.estimated_rows > 0:
            input_rows = self.metadata['input_rows']
            if input_rows > 0:
                return (input_rows - self.estimated_rows) / input_rows
        return 0.0


@dataclass
class ExecutionPlan:
    """Complete execution plan for a query."""
    
    query_id: str
    database: str
    total_cost: float
    steps: List[ExecutionStep]
    optimization_hints: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'query_id': self.query_id,
            'database': self.database,
            'total_cost': self.total_cost,
            'steps': [
                {
                    'operation': step.operation,
                    'description': step.description,
                    'estimated_rows': step.estimated_rows,
                    'estimated_cost': step.estimated_cost,
                    'actual_rows': step.actual_rows,
                    'actual_time_ms': step.actual_time_ms,
                    'metadata': step.metadata
                }
                for step in self.steps
            ],
            'optimization_hints': self.optimization_hints,
            'warnings': self.warnings
        }
    
    def to_text(self) -> str:
        """Generate human-readable execution plan."""
        lines = [
            f"Execution Plan for Query {self.query_id}",
            f"Database: {self.database}",
            f"Total Estimated Cost: {self.total_cost:.2f}",
            "",
            "Steps:"
        ]
        
        for i, step in enumerate(self.steps):
            indent = "  " * i
            lines.append(f"{indent}-> {step.operation.upper()}")
            lines.append(f"{indent}   {step.description}")
            lines.append(f"{indent}   Estimated Rows: {step.estimated_rows:,}")
            lines.append(f"{indent}   Estimated Cost: {step.estimated_cost:.2f}")
            
            if step.actual_rows is not None:
                lines.append(f"{indent}   Actual Rows: {step.actual_rows:,}")
            if step.actual_time_ms is not None:
                lines.append(f"{indent}   Actual Time: {step.actual_time_ms:.2f}ms")
            
            if step.row_reduction > 0:
                lines.append(f"{indent}   Row Reduction: {step.row_reduction*100:.1f}%")
        
        if self.optimization_hints:
            lines.extend(["", "Optimization Hints:"])
            for hint in self.optimization_hints:
                lines.append(f"  - {hint}")
        
        if self.warnings:
            lines.extend(["", "Warnings:"])
            for warning in self.warnings:
                lines.append(f"  ! {warning}")
        
        return "\n".join(lines)
    
    def visualize_ascii(self) -> str:
        """Generate ASCII visualization of execution plan."""
        lines = [
            "┌─────────────────────────────────────────┐",
            f"│ Query Plan: {self.database:<27} │",
            "├─────────────────────────────────────────┤"
        ]
        
        for i, step in enumerate(self.steps):
            is_last = i == len(self.steps) - 1
            prefix = "└──" if is_last else "├──"
            cont_prefix = "   " if is_last else "│  "
            
            lines.append(f"│ {prefix} {step.operation.upper():<33} │")
            lines.append(f"│ {cont_prefix} Rows: {step.estimated_rows:<28} │")
            lines.append(f"│ {cont_prefix} Cost: {step.estimated_cost:<28.1f} │")
            
            if not is_last:
                lines.append("│ │                                       │")
        
        lines.append("└─────────────────────────────────────────┘")
        
        return "\n".join(lines)


class ExecutionPlanner:
    """Create and analyze query execution plans."""
    
    def __init__(self):
        """Initialize execution planner."""
        self._plan_cache: Dict[str, ExecutionPlan] = {}
        self._query_counter = 0
    
    def create_plan(self, query: StructuredQuery, statistics: Dict[str, Any]) -> ExecutionPlan:
        """Create execution plan for a query."""
        self._query_counter += 1
        query_id = f"Q{self._query_counter:04d}"
        
        steps = []
        current_rows = statistics.get('row_count', 10000)
        total_cost = 0.0
        
        # Step 1: Data Access
        access_step = self._create_access_step(query, statistics, current_rows)
        steps.append(access_step)
        total_cost += access_step.estimated_cost
        
        # Step 2: Filters
        for filter in query.filters:
            filter_step = self._create_filter_step(filter, current_rows, statistics)
            current_rows = filter_step.estimated_rows
            steps.append(filter_step)
            total_cost += filter_step.estimated_cost
        
        # Step 3: Sorting (if needed)
        if query.sort_fields:
            sort_step = self._create_sort_step(query.sort_fields, current_rows)
            steps.append(sort_step)
            total_cost += sort_step.estimated_cost
        
        # Step 4: Distinct (if needed)
        if query.distinct:
            distinct_step = self._create_distinct_step(current_rows, statistics)
            current_rows = distinct_step.estimated_rows
            steps.append(distinct_step)
            total_cost += distinct_step.estimated_cost
        
        # Step 5: Pagination
        if query.pagination:
            page_step = self._create_pagination_step(query.pagination, current_rows)
            steps.append(page_step)
            total_cost += page_step.estimated_cost
        
        # Create plan
        plan = ExecutionPlan(
            query_id=query_id,
            database=query.database,
            total_cost=total_cost,
            steps=steps
        )
        
        # Add optimization hints and warnings
        self._add_optimization_hints(plan, query, statistics)
        self._add_warnings(plan, query, statistics)
        
        # Cache plan
        self._plan_cache[query_id] = plan
        
        return plan
    
    def _create_access_step(self, query: StructuredQuery, statistics: Dict[str, Any], rows: int) -> ExecutionStep:
        """Create data access step."""
        indexed_fields = statistics.get('indexed_fields', [])
        
        # Check if we can use index
        can_use_index = False
        index_field = None
        
        for filter in query.filters:
            if filter.field in indexed_fields and filter.operator in ['eq', 'gt', 'lt', 'gte', 'lte']:
                can_use_index = True
                index_field = filter.field
                break
        
        if can_use_index:
            return ExecutionStep(
                operation="index_scan",
                description=f"Index scan on {index_field}",
                estimated_rows=rows,
                estimated_cost=rows * 0.1,  # Index scan is cheaper
                metadata={'index': index_field}
            )
        else:
            return ExecutionStep(
                operation="table_scan",
                description=f"Full table scan on {query.database}",
                estimated_rows=rows,
                estimated_cost=rows * 1.0,
                metadata={'reason': 'No suitable index found'}
            )
    
    def _create_filter_step(self, filter: QueryFilter, input_rows: int, statistics: Dict[str, Any]) -> ExecutionStep:
        """Create filter step."""
        # Estimate selectivity
        selectivity = self._estimate_filter_selectivity(filter, statistics)
        output_rows = int(input_rows * selectivity)
        
        # Estimate cost based on operator
        operator_costs = {
            'eq': 1.0,
            'contains': 5.0,
            'regex': 10.0,
            'fuzzy': 15.0
        }
        
        cost_per_row = operator_costs.get(filter.operator.value if hasattr(filter.operator, 'value') else filter.operator, 1.0)
        
        return ExecutionStep(
            operation="filter",
            description=f"Filter: {filter.field} {filter.operator} {filter.value}",
            estimated_rows=output_rows,
            estimated_cost=input_rows * cost_per_row,
            metadata={
                'field': filter.field,
                'operator': str(filter.operator),
                'selectivity': selectivity,
                'input_rows': input_rows
            }
        )
    
    def _create_sort_step(self, sort_fields: List[Any], rows: int) -> ExecutionStep:
        """Create sort step."""
        # Sort cost is O(n log n)
        import math
        cost = rows * math.log2(max(rows, 2))
        
        sort_desc = ", ".join([f"{f.field} {f.order}" for f in sort_fields])
        
        return ExecutionStep(
            operation="sort",
            description=f"Sort by: {sort_desc}",
            estimated_rows=rows,
            estimated_cost=cost,
            metadata={'fields': [f.field for f in sort_fields]}
        )
    
    def _create_distinct_step(self, rows: int, statistics: Dict[str, Any]) -> ExecutionStep:
        """Create distinct step."""
        # Estimate distinct ratio
        distinct_ratio = 0.7  # Default assumption
        output_rows = int(rows * distinct_ratio)
        
        return ExecutionStep(
            operation="distinct",
            description="Remove duplicate rows",
            estimated_rows=output_rows,
            estimated_cost=rows * 2.0,  # Hash-based distinct
            metadata={'distinct_ratio': distinct_ratio}
        )
    
    def _create_pagination_step(self, pagination: Any, rows: int) -> ExecutionStep:
        """Create pagination step."""
        output_rows = min(pagination.size, rows - pagination.offset)
        output_rows = max(0, output_rows)
        
        return ExecutionStep(
            operation="limit",
            description=f"Limit: {pagination.size} rows, Offset: {pagination.offset}",
            estimated_rows=output_rows,
            estimated_cost=pagination.offset + pagination.size,
            metadata={
                'limit': pagination.size,
                'offset': pagination.offset
            }
        )
    
    def _estimate_filter_selectivity(self, filter: QueryFilter, statistics: Dict[str, Any]) -> float:
        """Estimate filter selectivity."""
        # Simplified selectivity estimation
        operator_selectivity = {
            'eq': 0.1,
            'ne': 0.9,
            'contains': 0.3,
            'gt': 0.3,
            'lt': 0.3,
            'between': 0.25,
            'in': 0.2,
            'is_null': 0.05,
            'is_not_null': 0.95,
            'regex': 0.15,
            'fuzzy': 0.2
        }
        
        operator_str = filter.operator.value if hasattr(filter.operator, 'value') else str(filter.operator)
        return operator_selectivity.get(operator_str, 0.5)
    
    def _add_optimization_hints(self, plan: ExecutionPlan, query: StructuredQuery, statistics: Dict[str, Any]):
        """Add optimization hints to plan."""
        indexed_fields = statistics.get('indexed_fields', [])
        
        # Check for missing indexes
        for filter in query.filters:
            if filter.field not in indexed_fields:
                plan.optimization_hints.append(
                    f"Consider adding index on '{filter.field}' for better filter performance"
                )
        
        # Check for expensive operations
        for step in plan.steps:
            if step.operation == "table_scan" and step.estimated_rows > 10000:
                plan.optimization_hints.append(
                    "Large table scan detected - consider adding appropriate indexes"
                )
            elif step.operation == "sort" and step.estimated_rows > 5000:
                plan.optimization_hints.append(
                    "Large sort operation - consider adding index on sort fields"
                )
    
    def _add_warnings(self, plan: ExecutionPlan, query: StructuredQuery, statistics: Dict[str, Any]):
        """Add warnings to plan."""
        # Check for potential performance issues
        if plan.total_cost > 1000000:
            plan.warnings.append("Query has high estimated cost - may be slow")
        
        # Check for missing statistics
        if not statistics.get('row_count'):
            plan.warnings.append("Table statistics missing - cost estimates may be inaccurate")
        
        # Check for complex regex/fuzzy filters
        for filter in query.filters:
            if filter.operator in ['regex', 'fuzzy']:
                plan.warnings.append(f"Complex {filter.operator} operation on '{filter.field}' may be slow")
    
    def analyze_plan(self, plan: ExecutionPlan) -> Dict[str, Any]:
        """Analyze execution plan for insights."""
        analysis = {
            'total_cost': plan.total_cost,
            'step_count': len(plan.steps),
            'bottlenecks': [],
            'row_reduction': 0.0,
            'dominant_cost': None
        }
        
        # Find bottlenecks (steps with >30% of total cost)
        for step in plan.steps:
            if step.estimated_cost > plan.total_cost * 0.3:
                analysis['bottlenecks'].append({
                    'operation': step.operation,
                    'cost_percentage': (step.estimated_cost / plan.total_cost) * 100
                })
        
        # Calculate total row reduction
        if plan.steps:
            first_rows = plan.steps[0].estimated_rows
            last_rows = plan.steps[-1].estimated_rows
            if first_rows > 0:
                analysis['row_reduction'] = (first_rows - last_rows) / first_rows
        
        # Find dominant cost operation
        max_cost_step = max(plan.steps, key=lambda s: s.estimated_cost)
        analysis['dominant_cost'] = {
            'operation': max_cost_step.operation,
            'cost': max_cost_step.estimated_cost,
            'percentage': (max_cost_step.estimated_cost / plan.total_cost) * 100
        }
        
        return analysis