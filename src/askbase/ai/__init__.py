"""AI providers package exports."""

from askbase.ai.base import (
    Citation,
    EmbeddingProvider,
    GroundedAnswerResult,
    GroundedPassage,
    LLMProvider,
)
from askbase.ai.providers import (
    ExtractiveGroundedSynthesizer,
    FakeEmbeddingProvider,
    NoopEmbeddingProvider,
    get_embedding_provider,
    get_llm_provider,
)

__all__ = [
    "EmbeddingProvider",
    "LLMProvider",
    "GroundedPassage",
    "Citation",
    "GroundedAnswerResult",
    "FakeEmbeddingProvider",
    "NoopEmbeddingProvider",
    "ExtractiveGroundedSynthesizer",
    "get_embedding_provider",
    "get_llm_provider",
]
