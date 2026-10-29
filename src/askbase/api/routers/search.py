"""Search endpoint router."""

import uuid
from typing import Literal

from fastapi import APIRouter, Query

from askbase.api.deps import DBSession, WorkspaceMember
from askbase.api.schemas.search import (
    SearchHitResponse,
    SearchRequest,
    SearchResponse,
)
from askbase.retrieval.search import RetrievalEngine

router = APIRouter(prefix="/api/workspaces/{workspace_id}/search", tags=["Search"])


@router.post("", response_model=SearchResponse)
async def search_workspace_post(
    workspace_id: uuid.UUID,
    req: SearchRequest,
    _membership: WorkspaceMember,
    db: DBSession,
):
    """Search documents in workspace using lexical, semantic, or hybrid retrieval."""
    engine = RetrievalEngine(db)
    hits = await engine.search(
        workspace_id=workspace_id,
        query=req.query,
        mode=req.mode,
        limit=req.limit,
    )
    return SearchResponse(
        query=req.query,
        mode=req.mode,
        total=len(hits),
        results=[
            SearchHitResponse(
                chunk_id=h.chunk_id,
                document_id=h.document_id,
                document_title=h.document_title,
                version_id=h.version_id,
                version_number=h.version_number,
                page_number=h.page_number,
                section_heading=h.section_heading,
                snippet=h.snippet,
                score=h.score,
                search_mode=h.search_mode,
            )
            for h in hits
        ],
    )


@router.get("", response_model=SearchResponse)
async def search_workspace_get(
    workspace_id: uuid.UUID,
    _membership: WorkspaceMember,
    db: DBSession,
    q: str = Query(..., min_length=1, max_length=500),
    mode: Literal["lexical", "semantic", "hybrid"] = Query("hybrid"),
    limit: int = Query(10, ge=1, le=50),
):
    """GET query parameter search endpoint."""
    engine = RetrievalEngine(db)
    hits = await engine.search(
        workspace_id=workspace_id,
        query=q,
        mode=mode,
        limit=limit,
    )
    return SearchResponse(
        query=q,
        mode=mode,
        total=len(hits),
        results=[
            SearchHitResponse(
                chunk_id=h.chunk_id,
                document_id=h.document_id,
                document_title=h.document_title,
                version_id=h.version_id,
                version_number=h.version_number,
                page_number=h.page_number,
                section_heading=h.section_heading,
                snippet=h.snippet,
                score=h.score,
                search_mode=h.search_mode,
            )
            for h in hits
        ],
    )
