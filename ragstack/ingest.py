"""
ragstack/ingest.py — file & directory chunker.

Splits source files into overlapping text chunks suitable for the
MemoryRetrieverBackend (or any retriever that accepts list[dict]).
No external dependencies required.
"""
from __future__ import annotations

import os
from pathlib import Path

# Directories that are never useful to index
_SKIP_DIRS: frozenset[str] = frozenset({
    ".git", ".hg", ".svn",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    "node_modules", ".pnp",
    ".venv", "venv", "env", ".env",
    "dist", "build", "out", ".next", ".nuxt", ".output",
    "coverage", ".nyc_output",
    "ragstack-docs.json",  # never index our own DB
})

# File extensions indexed by default
DEFAULT_EXTENSIONS: frozenset[str] = frozenset({
    # Code
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".go", ".rs", ".java", ".kt", ".swift",
    ".c", ".cpp", ".h", ".hpp", ".cs",
    ".rb", ".php", ".scala", ".ex", ".exs",
    ".sh", ".bash", ".zsh", ".fish",
    # Config / data
    ".yaml", ".yml", ".toml", ".ini", ".cfg", ".env.example",
    ".json", ".jsonc",
    # Docs
    ".md", ".mdx", ".rst", ".txt",
    # Web
    ".html", ".css", ".scss", ".sql",
})

# Chunk parameters
_CHUNK_LINES = 80
_OVERLAP_LINES = 15
_MAX_CHUNK_BYTES = 8_000  # guard against minified files


def chunk_text(text: str, source: str,
               chunk_lines: int = _CHUNK_LINES,
               overlap: int = _OVERLAP_LINES) -> list[dict]:
    """Split *text* into overlapping line-window chunks."""
    lines = text.splitlines()
    if not lines:
        return []

    chunks: list[dict] = []
    i = 0
    while i < len(lines):
        window = lines[i: i + chunk_lines]
        body = "\n".join(window).strip()
        if body and len(body.encode()) <= _MAX_CHUNK_BYTES:
            chunks.append({
                "text": body,
                "source": source,
                "score": 0.0,
                "metadata": {"start_line": i + 1, "end_line": i + len(window)},
            })
        i += chunk_lines - overlap

    return chunks


def ingest_file(path: str, chunk_lines: int = _CHUNK_LINES,
                overlap: int = _OVERLAP_LINES) -> list[dict]:
    """Read *path* and return a list of chunk dicts, or [] on error."""
    try:
        text = Path(path).read_text(encoding="utf-8", errors="replace")
    except (OSError, PermissionError) as exc:
        print(f"[ragstack] ingest: skipping {path} — {exc}")
        return []
    return chunk_text(text, source=path, chunk_lines=chunk_lines, overlap=overlap)


def ingest_directory(
    directory: str,
    extensions: set[str] | frozenset[str] | None = None,
    max_files: int = 1_000,
    chunk_lines: int = _CHUNK_LINES,
    overlap: int = _OVERLAP_LINES,
) -> tuple[list[dict], int]:
    """
    Walk *directory* recursively and chunk every matching file.

    Returns (chunks, file_count).  Skips hidden dirs and common noise
    dirs automatically.  *extensions* defaults to DEFAULT_EXTENSIONS.
    """
    exts = extensions if extensions is not None else DEFAULT_EXTENSIONS
    all_chunks: list[dict] = []
    file_count = 0

    for root, dirs, files in os.walk(directory, topdown=True):
        # Prune undesired directories in-place (affects os.walk traversal)
        dirs[:] = [
            d for d in dirs
            if d not in _SKIP_DIRS and not d.startswith(".")
        ]

        for fname in sorted(files):
            if file_count >= max_files:
                break
            if Path(fname).suffix.lower() not in exts:
                continue

            full_path = os.path.join(root, fname)
            chunks = ingest_file(full_path, chunk_lines=chunk_lines, overlap=overlap)
            if chunks:
                all_chunks.extend(chunks)
                file_count += 1

    return all_chunks, file_count
