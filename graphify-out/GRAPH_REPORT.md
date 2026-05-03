# Graph Report - .  (2026-05-03)

## Corpus Check
- Corpus is ~23,986 words - fits in a single context window. You may not need a graph.

## Summary
- 334 nodes · 542 edges · 21 communities detected
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 107 edges (avg confidence: 0.58)
- Token cost: 18,500 input · 4,200 output

## Community Hubs (Navigation)
- [[_COMMUNITY_Backend Implementations|Backend Implementations]]
- [[_COMMUNITY_Abstract Base Classes|Abstract Base Classes]]
- [[_COMMUNITY_GUI & User Interface|GUI & User Interface]]
- [[_COMMUNITY_Document Ingestion|Document Ingestion]]
- [[_COMMUNITY_Retriever Backends|Retriever Backends]]
- [[_COMMUNITY_Query Optimizer Backends|Query Optimizer Backends]]
- [[_COMMUNITY_Chunking & Ingest Integration|Chunking & Ingest Integration]]
- [[_COMMUNITY_CLI Installer|CLI Installer]]
- [[_COMMUNITY_Architecture & QueryContext|Architecture & QueryContext]]
- [[_COMMUNITY_Vector Cache Backends|Vector Cache Backends]]
- [[_COMMUNITY_Compressor Backends|Compressor Backends]]
- [[_COMMUNITY_Query Rewriter Backends|Query Rewriter Backends]]
- [[_COMMUNITY_Prompt Cache Backends|Prompt Cache Backends]]
- [[_COMMUNITY_Docs & GUI Presets|Docs & GUI Presets]]
- [[_COMMUNITY_MCP Server & Registration|MCP Server & Registration]]
- [[_COMMUNITY_HTML Docs Generator|HTML Docs Generator]]
- [[_COMMUNITY_Demo Example|Demo Example]]
- [[_COMMUNITY_Cache Key Strategy|Cache Key Strategy]]
- [[_COMMUNITY_Query Form Selection|Query Form Selection]]
- [[_COMMUNITY_Optimized Prompt Form|Optimized Prompt Form]]
- [[_COMMUNITY_Optimizer Stats|Optimizer Stats]]

## God Nodes (most connected - your core abstractions)
1. `RAGStack.from_config()` - 23 edges
2. `RAGStack` - 16 edges
3. `RetrieverBackend` - 15 edges
4. `PromptOptimizerBackend` - 14 edges
5. `_Embedder` - 14 edges
6. `_OllamaEmbedder` - 14 edges
7. `MemoryCacheBackend` - 14 edges
8. `CacheBackend` - 13 edges
9. `RewriterBackend` - 13 edges
10. `CompressorBackend` - 13 edges

## Surprising Connections (you probably didn't know these)
- `RuleBasedOptimizerBackend` --uses--> `PromptOptimizerBackend`  [INFERRED]
  ragstack\layers\optimizer.py → ragstack\base.py
- `LLMOptimizerBackend` --uses--> `PromptOptimizerBackend`  [INFERRED]
  ragstack\layers\optimizer.py → ragstack\base.py
- `PassthroughOptimizerBackend` --uses--> `PromptOptimizerBackend`  [INFERRED]
  ragstack\layers\optimizer.py → ragstack\base.py
- `RedisCacheBackend` --uses--> `CacheBackend`  [INFERRED]
  ragstack\layers\cache.py → ragstack\base.py
- `QdrantCacheBackend` --uses--> `CacheBackend`  [INFERRED]
  ragstack\layers\cache.py → ragstack\base.py

## Hyperedges (group relationships)
- **6-Layer RAGStack Query Pipeline Flow** — layers_optimizer_RuleBasedOptimizerBackend, layers_cache_MemoryCacheBackend, layers_rewriter_LLMRewriterBackend, layers_retriever_GraphifyRetrieverBackend, layers_compressor_PassthroughCompressorBackend, layers_prompt_cache_AnthropicPromptCacheBackend, base_QueryContext [EXTRACTED 1.00]
- **MCP Ingestion Pipeline (tool -> ingest -> persist -> retriever)** — mcp_server_rag_ingest_file, mcp_server_rag_ingest_directory, mcp_server_rag_ingest_text, ingest_ingest_directory, ingest_ingest_file, pipeline_RAGStack_ingest_docs, mcp_server_persist [EXTRACTED 1.00]
- **ABC + Backend Registry Pattern (all 6 layers)** — base_PromptOptimizerBackend, base_CacheBackend, base_RewriterBackend, base_RetrieverBackend, base_CompressorBackend, base_PromptCacheBackend, pipeline_RAGStack_from_config [EXTRACTED 1.00]

## Communities

### Community 0 - "Backend Implementations"
Cohesion: 0.06
Nodes (29): ABC, MemoryCacheBackend, CacheBackend, CompressorBackend, PromptCacheBackend, PromptOptimizerBackend, QueryContext, Layer 0 — trim tokens from the user prompt before anything else runs. (+21 more)

### Community 1 - "Abstract Base Classes"
Cohesion: 0.07
Nodes (41): CacheBackend (ABC), CompressorBackend (ABC), PromptCacheBackend (ABC), PromptOptimizerBackend (ABC), RetrieverBackend (ABC), RewriterBackend (ABC), Graphify External Tool (graphifyy package), MemoryCacheBackend (+33 more)

### Community 2 - "GUI & User Interface"
Cohesion: 0.12
Nodes (32): apply_preset(), apply_yaml(), _bar(), build_ui(), clear_chat(), _deep_update(), do_add_text(), do_clear_cache() (+24 more)

### Community 3 - "Document Ingestion"
Cohesion: 0.12
Nodes (24): chunk_text(), ingest_directory(), ingest_file(), ragstack/ingest.py — file & directory chunker.  Splits source files into overlap, Split *text* into overlapping line-window chunks., Read *path* and return a list of chunk dicts, or [] on error., Walk *directory* recursively and chunk every matching file.      Returns (chunks, _get_stack() (+16 more)

### Community 4 - "Retriever Backends"
Cohesion: 0.11
Nodes (8): ChromaRetrieverBackend, GraphifyRetrieverBackend, MemoryRetrieverBackend, PineconeRetrieverBackend, Zero-dependency backend. Accepts docs at init; supports dynamic add_docs()., Append documents at runtime. Returns new total count., WeaviateRetrieverBackend, RetrieverBackend

### Community 5 - "Query Optimizer Backends"
Cohesion: 0.18
Nodes (12): _apply_rules(), LLMOptimizerBackend, PassthroughOptimizerBackend, ragstack/layers/optimizer.py — Layer 0: Prompt Optimizer  Trims tokens from the, LLM-powered optimizer. Uses a cheap fast model (default: Haiku) so the     cost, No-op. Returns the prompt unchanged. Use when latency budget is tight., ~4 chars per token — matches OpenAI/Anthropic average for English prose., Zero-dependency optimizer using hand-crafted regex rules.     Strips filler pref (+4 more)

### Community 6 - "Chunking & Ingest Integration"
Cohesion: 0.16
Nodes (15): gui.do_index_dir(), ingest.chunk_text(), ingest.ingest_directory(), ingest.ingest_file(), Overlapping Line-Window Chunking Strategy, RAGStack Slash Commands, MemoryRetrieverBackend, ragstack-docs.json Persistence Store (+7 more)

### Community 7 - "CLI Installer"
Cohesion: 0.29
Nodes (14): _box(), _claude_settings_path(), _fail(), install(), _install_slash_commands(), _load_settings(), main(), _ok() (+6 more)

### Community 8 - "Architecture & QueryContext"
Cohesion: 0.18
Nodes (10): QueryContext, Shared QueryContext Data Flow Pattern, RAGStack Demo (example.py), gui.submit_query(), rag_query MCP tool, RAGStack (pipeline), RAGStack.answer_from_inspection(), RAGStack.inspect() (+2 more)

### Community 9 - "Vector Cache Backends"
Cohesion: 0.18
Nodes (4): CacheBackend, _cosine(), QdrantCacheBackend, RedisCacheBackend

### Community 10 - "Compressor Backends"
Cohesion: 0.23
Nodes (4): CompressorBackend, LLMLinguaCompressorBackend, PassthroughCompressorBackend, RerankerCompressorBackend

### Community 11 - "Query Rewriter Backends"
Cohesion: 0.22
Nodes (5): HyDERewriterBackend, LLMRewriterBackend, PassthroughRewriterBackend, Hypothetical Document Embedding — embed a generated answer, not the raw query., RewriterBackend

### Community 12 - "Prompt Cache Backends"
Cohesion: 0.24
Nodes (6): AnthropicPromptCacheBackend, NoPromptCacheBackend, OpenAIPromptCacheBackend, OpenAI caches prompts automatically for requests >= 1024 tokens.     No special, Returns messages structured for Anthropic's prompt caching API.     The system p, PromptCacheBackend

### Community 13 - "Docs & GUI Presets"
Cohesion: 0.22
Nodes (7): docs.get_docs_html(), RAGStack HTML Documentation Page, gui.apply_preset(), gui.build_ui(), FastAPI /ragstack-docs Route, GUI Quick Presets Configuration, static/docs.html (served file)

### Community 14 - "MCP Server & Registration"
Cohesion: 0.4
Nodes (4): install.py install(), MCP Server Registration Pattern, Lazy Pipeline Initialization Pattern, RAGStack MCP Server (FastMCP)

### Community 15 - "HTML Docs Generator"
Cohesion: 0.4
Nodes (4): get_docs_html(), ragstack/docs.py — Documentation HTML generator  Returns a self-contained HTML p, Return the full docs HTML page., _write_docs_file()

### Community 16 - "Demo Example"
Cohesion: 1.0
Nodes (1): RAGStack demo — uses memory retriever, passthrough compressor, and memory cache

### Community 20 - "Cache Key Strategy"
Cohesion: 1.0
Nodes (1): Stable key for semantic cache — uses optimized (normalized) query.

### Community 21 - "Query Form Selection"
Cohesion: 1.0
Nodes (1): For retrieval: richest form (rewritten > optimized > original).

### Community 22 - "Optimized Prompt Form"
Cohesion: 1.0
Nodes (1): What the LLM sees as the user question — concise optimized form.

### Community 23 - "Optimizer Stats"
Cohesion: 1.0
Nodes (1): Return (optimized_prompt, stats).         stats keys: original_tokens, optimized

## Knowledge Gaps
- **67 isolated node(s):** `Write .claude/commands/<name>.md files into the project.`, `Stable key for semantic cache — uses optimized (normalized) query.`, `For retrieval: richest form (rewritten > optimized > original).`, `What the LLM sees as the user question — concise optimized form.`, `Layer 0 — trim tokens from the user prompt before anything else runs.` (+62 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **Thin community `Demo Example`** (2 nodes): `example.py`, `RAGStack demo — uses memory retriever, passthrough compressor, and memory cache`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Cache Key Strategy`** (1 nodes): `Stable key for semantic cache — uses optimized (normalized) query.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Query Form Selection`** (1 nodes): `For retrieval: richest form (rewritten > optimized > original).`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Optimized Prompt Form`** (1 nodes): `What the LLM sees as the user question — concise optimized form.`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.
- **Thin community `Optimizer Stats`** (1 nodes): `Return (optimized_prompt, stats).         stats keys: original_tokens, optimized`
  Too small to be a meaningful cluster - may be noise or needs more connections extracted.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `RetrieverBackend` connect `Backend Implementations` to `Retriever Backends`?**
  _High betweenness centrality (0.061) - this node is a cross-community bridge._
- **Why does `PromptOptimizerBackend` connect `Backend Implementations` to `Query Optimizer Backends`?**
  _High betweenness centrality (0.040) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `RAGStack` (e.g. with `CacheBackend` and `CompressorBackend`) actually correct?**
  _`RAGStack` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `RetrieverBackend` (e.g. with `_AnthropicAdapter` and `_OpenAIAdapter`) actually correct?**
  _`RetrieverBackend` has 13 INFERRED edges - model-reasoned connections that need verification._
- **Are the 11 inferred relationships involving `PromptOptimizerBackend` (e.g. with `_AnthropicAdapter` and `_OpenAIAdapter`) actually correct?**
  _`PromptOptimizerBackend` has 11 INFERRED edges - model-reasoned connections that need verification._
- **Are the 8 inferred relationships involving `_Embedder` (e.g. with `CacheBackend` and `CompressorBackend`) actually correct?**
  _`_Embedder` has 8 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Write .claude/commands/<name>.md files into the project.`, `Stable key for semantic cache — uses optimized (normalized) query.`, `For retrieval: richest form (rewritten > optimized > original).` to the rest of the system?**
  _67 weakly-connected nodes found - possible documentation gaps or missing edges._