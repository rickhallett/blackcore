"""Query service layer for HTTP API integration."""

from typing import Dict, List, Any, Optional, AsyncIterator
from datetime import datetime
from pathlib import Path
import asyncio
import json
import structlog

from fastapi import HTTPException, status

from .query_models import (
    QueryRequest, QueryResponse, TextSearchRequest, TextSearchResponse,
    ExportRequest, ExportJob, QueryEstimateRequest, QueryEstimateResponse,
    QueryStatsResponse
)
from .export_manager import ExportJobManager
from ..query_engine import QueryEngine, StructuredQuery
from ..query_engine.factory import QueryEngineFactory
from ..query_engine.models import QueryFilter as EngineFilter
from ..query_engine.export import ExportManager
from ..query_engine.optimization import QueryOptimizer
from ..query_engine.statistics import StatisticsCollector


logger = structlog.get_logger()


class QueryService:
    """Bridge between HTTP endpoints and query engine."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize query service."""
        self.config = config or {}
        self.engine = None
        self.export_manager = None
        self.export_job_manager = None
        self.stats_collector = None
        self.optimizer = None
        self._initialized = False
    
    async def initialize(self):
        """Initialize query engine and related components."""
        if self._initialized:
            return
        
        # Initialize query engine with configuration
        logger.info("Initializing query service components")
        
        # Initialize components with proper configuration
        engine_config = self.config.get('query_engine', {})
        self.engine = QueryEngineFactory.create_structured_executor(engine_config)
        
        export_config = self.config.get('export', {})
        self.export_manager = ExportManager()
        self.export_job_manager = ExportJobManager()
        
        # Initialize statistics collector and optimizer
        self.stats_collector = StatisticsCollector()
        self.optimizer = QueryOptimizer()
        
        # Start background tasks
        await self.export_job_manager.start()
        
        self._initialized = True
    
    async def execute_query(
        self, 
        request: QueryRequest, 
        user: Dict[str, Any]
    ) -> QueryResponse:
        """Execute a structured query."""
        if not self._initialized:
            await self.initialize()
        
        # Execute actual query with proper logging
        logger.info(
            "Executing structured query",
            database=request.database,
            filter_count=len(request.filters),
            includes_count=len(request.includes),
            user_id=user.get("sub")
        )
        
        # Validate access
        self._validate_access(request.database, user)
        
        # Check query complexity
        if self._is_expensive_query(request):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Query too complex. Please add more filters or reduce includes."
            )
        
        # Convert to internal query format
        internal_query = self._build_internal_query(request)
        
        # Execute query with engine
        try:
            result = await self.engine.execute_structured_query_async(internal_query)
            
            # Record statistics
            if self.stats_collector:
                filter_fields = [f.field for f in request.filters]
                self.stats_collector.record_query(
                    database=request.database,
                    filters=filter_fields,
                    execution_time_ms=result.execution_time_ms,
                    from_cache=result.from_cache
                )
                
                # Track cache tier hits if available
                if hasattr(result, 'cache_tier') and result.cache_tier:
                    self.stats_collector.update_cache_tier_hit(result.cache_tier)
            
            # Build HTTP response
            return QueryResponse(
                data=result.data,
                total_count=result.total_count,
                page=result.page,
                page_size=result.page_size,
                execution_time_ms=result.execution_time_ms,
                from_cache=result.from_cache,
                links=self._build_pagination_links(request, result.total_count)
            )
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            # Re-raise with appropriate HTTP status
            if "not found" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Database '{request.database}' not found"
                )
            elif "validation" in str(e).lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Query validation failed: {e}"
                )
            else:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Query execution failed"
                )
    
    async def text_search(
        self,
        request: TextSearchRequest,
        user: Dict[str, Any]
    ) -> TextSearchResponse:
        """Execute text search across databases."""
        if not self._initialized:
            await self.initialize()
        
        # Execute actual text search
        logger.info(
            "Executing text search",
            query=request.query_text,
            databases=request.databases,
            user_id=user.get("sub")
        )
        
        # Validate database access
        if request.databases:
            for db in request.databases:
                self._validate_access(db, user)
        
        # Execute search with engine
        try:
            start_time = asyncio.get_event_loop().time()
            
            results = await self.engine.text_search_async(
                request.query_text, 
                request.databases
            )
            
            execution_time = (asyncio.get_event_loop().time() - start_time) * 1000
            
            # Record text search statistics
            if self.stats_collector:
                search_databases = request.databases or ["all"]
                for db in search_databases:
                    self.stats_collector.record_query(
                        database=db,
                        filters=["text_search"],  # Special filter type for search
                        execution_time_ms=execution_time,
                        from_cache=False  # Text searches typically aren't cached
                    )
            
            # Filter by similarity threshold and limit results
            filtered_results = []
            for result in results:
                score = result.get("_score", 0.0)
                if score >= request.similarity_threshold:
                    # Format result for HTTP response
                    match = {
                        "entity_id": result.get("id", "unknown"),
                        "database": result.get("_database", "unknown"),
                        "similarity_score": score,
                        "matched_content": self._extract_match_snippet(result, request.query_text),
                        "entity_data": {k: v for k, v in result.items() 
                                      if not k.startswith("_")}
                    }
                    filtered_results.append(match)
            
            # Apply max results limit
            limited_results = filtered_results[:request.max_results]
            
            return TextSearchResponse(
                matches=limited_results,
                query_text=request.query_text,
                execution_time_ms=execution_time,
                total_matches=len(filtered_results)
            )
            
        except Exception as e:
            logger.error(f"Text search failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Text search failed"
            )
    
    async def create_export(
        self,
        request: ExportRequest,
        user: Dict[str, Any]
    ) -> ExportJob:
        """Create an export job."""
        if not self._initialized:
            await self.initialize()
        
        # Create actual export job
        logger.info(
            "Creating export job",
            database=request.query.database,
            format=request.format,
            user_id=user.get("sub")
        )
        
        # Validate access
        self._validate_access(request.query.database, user)
        
        # Estimate export size
        estimated_size = await self._estimate_export_size(request)
        if not self._check_export_quota(user, estimated_size):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Export exceeds user quota"
            )
        
        # Create actual export job
        try:
            job = self.export_job_manager.create_export_job(
                request=request,
                user_id=user.get("sub", "unknown"),
                query_engine=self.engine
            )
            return job
            
        except Exception as e:
            logger.error(f"Failed to create export job: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create export job"
            )
    
    async def get_export_status(
        self,
        job_id: str,
        user: Dict[str, Any]
    ) -> Optional[ExportJob]:
        """Get export job status."""
        logger.info(
            "Getting export status",
            job_id=job_id,
            user_id=user.get("sub")
        )
        
        job = self.export_job_manager.get_job_status(
            job_id=job_id,
            user_id=user.get("sub", "unknown")
        )
        
        return job
    
    async def download_export(
        self,
        job_id: str,
        user: Dict[str, Any]
    ) -> Optional[AsyncIterator[bytes]]:
        """Download export file."""
        logger.info(
            "Downloading export",
            job_id=job_id,
            user_id=user.get("sub")
        )
        
        result = await self.export_job_manager.get_file_stream(
            job_id=job_id,
            user_id=user.get("sub", "unknown")
        )
        
        if result:
            file_stream, file_size = result
            return file_stream
        
        return None
    
    async def estimate_query(
        self,
        request: QueryEstimateRequest,
        user: Dict[str, Any]
    ) -> QueryEstimateResponse:
        """Estimate query cost and performance."""
        if not self._initialized:
            await self.initialize()
        
        # Implement actual query estimation using optimizer
        logger.info(
            "Estimating query cost",
            database=request.database,
            filter_count=len(request.filters),
            user_id=user.get("sub")
        )
        
        # Convert to internal query format for estimation
        internal_query = self._build_internal_query(request)
        
        # Use optimizer to estimate cost
        estimated_cost = self.optimizer.estimate_cost(internal_query)
        execution_plan = self.optimizer.generate_execution_plan(internal_query)
        
        # Calculate estimated rows from execution plan
        estimated_rows = execution_plan.get('estimated_rows', 1000)
        estimated_time_ms = max(50.0, estimated_cost * 0.1)  # Rough time estimation
        
        # Generate optimization hints
        optimization_hints = []
        if len(request.filters) == 0:
            optimization_hints.append("Consider adding filters to improve performance")
        if len(request.filters) > 10:
            optimization_hints.append("Large number of filters may impact performance")
        
        # Generate index suggestions
        suggested_indexes = self.optimizer.suggest_indexes([internal_query])
        
        # Build response with actual estimates
        return QueryEstimateResponse(
            estimated_rows=int(estimated_rows),
            estimated_cost=estimated_cost,
            estimated_time_ms=estimated_time_ms,
            optimization_hints=optimization_hints,
            suggested_indexes=suggested_indexes[:5]  # Limit to top 5 suggestions
        )
    
    async def get_statistics(self) -> QueryStatsResponse:
        """Get query statistics."""
        if not self._initialized:
            await self.initialize()
        
        # Get actual statistics from stats collector
        stats = self.stats_collector.get_query_statistics()
        
        return QueryStatsResponse(
            total_queries=stats.get("total_queries", 0),
            cache_hit_rate=stats.get("cache_hit_rate", 0.0),
            average_execution_time_ms=stats.get("average_execution_time_ms", 0.0),
            popular_databases=stats.get("popular_databases", {}),
            popular_filters=stats.get("popular_filters", {}),
            cache_statistics=stats.get("cache_statistics", {
                "memory_hit_rate": 0.0,
                "redis_hit_rate": 0.0,
                "disk_hit_rate": 0.0
            })
        )
    
    def _validate_access(self, database: str, user: Dict[str, Any]):
        """Validate user access to database."""
        # Get available databases dynamically
        try:
            available_databases = [db["name"] for db in asyncio.run(self.get_available_databases())]
        except Exception:
            # Fallback to hardcoded list if dynamic discovery fails
            available_databases = [
                "People & Contacts",
                "Organizations & Bodies", 
                "Actionable Tasks",
                "Intelligence & Transcripts",
                "Documents & Evidence",
                "Key Places & Events",
                "Agendas & Epics",
                "Identified Transgressions"
            ]
        
        if database not in available_databases:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Database '{database}' not found"
            )
        
        # Check user permissions based on scopes
        user_scopes = user.get("scopes", [])
        if "admin" not in user_scopes:
            # Non-admin users have read-only access to most databases
            if "read" not in user_scopes:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Insufficient permissions for database access"
                )
    
    def _is_expensive_query(self, request: QueryRequest) -> bool:
        """Check if query is too expensive."""
        # Simple heuristics for query complexity
        filter_count = len(request.filters)
        include_count = len(request.includes)
        
        # Too many filters
        if filter_count > 20:
            return True
        
        # Too many includes
        if include_count > 5:
            return True
        
        # No filters with large pagination
        if filter_count == 0 and request.pagination.size > 100:
            return True
        
        return False
    
    def _build_internal_query(self, request: QueryRequest) -> StructuredQuery:
        """Convert API request to internal query format."""
        from ..query_engine.models import QueryPagination, SortField, RelationshipInclude
        
        # Convert filters
        engine_filters = []
        for http_filter in request.filters:
            engine_filter = EngineFilter(
                field=http_filter.field,
                operator=http_filter.operator,
                value=http_filter.value,
                case_sensitive=http_filter.case_sensitive
            )
            engine_filters.append(engine_filter)
        
        # Convert sort fields
        engine_sort_fields = []
        for http_sort in request.sort_fields:
            from ..query_engine.models import SortOrder
            sort_order = SortOrder.ASC if http_sort.order == "asc" else SortOrder.DESC
            engine_sort = SortField(
                field=http_sort.field,
                order=sort_order
            )
            engine_sort_fields.append(engine_sort)
        
        # Convert includes (HTTP uses simple strings, engine needs RelationshipInclude objects)
        engine_includes = []
        for include_field in request.includes:
            relationship_include = RelationshipInclude(
                relation_field=include_field,
                target_database=None,  # Will be auto-detected by engine
                max_depth=1
            )
            engine_includes.append(relationship_include)
        
        # Convert pagination
        engine_pagination = QueryPagination(
            page=request.pagination.page,
            size=request.pagination.size
        )
        
        return StructuredQuery(
            database=request.database,
            filters=engine_filters,
            sort_fields=engine_sort_fields,
            includes=engine_includes,
            pagination=engine_pagination,
            distinct=request.distinct
        )
    
    def _build_pagination_links(
        self, 
        request: QueryRequest, 
        total_count: int
    ) -> Dict[str, str]:
        """Build HATEOAS pagination links."""
        base_url = "/api/v1/query/structured"
        current_page = request.pagination.page
        page_size = request.pagination.size
        total_pages = (total_count + page_size - 1) // page_size
        
        links = {
            "self": f"{base_url}?page={current_page}"
        }
        
        if current_page > 1:
            links["first"] = f"{base_url}?page=1"
            links["prev"] = f"{base_url}?page={current_page - 1}"
        
        if current_page < total_pages:
            links["next"] = f"{base_url}?page={current_page + 1}"
            links["last"] = f"{base_url}?page={total_pages}"
        
        return links
    
    async def _estimate_export_size(self, request: ExportRequest) -> int:
        """Estimate export file size in bytes."""
        # Estimate based on query complexity
        internal_query = self._build_internal_query(request.query)
        estimated_rows = self.optimizer.estimate_cost(internal_query)
        
        # Rough size estimation: avg 1KB per row for JSON, 0.5KB for CSV
        bytes_per_row = 1024 if request.format == "json" else 512
        estimated_size = int(estimated_rows * bytes_per_row)
        
        # Add overhead for headers, formatting, etc.
        overhead = max(4096, int(estimated_size * 0.1))  # 10% overhead, min 4KB
        
        return estimated_size + overhead
    
    def _check_export_quota(self, user: Dict[str, Any], size_bytes: int) -> bool:
        """Check if user has sufficient export quota."""
        # Get user's rate limit as a proxy for quota (higher rate = more quota)
        user_rate_limit = user.get("rate_limit", 60)
        
        # Admin users get higher quota
        if "admin" in user.get("scopes", []):
            max_size = 500 * 1024 * 1024  # 500MB for admins
        elif user_rate_limit >= 600:
            max_size = 100 * 1024 * 1024  # 100MB for high-rate users  
        else:
            max_size = 50 * 1024 * 1024   # 50MB for regular users
        
        return size_bytes <= max_size
    
    def _extract_match_snippet(self, result: Dict[str, Any], query_text: str) -> str:
        """Extract a snippet showing where the query text was found."""
        # Try to find the query text in various fields and extract context
        query_lower = query_text.lower()
        
        # Check properties for text content
        properties = result.get("properties", {})
        for prop_name, prop_value in properties.items():
            if isinstance(prop_value, dict):
                # Extract text from title or rich_text properties
                text_content = ""
                if "title" in prop_value and prop_value["title"]:
                    text_content = prop_value["title"][0].get("plain_text", "")
                elif "rich_text" in prop_value and prop_value["rich_text"]:
                    text_content = " ".join([rt.get("plain_text", "") for rt in prop_value["rich_text"]])
                
                if text_content and query_lower in text_content.lower():
                    # Extract snippet with context
                    text_lower = text_content.lower()
                    match_pos = text_lower.find(query_lower)
                    if match_pos != -1:
                        # Extract ~50 chars before and after the match
                        start_pos = max(0, match_pos - 50)
                        end_pos = min(len(text_content), match_pos + len(query_text) + 50)
                        snippet = text_content[start_pos:end_pos]
                        
                        # Add ellipsis if we truncated
                        if start_pos > 0:
                            snippet = "..." + snippet
                        if end_pos < len(text_content):
                            snippet = snippet + "..."
                        
                        return snippet
        
        # Fallback: return first bit of any text content found
        for prop_name, prop_value in properties.items():
            if isinstance(prop_value, dict):
                if "title" in prop_value and prop_value["title"]:
                    text = prop_value["title"][0].get("plain_text", "")
                    if text:
                        return text[:100] + ("..." if len(text) > 100 else "")
                elif "rich_text" in prop_value and prop_value["rich_text"]:
                    text = " ".join([rt.get("plain_text", "") for rt in prop_value["rich_text"]])
                    if text:
                        return text[:100] + ("..." if len(text) > 100 else "")
        
        return f"Match found for '{query_text}'"
    
    async def get_available_databases(self) -> List[Dict[str, Any]]:
        """Get list of available databases by scanning JSON cache directory."""
        databases = []
        cache_dir = Path("blackcore/models/json")
        
        if not cache_dir.exists():
            logger.warning(f"Cache directory not found: {cache_dir}")
            return databases
        
        # Scan for JSON files
        for json_file in cache_dir.glob("*.json"):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Skip empty files
                if not data:
                    continue
                
                # Extract database name from filename (convert back from file format)
                db_name = self._filename_to_database_name(json_file.stem)
                
                # Get sample record to analyze structure
                sample_record = data[0] if data else {}
                
                # Extract basic metadata
                record_count = len(data)
                
                # Get last modified time
                last_modified = datetime.fromtimestamp(json_file.stat().st_mtime)
                
                database_info = {
                    "name": db_name,
                    "filename": json_file.name,
                    "record_count": record_count,
                    "last_modified": last_modified.isoformat(),
                    "fields": self._extract_database_fields(sample_record),
                    "size_bytes": json_file.stat().st_size
                }
                
                databases.append(database_info)
                
            except (json.JSONDecodeError, FileNotFoundError, KeyError) as e:
                logger.warning(f"Failed to process database file {json_file}: {e}")
                continue
        
        # Sort by name for consistent ordering
        databases.sort(key=lambda x: x["name"])
        
        return databases
    
    def _filename_to_database_name(self, filename: str) -> str:
        """Convert filename back to proper database name."""
        # Reverse the conversion done in the engine: lower().replace(" ", "_").replace("&", "and")
        name = filename.replace("_", " ").replace("and", "&")
        
        # Capitalize properly - basic title case with some adjustments
        words = name.split()
        capitalized_words = []
        
        for word in words:
            if word.lower() in ["&", "and", "of", "the", "a", "an"]:
                capitalized_words.append(word.lower())
            else:
                capitalized_words.append(word.capitalize())
        
        # First word should always be capitalized
        if capitalized_words:
            capitalized_words[0] = capitalized_words[0].capitalize()
        
        return " ".join(capitalized_words)
    
    def _extract_database_fields(self, sample_record: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract field information from a sample record."""
        fields = []
        
        if not sample_record:
            return fields
        
        # Extract from properties if it's a Notion record
        properties = sample_record.get("properties", {})
        
        for field_name, field_data in properties.items():
            field_info = {
                "name": field_name,
                "type": self._detect_field_type(field_data),
                "filterable": True,  # Most fields are filterable
                "sortable": True     # Most fields are sortable
            }
            
            # Adjust based on field type
            if field_info["type"] in ["relation", "multi_select", "people"]:
                field_info["sortable"] = False  # Complex types typically not sortable
            
            fields.append(field_info)
        
        # Add some common Notion fields that might not be in properties
        if "id" in sample_record:
            fields.append({
                "name": "id",
                "type": "text",
                "filterable": True,
                "sortable": False
            })
        
        if "created_time" in sample_record:
            fields.append({
                "name": "created_time",
                "type": "date",
                "filterable": True,
                "sortable": True
            })
        
        if "last_edited_time" in sample_record:
            fields.append({
                "name": "last_edited_time",
                "type": "date",
                "filterable": True,
                "sortable": True
            })
        
        return fields
    
    def _detect_field_type(self, field_data: Any) -> str:
        """Detect field type from Notion property data."""
        if not isinstance(field_data, dict):
            return "text"
        
        # Check for specific Notion property types
        if "title" in field_data:
            return "text"
        elif "rich_text" in field_data:
            return "text"
        elif "number" in field_data:
            return "number"
        elif "select" in field_data:
            return "select"
        elif "multi_select" in field_data:
            return "multi_select"
        elif "date" in field_data:
            return "date"
        elif "checkbox" in field_data:
            return "checkbox"
        elif "url" in field_data:
            return "url"
        elif "email" in field_data:
            return "email"
        elif "phone_number" in field_data:
            return "phone"
        elif "relation" in field_data:
            return "relation"
        elif "people" in field_data:
            return "people"
        elif "files" in field_data:
            return "files"
        elif "formula" in field_data:
            return "formula"
        elif "rollup" in field_data:
            return "rollup"
        elif "created_time" in field_data:
            return "date"
        elif "created_by" in field_data:
            return "people"
        elif "last_edited_time" in field_data:
            return "date"
        elif "last_edited_by" in field_data:
            return "people"
        else:
            return "text"  # Default fallback