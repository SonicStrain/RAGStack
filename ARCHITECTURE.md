# RAGStack — Architecture

## Full Pipeline Flow

```mermaid
flowchart TD
    USER([User Query]) --> L0

    subgraph L0["Layer 0 · Prompt Optimizer"]
        O["Strips filler words, hedges, verbose phrasing\nOutput: optimized_query  (shorter, same intent)"]
    end

    L0 -->|optimized_query| L1

    subgraph L1["Layer 1 · Semantic Cache"]
        C["Embeds optimized_query, cosine-compares vs stored embeddings\nHIT → return cached answer instantly\nCache key = optimized_query"]
    end

    L1 -->|"✅ HIT"| CACHED([Return cached answer])
    L1 -->|"❌ MISS"| L2

    subgraph L2["Layer 2 · Query Rewriter"]
        R["Enriches for retrieval: expand abbreviations,\nadd synonyms, or generate HyDE document\nOutput: rewritten_query  (used for retrieval ONLY)"]
    end

    L2 -->|rewritten_query| L3

    subgraph L3["Layer 3 · Retriever"]
        RT["Finds top-K chunks from indexed corpus\nGraphify: BFS graph traversal\nOthers: vector cosine search"]
    end

    L3 -->|"retrieved_chunks  (up to top_k)"| L4

    subgraph L4["Layer 4 · Compressor"]
        CP["Re-scores and filters chunks\nOnly best top_k survive\nOutput: compressed_chunks"]
    end

    L4 -->|final_chunks| L5

    subgraph L5["Layer 5 · Prompt Cache Builder"]
        PC["Assembles messages dict\nAnthropic: marks system prefix ephemeral\nfor prompt-cache savings on repeat calls"]
    end

    L5 -->|"{ system: [...], messages: [...] }"| LLM

    LLM([LLM API Call\noptimized_query as user question])
    LLM --> STORE["Store answer in L1 cache"]
    STORE --> OUT([Return answer + citations])

    style CACHED fill:#16a34a,color:#fff
    style LLM    fill:#4f46e5,color:#fff
    style OUT    fill:#4f46e5,color:#fff
```

---

## QueryContext — the data object

A single `QueryContext` dataclass flows through every layer. No layer imports another layer — they all read/write `QueryContext` fields.

```python
@dataclass
class QueryContext:
    original_query:    str        # what the user typed
    optimized_query:   str = ""   # after Layer 0 (shorter)
    rewritten_query:   str = ""   # after Layer 2 (richer, for retrieval only)
    retrieved_chunks:  list[dict] # after Layer 3
    compressed_chunks: list[dict] # after Layer 4

    @property
    def cache_key(self) -> str:
        # optimized_query normalises phrasing variations → more cache hits
        return self.optimized_query or self.original_query

    @property
    def active_query(self) -> str:
        # richest form used for vector retrieval
        return self.rewritten_query or self.optimized_query or self.original_query

    @property
    def llm_query(self) -> str:
        # what the LLM sees — concise, optimized
        return self.optimized_query or self.original_query

    @property
    def final_chunks(self) -> list[dict]:
        return self.compressed_chunks or self.retrieved_chunks
```

---

## Token Savings Walkthrough

```mermaid
flowchart LR
    RAW["User types:\n'Could you please explain how the\nauthentication flow works in this\napplication, and also tell me what\ncalls the token validator?'\n35 tokens"] -->|"L0 rules optimizer"| OPT

    OPT["Optimized:\n'Authentication flow?\nWhat calls token validator?'\n8 tokens  (-77%)"] -->|"becomes cache key"| CK["L1 cache key\nnormalised form"]

    OPT -->|"L2 rewriter\n(retrieval only)"| REW["Rewritten:\n'authentication login flow JWT\ntoken validator middleware caller'\n(never sent to LLM)"]

    REW -->|"L3 retrieves"| CHUNKS["8 relevant chunks"]
    CHUNKS -->|"L4 keeps top 3"| FINAL["3 chunks × ~200 tok\n= ~600 context tokens"]

    FINAL --> LLM["LLM receives:\n8 tok question\n+ 600 tok context\n+ cached system prefix\n= ~620 tokens total\nvs ~3500+ without RAGStack"]

    style LLM fill:#4f46e5,color:#fff
```

### Cumulative savings

| Source | Without RAGStack | With RAGStack |
|--------|-----------------|---------------|
| User prompt | 35 tokens | **8 tokens** (L0 −77%) |
| Context window | raw docs, unfiltered | **top 3 chunks** (L4) |
| System prefix | repeated every call | **cached** (L5 ephemeral) |
| Repeated questions | full LLM call each time | **cache hit, free** (L1) |

---

## Graphify — Graph-Based Retriever (Deep Dive)

### Why a graph?

Standard vector search finds chunks that are *textually similar* to the query. Graphify finds chunks that are *structurally connected* — callers, callees, dependencies — even if they don't share keywords.

### BFS traversal algorithm

```mermaid
flowchart TD
    Q[Query keywords] --> SEED["Seed node matching\nScan all node labels for keyword overlap\nKeep top-5 matching nodes"]

    SEED --> BFS

    subgraph BFS["BFS — up to hop_limit hops"]
        H0[Seed nodes\ndepth 0] -->|follow allowed edges| H1[Depth 1 neighbours]
        H1 --> H2[Depth 2 neighbours]
        H2 --> HN["... up to hop_limit"]
    end

    BFS --> FILTER["Filter by allowed edge_types\n(calls, depends_on, similar_to, rationale_for)"]
    FILTER --> TOPK["Slice to top_k\nSeed nodes score 1.0\nBFS neighbours score 0.7"]
    TOPK --> OUT([Retrieved chunks])

    style OUT fill:#4f46e5,color:#fff
```

### Graph JSON schema

```json
{
  "nodes": [
    {
      "id":      "auth/auth_service.py::AuthService",
      "label":   "AuthService",
      "type":    "class",
      "file":    "auth/auth_service.py",
      "content": "class AuthService:\n    def authenticate(self, token): ..."
    },
    {
      "id":      "auth/token_validator.py::TokenValidator",
      "label":   "TokenValidator",
      "type":    "class",
      "file":    "auth/token_validator.py",
      "content": "class TokenValidator:\n    def validate(self, jwt): ..."
    }
  ],
  "edges": [
    {
      "source":   "auth/auth_service.py::AuthService",
      "target":   "auth/token_validator.py::TokenValidator",
      "relation": "calls"
    },
    {
      "source":   "auth/token_validator.py::TokenValidator",
      "target":   "auth/auth_service.py::AuthService",
      "relation": "depends_on"
    }
  ]
}
```

### Supported edge types

| Type | Meaning |
|------|---------|
| `calls` | Function/method A calls B |
| `depends_on` | Module A imports or depends on B |
| `semantically_similar_to` | A and B are semantically related |
| `rationale_for` | A explains why B exists |

### Fallback behaviour

If no seed nodes match the query keywords, Graphify falls back to returning the `GRAPH_REPORT.md` content (first 2000 chars). Keep a human-readable architecture summary there.

---

## ABCs and registries

Every layer follows the same pattern: one ABC in `base.py`, multiple backends in `layers/<name>.py`, one registry dict at the bottom.

```
base.py                         layers/<name>.py
──────────────────────          ─────────────────────────────────────
PromptOptimizerBackend  ←──     RuleBasedOptimizerBackend
                        ←──     LLMOptimizerBackend
                        ←──     PassthroughOptimizerBackend
                                OPTIMIZER_BACKENDS = {"rules": ..., "llm": ..., ...}

CacheBackend            ←──     MemoryCacheBackend
                        ←──     RedisCacheBackend
                        ←──     QdrantCacheBackend
                                CACHE_BACKENDS = {"memory": ..., "redis": ..., ...}

RewriterBackend         ←──     LLMRewriterBackend
                        ←──     HyDERewriterBackend
                        ←──     PassthroughRewriterBackend

RetrieverBackend        ←──     GraphifyRetrieverBackend
                        ←──     MemoryRetrieverBackend
                        ←──     ChromaRetrieverBackend
                        ←──     PineconeRetrieverBackend
                        ←──     WeaviateRetrieverBackend

CompressorBackend       ←──     RerankerCompressorBackend
                        ←──     LLMLinguaCompressorBackend
                        ←──     PassthroughCompressorBackend

PromptCacheBackend      ←──     AnthropicPromptCacheBackend
                        ←──     OpenAIPromptCacheBackend
                        ←──     NoPromptCacheBackend
```

`pipeline.py` is the **only file** that imports from multiple layers. No layer file imports another layer file.

---

## LLM Provider Adapters

```mermaid
flowchart LR
    CFG["ragstack.config.yaml\nllm.provider: X"] --> PL["pipeline.py\nfrom_config()"]
    PL -->|anthropic| A["_AnthropicAdapter\n.chat(model, messages, system, max_tokens)"]
    PL -->|openai| B["_OpenAIAdapter\n.chat(...)"]
    PL -->|gemini| C["_GeminiAdapter\n.chat(...)"]
    PL -->|ollama| D["_OllamaAdapter\n.chat(...)"]
```

All adapters expose the same `.chat()` interface. The pipeline never imports a provider SDK at module level — each adapter does a lazy `import` inside `_get()`.

---

## MCP Integration

```mermaid
sequenceDiagram
    participant CC as Claude Code
    participant MCP as mcp_server.py
    participant RS as RAGStack pipeline
    participant DB as ragstack-docs.json

    CC->>MCP: tool call: rag_query("how does auth work?")
    MCP->>MCP: _get_stack() — lazy init on first call
    MCP->>DB: load indexed docs on startup
    MCP->>RS: stack.query("how does auth work?")
    RS->>RS: L0 → L1 → L2 → L3 → L4 → L5 → LLM
    RS-->>MCP: answer + source citations
    MCP-->>CC: tool result
    CC->>CC: display answer in conversation

    note over MCP,DB: rag_ingest_* tools append to DB and write back to disk
```

The MCP server starts lazy — `RAGStack.from_config()` only runs on the first tool call.

---

## Cache Hit vs Miss Flow

```mermaid
flowchart TD
    Q[optimized_query] --> EMPTY{Cache\nempty?}
    EMPTY -->|Yes| MISS2[Skip embed call\nReturn None]
    EMPTY -->|No| EMB[Embed query\nOpenAI API call]
    EMB --> COS{Cosine similarity\n≥ threshold?}
    COS -->|Yes — HIT| RET([Return cached answer\nSkip L2–L5 entirely])
    COS -->|No — MISS| CONT([Continue to L2])
    MISS2 --> CONT

    style RET fill:#16a34a,color:#fff
```

The empty-cache short-circuit means **zero embedding API calls** on a fresh pipeline (no `OPENAI_API_KEY` needed when cache is empty).

---

## Adding a New Backend — Step by Step

Example: adding a **Milvus** retriever.

### 1. Implement the class in `layers/retriever.py`

```python
class MilvusRetrieverBackend(RetrieverBackend):
    def __init__(self, embedder, uri: str, collection: str):
        from pymilvus import MilvusClient   # lazy import
        self._embedder   = embedder
        self._client     = MilvusClient(uri=uri)
        self._collection = collection

    def retrieve(self, query: str, top_k: int) -> list[dict]:
        vec = self._embedder.embed(query)
        results = self._client.search(
            collection_name=self._collection,
            data=[vec], limit=top_k,
            output_fields=["text", "source"],
        )
        return [
            {"text": r["entity"]["text"], "source": r["entity"]["source"],
             "score": r["distance"], "metadata": {}}
            for r in results[0]
        ]
```

### 2. Add one line to the registry

```python
RETRIEVER_BACKENDS["milvus"] = MilvusRetrieverBackend
```

### 3. Wire it in `pipeline.py` `from_config()`

```python
elif ret_backend_name == "milvus":
    m_cfg = ret_cfg.get("milvus", {})
    retriever = RETRIEVER_BACKENDS["milvus"](
        embedder=embedder,
        uri=m_cfg.get("uri", "http://localhost:19530"),
        collection=m_cfg.get("collection", "ragstack_docs"),
    )
```

### 4. Update `ragstack.config.yaml`

```yaml
retriever:
  backend: milvus
  milvus:
    uri: http://localhost:19530
    collection: ragstack_docs
```

### 5. Done

Every other layer, the MCP server, GUI, and slash commands work with zero additional changes. Restart Claude Code and the new backend is active.

---

## Dependency Policy

| Rule | Why |
|------|-----|
| Never import a backend SDK at module level | Zero-dep backends remain importable without optional packages |
| Never import one layer from another layer | Keeps coupling explicit and testable in isolation |
| All config values come from YAML | No hardcoded model names, URLs, or thresholds |
| Passthrough / memory backends always available | Any stack runs with zero external services |
