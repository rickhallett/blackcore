#!/usr/bin/env python3
"""Simple FastAPI app for testing GUI integration without full configuration."""

import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import the simplified endpoints
from test_dashboard_endpoints import router as dashboard_router
from test_search_endpoints import router as search_router

def create_test_app():
    """Create a minimal FastAPI app for GUI testing."""
    app = FastAPI(
        title="Nassau Campaign Intelligence GUI Test API",
        version="1.0.0",
        description="Simplified API for testing GUI integration"
    )

    # Add CORS middleware for frontend access
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8501", "http://127.0.0.1:8501"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Health check endpoint
    @app.get("/health")
    async def health_check():
        return {"status": "healthy", "message": "GUI test API is running"}

    # Simple auth bypass for testing
    def mock_get_current_user():
        return {"user": "test-user", "role": "admin"}

    # Override the auth dependency in the routers
    dashboard_router.dependency_overrides = {}
    search_router.dependency_overrides = {}
    
    # Include routers without auth for testing
    app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
    app.include_router(search_router, prefix="/api/search", tags=["search"])

    return app

app = create_test_app()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)