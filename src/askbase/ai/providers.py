"""Implementations of embedding and grounded LLM providers."""

import hashlib
import math
import re

from askbase.ai.base import (
    Citation,
    EmbeddingProvider,
    GroundedAnswerResult,
    GroundedPassage,
    LLMProvider,
)
from askbase.core.settings import get_settings


class FakeEmbeddingProvider:
    """Deterministic, self-contained pseudo-embedding provider for testing and offline execution.

    Generates a 64-dimensional unit vector based on hashed n-grams, enabling genuine
    cosine similarity computations without external models or network access.
    """

    def __init__(self, dimension: int = 64) -> None:
        self._dim = dimension

    @property
    def name(self) -> str:
        return "fake-hash-embedding"

    @property
    def dimension(self) -> int:
        return self._dim

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dim
        words = re.findall(r"\w+", text.lower())
        if not words:
            return vec

        for word in words:
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self._dim
            sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
            vec[idx] += sign

        # Compute L2 norm
        norm = math.sqrt(sum(x * x for x in vec))
        if norm > 0:
            vec = [round(x / norm, 6) for x in vec]
        return vec

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    async def embed_query(self, query: str) -> list[float]:
        return self._embed(query)


class NoopEmbeddingProvider:
    """Disabled embedding provider."""

    @property
    def name(self) -> str:
        return "none"

    @property
    def dimension(self) -> int:
        return 0

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return [[] for _ in texts]

    async def embed_query(self, query: str) -> list[float]:
        return []


class ExtractiveGroundedSynthesizer:
    """Evidence-grounded synthesizer that answers questions strictly from retrievable passages.

    Enforces mandatory abstention when available evidence is insufficient.
    """

    @property
    def name(self) -> str:
        return "extractive-grounded-synthesizer"

    async def generate_grounded_answer(
        self,
        question: str,
        passages: list[GroundedPassage],
        evidence_threshold: float = 0.15,
    ) -> GroundedAnswerResult:
        """Synthesize answer with verifiable citations or abstain if evidence is insufficient."""
        if not passages:
            return GroundedAnswerResult(
                question=question,
                answer="I cannot answer this question based on the provided documents. Sufficient evidence was not found.",
                abstained=True,
                evidence_score=0.0,
                citations=[],
            )

        STOPWORDS = {
            "a",
            "an",
            "the",
            "and",
            "or",
            "but",
            "if",
            "because",
            "as",
            "what",
            "which",
            "this",
            "that",
            "these",
            "those",
            "then",
            "just",
            "so",
            "than",
            "such",
            "both",
            "through",
            "about",
            "for",
            "is",
            "of",
            "while",
            "during",
            "to",
            "from",
            "in",
            "out",
            "on",
            "off",
            "over",
            "under",
            "again",
            "further",
            "once",
            "here",
            "there",
            "when",
            "where",
            "why",
            "how",
            "all",
            "any",
            "each",
            "few",
            "more",
            "most",
            "other",
            "some",
            "no",
            "nor",
            "not",
            "only",
            "own",
            "same",
            "too",
            "very",
            "can",
            "will",
            "should",
            "now",
            "are",
            "was",
            "were",
            "been",
            "being",
            "have",
            "has",
            "had",
            "having",
            "do",
            "does",
            "did",
            "doing",
            "would",
            "could",
            "you",
            "your",
            "they",
            "their",
            "we",
            "our",
            "per",
            "with",
            "into",
        }
        q_words = {w for w in re.findall(r"\w{3,}", question.lower()) if w not in STOPWORDS}
        if not q_words:
            q_words = set(re.findall(r"\w{2,}", question.lower()))

        # Evaluate token overlap and evidence presence across passages
        min_required_overlap = min(2, len(q_words)) if len(q_words) >= 2 else 1

        matching_passages: list[tuple[GroundedPassage, int]] = []
        for p in passages:
            p_words = set(re.findall(r"\w+", p.text.lower()))
            overlap = q_words.intersection(p_words)
            if len(overlap) >= min_required_overlap:
                matching_passages.append((p, len(overlap)))

        # If no passages meet minimum evidence threshold, ABSTAIN
        if not matching_passages:
            return GroundedAnswerResult(
                question=question,
                answer="I cannot answer this question based on the provided documents. Sufficient evidence was not found.",
                abstained=True,
                evidence_score=0.0,
                citations=[],
            )

        # Sort matching passages by keyword overlap descending
        matching_passages.sort(key=lambda x: (x[1], x[0].relevance_score), reverse=True)
        top_passage, _ = matching_passages[0]

        # Extract and rank sentences across matching passages
        candidate_sentences: list[tuple[str, int, GroundedPassage]] = []
        for p, _ in matching_passages[:3]:
            sentences = re.split(r"(?<=[.!?\n])\s+", p.text)
            for s in sentences:
                clean_s = s.strip()
                if len(clean_s) > 10:
                    s_words = set(re.findall(r"\w+", clean_s.lower()))
                    s_overlap = len(q_words.intersection(s_words))
                    if s_overlap > 0:
                        candidate_sentences.append((clean_s, s_overlap, p))

        # Sort sentences by keyword overlap descending so the most specific answer comes first
        candidate_sentences.sort(key=lambda x: x[1], reverse=True)

        citations: list[Citation] = []
        answer_parts: list[str] = []
        citation_id = 1
        seen_sentences: set[str] = set()

        for s_text, _, p in candidate_sentences[:3]:
            if s_text in seen_sentences:
                continue
            seen_sentences.add(s_text)
            answer_parts.append(f"{s_text} [{citation_id}]")
            citations.append(
                Citation(
                    citation_id=citation_id,
                    document_id=p.document_id,
                    document_title=p.document_title,
                    version_id=p.version_id,
                    version_number=p.version_number,
                    page_number=p.page_number,
                    section_heading=p.section_heading,
                    cited_text=s_text,
                )
            )
            citation_id += 1

        if not citations:
            return GroundedAnswerResult(
                question=question,
                answer="I cannot answer this question based on the provided documents. Sufficient evidence was not found.",
                abstained=True,
                evidence_score=0.0,
                citations=[],
            )

        answer_text = " ".join(answer_parts)

        return GroundedAnswerResult(
            question=question,
            answer=answer_text,
            abstained=False,
            evidence_score=round(top_passage.relevance_score, 4),
            citations=citations,
        )


def get_embedding_provider() -> EmbeddingProvider:
    """Factory creating configured embedding provider."""
    settings = get_settings()
    if settings.EMBEDDING_PROVIDER == "none":
        return NoopEmbeddingProvider()
    return FakeEmbeddingProvider()


def get_llm_provider() -> LLMProvider:
    """Factory creating configured LLM provider."""
    return ExtractiveGroundedSynthesizer()
