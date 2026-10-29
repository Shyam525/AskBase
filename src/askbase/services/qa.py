"""Grounded Question Answering service with verifiable citations and abstention."""

import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from askbase.ai.base import GroundedAnswerResult, GroundedPassage, LLMProvider
from askbase.ai.providers import get_llm_provider
from askbase.core.settings import get_settings
from askbase.retrieval.search import RetrievalEngine


class QAService:
    """Answers user queries grounded strictly in workspace document evidence."""

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: LLMProvider | None = None,
    ) -> None:
        self.session = session
        self.retrieval = RetrievalEngine(session)
        self.llm_provider = llm_provider or get_llm_provider()
        self.settings = get_settings()

    async def answer_question(
        self,
        workspace_id: uuid.UUID,
        question: str,
    ) -> GroundedAnswerResult:
        """Retrieve evidence passages and synthesize an answer with citations or abstain."""
        clean_q = question.strip()
        if not clean_q:
            return GroundedAnswerResult(
                question=question,
                answer="Question cannot be empty.",
                abstained=True,
                evidence_score=0.0,
                citations=[],
            )

        # 1. Retrieve most relevant passages in workspace
        hits = await self.retrieval.search(
            workspace_id=workspace_id,
            query=clean_q,
            mode="hybrid",
            limit=5,
        )

        passages = [
            GroundedPassage(
                chunk_id=h.chunk_id,
                document_id=h.document_id,
                document_title=h.document_title,
                version_id=h.version_id,
                version_number=h.version_number,
                page_number=h.page_number,
                section_heading=h.section_heading,
                text=h.snippet,
                relevance_score=h.score,
            )
            for h in hits
        ]

        # 2. Synthesize answer using grounded LLM provider
        return await self.llm_provider.generate_grounded_answer(
            question=clean_q,
            passages=passages,
            evidence_threshold=self.settings.EVIDENCE_MIN_SIMILARITY,
        )
