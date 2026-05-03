from __future__ import annotations

from ragstack.base import PromptCacheBackend


class AnthropicPromptCacheBackend(PromptCacheBackend):
    """
    Returns messages structured for Anthropic's prompt caching API.
    The system prefix block is marked ephemeral so Anthropic caches it
    across requests, saving tokens on repeated calls with the same prefix.
    """

    def build_messages(self, prefix: str, context: str, query: str) -> dict:
        return {
            "system": [
                {
                    "type": "text",
                    "text": prefix,
                    "cache_control": {"type": "ephemeral"},
                },
                {
                    "type": "text",
                    "text": f"Context:\n{context}",
                },
            ],
            "messages": [
                {"role": "user", "content": query},
            ],
        }


class OpenAIPromptCacheBackend(PromptCacheBackend):
    """
    OpenAI caches prompts automatically for requests >= 1024 tokens.
    No special markup needed — just concatenate prefix + context into system.
    """

    def build_messages(self, prefix: str, context: str, query: str) -> dict:
        system_content = f"{prefix}\n\nContext:\n{context}"
        return {
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": query},
            ]
        }


class NoPromptCacheBackend(PromptCacheBackend):
    def build_messages(self, prefix: str, context: str, query: str) -> dict:
        system_content = f"{prefix}\n\nContext:\n{context}"
        return {
            "messages": [
                {"role": "system", "content": system_content},
                {"role": "user", "content": query},
            ]
        }


PROMPT_CACHE_BACKENDS: dict[str, type[PromptCacheBackend]] = {
    "anthropic": AnthropicPromptCacheBackend,
    "openai": OpenAIPromptCacheBackend,
    "none": NoPromptCacheBackend,
}
