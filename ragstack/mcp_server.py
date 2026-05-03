#!/usr/bin/env python3
"""
ragstack/mcp_server.py — RAGStack MCP Server

Registers RAGStack as a set of tools inside Claude Code (or any MCP host).
After running install.py once, Claude sees these tools in every conversation
and can call them automatically when you ask about your codebase.

Usage (managed by install.py — you normally don't run this directly):
    python mcp_server.py --config /abs/path/ragstack.config.yaml \
                         --docs-db  /abs/path/ragstack-docs.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ── globals (set before mcp.run()) ──────────────────────────────────────────
_config_path: str = "ragstack.config.yaml"
_docs_db_path: str | None = None
_stack = None  # lazy-initialised on first tool call


def _get_stack():
    global _stack
    if _stack is not None:
        return _stack

    # Make ragstack importable even when called from a foreign cwd
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from ragstack.pipeline import RAGStack

    _stack = RAGStack.from_config(_config_path)

    # Re-hydrate previously indexed docs from the JSON store
    if _docs_db_path:
        db = Path(_docs_db_path)
        if db.exists() and db.stat().st_size > 2:
            try:
                persisted: list[dict] = json.loads(db.read_text())
                if persisted and hasattr(_stack._retriever, "add_docs"):
                    _stack._retriever.add_docs(persisted)
                    _log(f"Loaded {len(persisted)} persisted chunks from {db.name}")
            except Exception as exc:
                _log(f"Warning: could not load docs DB — {exc}")

    return _stack


def _persist(chunks: list[dict]) -> None:
    """Append *chunks* to the JSON docs store (creates it if absent)."""
    if not _docs_db_path:
        return
    db = Path(_docs_db_path)
    existing: list[dict] = []
    if db.exists() and db.stat().st_size > 2:
        try:
            existing = json.loads(db.read_text())
        except Exception:
            pass
    existing.extend(chunks)
    db.write_text(json.dumps(existing, ensure_ascii=False))


def _log(msg: str) -> None:
    print(f"[ragstack-mcp] {msg}", file=sys.stderr, flush=True)


# ── MCP server ───────────────────────────────────────────────────────────────

from mcp.server.fastmcp import FastMCP  # noqa: E402  (lazy dep — only needed at runtime)

mcp = FastMCP(
    "RAGStack",
    instructions="""
RAGStack is your semantic codebase search pipeline.

Typical workflow:
  1. rag_ingest_directory("path/to/project") — index files once per session
  2. rag_query("how does X work?")           — get grounded answers with citations

Tool cheatsheet:
  rag_query            Search indexed docs, return a cited answer
  rag_ingest_file      Index a single file
  rag_ingest_directory Index all code/doc files in a directory tree
  rag_ingest_text      Add a raw text snippet with a source label
  rag_status           Show backends, doc count, cache size
  rag_clear_cache      Flush the semantic cache (force fresh retrieval)
""".strip(),
)


@mcp.tool()
def rag_query(query: str) -> str:
    """
    Search the indexed codebase and return a grounded answer with source citations.

    If no documents have been indexed yet, returns a hint to call
    rag_ingest_directory first.  Leverages all 5 RAGStack layers:
    semantic cache → query rewriting → retrieval → reranking → prompt caching.
    """
    try:
        stack = _get_stack()
        if len(getattr(stack._retriever, "_docs", [])) == 0:
            return (
                "No documents indexed yet.\n"
                "Call rag_ingest_directory('path/to/your/project') first, "
                "then retry your query."
            )
        return stack.query(query)
    except Exception as exc:
        return f"[RAGStack error] {exc}"


@mcp.tool()
def rag_ingest_file(path: str) -> str:
    """
    Index a single file into RAGStack.

    The file is chunked into overlapping 80-line windows and added to the
    retriever.  Chunks persist across server restarts via the docs JSON store.
    """
    try:
        from ragstack.ingest import ingest_file
        chunks = ingest_file(path)
        if not chunks:
            return f"No content extracted from {path!r} (file empty or unreadable)."
        stack = _get_stack()
        total = stack.ingest_docs(chunks)
        _persist(chunks)
        return f"Indexed {len(chunks)} chunk(s) from {path!r}. Total indexed: {total}."
    except TypeError as exc:
        return f"[RAGStack] {exc}"
    except Exception as exc:
        return f"[RAGStack error] {exc}"


@mcp.tool()
def rag_ingest_directory(
    directory: str,
    extensions: str = ".py,.js,.ts,.go,.rs,.java,.md,.txt,.yaml,.toml",
) -> str:
    """
    Recursively index all matching files in a directory.

    *extensions* — comma-separated list (e.g. '.py,.md').  Skips .git,
    node_modules, __pycache__, .venv, and other noise directories automatically.
    Chunks persist across server restarts.
    """
    try:
        from ragstack.ingest import ingest_directory
        ext_set = {
            e.strip() if e.strip().startswith(".") else f".{e.strip()}"
            for e in extensions.split(",")
            if e.strip()
        }
        chunks, file_count = ingest_directory(directory, extensions=ext_set)
        if not chunks:
            return (
                f"No files found in {directory!r} matching {extensions!r}.\n"
                "Check the path and extension list."
            )
        stack = _get_stack()
        total = stack.ingest_docs(chunks)
        _persist(chunks)
        return (
            f"Indexed {len(chunks)} chunk(s) from {file_count} file(s) "
            f"in {directory!r}. Total indexed: {total}."
        )
    except TypeError as exc:
        return f"[RAGStack] {exc}"
    except Exception as exc:
        return f"[RAGStack error] {exc}"


@mcp.tool()
def rag_ingest_text(text: str, source: str = "manual") -> str:
    """
    Add a raw text snippet to RAGStack with a source label.

    Useful for pasting API specs, architecture notes, or any text you want
    Claude to be able to cite when answering questions.
    """
    try:
        if not text.strip():
            return "Empty text — nothing to index."
        chunk = [{"text": text, "source": source, "score": 0.0, "metadata": {}}]
        stack = _get_stack()
        total = stack.ingest_docs(chunk)
        _persist(chunk)
        return f"Added text snippet (source: {source!r}). Total indexed: {total}."
    except TypeError as exc:
        return f"[RAGStack] {exc}"
    except Exception as exc:
        return f"[RAGStack error] {exc}"


@mcp.tool()
def rag_status() -> str:
    """
    Show a summary of the active RAGStack configuration.

    Reports: retriever backend & indexed doc count, compressor, rewriter,
    semantic cache size, LLM model, and config file path.
    """
    try:
        stack = _get_stack()
        s = stack.status()
        lines = [
            "RAGStack Status",
            "─" * 42,
            f"  Retriever    : {s['retriever']}",
            f"  Indexed docs : {s['indexed_docs']} chunks",
            f"  Compressor   : {s['compressor']}",
            f"  Rewriter     : {s['rewriter']}",
            f"  Cache        : {s['cache']} ({s['cached_queries']} entries)",
            f"  Prompt cache : {s['prompt_cache']}",
            f"  LLM model    : {s['llm_model']}",
            f"  Config       : {_config_path}",
        ]
        if _docs_db_path:
            db = Path(_docs_db_path)
            lines.append(f"  Docs DB      : {_docs_db_path} ({db.stat().st_size if db.exists() else 0} bytes)")
        return "\n".join(lines)
    except Exception as exc:
        return f"[RAGStack error] {exc}"


@mcp.tool()
def rag_clear_cache() -> str:
    """
    Flush the semantic cache.

    Forces the next queries to go through the full retrieval pipeline
    instead of returning a cached answer.
    """
    try:
        stack = _get_stack()
        cleared = stack.clear_cache()
        return f"Cleared {cleared} cache entr{'y' if cleared == 1 else 'ies'}."
    except Exception as exc:
        return f"[RAGStack error] {exc}"


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    global _config_path, _docs_db_path

    parser = argparse.ArgumentParser(description="RAGStack MCP Server")
    parser.add_argument(
        "--config", default=None,
        help="Absolute path to ragstack.config.yaml (default: ./ragstack.config.yaml)",
    )
    parser.add_argument(
        "--docs-db", default=None,
        help="Absolute path to JSON file used to persist indexed docs across restarts",
    )
    args = parser.parse_args()

    if args.config:
        _config_path = args.config

    _docs_db_path = args.docs_db or str(Path(_config_path).parent / "ragstack-docs.json")

    _log(f"Starting — config: {_config_path}")
    _log(f"Docs DB : {_docs_db_path}")
    mcp.run()


if __name__ == "__main__":
    main()
