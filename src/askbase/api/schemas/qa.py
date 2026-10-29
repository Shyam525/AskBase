"""Question answering and citation schemas."""

import uuid

from pydantic import BaseModel, Field


class AskQuestionRequest(BaseModel):
    """Grounded question request."""

    question: str = Field(min_length=1, max_length=1000)


class CitationResponse(BaseModel):
    """Verifiable citation referencing document version, page, and section."""

    citation_id: int
    document_id: uuid.UUID
    document_title: str
    version_id: uuid.UUID
    version_number: int
    page_number: int | None = None
    section_heading: str | None = None
    cited_text: str


class AskQuestionResponse(BaseModel):
    """Evidence-grounded answer response."""

    question: str
    answer: str
    abstained: bool
    evidence_score: float
    citations: list[CitationResponse]
