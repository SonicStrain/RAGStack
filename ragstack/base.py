from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class QueryContext:
    original_query: str
    optimized_query: str = ""   # Layer 0: prompt optimizer output (token-efficient)
    rewritten_query: str = ""   # Layer 2: retrieval-enriched version
    retrieved_chunks: list[dict] = field(default_factory=list)
    compressed_chunks: list[dict] = field(default_factory=list)
    cached_response: str | None = None
    metadata: dict = field(default_factory=dict)

    @property
    def cache_key(self) -> str:
        """Stable key for semantic cache — uses optimized (normalized) query."""
        return self.optimized_query or self.original_query

    @property
    def active_query(self) -> str:
        """For retrieval: richest form (rewritten > optimized > original)."""
        return self.rewritten_query or self.optimized_query or self.original_query

    @property
    def llm_query(self) -> str:
        """What the LLM sees as the user question — concise optimized form."""
        return self.optimized_query or self.original_query

    @property
    def final_chunks(self) -> list[dict]:
        return self.compressed_chunks or self.retrieved_chunks


# ── Layer ABCs ────────────────────────────────────────────────────────────────

class PromptOptimizerBackend(ABC):
    """Layer 0 — trim tokens from the user prompt before anything else runs."""

    @abstractmethod
    def optimize(self, prompt: str) -> tuple[str, dict]:
        """
        Return (optimized_prompt, stats).
        stats keys: original_tokens, optimized_tokens, savings_pct
        """
        ...


class CacheBackend(ABC):
    @abstractmethod
    def get(self, query: str) -> str | None: ...

    @abstractmethod
    def set(self, query: str, answer: str) -> None: ...


class RewriterBackend(ABC):
    @abstractmethod
    def rewrite(self, query: str) -> str: ...


class RetrieverBackend(ABC):
    @abstractmethod
    def retrieve(self, query: str, top_k: int) -> list[dict]: ...


class CompressorBackend(ABC):
    @abstractmethod
    def compress(self, query: str, chunks: list[dict], top_k: int) -> list[dict]: ...


class PromptCacheBackend(ABC):
    @abstractmethod
    def build_messages(self, prefix: str, context: str, query: str) -> dict: ...
