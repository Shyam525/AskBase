# syntax=docker/dockerfile:1
FROM python:3.13-slim AS builder

WORKDIR /app

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:0.5.15 /uv /bin/uv

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specifications
COPY pyproject.toml uv.lock ./

# Install dependencies into virtual environment
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
RUN uv sync --frozen --no-install-project --no-dev

# Final runtime image
FROM python:3.13-slim

WORKDIR /app

# Create non-privileged service user
RUN groupadd -r askbase && useradd -r -g askbase -d /app -s /sbin/nologin askbase

# Copy installed virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy source code and configuration
COPY src /app/src
COPY alembic /app/alembic
COPY alembic.ini pyproject.toml ./

# Create persistent document storage directory with proper permissions
RUN mkdir -p /app/storage/documents && chown -R askbase:askbase /app

USER askbase

EXPOSE 5000

HEALTHCHECK --interval=10s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health/live')" || exit 1

CMD ["uvicorn", "askbase.main:app", "--host", "0.0.0.0", "--port", "5000"]
