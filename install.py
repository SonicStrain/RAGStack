#!/usr/bin/env python3
"""
RAGStack — one-click installer
════════════════════════════════════════════════════════════════════════════════
Run once from your project root:

    python install.py

What it does:
  1. Checks Python >= 3.10
  2. Installs core Python dependencies (mcp, anthropic, pyyaml, numpy)
  3. Copies ragstack.config.yaml to your project root (if absent)
  4. Creates an empty ragstack-docs.json persistence store
  5. Registers RAGStack as an MCP server in ~/.claude/settings.json
     → Claude Code picks it up automatically on next restart

To unregister:
    python install.py --uninstall

To install optional backends (redis, chroma, reranker, …):
    python install.py --extras redis reranker chroma
════════════════════════════════════════════════════════════════════════════════
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# ── paths ────────────────────────────────────────────────────────────────────
HERE = Path(__file__).parent.resolve()
RAGSTACK_DIR = HERE / "ragstack"
MCP_SERVER = RAGSTACK_DIR / "mcp_server.py"
CONFIG_TEMPLATE = RAGSTACK_DIR / "ragstack.config.yaml"

# ── dependency sets ──────────────────────────────────────────────────────────
CORE_DEPS = [
    "mcp[cli]>=1.0",
    "anthropic>=0.40.0",
    "pyyaml>=6.0",
    "numpy>=1.24",
    "gradio>=4.0",
    "pandas>=2.0",
    "matplotlib>=3.9",
]

OPTIONAL_EXTRAS: dict[str, list[str]] = {
    "openai":    ["openai>=1.0"],                             # embeddings + LLM
    "redis":     ["redis[hiredis]>=5.0"],                     # cache: redis
    "qdrant":    ["qdrant-client>=1.7"],                      # cache: qdrant
    "reranker":  ["sentence-transformers>=2.0"],               # compressor: reranker
    "llmlingua": ["llmlingua>=0.2"],                          # compressor: llmlingua
    "chroma":    ["chromadb>=0.4"],                           # retriever: chroma
    "pinecone":  ["pinecone-client>=3.0"],                    # retriever: pinecone
    "weaviate":  ["weaviate-client>=4.0"],                    # retriever: weaviate
    "gemini":    ["google-generativeai>=0.5"],                # LLM: gemini
    "ollama":    ["ollama>=0.2"],                             # LLM: ollama
}

MCP_SERVER_NAME = "ragstack"


# ── helpers ──────────────────────────────────────────────────────────────────

def _pip(*packages: str) -> bool:
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-q", "--upgrade", *packages],
        capture_output=True, text=True,
    )
    return result.returncode == 0


def _claude_settings_path() -> Path:
    return Path.home() / ".claude" / "settings.json"


def _load_settings(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save_settings(path: Path, settings: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2, ensure_ascii=False), encoding="utf-8")


def _box(lines: list[str], width: int = 64) -> str:
    top    = "╔" + "═" * (width - 2) + "╗"
    bottom = "╚" + "═" * (width - 2) + "╝"
    mid    = [f"║  {ln:<{width - 4}}║" for ln in lines]
    return "\n".join([top, *mid, bottom])


def _step(n: int, total: int, msg: str) -> None:
    print(f"\n[{n}/{total}] {msg}")


def _ok(msg: str)   -> None: print(f"  ✓  {msg}")
def _warn(msg: str) -> None: print(f"  ⚠  {msg}")
def _fail(msg: str) -> None: print(f"  ✗  {msg}")


# ── slash command templates ───────────────────────────────────────────────────

_SLASH_COMMANDS: dict[str, str] = {
    "rag-query": """\
Search the indexed codebase using RAGStack and answer the following question: $ARGUMENTS

Steps:
1. Call `rag_status` to confirm documents are indexed. If indexed_docs is 0, call `rag_ingest_directory` on the project root first, then proceed.
2. Call `rag_query` with the question above.
3. Present the answer with source citations clearly highlighted.

If no arguments were provided, ask the user what they want to search for.
""",
    "rag-index": """\
Index files into RAGStack so they can be searched.

Target: $ARGUMENTS

Steps:
1. If no path was given in $ARGUMENTS, use "." (the current project root).
2. Call `rag_ingest_directory` on the target path.
   - Default extensions cover: .py .js .ts .go .rs .java .md .txt .yaml .toml
   - To restrict to specific types, mention them (e.g. "only .py and .md files")
3. After indexing, call `rag_status` and report:
   - How many files and chunks were indexed
   - Which retriever backend is active
   - Total indexed docs now available

Tip: re-running this command on the same directory adds new/changed files to
the index (duplicates are harmless — the retriever scores by relevance).
""",
    "rag-status": """\
Show the current RAGStack configuration and health summary.

Call `rag_status` and display the result in a clean table, including:
- Active backend for each of the 6 layers (optimizer, cache, rewriter, retriever, compressor, prompt_cache)
- Number of indexed document chunks
- Number of cached query responses
- LLM model in use
- Config file path

Then give a one-line assessment: is RAGStack ready to answer questions, or does
the user need to index documents first?
""",
    "rag-clear": """\
Flush the RAGStack semantic cache so the next queries are retrieved fresh.

Steps:
1. Call `rag_clear_cache`.
2. Report how many cache entries were cleared.
3. Confirm with a follow-up `rag_status` showing cached_queries is now 0.

Use this when:
- You have updated source files and want fresh answers
- A cached answer looked stale or incorrect
- You are testing pipeline changes and want to bypass the cache
""",
    "rag-add": """\
Add a raw text snippet to RAGStack's index so it can be retrieved later.

Text to add: $ARGUMENTS

Steps:
1. Parse the input: the text to index is everything in $ARGUMENTS.
   - If it starts with a quoted source label like [auth-spec]:, use that as the source name.
   - Otherwise, default source label is "manual".
2. Call `rag_ingest_text` with the text and source label.
3. Confirm how many total chunks are now indexed.

Example usage:
  /rag-add [api-spec]: All POST /auth/login requests must include a CSRF token header.
  /rag-add The database uses PostgreSQL 15 with pgvector for embeddings.
""",
}


def _install_slash_commands(project_root: Path) -> None:
    """Write .claude/commands/<name>.md files into the project."""
    commands_dir = project_root / ".claude" / "commands"
    commands_dir.mkdir(parents=True, exist_ok=True)
    for name, content in _SLASH_COMMANDS.items():
        dest = commands_dir / f"{name}.md"
        dest.write_text(content, encoding="utf-8")
        _ok(f"/{name}  →  {dest.relative_to(project_root)}")


# ── install ──────────────────────────────────────────────────────────────────

def install(extras: list[str]) -> None:
    total = 6
    print(_box([
        "RAGStack — One-Click Setup",
        "",
        f"Python  : {sys.version.split()[0]}",
        f"Platform: {platform.system()} {platform.machine()}",
        f"Project : {HERE}",
    ]))

    # ── 1. Python version check ───────────────────────────────────────────────
    _step(1, total, "Checking Python version")
    if sys.version_info < (3, 10):
        _fail(f"Python 3.10+ required — you have {sys.version.split()[0]}")
        sys.exit(1)
    _ok(f"Python {sys.version.split()[0]} ✓")

    # ── 2. Install dependencies ───────────────────────────────────────────────
    _step(2, total, "Installing core dependencies")
    for dep in CORE_DEPS:
        if _pip(dep):
            _ok(dep)
        else:
            _fail(f"Failed to install {dep}")
            _warn("Try: python -m pip install " + dep)
            sys.exit(1)

    if extras:
        print(f"\n  Installing extras: {', '.join(extras)}")
        for name in extras:
            pkgs = OPTIONAL_EXTRAS.get(name)
            if not pkgs:
                _warn(f"Unknown extra {name!r} — skipping (valid: {', '.join(OPTIONAL_EXTRAS)})")
                continue
            if _pip(*pkgs):
                _ok(f"{name}: {', '.join(pkgs)}")
            else:
                _warn(f"Could not install {name} extras — continuing")

    # ── 3. Project config & docs DB ───────────────────────────────────────────
    _step(3, total, "Setting up project files")

    config_dst = HERE / "ragstack.config.yaml"
    if config_dst.exists():
        _ok(f"Config already exists: {config_dst.name}")
    else:
        shutil.copy(CONFIG_TEMPLATE, config_dst)
        _ok(f"Created: {config_dst.name}")

    docs_db = HERE / "ragstack-docs.json"
    if not docs_db.exists():
        docs_db.write_text("[]", encoding="utf-8")
        _ok(f"Created: {docs_db.name}")
    else:
        _ok(f"Docs DB already exists: {docs_db.name}")

    # ── 4. Register MCP server ────────────────────────────────────────────────
    _step(4, total, "Registering MCP server with Claude Code")

    settings_path = _claude_settings_path()
    settings = _load_settings(settings_path)

    settings.setdefault("mcpServers", {})[MCP_SERVER_NAME] = {
        "command": sys.executable,
        "args": [
            str(MCP_SERVER),
            "--config", str(config_dst),
            "--docs-db", str(docs_db),
        ],
        "env": {
            # Ensure ragstack package is importable from the server process
            "PYTHONPATH": str(HERE),
        },
    }

    _save_settings(settings_path, settings)
    _ok(f"Registered in: {settings_path}")
    _ok(f"  command : {sys.executable}")
    _ok(f"  config  : {config_dst}")
    _ok(f"  docs-db : {docs_db}")

    # ── 5. Create slash commands ──────────────────────────────────────────────
    _step(5, total, "Installing slash commands into .claude/commands/")
    _install_slash_commands(HERE)

    # ── 6. Smoke test ────────────────────────────────────────────────────────
    _step(6, total, "Smoke-testing RAGStack import")
    sys.path.insert(0, str(HERE))
    try:
        import importlib
        importlib.import_module("ragstack")
        from ragstack.layers.cache      import CACHE_BACKENDS
        from ragstack.layers.retriever  import RETRIEVER_BACKENDS
        from ragstack.layers.compressor import COMPRESSOR_BACKENDS
        _ok("ragstack importable")
        _ok(f"cache backends     : {', '.join(CACHE_BACKENDS)}")
        _ok(f"retriever backends : {', '.join(RETRIEVER_BACKENDS)}")
        _ok(f"compressor backends: {', '.join(COMPRESSOR_BACKENDS)}")
    except Exception as exc:
        _fail(f"Import error: {exc}")
        sys.exit(1)

    # ── Done ─────────────────────────────────────────────────────────────────
    print()
    print(_box([
        "RAGStack is ready!",
        "",
        "Next steps:",
        "  1. Set API key(s):",
        "       export ANTHROPIC_API_KEY=sk-ant-...",
        "       export OPENAI_API_KEY=sk-...  (for embeddings)",
        "",
        "  2. Restart Claude Code",
        "",
        "  3. Launch the Pipeline Studio GUI:",
        "       python ragstack/gui.py",
        "       python ragstack/gui.py --port 7861 --share",
        "",
        "  4. Use slash commands in any conversation:",
        "       /rag-index .          <- index this project",
        "       /rag-query <question> <- search and answer",
        "       /rag-status           <- health check",
        "       /rag-clear            <- flush cache",
        "       /rag-add <text>       <- add a snippet",
        "",
        "  5. Or just ask naturally:",
        '       "Index my codebase and tell me how auth works"',
        "",
        "  6. Swap backends anytime — just edit ragstack.config.yaml",
        "     and restart Claude Code. Zero code changes needed.",
        "",
        f"  Config : {config_dst}",
        f"  Docs DB: {docs_db}",
    ]))


# ── uninstall ─────────────────────────────────────────────────────────────────

def uninstall() -> None:
    settings_path = _claude_settings_path()
    settings = _load_settings(settings_path)
    servers = settings.get("mcpServers", {})
    if MCP_SERVER_NAME in servers:
        del servers[MCP_SERVER_NAME]
        _save_settings(settings_path, settings)
        print(f"✓ Removed '{MCP_SERVER_NAME}' from {settings_path}")
    else:
        print(f"'{MCP_SERVER_NAME}' was not registered — nothing to do.")


# ── entry ─────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description="RAGStack one-click installer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="\n".join([
            "Examples:",
            "  python install.py                          # core only",
            "  python install.py --extras redis reranker  # + optional backends",
            "  python install.py --uninstall              # remove MCP registration",
        ]),
    )
    parser.add_argument(
        "--extras", nargs="*", default=[],
        metavar="NAME",
        help=f"Optional backend extras to install. Choices: {', '.join(OPTIONAL_EXTRAS)}",
    )
    parser.add_argument(
        "--uninstall", action="store_true",
        help="Remove RAGStack from Claude Code MCP settings",
    )
    args = parser.parse_args()

    if args.uninstall:
        uninstall()
    else:
        install(args.extras or [])


if __name__ == "__main__":
    main()
