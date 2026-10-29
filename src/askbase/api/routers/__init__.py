"""API routers exports."""

from askbase.api.routers.auth import router as auth_router
from askbase.api.routers.documents import router as documents_router
from askbase.api.routers.health import router as health_router
from askbase.api.routers.qa import router as qa_router
from askbase.api.routers.search import router as search_router
from askbase.api.routers.workspaces import router as workspaces_router

__all__ = [
    "health_router",
    "auth_router",
    "workspaces_router",
    "documents_router",
    "search_router",
    "qa_router",
]
