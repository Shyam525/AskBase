"""Interfaces for AI embeddings and grounded answer generation."""

import uuid
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class GroundedPassage:
    """Retrieved passage passed into grounded answer generation."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    version_id: uuid.UUID
    version_number: int
    page_number: int | None
    section_heading: str | None
    text: str
    relevance_score: float


@dataclass(frozen=True)
class Citation:
    """Verifiable citation referencing the exact document version and location."""

    citation_id: int
    document_id: uuid.UUID
    document_title: str
    version_id: uuid.UUID
    version_number: int
    page_number: int | None
    section_heading: str | None
    cited_text: str


@dataclass(frozen=True)
class GroundedAnswerResult:
    """Result of grounded synthesis with abstention and citation indicators."""

    question: str
    answer: str
    abstained: bool
    evidence_score: float
    citations: list[Citation] = field(default_factory=list)


@runtime_checkable
class EmbeddingProvider(Protocol):
    """Protocol for vector embedding models."""

    @property
    def name(self) -> str:
        """Provider name identifier."""
        ...

    @property
    def dimension(self) -> int:
        """Dimensionality of the vector space."""
        ...

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Batch generate embeddings for multiple texts."""
        ...

    async def embed_query(self, query: str) -> list[float]:
        """Generate embedding vector for a single search query."""
        ...


@runtime_checkable
class LLMProvider(Protocol):
    """Protocol for evidence-grounded answer generation models."""

    @property
    def name(self) -> str:
        """Provider name identifier."""
        ...

    async def generate_grounded_answer(
        self,
        question: str,
        passages: list[GroundedPassage],
        evidence_threshold: float = 0.15,
    ) -> GroundedAnswerResult:
        """Synthesize answer grounded strictly in passages, or abstain if insufficient."""
        ...
