"""FastAPI application entry point with lifespan, correlation middleware, and error contracts."""

import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError
from starlette.exceptions import HTTPException as StarletteHTTPException

from askbase.api.routers import (
    auth_router,
    documents_router,
    health_router,
    qa_router,
    search_router,
    workspaces_router,
)
from askbase.core.errors import AppError
from askbase.core.logging import get_logger, request_id_var, setup_logging
from askbase.core.settings import get_settings
from askbase.db.engine import close_engine, get_engine

logger = get_logger("askbase")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifecycle context handling startup validation and graceful shutdown."""
    settings = get_settings()
    setup_logging(settings.LOG_LEVEL)
    logger.info(f"Starting AskBase in '{settings.ENVIRONMENT}' mode...")

    # Validate database engine initialization
    get_engine()
    yield

    # Graceful shutdown: close connection pool
    logger.info("Initiating graceful shutdown...")
    await close_engine()
    logger.info("AskBase shutdown complete.")


def create_app() -> FastAPI:
    """Application factory constructing FastAPI instance with middlewares and error handlers."""
    settings = get_settings()

    app = FastAPI(
        title="AskBase API",
        version="0.2.0",
        description="A permission-aware, evidence-grounded knowledge system",
        lifespan=lifespan,
    )

    # CORS configuration
    origins = [settings.CORS_ORIGIN] if settings.CORS_ORIGIN != "*" else ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request correlation middleware
    @app.middleware("http")
    async def request_correlation_middleware(request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        token = request_id_var.set(req_id)
        try:
            response = await call_next(request)
            response.headers["X-Request-ID"] = req_id
            return response
        finally:
            request_id_var.reset(token)

    # 1. Custom operational AppError handler
    @app.exception_handler(AppError)
    async def app_error_handler(_request: Request, exc: AppError):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    # 2. FastAPI Request Validation handler (standardize to 400 VALIDATION_ERROR)
    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(_request: Request, exc: RequestValidationError):
        details = []
        for err in exc.errors():
            loc = ".".join(str(x) for x in err.get("loc", []))
            details.append({"field": loc, "message": err.get("msg", "Invalid value")})

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request validation failed.",
                    "details": details,
                }
            },
        )

    # 3. HTTP status code exception handler (e.g. 404, 405)
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
        code_map = {
            404: "NOT_FOUND",
            405: "METHOD_NOT_ALLOWED",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
        }
        code = code_map.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": code,
                    "message": exc.detail or "The requested endpoint was not found.",
                }
            },
        )

    # 4. Database integrity error handler
    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(_request: Request, exc: IntegrityError):
        err_str = str(exc.orig).lower() if hasattr(exc, "orig") else str(exc).lower()
        if "unique" in err_str:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error": {
                        "code": "RESOURCE_CONFLICT",
                        "message": "A record with this identifier or unique attribute already exists.",
                    }
                },
            )
        elif "foreign key" in err_str or "foreignkey" in err_str:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "error": {
                        "code": "FOREIGN_KEY_VIOLATION",
                        "message": "Referenced entity does not exist or relation is constrained.",
                    }
                },
            )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "code": "DATABASE_INTEGRITY_ERROR",
                    "message": "Database constraint violation.",
                }
            },
        )

    # 5. Global unhandled error handler
    @app.exception_handler(Exception)
    async def generic_exception_handler(_request: Request, exc: Exception):
        logger.error(f"Unhandled internal server error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal error occurred.",
                }
            },
        )

    # Register routers
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(workspaces_router)
    app.include_router(documents_router)
    app.include_router(search_router)
    app.include_router(qa_router)

    return app


app = create_app()
