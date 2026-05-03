from __future__ import annotations

from ragstack.base import CompressorBackend


class RerankerCompressorBackend(CompressorBackend):
    def __init__(self, model: str, score_threshold: float = 0.3):
        self._model_name = model
        self._score_threshold = score_threshold
        self._encoder = None

    def _get_encoder(self):
        if self._encoder is None:
            from sentence_transformers import CrossEncoder
            self._encoder = CrossEncoder(self._model_name)
        return self._encoder

    def compress(self, query: str, chunks: list[dict], top_k: int) -> list[dict]:
        if not chunks:
            return []
        encoder = self._get_encoder()
        pairs = [(query, chunk.get("text", "")) for chunk in chunks]
        scores = encoder.predict(pairs)
        scored = [
            {**chunk, "score": float(score)}
            for chunk, score in zip(chunks, scores)
            if float(score) >= self._score_threshold
        ]
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]


class LLMLinguaCompressorBackend(CompressorBackend):
    def __init__(self, model: str, ratio: float = 0.4, top_k: int = 5):
        self._model_name = model
        self._ratio = ratio
        self._default_top_k = top_k
        self._compressor = None

    def _get_compressor(self):
        if self._compressor is None:
            from llmlingua import PromptCompressor
            self._compressor = PromptCompressor(self._model_name, use_llmlingua2=True)
        return self._compressor

    def compress(self, query: str, chunks: list[dict], top_k: int) -> list[dict]:
        if not chunks:
            return []
        compressor = self._get_compressor()
        result = []
        for chunk in chunks[:top_k]:
            original_text = chunk.get("text", "")
            try:
                compressed = compressor.compress_prompt(
                    original_text,
                    ratio=self._ratio,
                    target_token=None,
                )
                compressed_text = compressed.get("compressed_prompt", original_text)
            except Exception:
                compressed_text = original_text
            result.append({**chunk, "text": compressed_text})
        return result


class PassthroughCompressorBackend(CompressorBackend):
    def compress(self, query: str, chunks: list[dict], top_k: int) -> list[dict]:
        sorted_chunks = sorted(chunks, key=lambda x: x.get("score", 0), reverse=True)
        return sorted_chunks[:top_k]


COMPRESSOR_BACKENDS: dict[str, type[CompressorBackend]] = {
    "reranker": RerankerCompressorBackend,
    "llmlingua": LLMLinguaCompressorBackend,
    "passthrough": PassthroughCompressorBackend,
}
