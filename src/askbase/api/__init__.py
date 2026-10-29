"""API package exports."""

from askbase.api.routers import (
    auth_router,
    documents_router,
    health_router,
    qa_router,
    search_router,
    workspaces_router,
)

__all__ = [
    "health_router",
    "auth_router",
    "workspaces_router",
    "documents_router",
    "search_router",
    "qa_router",
]
