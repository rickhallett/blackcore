"""Query engine HTTP endpoints."""

from typing import Dict, Any, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Security, status, Query
from fastapi.responses import StreamingResponse
import structlog

from .auth import get_current_user, rate_limiter
from .query_models import (
    QueryRequest, QueryResponse, TextSearchRequest, TextSearchResponse,
    ExportRequest, ExportJob, QueryEstimateRequest, QueryEstimateResponse,
    QueryStatsResponse
)
from .query_service import QueryService


logger = structlog.get_logger()

# Create router
router = APIRouter(prefix="/api/v1/query", tags=["Query Engine"])

# Initialize query service (would be injected in production)
query_service = QueryService()


@router.post(
    "/structured",
    response_model=QueryResponse,
    summary="Execute structured query",
    description="Execute a structured query with filters, sorting, and pagination",
    dependencies=[Depends(rate_limiter.rate_limit_dependency)]
)
async def execute_structured_query(
    request: QueryRequest,
    current_user: Dict[str, Any] = Security(get_current_user)
) -> QueryResponse:
    """Execute a structured query against a database."""
    logger.info(
        "Structured query request",
        database=request.database,
        user_id=current_user.get("sub")
    )
    
    try:
        result = await query_service.execute_query(request, current_user)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query execution failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Query execution failed"
        )


@router.post(
    "/search",
    response_model=TextSearchResponse,
    summary="Text search",
    description="Perform full-text search across one or more databases",
    dependencies=[Depends(rate_limiter.rate_limit_dependency)]
)
async def text_search(
    request: TextSearchRequest,
    current_user: Dict[str, Any] = Security(get_current_user)
) -> TextSearchResponse:
    """Search for text across databases."""
    logger.info(
        "Text search request",
        query=request.query_text[:50],  # Log first 50 chars
        user_id=current_user.get("sub")
    )
    
    try:
        result = await query_service.text_search(request, current_user)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Text search failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Text search failed"
        )


@router.post(
    "/export",
    response_model=ExportJob,
    summary="Create export job",
    description="Create an asynchronous export job for query results",
    dependencies=[Depends(rate_limiter.rate_limit_dependency)]
)
async def create_export(
    request: ExportRequest,
    current_user: Dict[str, Any] = Security(get_current_user)
) -> ExportJob:
    """Create an export job for query results."""
    logger.info(
        "Export job creation request",
        database=request.query.database,
        format=request.format,
        user_id=current_user.get("sub")
    )
    
    try:
        job = await query_service.create_export(request, current_user)
        
        # Add links to response
        job.download_url = f"/api/v1/query/export/{job.job_id}/download"
        
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export creation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export creation failed"
        )


@router.get(
    "/export/{job_id}",
    response_model=ExportJob,
    summary="Get export job status",
    description="Get the status of an export job"
)
async def get_export_status(
    job_id: str,
    current_user: Dict[str, Any] = Security(get_current_user)
) -> ExportJob:
    """Get export job status."""
    logger.info(
        "Export status request",
        job_id=job_id,
        user_id=current_user.get("sub")
    )
    
    try:
        job = await query_service.get_export_status(job_id, current_user)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found"
            )
        
        return job
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export status retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get export status"
        )


@router.get(
    "/export/{job_id}/download",
    summary="Download export file",
    description="Download the exported file (available after job completion)"
)
async def download_export(
    job_id: str,
    current_user: Dict[str, Any] = Security(get_current_user)
) -> StreamingResponse:
    """Download export file."""
    logger.info(
        "Export download request",
        job_id=job_id,
        user_id=current_user.get("sub")
    )
    
    try:
        # Get job status first
        job = await query_service.get_export_status(job_id, current_user)
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Export job not found"
            )
        
        if job.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Export not ready. Current status: {job.status}"
            )
        
        # Get file stream
        file_stream = await query_service.download_export(job_id, current_user)
        
        # Determine content type based on format
        content_types = {
            "csv": "text/csv",
            "json": "application/json",
            "jsonl": "application/x-ndjson",
            "excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "parquet": "application/octet-stream",
            "tsv": "text/tab-separated-values"
        }
        
        content_type = content_types.get(job.format, "application/octet-stream")
        filename = f"export_{job_id}.{job.format}"
        
        return StreamingResponse(
            file_stream,
            media_type=content_type,
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Export download failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Export download failed"
        )


@router.post(
    "/estimate",
    response_model=QueryEstimateResponse,
    summary="Estimate query cost",
    description="Estimate the cost and performance of a query before execution"
)
async def estimate_query(
    request: QueryEstimateRequest,
    current_user: Dict[str, Any] = Security(get_current_user)
) -> QueryEstimateResponse:
    """Estimate query cost and performance."""
    logger.info(
        "Query estimation request",
        database=request.database,
        user_id=current_user.get("sub")
    )
    
    try:
        estimate = await query_service.estimate_query(request, current_user)
        return estimate
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Query estimation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Query estimation failed"
        )


@router.get(
    "/stats",
    response_model=QueryStatsResponse,
    summary="Get query statistics",
    description="Get query engine performance statistics"
)
async def get_query_statistics(
    current_user: Dict[str, Any] = Security(get_current_user)
) -> QueryStatsResponse:
    """Get query engine statistics."""
    logger.info(
        "Query statistics request",
        user_id=current_user.get("sub")
    )
    
    try:
        stats = await query_service.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"Statistics retrieval failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get statistics"
        )


@router.get(
    "/databases",
    summary="List available databases",
    description="Get list of databases available for querying"
)
async def list_databases(
    current_user: Dict[str, Any] = Security(get_current_user)
) -> Dict[str, Any]:
    """List available databases."""
    # TODO: Get actual database list from configuration
    databases = [
        {
            "name": "People & Contacts",
            "entity_type": "people",
            "description": "Individual contacts and relationships"
        },
        {
            "name": "Organizations & Bodies",
            "entity_type": "organizations",
            "description": "Organizations and institutional entities"
        },
        {
            "name": "Actionable Tasks",
            "entity_type": "tasks",
            "description": "Tasks and action items"
        },
        {
            "name": "Intelligence & Transcripts",
            "entity_type": "intelligence",
            "description": "Intelligence reports and meeting transcripts"
        },
        {
            "name": "Documents & Evidence",
            "entity_type": "documents",
            "description": "Documents and evidence files"
        }
    ]
    
    return {
        "databases": databases,
        "total": len(databases)
    }


@router.get(
    "/fields/{database}",
    summary="Get database fields",
    description="Get available fields for a specific database"
)
async def get_database_fields(
    database: str,
    current_user: Dict[str, Any] = Security(get_current_user)
) -> Dict[str, Any]:
    """Get fields available in a database."""
    # TODO: Get actual fields from database schema
    
    # Placeholder field definitions
    field_mappings = {
        "People & Contacts": [
            {"name": "Full Name", "type": "text", "filterable": True, "sortable": True},
            {"name": "Organization", "type": "relation", "filterable": True, "sortable": False},
            {"name": "Role", "type": "text", "filterable": True, "sortable": True},
            {"name": "Email", "type": "email", "filterable": True, "sortable": False},
            {"name": "Date Created", "type": "date", "filterable": True, "sortable": True}
        ],
        "Actionable Tasks": [
            {"name": "Title", "type": "text", "filterable": True, "sortable": True},
            {"name": "Status", "type": "select", "filterable": True, "sortable": True},
            {"name": "Assignee", "type": "relation", "filterable": True, "sortable": False},
            {"name": "Due Date", "type": "date", "filterable": True, "sortable": True},
            {"name": "Priority", "type": "select", "filterable": True, "sortable": True}
        ]
    }
    
    fields = field_mappings.get(database, [])
    
    if not fields:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Database '{database}' not found"
        )
    
    return {
        "database": database,
        "fields": fields,
        "total": len(fields)
    }