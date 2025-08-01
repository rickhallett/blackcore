"""FastAPI application for the Query Engine API."""

from fastapi import FastAPI, HTTPException, Depends, Query as QueryParam, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from typing import List, Optional, Dict, Any
import time
import logging
from pathlib import Path
import asyncio

from .models import (
    QueryRequest, QueryResponse, GraphQueryRequest, GraphQueryResponse,
    TextSearchRequest, TextSearchResponse, SystemStatusResponse,
    ErrorResponse, DatabaseInfo, EntityResponse, TextSearchResult
)
from .auth import get_current_api_key, RateLimiter
from .search_api import router as search_router
from .analytics_api import router as analytics_router
from ..interfaces import QueryEngine, QueryEngineFactory
from ..models import (
    StructuredQuery, QueryFilter, SortField, RelationshipInclude,
    QueryPagination, GraphQuery, QueryError, QueryValidationError
)

logger = logging.getLogger(__name__)


def create_app(
    cache_dir: str = "blackcore/models/json",
    enable_caching: bool = True,
    enable_auth: bool = True
) -> FastAPI:
    """Create and configure the FastAPI application.
    
    Args:
        cache_dir: Directory containing JSON database files
        enable_caching: Enable query result caching
        enable_auth: Enable API key authentication
        
    Returns:
        Configured FastAPI application
    """
    
    app = FastAPI(
        title="BlackCore Query Engine API",
        description="High-performance API for querying the BlackCore knowledge graph",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize query engine
    query_engine = QueryEngineFactory.create_structured_executor(
        cache_dir=cache_dir,
        enable_caching=enable_caching,
        enable_optimization=True
    )
    
    # Initialize rate limiter
    rate_limiter = RateLimiter(requests_per_minute=60)
    
    # Include routers
    app.include_router(search_router)
    app.include_router(analytics_router)
    
    # Dependency injection
    def get_query_engine() -> QueryEngine:
        return QueryEngine(structured_executor=query_engine)
    
    async def check_rate_limit(
        request: Request,
        api_key: str = Depends(get_current_api_key if enable_auth else lambda: "anonymous")
    ):
        """Check rate limit for API key."""
        if not await rate_limiter.check_limit(api_key):
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later."
            )
    
    # Exception handlers
    @app.exception_handler(QueryValidationError)
    async def validation_error_handler(request: Request, exc: QueryValidationError):
        return JSONResponse(
            status_code=400,
            content=ErrorResponse(
                error="validation_error",
                message=str(exc),
                details={"query": exc.query} if hasattr(exc, 'query') else None
            ).dict()
        )
    
    @app.exception_handler(QueryError)
    async def query_error_handler(request: Request, exc: QueryError):
        return JSONResponse(
            status_code=500,
            content=ErrorResponse(
                error="query_error",
                message=str(exc),
                details={"query": exc.query} if hasattr(exc, 'query') else None
            ).dict()
        )
    
    # Health check
    @app.get("/health", tags=["System"])
    async def health_check():
        """Check API health status."""
        return {"status": "healthy", "timestamp": time.time()}
    
    # System status
    @app.get("/status", response_model=SystemStatusResponse, tags=["System"])
    async def get_system_status(
        query_engine: QueryEngine = Depends(get_query_engine)
    ):
        """Get detailed system status including available databases."""
        try:
            # Get available databases
            available_dbs = query_engine.structured_executor.data_loader.get_available_databases()
            
            databases = []
            for db_name in available_dbs:
                try:
                    stats = query_engine.structured_executor.data_loader.get_database_stats(db_name)
                    data = query_engine.structured_executor.data_loader.load_database(db_name)
                    
                    # Extract available fields from first record
                    fields = []
                    if data:
                        fields = list(data[0].keys())
                    
                    databases.append(DatabaseInfo(
                        name=db_name,
                        record_count=len(data),
                        last_updated=None,  # Could extract from file stats
                        available_fields=fields,
                        indexed_fields=["id", "created_time"]  # Default indexed fields
                    ))
                except Exception as e:
                    logger.error(f"Error loading database {db_name}: {e}")
            
            return SystemStatusResponse(
                status="healthy",
                version="1.0.0",
                databases=databases,
                cache_status={
                    "enabled": enable_caching,
                    "type": "memory" if enable_caching else "none"
                },
                performance_metrics={
                    "avg_query_time_ms": 0.0  # TODO: Track actual metrics
                }
            )
        except Exception as e:
            logger.error(f"Error getting system status: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Main query endpoint
    @app.post(
        "/query", 
        response_model=QueryResponse,
        tags=["Query"],
        dependencies=[Depends(check_rate_limit)]
    )
    async def execute_query(
        request: QueryRequest,
        query_engine: QueryEngine = Depends(get_query_engine)
    ):
        """Execute a structured query against the knowledge graph.
        
        This endpoint supports:
        - Complex filtering with multiple operators
        - Multi-field sorting
        - Relationship traversal
        - Pagination
        - Caching for performance
        """
        try:
            # Convert API models to internal models
            filters = [
                QueryFilter(
                    field=f.field,
                    operator=f.operator,
                    value=f.value,
                    case_sensitive=f.case_sensitive
                )
                for f in request.filters
            ]
            
            sort_fields = [
                SortField(field=s.field, order=s.order)
                for s in request.sort
            ]
            
            includes = [
                RelationshipInclude(
                    relation_field=i.relation_field,
                    target_database=i.target_database,
                    filters=[
                        QueryFilter(
                            field=f.field,
                            operator=f.operator,
                            value=f.value,
                            case_sensitive=f.case_sensitive
                        )
                        for f in i.filters
                    ],
                    max_depth=i.max_depth
                )
                for i in request.includes
            ]
            
            # Build internal query
            query = StructuredQuery(
                database=request.database,
                filters=filters,
                sort_fields=sort_fields,
                includes=includes,
                pagination=QueryPagination(
                    page=request.pagination.page,
                    size=request.pagination.size
                ),
                distinct=request.distinct
            )
            
            # Execute query
            result = await asyncio.to_thread(
                query_engine.execute_structured_query, query
            )
            
            # Convert to API response
            entities = [
                EntityResponse(
                    id=item.get("id", ""),
                    database=request.database,
                    properties=item.get("properties", {}),
                    created_time=item.get("created_time", ""),
                    last_edited_time=item.get("last_edited_time", ""),
                    url=item.get("url")
                )
                for item in result.data
            ]
            
            return QueryResponse(
                data=entities,
                total_count=result.total_count,
                page=result.page,
                page_size=result.page_size,
                total_pages=result.total_pages,
                execution_time_ms=result.execution_time_ms,
                from_cache=result.from_cache
            )
            
        except QueryValidationError:
            raise
        except Exception as e:
            logger.error(f"Query execution error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Text search endpoint
    @app.post(
        "/search",
        response_model=TextSearchResponse,
        tags=["Search"],
        dependencies=[Depends(check_rate_limit)]
    )
    async def text_search(
        request: TextSearchRequest,
        query_engine: QueryEngine = Depends(get_query_engine)
    ):
        """Perform text search across databases.
        
        Search for entities containing the query text in any text field.
        Supports fuzzy matching and field-specific search.
        """
        try:
            start_time = time.time()
            
            # Execute search
            results = await asyncio.to_thread(
                query_engine.text_search,
                query_text=request.query,
                databases=request.databases
            )
            
            # Limit results
            results = results[:request.max_results]
            
            # Convert to API response
            search_results = []
            for item in results:
                # Extract matched fields (simplified - would need actual implementation)
                matched_fields = []
                for key, value in item.get("properties", {}).items():
                    if isinstance(value, str) and request.query.lower() in value.lower():
                        matched_fields.append(f"properties.{key}")
                
                search_results.append(TextSearchResult(
                    entity=EntityResponse(
                        id=item.get("id", ""),
                        database=item.get("_database", ""),
                        properties=item.get("properties", {}),
                        created_time=item.get("created_time", ""),
                        last_edited_time=item.get("last_edited_time", ""),
                        url=item.get("url"),
                        _score=item.get("_score", 0.0)
                    ),
                    matched_fields=matched_fields,
                    score=item.get("_score", 0.0)
                ))
            
            execution_time = (time.time() - start_time) * 1000
            
            return TextSearchResponse(
                results=search_results,
                total_count=len(results),
                query=request.query,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"Search error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # List databases endpoint
    @app.get(
        "/databases",
        response_model=List[DatabaseInfo],
        tags=["Metadata"]
    )
    async def list_databases(
        query_engine: QueryEngine = Depends(get_query_engine)
    ):
        """List all available databases with metadata."""
        try:
            databases = []
            available_dbs = query_engine.structured_executor.data_loader.get_available_databases()
            
            for db_name in available_dbs:
                try:
                    stats = query_engine.structured_executor.data_loader.get_database_stats(db_name)
                    databases.append(DatabaseInfo(
                        name=db_name,
                        record_count=stats.get("record_count", 0),
                        last_updated=None,
                        available_fields=[],
                        indexed_fields=["id", "created_time"]
                    ))
                except Exception as e:
                    logger.error(f"Error getting stats for {db_name}: {e}")
            
            return databases
            
        except Exception as e:
            logger.error(f"Error listing databases: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Get database schema endpoint
    @app.get(
        "/databases/{database_name}/schema",
        response_model=Dict[str, Any],
        tags=["Metadata"]
    )
    async def get_database_schema(
        database_name: str,
        query_engine: QueryEngine = Depends(get_query_engine)
    ):
        """Get schema information for a specific database."""
        try:
            # Load a sample record to infer schema
            data = query_engine.structured_executor.data_loader.load_database(database_name)
            
            if not data:
                raise HTTPException(
                    status_code=404,
                    detail=f"Database '{database_name}' is empty or not found"
                )
            
            # Analyze first few records to determine schema
            schema = {}
            sample_size = min(10, len(data))
            
            for record in data[:sample_size]:
                for key, value in record.items():
                    if key not in schema:
                        schema[key] = {
                            "type": type(value).__name__ if value is not None else "null",
                            "nullable": False,
                            "examples": []
                        }
                    
                    if value is None:
                        schema[key]["nullable"] = True
                    elif len(schema[key]["examples"]) < 3 and value not in schema[key]["examples"]:
                        schema[key]["examples"].append(value)
            
            return {
                "database": database_name,
                "record_count": len(data),
                "fields": schema
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting database schema: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Batch query endpoint
    @app.post(
        "/query/batch",
        response_model=List[QueryResponse],
        tags=["Query"],
        dependencies=[Depends(check_rate_limit)]
    )
    async def execute_batch_queries(
        requests: List[QueryRequest],
        query_engine: QueryEngine = Depends(get_query_engine)
    ):
        """Execute multiple queries in a single request.
        
        Useful for dashboard applications that need data from multiple sources.
        Queries are executed in parallel for better performance.
        """
        if len(requests) > 10:
            raise HTTPException(
                status_code=400,
                detail="Maximum 10 queries allowed in a single batch"
            )
        
        # Execute queries in parallel
        tasks = []
        for req in requests:
            tasks.append(execute_query(req, query_engine))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle any exceptions
        responses = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                # Return error response for failed query
                responses.append(QueryResponse(
                    data=[],
                    total_count=0,
                    page=1,
                    page_size=requests[i].pagination.size,
                    total_pages=0,
                    execution_time_ms=0.0,
                    from_cache=False
                ))
            else:
                responses.append(result)
        
        return responses
    
    return app


# Create default app instance
app = create_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)