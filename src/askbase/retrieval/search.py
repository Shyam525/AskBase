"""Search retrieval engine supporting lexical, semantic, and hybrid ranking modes."""

import math
import re
import uuid
from dataclasses import dataclass
from typing import Literal

from sqlalchemy.ext.asyncio import AsyncSession

from askbase.ai.base import EmbeddingProvider
from askbase.ai.providers import get_embedding_provider
from askbase.models.chunk import DocumentChunk
from askbase.repositories.chunk import ChunkRepository


@dataclass(frozen=True)
class SearchResult:
    """Standardized search hit with rich snippet and provenance metadata."""

    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    version_id: uuid.UUID
    version_number: int
    page_number: int | None
    section_heading: str | None
    snippet: str
    score: float
    search_mode: Literal["lexical", "semantic", "hybrid"]


def cosine_similarity(vec_a: list[float], vec_b: list[float]) -> float:
    """Compute cosine similarity between two float vectors."""
    if not vec_a or not vec_b or len(vec_a) != len(vec_b):
        return 0.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b, strict=False))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def make_snippet(text: str, query: str, max_chars: int = 240) -> str:
    """Generate a contextual window around query term matches."""
    q_words = re.findall(r"\w+", query.lower())
    clean_text = " ".join(text.split())

    best_idx = -1
    for word in q_words:
        idx = clean_text.lower().find(word)
        if idx != -1:
            best_idx = idx
            break

    if best_idx == -1:
        return clean_text[:max_chars] + ("..." if len(clean_text) > max_chars else "")

    start = max(0, best_idx - 60)
    end = min(len(clean_text), start + max_chars)

    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(clean_text) else ""
    return prefix + clean_text[start:end].strip() + suffix


class RetrievalEngine:
    """Retrieval service scoped strictly to tenant workspaces."""

    def __init__(
        self,
        session: AsyncSession,
        embedding_provider: EmbeddingProvider | None = None,
    ) -> None:
        self.session = session
        self.chunk_repo = ChunkRepository(session)
        self.embedding_provider = embedding_provider or get_embedding_provider()

    async def search(
        self,
        workspace_id: uuid.UUID,
        query: str,
        mode: Literal["lexical", "semantic", "hybrid"] = "hybrid",
        limit: int = 10,
    ) -> list[SearchResult]:
        """Execute scoped workspace search in requested mode."""
        clean_q = query.strip()
        if not clean_q:
            return []

        chunks = await self.chunk_repo.get_chunks_for_workspace(workspace_id)
        if not chunks:
            return []

        if mode == "lexical":
            return self._search_lexical(chunks, clean_q, limit)
        elif mode == "semantic":
            return await self._search_semantic(chunks, clean_q, limit)
        else:
            return await self._search_hybrid(chunks, clean_q, limit)

    def _search_lexical(
        self,
        chunks: list[DocumentChunk],
        query: str,
        limit: int,
    ) -> list[SearchResult]:
        """Rank chunks via BM25-inspired term frequency and query coverage."""
        q_terms = [t.lower() for t in re.findall(r"\w{2,}", query)]
        if not q_terms:
            return []

        scored: list[tuple[float, DocumentChunk]] = []

        for chunk in chunks:
            text_lower = chunk.text.lower()
            term_matches = 0
            tf_score = 0.0

            for term in q_terms:
                count = text_lower.count(term)
                if count > 0:
                    term_matches += 1
                    # Diminishing returns on repeated words
                    tf_score += 1.0 + math.log(count)

            if term_matches > 0:
                # Reward chunks covering a higher proportion of query terms
                coverage = term_matches / len(q_terms)
                final_score = round(tf_score * (1.0 + coverage), 4)
                scored.append((final_score, chunk))

        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[SearchResult] = []
        for score, chunk in scored[:limit]:
            results.append(
                SearchResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_title=chunk.document.title if chunk.document else "Document",
                    version_id=chunk.version_id,
                    version_number=chunk.version.version_number if chunk.version else 1,
                    page_number=chunk.page_number,
                    section_heading=chunk.section_heading,
                    snippet=make_snippet(chunk.text, query),
                    score=score,
                    search_mode="lexical",
                )
            )
        return results

    async def _search_semantic(
        self,
        chunks: list[DocumentChunk],
        query: str,
        limit: int,
    ) -> list[SearchResult]:
        """Rank chunks via cosine similarity of dense vector embeddings."""
        query_vec = await self.embedding_provider.embed_query(query)
        if not query_vec:
            # If embedding provider is not available or inactive, return empty
            return []

        scored: list[tuple[float, DocumentChunk]] = []
        for chunk in chunks:
            chunk_vec = chunk.embedding
            if chunk_vec:
                sim = cosine_similarity(query_vec, chunk_vec)
                if sim > 0.05:
                    scored.append((round(sim, 4), chunk))

        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[SearchResult] = []
        for score, chunk in scored[:limit]:
            results.append(
                SearchResult(
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    document_title=chunk.document.title if chunk.document else "Document",
                    version_id=chunk.version_id,
                    version_number=chunk.version.version_number if chunk.version else 1,
                    page_number=chunk.page_number,
                    section_heading=chunk.section_heading,
                    snippet=make_snippet(chunk.text, query),
                    score=score,
                    search_mode="semantic",
                )
            )
        return results

    async def _search_hybrid(
        self,
        chunks: list[DocumentChunk],
        query: str,
        limit: int,
    ) -> list[SearchResult]:
        """Combine lexical and semantic retrieval using Reciprocal Rank Fusion (RRF)."""
        lex_results = self._search_lexical(chunks, query, limit=limit * 2)
        sem_results = await self._search_semantic(chunks, query, limit=limit * 2)

        if not sem_results:
            # If embedding provider returned nothing, fall back transparently to lexical
            return lex_results[:limit]

        rrf_k = 60.0
        scores: dict[uuid.UUID, float] = {}
        chunk_map: dict[uuid.UUID, SearchResult] = {}

        for rank, res in enumerate(lex_results):
            scores[res.chunk_id] = scores.get(res.chunk_id, 0.0) + (1.0 / (rrf_k + rank + 1))
            chunk_map[res.chunk_id] = res

        for rank, res in enumerate(sem_results):
            scores[res.chunk_id] = scores.get(res.chunk_id, 0.0) + (1.0 / (rrf_k + rank + 1))
            chunk_map[res.chunk_id] = res

        sorted_chunks = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        results: list[SearchResult] = []
        for chunk_id, combined_score in sorted_chunks[:limit]:
            base = chunk_map[chunk_id]
            results.append(
                SearchResult(
                    chunk_id=base.chunk_id,
                    document_id=base.document_id,
                    document_title=base.document_title,
                    version_id=base.version_id,
                    version_number=base.version_number,
                    page_number=base.page_number,
                    section_heading=base.section_heading,
                    snippet=base.snippet,
                    score=round(combined_score, 6),
                    search_mode="hybrid",
                )
            )
        return results
