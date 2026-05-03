"""
RAGStack demo — uses memory retriever, passthrough compressor, and memory
cache so it runs with zero external dependencies beyond anthropic + pyyaml.

Before running, set ANTHROPIC_API_KEY (and OPENAI_API_KEY if you want
embeddings; the memory cache + retriever work without embeddings when
the LLM rewriter is set to passthrough).

Quick start with no API keys at all (pure offline):
  1. Set rewriter.backend: passthrough in ragstack.config.yaml
  2. The memory retriever does keyword scoring — no embeddings needed.
  3. The cache uses cosine similarity, which requires embeddings; set
     cache.enabled: false to skip it entirely in offline mode.
"""
import os
import sys

# Allow running from the ragstack/ directory directly
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ragstack import RAGStack

CONFIG = os.path.join(os.path.dirname(__file__), "ragstack.config.yaml")

stack = RAGStack.from_config(CONFIG)

questions = [
    "How does the authentication flow work?",
    "What calls the token validator?",
    "How does the auth flow work?",   # semantically same as Q1 → should cache hit
]

for q in questions:
    print(f"\n{'─' * 60}")
    print(f"Q: {q}")
    answer = stack.query(q)
    print(f"A: {answer}")
