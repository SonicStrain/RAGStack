from __future__ import annotations

from ragstack.base import RewriterBackend


class LLMRewriterBackend(RewriterBackend):
    def __init__(self, llm_client, model: str, strategy: str = "expand"):
        self._llm = llm_client
        self._model = model
        self._strategy = strategy

    def rewrite(self, query: str) -> str:
        system = (
            "You are a search query optimizer. Rewrite the user's query to improve "
            "retrieval from a technical documentation corpus. Expand abbreviations, "
            "make the intent explicit, and add relevant synonyms. "
            "Return ONLY the rewritten query string, no explanation."
        )
        messages = [{"role": "user", "content": query}]
        rewritten = self._llm.chat(
            model=self._model,
            messages=messages,
            system=system,
            max_tokens=256,
        )
        return rewritten.strip()


class HyDERewriterBackend(RewriterBackend):
    """Hypothetical Document Embedding — embed a generated answer, not the raw query."""

    def __init__(self, llm_client, embedder, model: str):
        self._llm = llm_client
        self._embedder = embedder
        self._model = model

    def rewrite(self, query: str) -> str:
        system = (
            "You are a technical documentation writer. Write a concise factual paragraph "
            "that would be the ideal answer to the question, as if from technical "
            "documentation. Be specific and use domain terminology."
        )
        messages = [{"role": "user", "content": query}]
        hypothetical_doc = self._llm.chat(
            model=self._model,
            messages=messages,
            system=system,
            max_tokens=512,
        )
        # Return the hypothetical document text; the retriever will embed it
        return hypothetical_doc.strip()


class PassthroughRewriterBackend(RewriterBackend):
    def rewrite(self, query: str) -> str:
        return query


REWRITER_BACKENDS: dict[str, type[RewriterBackend]] = {
    "llm": LLMRewriterBackend,
    "hyde": HyDERewriterBackend,
    "passthrough": PassthroughRewriterBackend,
}
