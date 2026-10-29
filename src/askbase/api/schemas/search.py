"""Search schemas."""

import uuid
from typing import Literal

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    """Search request query payload."""

    query: str = Field(min_length=1, max_length=500)
    mode: Literal["lexical", "semantic", "hybrid"] = "hybrid"
    limit: int = Field(default=10, ge=1, le=50)


class SearchHitResponse(BaseModel):
    """Individual search match with rich snippet and provenance."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    version_id: uuid.UUID
    version_number: int
    page_number: int | None = None
    section_heading: str | None = None
    snippet: str
    score: float
    search_mode: str


class SearchResponse(BaseModel):
    """Search results response wrapper."""

    query: str
    mode: str
    total: int
    results: list[SearchHitResponse]
