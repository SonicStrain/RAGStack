from __future__ import annotations

import os
from typing import Any

import yaml

from ragstack.base import (
    CacheBackend,
    CompressorBackend,
    PromptCacheBackend,
    PromptOptimizerBackend,
    QueryContext,
    RetrieverBackend,
    RewriterBackend,
)
from ragstack.layers.cache import CACHE_BACKENDS
from ragstack.layers.compressor import COMPRESSOR_BACKENDS
from ragstack.layers.optimizer import OPTIMIZER_BACKENDS
from ragstack.layers.prompt_cache import PROMPT_CACHE_BACKENDS
from ragstack.layers.retriever import RETRIEVER_BACKENDS
from ragstack.layers.rewriter import REWRITER_BACKENDS


# ── LLM provider adapters ─────────────────────────────────────────────────────

class _AnthropicAdapter:
    def __init__(self):
        self._client = None

    def _get(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client

    def chat(self, model: str, messages: list[dict], system: str | list | None, max_tokens: int) -> str:
        client = self._get()
        kwargs: dict[str, Any] = {"model": model, "messages": messages, "max_tokens": max_tokens}
        if system:
            kwargs["system"] = system
        response = client.messages.create(**kwargs)
        return response.content[0].text


class _OpenAIAdapter:
    def __init__(self):
        self._client = None

    def _get(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI()
        return self._client

    def chat(self, model: str, messages: list[dict], system: str | list | None, max_tokens: int) -> str:
        client = self._get()
        full_messages = []
        if system:
            sys_text = system if isinstance(system, str) else " ".join(
                b.get("text", "") for b in system if isinstance(b, dict)
            )
            full_messages.append({"role": "system", "content": sys_text})
        full_messages.extend(messages)
        response = client.chat.completions.create(
            model=model, messages=full_messages, max_tokens=max_tokens
        )
        return response.choices[0].message.content


class _GeminiAdapter:
    def __init__(self):
        self._client = None

    def _get(self):
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=os.environ["GOOGLE_API_KEY"])
            self._client = genai
        return self._client

    def chat(self, model: str, messages: list[dict], system: str | list | None, max_tokens: int) -> str:
        genai = self._get()
        m = genai.GenerativeModel(model_name=model)
        parts = []
        if system:
            sys_text = system if isinstance(system, str) else " ".join(
                b.get("text", "") for b in system if isinstance(b, dict)
            )
            parts.append(sys_text)
        for msg in messages:
            parts.append(msg.get("content", ""))
        response = m.generate_content(
            " ".join(parts),
            generation_config={"max_output_tokens": max_tokens},
        )
        return response.text


class _OllamaAdapter:
    def __init__(self, base_url: str = "http://localhost:11434"):
        self._base_url = base_url
        self._client = None

    def _get(self):
        if self._client is None:
            import ollama
            self._client = ollama.Client(host=self._base_url)
        return self._client

    def chat(self, model: str, messages: list[dict], system: str | list | None, max_tokens: int) -> str:
        client = self._get()
        full_messages = []
        if system:
            sys_text = system if isinstance(system, str) else " ".join(
                b.get("text", "") for b in system if isinstance(b, dict)
            )
            full_messages.append({"role": "system", "content": sys_text})
        full_messages.extend(messages)
        response = client.chat(model=model, messages=full_messages)
        return response["message"]["content"]


_LLM_ADAPTERS = {
    "anthropic": _AnthropicAdapter,
    "openai":    _OpenAIAdapter,
    "gemini":    _GeminiAdapter,
    "ollama":    _OllamaAdapter,
}


# ── Shared embedders ──────────────────────────────────────────────────────────

class _Embedder:
    """OpenAI text-embedding-* embedder.  Requires OPENAI_API_KEY."""

    def __init__(self, model: str, dimensions: int = 1536):
        self._model = model
        self._dimensions = dimensions
        self._client = None

    def _get(self):
        if self._client is None:
            import openai
            self._client = openai.OpenAI()
        return self._client

    def embed(self, text: str) -> list[float]:
        client = self._get()
        response = client.embeddings.create(
            model=self._model,
            input=text,
            dimensions=self._dimensions,
        )
        return response.data[0].embedding


class _OllamaEmbedder:
    """Embedder backed by a local Ollama instance — no API key required.

    Uses the same model as the LLM by default.  For best embedding quality
    pull a dedicated model first:  ``ollama pull nomic-embed-text``
    """

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama3.2"):
        self._base_url = base_url
        self._model = model
        self._client = None

    def _get(self):
        if self._client is None:
            import ollama
            self._client = ollama.Client(host=self._base_url)
        return self._client

    def embed(self, text: str) -> list[float]:
        client = self._get()
        try:
            # ollama SDK ≥ 0.3 exposes .embed(); older SDKs use .embeddings()
            if hasattr(client, "embed"):
                resp = client.embed(model=self._model, input=text)
                return resp.embeddings[0] if resp.embeddings else resp.get("embedding", [])
            else:
                resp = client.embeddings(model=self._model, prompt=text)
                return resp.get("embedding", [])
        except Exception as exc:
            print(f"[ragstack] OllamaEmbedder warning: {exc} — returning zero vector")
            return [0.0] * 768  # safe fallback; cosine of two zero-vecs is undefined


class _NullEmbedder:
    """No-op embedder — disables semantic cache without crashing.

    Used when no embedding provider is configured and no API key is available.
    """

    def embed(self, text: str) -> list[float]:
        return []


def _build_embedder(embed_cfg: dict, llm_provider: str, llm_cfg: dict):
    """Choose the right embedder from config + runtime environment.

    Priority:
      1. ``embeddings.provider`` explicit override in YAML
      2. Auto-detect: if LLM provider is ``ollama`` → use OllamaEmbedder
      3. Auto-detect: if OPENAI_API_KEY is set → use OpenAI embedder
      4. Fallback: NullEmbedder (semantic cache disabled gracefully)
    """
    explicit = embed_cfg.get("provider", None)

    if explicit == "openai" or (explicit is None and llm_provider not in ("ollama",) and os.environ.get("OPENAI_API_KEY")):
        return _Embedder(
            model=embed_cfg.get("model", "text-embedding-3-small"),
            dimensions=embed_cfg.get("dimensions", 1536),
        )

    if explicit == "ollama" or (explicit is None and llm_provider == "ollama"):
        ollama_cfg = llm_cfg.get("ollama", {})
        return _OllamaEmbedder(
            base_url=ollama_cfg.get("base_url", "http://localhost:11434"),
            model=embed_cfg.get("embed_model", embed_cfg.get("model", "llama3.2")),
        )

    if explicit == "none":
        return _NullEmbedder()

    # Last resort: OpenAI (will fail loudly if key absent — user explicitly set provider)
    return _Embedder(
        model=embed_cfg.get("model", "text-embedding-3-small"),
        dimensions=embed_cfg.get("dimensions", 1536),
    )


# ── RAGStack pipeline ─────────────────────────────────────────────────────────

class RAGStack:
    def __init__(
        self,
        optimizer: PromptOptimizerBackend,
        cache: CacheBackend,
        rewriter: RewriterBackend,
        retriever: RetrieverBackend,
        compressor: CompressorBackend,
        prompt_cache: PromptCacheBackend,
        llm_client,
        llm_model: str,
        llm_max_tokens: int,
        cached_prefix: str,
        retriever_top_k: int,
        compressor_top_k: int,
        report_savings: bool = True,
    ):
        self._optimizer = optimizer
        self._cache = cache
        self._rewriter = rewriter
        self._retriever = retriever
        self._compressor = compressor
        self._prompt_cache = prompt_cache
        self._llm = llm_client
        self._llm_model = llm_model
        self._llm_max_tokens = llm_max_tokens
        self._cached_prefix = cached_prefix
        self._retriever_top_k = retriever_top_k
        self._compressor_top_k = compressor_top_k
        self._report_savings = report_savings

    @classmethod
    def from_config(cls, config_path: str = "ragstack.config.yaml") -> "RAGStack":
        with open(config_path, encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        layers = cfg.get("layers", {})
        embed_cfg = cfg.get("embeddings", {})
        llm_cfg = cfg.get("llm", {})

        # ── LLM provider (needed before embedder so _build_embedder can read it) ─
        provider = llm_cfg.get("provider", "anthropic")

        # ── Embedder (shared) ─────────────────────────────────────────────────
        embedder = _build_embedder(embed_cfg, provider, llm_cfg)
        adapter_cls = _LLM_ADAPTERS[provider]
        if provider == "ollama":
            ollama_cfg = llm_cfg.get("ollama", {})
            llm_client = adapter_cls(base_url=ollama_cfg.get("base_url", "http://localhost:11434"))
        else:
            llm_client = adapter_cls()
        llm_model = llm_cfg.get("model", "claude-sonnet-4-6")
        llm_max_tokens = llm_cfg.get("max_tokens", 1024)

        # ── Layer 0: prompt optimizer ─────────────────────────────────────────
        opt_cfg = layers.get("optimizer", {})
        opt_enabled = opt_cfg.get("enabled", True)
        opt_backend_name = opt_cfg.get("backend", "rules")
        report_savings = opt_cfg.get("report_savings", True)

        if not opt_enabled or opt_backend_name == "passthrough":
            optimizer = OPTIMIZER_BACKENDS["passthrough"]()
        elif opt_backend_name == "llm":
            llm_opt_cfg = opt_cfg.get("llm", {})
            optimizer = OPTIMIZER_BACKENDS["llm"](
                llm_client=llm_client,
                model=llm_opt_cfg.get("model", "claude-haiku-4-5-20251001"),
                max_tokens=llm_opt_cfg.get("max_tokens", 512),
            )
        else:
            optimizer = OPTIMIZER_BACKENDS["rules"]()

        # ── Layer 1: semantic cache ───────────────────────────────────────────
        cache_cfg = layers.get("cache", {})
        cache_enabled = cache_cfg.get("enabled", True)
        cache_backend_name = cache_cfg.get("backend", "memory")
        threshold = cache_cfg.get("similarity_threshold", 0.92)
        ttl = cache_cfg.get("ttl_seconds", 3600)

        if cache_backend_name == "redis":
            redis_cfg = cache_cfg.get("redis", {})
            cache = CACHE_BACKENDS["redis"](
                embedder=embedder,
                url=redis_cfg.get("url", "redis://localhost:6379"),
                index_name=redis_cfg.get("index_name", "ragstack_cache"),
                similarity_threshold=threshold, ttl_seconds=ttl,
            )
        elif cache_backend_name == "qdrant":
            qdrant_cfg = cache_cfg.get("qdrant", {})
            cache = CACHE_BACKENDS["qdrant"](
                embedder=embedder,
                url=qdrant_cfg.get("url", "http://localhost:6333"),
                collection=qdrant_cfg.get("collection", "ragstack_cache"),
                similarity_threshold=threshold, ttl_seconds=ttl,
            )
        else:
            cache = CACHE_BACKENDS["memory"](
                embedder=embedder, similarity_threshold=threshold, ttl_seconds=ttl,
            )

        if not cache_enabled:
            from ragstack.layers.cache import MemoryCacheBackend

            class _DisabledCache(MemoryCacheBackend):
                def get(self, query): return None
                def set(self, query, answer): pass

            cache = _DisabledCache(embedder=embedder)

        # ── Layer 2: query rewriter ───────────────────────────────────────────
        rew_cfg = layers.get("rewriter", {})
        rew_enabled = rew_cfg.get("enabled", True)
        rew_backend_name = rew_cfg.get("backend", "passthrough")

        if not rew_enabled or rew_backend_name == "passthrough":
            rewriter = REWRITER_BACKENDS["passthrough"]()
        elif rew_backend_name == "llm":
            rewriter = REWRITER_BACKENDS["llm"](
                llm_client=llm_client,
                model=rew_cfg.get("model", llm_model),
                strategy=rew_cfg.get("strategy", "expand"),
            )
        elif rew_backend_name == "hyde":
            hyde_cfg = rew_cfg.get("hyde", {})
            rewriter = REWRITER_BACKENDS["hyde"](
                llm_client=llm_client,
                embedder=embedder,
                model=hyde_cfg.get("model", llm_model),
            )
        else:
            rewriter = REWRITER_BACKENDS["passthrough"]()

        # ── Layer 3: retriever ────────────────────────────────────────────────
        ret_cfg = layers.get("retriever", {})
        ret_enabled = ret_cfg.get("enabled", True)
        ret_backend_name = ret_cfg.get("backend", "memory")
        ret_top_k = ret_cfg.get("top_k", 8)

        if not ret_enabled or ret_backend_name == "memory":
            retriever = RETRIEVER_BACKENDS["memory"](
                docs=ret_cfg.get("memory", {}).get("docs", [])
            )
        elif ret_backend_name == "graphify":
            g_cfg = ret_cfg.get("graphify", {})
            retriever = RETRIEVER_BACKENDS["graphify"](
                graph_path=g_cfg.get("graph_path", "./graphify-out/graph.json"),
                report_path=g_cfg.get("report_path", "./graphify-out/GRAPH_REPORT.md"),
                hop_limit=g_cfg.get("hop_limit", 3),
                edge_types=g_cfg.get("edge_types", []),
            )
        elif ret_backend_name == "chroma":
            c_cfg = ret_cfg.get("chroma", {})
            retriever = RETRIEVER_BACKENDS["chroma"](
                embedder=embedder,
                host=c_cfg.get("host", "localhost"),
                port=c_cfg.get("port", 8000),
                collection=c_cfg.get("collection", "ragstack_docs"),
            )
        elif ret_backend_name == "pinecone":
            p_cfg = ret_cfg.get("pinecone", {})
            retriever = RETRIEVER_BACKENDS["pinecone"](
                embedder=embedder,
                index_name=p_cfg.get("index_name", "ragstack-index"),
                environment=p_cfg.get("environment", "us-east-1"),
            )
        elif ret_backend_name == "weaviate":
            w_cfg = ret_cfg.get("weaviate", {})
            retriever = RETRIEVER_BACKENDS["weaviate"](
                embedder=embedder,
                url=w_cfg.get("url", "http://localhost:8080"),
                class_name=w_cfg.get("class_name", "Document"),
            )
        else:
            retriever = RETRIEVER_BACKENDS["memory"]()

        # ── Layer 4: compressor ───────────────────────────────────────────────
        comp_cfg = layers.get("compressor", {})
        comp_enabled = comp_cfg.get("enabled", True)
        comp_backend_name = comp_cfg.get("backend", "passthrough")
        comp_top_k = comp_cfg.get("top_k", 3)

        if not comp_enabled or comp_backend_name == "passthrough":
            compressor = COMPRESSOR_BACKENDS["passthrough"]()
        elif comp_backend_name == "reranker":
            r_cfg = comp_cfg.get("reranker", {})
            compressor = COMPRESSOR_BACKENDS["reranker"](
                model=r_cfg.get("model", "cross-encoder/ms-marco-MiniLM-L-6-v2"),
                score_threshold=r_cfg.get("score_threshold", 0.3),
            )
        elif comp_backend_name == "llmlingua":
            l_cfg = comp_cfg.get("llmlingua", {})
            compressor = COMPRESSOR_BACKENDS["llmlingua"](
                model=l_cfg.get("model", "microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank"),
                ratio=l_cfg.get("ratio", 0.4),
            )
        else:
            compressor = COMPRESSOR_BACKENDS["passthrough"]()

        # ── Layer 5: prompt cache ─────────────────────────────────────────────
        pc_cfg = layers.get("prompt_cache", {})
        pc_backend_name = pc_cfg.get("backend", "none")
        pc_backend_cls = PROMPT_CACHE_BACKENDS.get(pc_backend_name, PROMPT_CACHE_BACKENDS["none"])
        prompt_cache_layer = pc_backend_cls()
        cached_prefix = pc_cfg.get("cached_prefix", "You are a helpful assistant.")

        return cls(
            optimizer=optimizer,
            cache=cache,
            rewriter=rewriter,
            retriever=retriever,
            compressor=compressor,
            prompt_cache=prompt_cache_layer,
            llm_client=llm_client,
            llm_model=llm_model,
            llm_max_tokens=llm_max_tokens,
            cached_prefix=cached_prefix,
            retriever_top_k=ret_top_k,
            compressor_top_k=comp_top_k,
            report_savings=report_savings,
        )

    # ── Main query entrypoint ─────────────────────────────────────────────────

    def query(self, user_query: str) -> str:
        ctx = QueryContext(original_query=user_query)

        # Layer 0: prompt optimization — trim tokens before anything else
        optimized, stats = self._optimizer.optimize(user_query)
        ctx.optimized_query = optimized
        if self._report_savings and stats["savings_pct"] >= 5:
            pct = stats["savings_pct"]
            ot, tt = stats["original_tokens"], stats["optimized_tokens"]
            print(f"[ragstack] prompt optimized: {ot} → {tt} tokens  (-{pct}%)")
            if ot > 10:  # only echo for non-trivial prompts
                print(f"           before: {stats['original'][:80]!r}")
                print(f"           after : {stats['optimized'][:80]!r}")

        # Layer 1: semantic cache (keyed on normalized/optimized query)
        cached = self._cache.get(ctx.cache_key)
        if cached is not None:
            print("[ragstack] cache hit")
            ctx.cached_response = cached
            return cached

        # Layer 2: query rewriting for retrieval enrichment
        ctx.rewritten_query = self._rewriter.rewrite(ctx.optimized_query or ctx.original_query)
        if ctx.rewritten_query != ctx.active_query:
            print(f"[ragstack] rewritten: {ctx.rewritten_query!r}")

        # Layer 3: retrieval
        ctx.retrieved_chunks = self._retriever.retrieve(ctx.active_query, self._retriever_top_k)
        print(f"[ragstack] retrieved {len(ctx.retrieved_chunks)} chunks")

        # Layer 4: compression / reranking
        ctx.compressed_chunks = self._compressor.compress(
            ctx.active_query, ctx.retrieved_chunks, self._compressor_top_k
        )
        print(f"[ragstack] compressed to {len(ctx.final_chunks)} chunks")

        # Build context string from surviving chunks
        context = "\n\n".join(
            f"[{i+1}] (source: {c.get('source', 'unknown')})\n{c.get('text', '')}"
            for i, c in enumerate(ctx.final_chunks)
        )

        # Layer 5: build prompt-cached messages — LLM sees the optimized query
        built = self._prompt_cache.build_messages(
            prefix=self._cached_prefix,
            context=context,
            query=ctx.llm_query,
        )

        answer = self._llm.chat(
            model=self._llm_model,
            messages=built.get("messages", []),
            system=built.get("system"),
            max_tokens=self._llm_max_tokens,
        )

        # Store answer keyed on the optimized query
        self._cache.set(ctx.cache_key, answer)

        return answer

    # ── GUI / inspection helpers ──────────────────────────────────────────────

    def inspect(self, user_query: str) -> dict:
        """
        Dry-run: execute L0–L5 without calling the LLM.
        Returns every intermediate value so the GUI can display them.
        """
        from ragstack.layers.optimizer import _tokens

        ctx = QueryContext(original_query=user_query)

        # Layer 0
        optimized, opt_stats = self._optimizer.optimize(user_query)
        ctx.optimized_query = optimized

        # Layer 1
        cached = self._cache.get(ctx.cache_key)

        base = {
            "original_query":       user_query,
            "optimizer":            opt_stats,
            "optimizer_backend":    type(self._optimizer).__name__,
            "cache_backend":        type(self._cache).__name__,
            "rewriter_backend":     type(self._rewriter).__name__,
            "retriever_backend":    type(self._retriever).__name__,
            "compressor_backend":   type(self._compressor).__name__,
            "prompt_cache_backend": type(self._prompt_cache).__name__,
        }

        if cached is not None:
            return {**base, "cache_hit": True, "cached_answer": cached,
                    "rewritten_query": "", "retrieved_chunks": [],
                    "compressed_chunks": [], "context": "",
                    "final_messages": {}, "prompt_tokens": 0}

        # Layer 2
        ctx.rewritten_query = self._rewriter.rewrite(ctx.optimized_query or ctx.original_query)

        # Layer 3
        ctx.retrieved_chunks = self._retriever.retrieve(ctx.active_query, self._retriever_top_k)

        # Layer 4
        ctx.compressed_chunks = self._compressor.compress(
            ctx.active_query, ctx.retrieved_chunks, self._compressor_top_k
        )

        context = "\n\n".join(
            f"[{i+1}] (source: {c.get('source', 'unknown')})\n{c.get('text', '')}"
            for i, c in enumerate(ctx.final_chunks)
        )

        # Layer 5 — build messages, no LLM call
        built = self._prompt_cache.build_messages(
            prefix=self._cached_prefix,
            context=context,
            query=ctx.llm_query,
        )

        return {
            **base,
            "cache_hit":        False,
            "cached_answer":    None,
            "rewritten_query":  ctx.rewritten_query,
            "retrieved_chunks": ctx.retrieved_chunks,
            "compressed_chunks": ctx.final_chunks,
            "context":          context,
            "final_messages":   built,
            "prompt_tokens":    _tokens(str(built)),
        }

    def answer_from_inspection(self, result: dict) -> str:
        """
        Call the LLM using already-computed inspect() output.
        Avoids re-running L0–L4 when the GUI wants both the inspection
        view and the final answer.
        """
        if result.get("cache_hit"):
            return result["cached_answer"]

        built = result["final_messages"]
        answer = self._llm.chat(
            model=self._llm_model,
            messages=built.get("messages", []),
            system=built.get("system"),
            max_tokens=self._llm_max_tokens,
        )
        # Store in cache keyed on the optimized query
        cache_key = result["optimizer"].get("optimized") or result["original_query"]
        self._cache.set(cache_key, answer)
        return answer

    # ── Developer helpers (used by MCP server & tests) ────────────────────────

    def ingest_docs(self, docs: list[dict]) -> int:
        """Dynamically add documents to the retriever. Returns new total count."""
        if not hasattr(self._retriever, "add_docs"):
            raise TypeError(
                f"{type(self._retriever).__name__} does not support dynamic ingestion. "
                "Set retriever.backend: memory in ragstack.config.yaml."
            )
        return self._retriever.add_docs(docs)

    def clear_cache(self) -> int:
        """Clear the in-memory semantic cache. Returns number of entries cleared."""
        store = getattr(self._cache, "_store", None)
        if store is None:
            return 0
        count = len(store)
        store.clear()
        return count

    def status(self) -> dict:
        """Return a summary dict of active backends and counts."""
        return {
            "optimizer":      type(self._optimizer).__name__,
            "retriever":      type(self._retriever).__name__,
            "indexed_docs":   len(getattr(self._retriever, "_docs", [])),
            "compressor":     type(self._compressor).__name__,
            "rewriter":       type(self._rewriter).__name__,
            "cache":          type(self._cache).__name__,
            "cached_queries": len(getattr(self._cache, "_store", [])),
            "prompt_cache":   type(self._prompt_cache).__name__,
            "llm_model":      self._llm_model,
        }
