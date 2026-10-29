"""Evidence-grounded question answering router."""

import uuid

from fastapi import APIRouter

from askbase.api.deps import DBSession, WorkspaceMember
from askbase.api.schemas.qa import (
    AskQuestionRequest,
    AskQuestionResponse,
    CitationResponse,
)
from askbase.services.qa import QAService

router = APIRouter(prefix="/api/workspaces/{workspace_id}", tags=["Question Answering"])


@router.post("/ask", response_model=AskQuestionResponse)
async def ask_question(
    workspace_id: uuid.UUID,
    req: AskQuestionRequest,
    _membership: WorkspaceMember,
    db: DBSession,
):
    """Answer questions grounded strictly in workspace document evidence with verifiable citations."""
    service = QAService(db)
    result = await service.answer_question(
        workspace_id=workspace_id,
        question=req.question,
    )

    return AskQuestionResponse(
        question=result.question,
        answer=result.answer,
        abstained=result.abstained,
        evidence_score=result.evidence_score,
        citations=[
            CitationResponse(
                citation_id=c.citation_id,
                document_id=c.document_id,
                document_title=c.document_title,
                version_id=c.version_id,
                version_number=c.version_number,
                page_number=c.page_number,
                section_heading=c.section_heading,
                cited_text=c.cited_text,
            )
            for c in result.citations
        ],
    )
