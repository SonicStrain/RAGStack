#!/usr/bin/env python3
"""
ragstack/gui.py — RAGStack Pipeline Studio

A web-based GUI for inspecting the prompt pipeline and editing configuration.

Usage:
    python ragstack/gui.py
    python ragstack/gui.py --config /abs/path/ragstack.config.yaml
    python ragstack/gui.py --port 7861 --share

Tabs:
    Pipeline Studio  — chat window: input = query, output = pipeline inspection
    Configuration    — backend dropdowns + full YAML editor (bidirectionally synced)
    Status & Tools   — live backend health, index docs, clear cache
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import yaml
import gradio as gr

sys.path.insert(0, str(Path(__file__).parent.parent))

# ── App state ─────────────────────────────────────────────────────────────────

_stack = None
_config_path: str = str(Path(__file__).parent / "ragstack.config.yaml")
_session_saved_tokens: int = 0

# ── Docs static file (written once at import time) ────────────────────────────
# Gradio 6 strips srcdoc from iframes; we serve the HTML as a static file
# via allowed_paths and load it with a plain src= attribute instead.
_STATIC_DIR = Path(__file__).parent / "static"
_DOCS_FILE  = str(_STATIC_DIR / "docs.html")

def _write_docs_file() -> None:
    from ragstack.docs import get_docs_html
    _STATIC_DIR.mkdir(exist_ok=True)
    Path(_DOCS_FILE).write_text(get_docs_html(), encoding="utf-8")

_write_docs_file()


# ── Stack management ──────────────────────────────────────────────────────────

def _get_stack():
    global _stack
    if _stack is None:
        from ragstack.pipeline import RAGStack
        _stack = RAGStack.from_config(_config_path)
    return _stack


def _reload() -> str:
    global _stack
    _stack = None
    try:
        stack = _get_stack()
        s = stack.status()
        return (
            f"Reloaded. "
            f"Optimizer: {s['optimizer'].replace('Backend','')} | "
            f"Retriever: {s['retriever'].replace('Backend','')} "
            f"({s['indexed_docs']} docs) | LLM: {s['llm_model']}"
        )
    except Exception as exc:
        return f"Error reloading: {exc}"


def _read_cfg() -> dict:
    try:
        return yaml.safe_load(Path(_config_path).read_text(encoding="utf-8")) or {}
    except Exception:
        return {}


def _write_cfg(cfg: dict) -> str:
    text = yaml.dump(cfg, default_flow_style=False, allow_unicode=True, sort_keys=False)
    Path(_config_path).write_text(text, encoding="utf-8")
    return text


def load_yaml_text() -> str:
    try:
        return Path(_config_path).read_text(encoding="utf-8")
    except Exception as exc:
        return f"# Could not read config: {exc}"


# ── Form helpers ──────────────────────────────────────────────────────────────

def _form_tuple(cfg: dict) -> tuple:
    """Return the 14 form-field values extracted from a config dict."""
    L   = cfg.get("layers", {})
    llm = cfg.get("llm", {})
    return (
        L.get("optimizer",    {}).get("backend",              "rules"),
        L.get("optimizer",    {}).get("report_savings",       True),
        L.get("cache",        {}).get("backend",              "memory"),
        float(L.get("cache", {}).get("similarity_threshold",  0.92)),
        int(L.get("cache",   {}).get("ttl_seconds",           3600)),
        L.get("rewriter",     {}).get("backend",              "passthrough"),
        L.get("retriever",    {}).get("backend",              "memory"),
        int(L.get("retriever",{}).get("top_k",                8)),
        L.get("compressor",   {}).get("backend",              "passthrough"),
        int(L.get("compressor",{}).get("top_k",               3)),
        L.get("prompt_cache", {}).get("backend",              "anthropic"),
        llm.get("provider",   "anthropic"),
        llm.get("model",      "claude-sonnet-4-6"),
        int(llm.get("max_tokens", 1024)),
    )


# ── Inspection formatter ──────────────────────────────────────────────────────

def _bar(pct: float, width: int = 20) -> str:
    filled = max(0, min(width, int(pct / 100 * width)))
    return "=" * filled + "-" * (width - filled)


def _fmt_inspection(result: dict, include_raw: bool = False) -> str:
    lines: list[str] = []
    opt   = result["optimizer"]
    pct   = opt["savings_pct"]
    saved = opt["original_tokens"] - opt["optimized_tokens"]

    lines += [
        "### Pipeline Inspection Report",
        "",
        f"**L0 - Prompt Optimizer** | `{result['optimizer_backend'].replace('Backend','')}`",
        "",
        "| | Tokens | Text |",
        "|---|---|---|",
        f"| Before | **{opt['original_tokens']}** | `{opt['original'][:70]}` |",
        f"| After  | **{opt['optimized_tokens']}** | `{opt['optimized'][:70]}` |",
        f"| Saved  | **{saved} ({pct:.0f}%)** | `[{_bar(pct)}]` |",
        "",
    ]

    cache_b = result["cache_backend"].replace("Backend", "")
    if result["cache_hit"]:
        lines += [
            f"**L1 - Semantic Cache** | `{cache_b}` | **HIT** - returning cached answer, L2-L5 skipped.",
            "",
        ]
        return "\n".join(lines)

    lines += [f"**L1 - Semantic Cache** | `{cache_b}` | MISS", ""]

    rew_b = result["rewriter_backend"].replace("Backend", "")
    rq    = result.get("rewritten_query", "")
    orig  = opt["optimized"] or opt["original"]
    if rq and rq != orig:
        lines += [f"**L2 - Query Rewriter** | `{rew_b}`", "", f"`{rq[:120]}`", ""]
    else:
        lines += [f"**L2 - Query Rewriter** | `{rew_b}` | passthrough", ""]

    chunks = result.get("retrieved_chunks", [])
    ret_b  = result["retriever_backend"].replace("Backend", "")
    lines += [f"**L3 - Retriever** | `{ret_b}` | **{len(chunks)} chunk(s)** retrieved", ""]
    if chunks:
        lines += ["| # | Source | Score | Preview |", "|---|---|---|---|"]
        for i, c in enumerate(chunks[:8]):
            src   = str(c.get("source", "?"))[-40:]
            score = f"{c.get('score', 0):.2f}"
            prev  = c.get("text", "")[:55].replace("\n", " ").replace("|", ".")
            lines.append(f"| {i+1} | `{src}` | {score} | {prev}... |")
    lines.append("")

    final  = result.get("compressed_chunks", [])
    comp_b = result["compressor_backend"].replace("Backend", "")
    lines += [f"**L4 - Compressor** | `{comp_b}` | **{len(final)} chunk(s)** kept", ""]
    if final:
        srcs = " / ".join(f"`{c.get('source','?')[-30:]}`" for c in final)
        lines += [srcs, ""]

    pt    = result.get("prompt_tokens", 0)
    pc_b  = result["prompt_cache_backend"].replace("Backend", "")
    built = result.get("final_messages", {})
    sys_blocks = (
        len(built.get("system", []))
        if isinstance(built.get("system"), list)
        else (1 if built.get("system") else 0)
    )
    summary = {
        "user_question":          opt["optimized"] or opt["original"],
        "user_question_tokens":   opt["optimized_tokens"],
        "context_chunks":         len(final),
        "system_blocks":          sys_blocks,
        "estimated_total_tokens": pt,
    }
    lines += [
        f"**L5 - Final Prompt** | `{pc_b}` | **~{pt} tokens**",
        "",
        "```json",
        json.dumps(summary, indent=2),
        "```",
        "",
    ]

    if include_raw and built:
        lines += [
            "<details><summary>Raw prompt JSON</summary>",
            "",
            "```json",
            json.dumps(built, indent=2, default=str)[:3000],
            "```",
            "</details>",
            "",
        ]

    return "\n".join(lines)


# ── Event handlers ────────────────────────────────────────────────────────────

def _fmt_counter() -> str:
    return f"**{_session_saved_tokens}** tokens saved this session"


def submit_query(message: str, history: list, mode: str, show_raw: bool) -> tuple:
    global _session_saved_tokens
    if not message.strip():
        return "", history, _fmt_counter()

    try:
        stack = _get_stack()
    except Exception as exc:
        history = history + [
            {"role": "user",      "content": message},
            {"role": "assistant", "content": f"**Pipeline error:** {exc}\n\nCheck your config and API keys."},
        ]
        return "", history, _fmt_counter()

    try:
        result = stack.inspect(message)
    except Exception as exc:
        history = history + [
            {"role": "user",      "content": message},
            {"role": "assistant", "content": f"**Inspect error:** {exc}"},
        ]
        return "", history, _fmt_counter()

    opt = result["optimizer"]
    _session_saved_tokens += max(0, opt["original_tokens"] - opt["optimized_tokens"])

    inspection_md = _fmt_inspection(result, include_raw=show_raw)

    if "Full pipeline" in mode:
        try:
            answer = stack.answer_from_inspection(result)
            reply  = inspection_md + "\n\n---\n\n**LLM Answer**\n\n" + answer
        except Exception as exc:
            reply  = inspection_md + f"\n\n---\n\n**LLM Error:** {exc}"
    else:
        reply = inspection_md + "\n\n---\n\n*Inspect-only mode — switch to Full pipeline for an LLM answer.*"

    history = history + [
        {"role": "user",      "content": message},
        {"role": "assistant", "content": reply},
    ]
    return "", history, _fmt_counter()


def clear_chat() -> tuple:
    global _session_saved_tokens
    _session_saved_tokens = 0
    return [], _fmt_counter()


def apply_yaml(yaml_text: str) -> tuple:
    try:
        cfg = yaml.safe_load(yaml_text) or {}
    except yaml.YAMLError as exc:
        return (f"YAML parse error: {exc}",) + _form_tuple(_read_cfg())
    Path(_config_path).write_text(yaml_text, encoding="utf-8")
    msg = _reload()
    return (msg,) + _form_tuple(cfg)


def save_form(
    opt_b, opt_report,
    cache_b, sim_thresh, ttl,
    rew_b,
    ret_b, ret_topk,
    comp_b, comp_topk,
    pc_b,
    llm_prov, llm_mod, llm_max_tok,
) -> tuple:
    cfg = _read_cfg()
    L   = cfg.setdefault("layers", {})
    llm = cfg.setdefault("llm", {})

    L.setdefault("optimizer",    {}).update({"backend": opt_b, "report_savings": bool(opt_report)})
    L.setdefault("cache",        {}).update({
        "backend": cache_b,
        "similarity_threshold": float(sim_thresh),
        "ttl_seconds": int(ttl),
    })
    L.setdefault("rewriter",     {})["backend"] = rew_b
    L.setdefault("retriever",    {}).update({"backend": ret_b,   "top_k": int(ret_topk)})
    L.setdefault("compressor",   {}).update({"backend": comp_b,  "top_k": int(comp_topk)})
    L.setdefault("prompt_cache", {})["backend"] = pc_b
    llm.update({"provider": llm_prov, "model": llm_mod, "max_tokens": int(llm_max_tok)})

    yaml_text = _write_cfg(cfg)
    msg = _reload()
    return yaml_text, msg


def get_status_md() -> str:
    try:
        stack = _get_stack()
        s     = stack.status()
        rows  = [
            ("L0 - Optimizer",    s["optimizer"].replace("Backend", ""),    ""),
            ("L1 - Cache",        s["cache"].replace("Backend", ""),        f"{s['cached_queries']} entries"),
            ("L2 - Rewriter",     s["rewriter"].replace("Backend", ""),     ""),
            ("L3 - Retriever",    s["retriever"].replace("Backend", ""),    f"{s['indexed_docs']} chunks"),
            ("L4 - Compressor",   s["compressor"].replace("Backend", ""),   ""),
            ("L5 - Prompt Cache", s["prompt_cache"].replace("Backend", ""), ""),
            ("LLM Model",         s["llm_model"],                           ""),
        ]
        lines = ["| Layer | Backend | Info |", "|---|---|---|"]
        for layer, backend, info in rows:
            lines.append(f"| {layer} | `{backend}` | {info} |")
        lines += ["", f"Config: `{_config_path}`"]
        return "\n".join(lines)
    except Exception as exc:
        return f"**Pipeline not loaded:** {exc}\n\nCheck API keys and config."


def do_index_dir(directory: str, extensions: str) -> str:
    if not directory.strip():
        return "Please enter a directory path."
    try:
        from ragstack.ingest import ingest_directory
        ext_set = {
            e.strip() if e.strip().startswith(".") else f".{e.strip()}"
            for e in extensions.split(",") if e.strip()
        }
        chunks, fc = ingest_directory(directory.strip(), extensions=ext_set or None)
        if not chunks:
            return f"No files found in `{directory}` matching `{extensions}`."
        total = _get_stack().ingest_docs(chunks)
        return f"Indexed **{len(chunks)} chunks** from **{fc} files**. Total: **{total}**."
    except Exception as exc:
        return f"Error: {exc}"


def do_add_text(text: str, source: str) -> str:
    if not text.strip():
        return "Text is empty."
    try:
        total = _get_stack().ingest_docs([{
            "text": text.strip(), "source": source or "manual",
            "score": 0.0, "metadata": {},
        }])
        return f"Added (source: `{source or 'manual'}`). Total: **{total}**."
    except Exception as exc:
        return f"Error: {exc}"


def do_clear_cache() -> str:
    try:
        n = _get_stack().clear_cache()
        return f"Cleared **{n}** cache entr{'y' if n == 1 else 'ies'}."
    except Exception as exc:
        return f"Error: {exc}"


# ── API key management ────────────────────────────────────────────────────────

_KEY_VARS = {
    "ANTHROPIC_API_KEY": "Anthropic  (claude-* models)",
    "OPENAI_API_KEY":    "OpenAI  (embeddings + gpt-* models)",
    "GOOGLE_API_KEY":    "Google  (gemini-* models)",
}

# ── Quick presets ─────────────────────────────────────────────────────────────

_PRESETS: dict[str, dict] = {
    "Ollama / Llama (Free)": {
        "llm": {
            "provider": "ollama", "model": "llama3.2", "max_tokens": 1024,
            "ollama": {"base_url": "http://localhost:11434"},
        },
        "layers": {
            "optimizer":    {"backend": "rules",       "report_savings": True},
            "cache":        {"backend": "memory",      "similarity_threshold": 0.92, "ttl_seconds": 3600},
            "rewriter":     {"backend": "llm",         "strategy": "expand"},
            "retriever":    {"backend": "memory",      "top_k": 8},
            "compressor":   {"backend": "passthrough", "top_k": 3},
            "prompt_cache": {"backend": "none"},
        },
    },
    "Anthropic Claude": {
        "llm": {"provider": "anthropic", "model": "claude-sonnet-4-6", "max_tokens": 1024},
        "layers": {
            "optimizer":    {"backend": "rules",       "report_savings": True},
            "cache":        {"backend": "memory",      "similarity_threshold": 0.92, "ttl_seconds": 3600},
            "rewriter":     {"backend": "passthrough"},
            "retriever":    {"backend": "memory",      "top_k": 8},
            "compressor":   {"backend": "passthrough", "top_k": 3},
            "prompt_cache": {"backend": "anthropic"},
        },
    },
    "OpenAI GPT-4o": {
        "llm": {"provider": "openai", "model": "gpt-4o-mini", "max_tokens": 1024},
        "layers": {
            "optimizer":    {"backend": "rules",       "report_savings": True},
            "cache":        {"backend": "memory",      "similarity_threshold": 0.92, "ttl_seconds": 3600},
            "rewriter":     {"backend": "passthrough"},
            "retriever":    {"backend": "memory",      "top_k": 8},
            "compressor":   {"backend": "passthrough", "top_k": 3},
            "prompt_cache": {"backend": "openai"},
        },
    },
    "Google Gemini": {
        "llm": {"provider": "gemini", "model": "gemini-1.5-flash", "max_tokens": 1024},
        "layers": {
            "optimizer":    {"backend": "rules",       "report_savings": True},
            "cache":        {"backend": "memory",      "similarity_threshold": 0.92, "ttl_seconds": 3600},
            "rewriter":     {"backend": "passthrough"},
            "retriever":    {"backend": "memory",      "top_k": 8},
            "compressor":   {"backend": "passthrough", "top_k": 3},
            "prompt_cache": {"backend": "none"},
        },
    },
    "Graphify + Ollama (Code RAG)": {
        "llm": {
            "provider": "ollama", "model": "llama3.2", "max_tokens": 1024,
            "ollama": {"base_url": "http://localhost:11434"},
        },
        "layers": {
            "optimizer":    {"backend": "rules",       "report_savings": True},
            "cache":        {"backend": "memory",      "similarity_threshold": 0.92, "ttl_seconds": 3600},
            "rewriter":     {"backend": "llm",         "strategy": "expand"},
            "retriever":    {
                "backend": "graphify", "top_k": 8,
                "graphify": {
                    "graph_path":  "./graphify-out/graph.json",
                    "report_path": "./graphify-out/GRAPH_REPORT.md",
                    "hop_limit":   3,
                    "edge_types":  ["calls", "depends_on", "semantically_similar_to", "rationale_for"],
                },
            },
            "compressor":   {"backend": "passthrough", "top_k": 3},
            "prompt_cache": {"backend": "none"},
        },
    },
}


def _deep_update(base: dict, update: dict) -> dict:
    """Recursively merge update into base, modifying base in place."""
    for k, v in update.items():
        if isinstance(v, dict) and isinstance(base.get(k), dict):
            _deep_update(base[k], v)
        else:
            base[k] = v
    return base


def _ensure_ollama() -> str:
    """Install the ollama Python package and verify the Ollama server is running.

    Returns a human-readable status string to surface in the GUI.
    """
    import subprocess, sys, importlib, urllib.request

    steps: list[str] = []

    # ── 1. Check / install ollama Python package ──────────────────────────────
    try:
        importlib.import_module("ollama")
        steps.append("ollama package already installed.")
    except ModuleNotFoundError:
        steps.append("Installing ollama Python package…")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "ollama>=0.2"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            steps.append("ollama package installed.")
        else:
            err = (result.stderr or result.stdout or "").strip().splitlines()
            steps.append(f"pip install ollama failed: {err[-1] if err else 'unknown error'}")
            return "  |  ".join(steps)

    # ── 2. Check Ollama server reachability ───────────────────────────────────
    try:
        urllib.request.urlopen("http://localhost:11434", timeout=3)
        steps.append("Ollama server is running.")
    except Exception:
        steps.append(
            "⚠ Ollama server not detected at localhost:11434. "
            "Download from https://ollama.com and run: ollama serve"
        )
        return "  |  ".join(steps)

    # ── 3. Ensure llama3.2 model is pulled ───────────────────────────────────
    try:
        import ollama as _ollama
        local_models = [m.model for m in _ollama.list().models]
        if any("llama3.2" in m for m in local_models):
            steps.append("llama3.2 model already available.")
        else:
            steps.append("Pulling llama3.2 (this may take a few minutes)…")
            _ollama.pull("llama3.2")
            steps.append("llama3.2 pulled successfully.")
    except Exception as exc:
        steps.append(f"Model pull skipped: {exc}")

    return "  |  ".join(steps)


def _ensure_graphify() -> str:
    """Install graphifyy and run 'graphify install' if not already present.

    Returns a human-readable status string to surface in the GUI.
    """
    import subprocess, sys, shutil

    steps: list[str] = []

    # ── 1. Check whether graphifyy is importable ──────────────────────────────
    try:
        import importlib
        importlib.import_module("graphify")
        steps.append("graphifyy already installed.")
        already_installed = True
    except ModuleNotFoundError:
        already_installed = False

    # ── 2. pip install graphifyy if missing ───────────────────────────────────
    if not already_installed:
        steps.append("Installing graphifyy (pip install graphifyy)…")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "graphifyy"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            steps.append("graphifyy installed successfully.")
        else:
            err = (result.stderr or result.stdout or "").strip().splitlines()
            short_err = err[-1] if err else "unknown error"
            steps.append(f"pip install failed: {short_err}")
            return "  |  ".join(steps)

    # ── 3. Run 'graphify install' to register the skill in Claude Code ────────
    graphify_bin = shutil.which("graphify")
    if graphify_bin is None:
        # Fallback: try python -m graphify
        check = subprocess.run(
            [sys.executable, "-m", "graphify", "--version"],
            capture_output=True, text=True,
        )
        if check.returncode == 0:
            install_cmd = [sys.executable, "-m", "graphify", "install"]
        else:
            steps.append(
                "graphify CLI not found on PATH.  "
                "Add Python Scripts dir to PATH, then run 'graphify install' manually."
            )
            return "  |  ".join(steps)
    else:
        install_cmd = [graphify_bin, "install"]

    result2 = subprocess.run(install_cmd, capture_output=True, text=True)
    if result2.returncode == 0:
        steps.append("graphify install completed — skill registered in Claude Code.")
    else:
        out = (result2.stderr or result2.stdout or "").strip().splitlines()
        short = out[-1] if out else "unknown error"
        steps.append(f"graphify install warning: {short}")

    return "  |  ".join(steps)


def apply_preset(preset_name: str) -> tuple:
    """Apply a named preset, write config, reload pipeline.
    Returns (yaml_text, status, *form_fields) — 16-element tuple.
    """
    if preset_name not in _PRESETS:
        cfg = _read_cfg()
        return (load_yaml_text(), f"Unknown preset: {preset_name}") + _form_tuple(cfg)

    extra_notes: list[str] = []

    # Any Ollama-based preset: ensure ollama package + server + model
    _OLLAMA_PRESETS = {"Ollama / Llama (Free)", "Graphify + Ollama (Code RAG)"}
    if preset_name in _OLLAMA_PRESETS:
        extra_notes.append(_ensure_ollama())

    # Graphify preset: auto-install graphifyy + run 'graphify install' if needed
    if preset_name == "Graphify + Ollama (Code RAG)":
        extra_notes.append(_ensure_graphify())
        # Warn if graph.json is absent so users know to run /graphify first
        import pathlib
        graph_path = pathlib.Path("./graphify-out/graph.json")
        if not graph_path.exists():
            extra_notes.append(
                "⚠ No graph.json found at ./graphify-out/graph.json. "
                "Run '/graphify .' in Claude Code (or the Graphify CLI) to build the graph first. "
                "Until then, the retriever will return 0 chunks."
            )

    cfg = _read_cfg()
    preset = _PRESETS[preset_name]

    if "llm" in preset:
        _deep_update(cfg.setdefault("llm", {}), preset["llm"])
    if "layers" in preset:
        layers = cfg.setdefault("layers", {})
        for layer_name, layer_cfg in preset["layers"].items():
            _deep_update(layers.setdefault(layer_name, {}), layer_cfg)

    yaml_text = _write_cfg(cfg)
    msg = _reload()
    suffix = ("  |  " + "  |  ".join(extra_notes)) if extra_notes else ""
    return (yaml_text, f"Preset '{preset_name}' applied.  {msg}{suffix}") + _form_tuple(cfg)


def _key_status() -> str:
    """Return a markdown table showing which keys are set (never shows values)."""
    lines = ["| Variable | Status |", "|---|---|"]
    for var, label in _KEY_VARS.items():
        val = os.environ.get(var, "")
        if val:
            masked = val[:8] + "..." + val[-4:] if len(val) > 12 else "***"
            status = f"Set  (`{masked}`)"
        else:
            status = "Not set"
        lines.append(f"| `{var}` | {status} |")
    return "\n".join(lines)


def set_api_key(var: str, key: str) -> tuple[str, str]:
    """Set an API key in the current process environment and reset the pipeline."""
    global _stack
    key = key.strip()
    if not key:
        return _key_status(), "Key is empty — nothing changed."
    if var not in _KEY_VARS:
        return _key_status(), f"Unknown variable: {var}"
    os.environ[var] = key
    _stack = None          # force pipeline reload with new key
    return _key_status(), f"`{var}` set for this session. Pipeline will reload on next query."


# ── Build UI ──────────────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    # Read config once at build time — set component values directly,
    # no demo.load() needed (avoids Gradio queue freeze on startup).
    cfg       = _read_cfg()
    fv        = _form_tuple(cfg)          # 14-element tuple
    yaml_init = load_yaml_text()

    (
        v_opt_b, v_opt_rep,
        v_cache_b, v_sim, v_ttl,
        v_rew_b,
        v_ret_b, v_ret_topk,
        v_comp_b, v_comp_topk,
        v_pc_b,
        v_llm_prov, v_llm_mod, v_llm_max,
    ) = fv

    with gr.Blocks(title="RAGStack Pipeline Studio") as demo:

        # Header
        gr.HTML("""
        <div style="display:flex;align-items:center;gap:12px;padding:10px 0 6px;
                    border-bottom:1px solid #e5e7eb;margin-bottom:4px">
          <span style="font-size:1.8rem">&#x1F537;</span>
          <div>
            <div style="font-size:1.35rem;font-weight:700">RAGStack Pipeline Studio</div>
            <div style="font-size:0.82rem;color:#6b7280">
              Inspect every layer &middot; Edit config without touching code
            </div>
          </div>
        </div>
        """)

        with gr.Tabs():

            # ─────────────────────────────────────────────────────────────────
            #  TAB 1 — Pipeline Studio
            # ─────────────────────────────────────────────────────────────────
            with gr.TabItem("Pipeline Studio"):

                with gr.Row():
                    mode_radio = gr.Radio(
                        choices=[
                            "Inspect only  (no LLM call)",
                            "Full pipeline  (call LLM for answer)",
                        ],
                        value="Inspect only  (no LLM call)",
                        label="Mode",
                        scale=3,
                    )
                    show_raw = gr.Checkbox(
                        label="Show raw prompt JSON",
                        value=False,
                        scale=1,
                    )

                chatbot = gr.Chatbot(
                    label="Pipeline Output",
                    height=500,
                    render_markdown=True,
                )

                with gr.Row():
                    msg_box = gr.Textbox(
                        placeholder='e.g. "Could you please explain how the authentication flow works?"',
                        label="Query",
                        lines=2,
                        scale=5,
                        show_label=False,
                    )
                    with gr.Column(scale=1, min_width=110):
                        submit_btn = gr.Button("Submit", variant="primary")
                        clear_btn  = gr.Button("Clear")

                token_md = gr.Markdown(_fmt_counter())

                submit_btn.click(
                    submit_query,
                    inputs=[msg_box, chatbot, mode_radio, show_raw],
                    outputs=[msg_box, chatbot, token_md],
                )
                msg_box.submit(
                    submit_query,
                    inputs=[msg_box, chatbot, mode_radio, show_raw],
                    outputs=[msg_box, chatbot, token_md],
                )
                clear_btn.click(clear_chat, outputs=[chatbot, token_md])

            # ─────────────────────────────────────────────────────────────────
            #  TAB 2 — Configuration
            # ─────────────────────────────────────────────────────────────────
            with gr.TabItem("Configuration"):

                gr.Markdown(
                    "Change backends with dropdowns then **Save & Reload**. "
                    "The YAML editor stays in sync."
                )

                # ── Quick Presets ──────────────────────────────────────────────
                with gr.Accordion("Quick Presets  (one-click setup)", open=True):
                    gr.Markdown(
                        "Click any preset to instantly apply a provider configuration "
                        "and reload the pipeline. Your custom YAML settings are preserved "
                        "where possible."
                    )
                    with gr.Row():
                        btn_ollama    = gr.Button("🦙 Ollama / Llama (Free)", size="sm")
                        btn_anthropic = gr.Button("🤖 Anthropic Claude",      size="sm")
                        btn_openai    = gr.Button("🔵 OpenAI GPT-4o",         size="sm")
                        btn_gemini    = gr.Button("🌟 Google Gemini",          size="sm")
                        btn_graphify  = gr.Button("🕸 Graphify + Ollama",      size="sm")
                    preset_status = gr.Textbox(
                        label="Status", interactive=False, lines=5,
                        placeholder="Click a preset to apply it…",
                    )

                gr.HTML("<hr style='margin:10px 0 16px'/>")

                with gr.Row(equal_height=False):

                    # Left — form controls
                    with gr.Column(scale=1):

                        gr.Markdown("**L0 — Prompt Optimizer**")
                        opt_dd     = gr.Dropdown(["rules", "llm", "passthrough"],
                                                 label="Backend", value=v_opt_b)
                        opt_report = gr.Checkbox(label="Print savings to console",
                                                 value=v_opt_rep)

                        gr.Markdown("**L1 — Semantic Cache**")
                        cache_dd   = gr.Dropdown(["memory", "redis", "qdrant"],
                                                 label="Backend", value=v_cache_b)
                        sim_slider = gr.Slider(0.50, 1.00, step=0.01, value=v_sim,
                                               label="Similarity threshold")
                        ttl_slider = gr.Slider(0, 86400, step=300, value=v_ttl,
                                               label="TTL seconds (0 = no expiry)")

                        gr.Markdown("**L2 — Query Rewriter**")
                        rew_dd     = gr.Dropdown(["passthrough", "llm", "hyde"],
                                                 label="Backend", value=v_rew_b)

                        gr.Markdown("**L3 — Retriever**")
                        ret_dd     = gr.Dropdown(
                            ["memory", "graphify", "chroma", "pinecone", "weaviate"],
                            label="Backend", value=v_ret_b)
                        ret_topk   = gr.Slider(1, 20, step=1, value=v_ret_topk,
                                               label="top_k (chunks to retrieve)")

                        gr.Markdown("**L4 — Compressor**")
                        comp_dd    = gr.Dropdown(["passthrough", "reranker", "llmlingua"],
                                                 label="Backend", value=v_comp_b)
                        comp_topk  = gr.Slider(1, 10, step=1, value=v_comp_topk,
                                               label="top_k (chunks to keep)")

                        gr.Markdown("**L5 — Prompt Cache**")
                        pc_dd      = gr.Dropdown(["anthropic", "openai", "none"],
                                                 label="Backend", value=v_pc_b)

                        gr.Markdown("**LLM Provider**")
                        llm_prov_dd  = gr.Dropdown(
                            ["anthropic", "openai", "gemini", "ollama"],
                            label="Provider", value=v_llm_prov)
                        llm_model_tb = gr.Textbox(label="Model name",
                                                  value=v_llm_mod, max_lines=1)
                        llm_max_tok  = gr.Slider(128, 8192, step=128, value=v_llm_max,
                                                 label="max_tokens")

                        save_btn    = gr.Button("Save & Reload Pipeline", variant="primary")
                        form_status = gr.Textbox(label="Status", interactive=False, lines=2)

                    # Right — YAML editor
                    with gr.Column(scale=1):
                        gr.Markdown("**Full YAML Editor** — for advanced settings")
                        yaml_editor = gr.Code(
                            value=yaml_init,
                            language="yaml",
                            label="ragstack.config.yaml",
                            lines=36,
                            interactive=True,
                        )
                        with gr.Row():
                            load_btn  = gr.Button("Load from disk")
                            apply_btn = gr.Button("Apply YAML & Reload", variant="primary")
                        yaml_status = gr.Textbox(label="Status", interactive=False, lines=1)

                # All 14 form components in order (must match _form_tuple)
                _form_fields = [
                    opt_dd, opt_report,
                    cache_dd, sim_slider, ttl_slider,
                    rew_dd,
                    ret_dd, ret_topk,
                    comp_dd, comp_topk,
                    pc_dd,
                    llm_prov_dd, llm_model_tb, llm_max_tok,
                ]

                # Preset button wiring (must be after _form_fields is defined)
                _preset_outputs = [yaml_editor, preset_status] + _form_fields
                btn_ollama.click(
                    lambda: apply_preset("Ollama / Llama (Free)"),
                    outputs=_preset_outputs,
                )
                btn_anthropic.click(
                    lambda: apply_preset("Anthropic Claude"),
                    outputs=_preset_outputs,
                )
                btn_openai.click(
                    lambda: apply_preset("OpenAI GPT-4o"),
                    outputs=_preset_outputs,
                )
                btn_gemini.click(
                    lambda: apply_preset("Google Gemini"),
                    outputs=_preset_outputs,
                )
                btn_graphify.click(
                    lambda: apply_preset("Graphify + Ollama (Code RAG)"),
                    outputs=_preset_outputs,
                )

                load_btn.click(load_yaml_text, outputs=[yaml_editor])

                apply_btn.click(
                    apply_yaml,
                    inputs=[yaml_editor],
                    outputs=[yaml_status] + _form_fields,
                )

                save_btn.click(
                    save_form,
                    inputs=_form_fields,
                    outputs=[yaml_editor, form_status],
                )

            # ─────────────────────────────────────────────────────────────────
            #  TAB 4 — Documentation
            # ─────────────────────────────────────────────────────────────────
            with gr.TabItem("Docs"):
                # Docs served at /ragstack-docs via FastAPI route added in main()
                gr.HTML("""
                <div style="display:flex;gap:10px;align-items:center;margin-bottom:8px">
                  <a href="/ragstack-docs" target="_blank"
                     style="padding:6px 14px;background:#4f46e5;color:white;
                            border-radius:6px;text-decoration:none;font-size:0.85rem;
                            font-weight:600">
                    &#x2197; Open in new tab
                  </a>
                  <span style="color:#6b7280;font-size:0.82rem">
                    Full interactive docs with live Mermaid diagrams
                  </span>
                </div>
                <iframe src="/ragstack-docs"
                  style="width:100%;height:820px;border:1px solid #e2e8f0;border-radius:8px">
                </iframe>
                """)

            # ─────────────────────────────────────────────────────────────────
            #  TAB 3 — Status & Tools
            # ─────────────────────────────────────────────────────────────────
            with gr.TabItem("Status & Tools"):

                # ── API Keys (shown first — most likely thing a new user needs) ──
                with gr.Accordion("API Keys  (session only — never written to disk)", open=True):
                    key_status_md = gr.Markdown(_key_status())
                    with gr.Row():
                        key_var_dd = gr.Dropdown(
                            choices=list(_KEY_VARS.keys()),
                            value="ANTHROPIC_API_KEY",
                            label="Variable",
                            scale=1,
                        )
                        key_input = gr.Textbox(
                            label="Paste your API key here",
                            placeholder="sk-ant-...  or  sk-...",
                            type="password",
                            max_lines=1,
                            scale=3,
                        )
                        key_btn = gr.Button("Set Key", variant="primary", scale=0, min_width=100)
                    key_msg = gr.Markdown()
                    key_btn.click(
                        set_api_key,
                        inputs=[key_var_dd, key_input],
                        outputs=[key_status_md, key_msg],
                    )
                    # Also allow pressing Enter in the key box
                    key_input.submit(
                        set_api_key,
                        inputs=[key_var_dd, key_input],
                        outputs=[key_status_md, key_msg],
                    )

                gr.HTML("<hr style='margin:14px 0'/>")

                with gr.Row(equal_height=False):

                    # Left — status table
                    with gr.Column(scale=2):
                        gr.Markdown("### Active Pipeline")
                        status_md   = gr.Markdown("*Click Refresh to load pipeline status.*")
                        refresh_btn = gr.Button("Refresh")
                        refresh_btn.click(get_status_md, outputs=[status_md])

                    # Right — tools
                    with gr.Column(scale=1):
                        gr.Markdown("### Tools")

                        gr.Markdown("**Index a directory**")
                        index_dir_tb = gr.Textbox(
                            label="Directory path",
                            placeholder="src/  or  .  or  /abs/path",
                            max_lines=1,
                        )
                        index_ext_tb = gr.Textbox(
                            label="Extensions (comma-separated)",
                            value=".py,.js,.ts,.go,.md,.txt,.yaml",
                            max_lines=1,
                        )
                        index_btn    = gr.Button("Index", variant="primary")
                        index_status = gr.Markdown()
                        index_btn.click(
                            do_index_dir,
                            inputs=[index_dir_tb, index_ext_tb],
                            outputs=[index_status],
                        )

                        gr.HTML("<hr style='margin:12px 0'/>")

                        gr.Markdown("**Add a text snippet**")
                        add_text_tb = gr.Textbox(
                            label="Text", lines=3,
                            placeholder="Paste any text to add to the index...",
                        )
                        add_src_tb  = gr.Textbox(label="Source label", value="manual",
                                                  max_lines=1)
                        add_btn     = gr.Button("Add to Index")
                        add_status  = gr.Markdown()
                        add_btn.click(
                            do_add_text,
                            inputs=[add_text_tb, add_src_tb],
                            outputs=[add_status],
                        )

                        gr.HTML("<hr style='margin:12px 0'/>")

                        gr.Markdown("**Cache**")
                        clear_cache_btn    = gr.Button("Clear Semantic Cache", variant="stop")
                        clear_cache_status = gr.Markdown()
                        clear_cache_btn.click(do_clear_cache, outputs=[clear_cache_status])

    return demo


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    global _config_path

    parser = argparse.ArgumentParser(description="RAGStack Pipeline Studio")
    parser.add_argument("--config",     default=None,
                        help="Path to ragstack.config.yaml")
    parser.add_argument("--port",       type=int, default=7860)
    parser.add_argument("--share",      action="store_true")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    if args.config:
        _config_path = args.config

    print(f"[ragstack-gui] config: {_config_path}")

    # Mount Gradio onto a FastAPI app so we can add custom routes
    # (needed to serve the docs page at /ragstack-docs cleanly)
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    import uvicorn

    fastapi_app = FastAPI()

    @fastapi_app.get("/ragstack-docs", response_class=HTMLResponse)
    def serve_docs():
        from ragstack.docs import get_docs_html
        return get_docs_html()

    demo = build_ui()
    app = gr.mount_gradio_app(fastapi_app, demo, path="/")

    url = f"http://127.0.0.1:{args.port}"
    print(f"[ragstack-gui] serving at {url}")
    if not args.no_browser:
        import threading, webbrowser, time
        threading.Thread(target=lambda: (time.sleep(2), webbrowser.open(url)),
                         daemon=True).start()

    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
