
"""Main FastAPI application for TripMate AI."""

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.core.logging import configure_logging

settings = get_settings()

configure_logging()

app = FastAPI(
    title=settings.app_name,
    description="AI-powered multi-agent travel planning platform.",
    version="0.1.0",
    debug=settings.debug,
)

# Register all API endpoints under the configured API prefix.
app.include_router(
    api_router,
    prefix=settings.api_v1_prefix,
)


@app.get("/", tags=["Root"])
def root() -> dict[str, str]:
    """Return basic application information."""
    return {
        "app_name": settings.app_name,
        "environment": settings.app_env,
        "message": "TripMate AI API is running",
    }
