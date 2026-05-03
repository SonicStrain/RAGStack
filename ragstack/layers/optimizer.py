"""
ragstack/layers/optimizer.py — Layer 0: Prompt Optimizer

Trims tokens from the user's raw prompt before it enters the pipeline.
The optimized prompt becomes the cache key and the final LLM question,
so every downstream layer benefits from the compression.

Savings are approximate (len/4 token estimate) but accurate enough to guide
config tuning.  The rule-based backend has zero external dependencies.
"""
from __future__ import annotations

import re

from ragstack.base import PromptOptimizerBackend


# ── token estimate (no tiktoken dependency) ───────────────────────────────────

def _tokens(text: str) -> int:
    """~4 chars per token — matches OpenAI/Anthropic average for English prose."""
    return max(1, len(text) // 4)


def _stats(original: str, optimized: str) -> dict:
    ot = _tokens(original)
    tt = _tokens(optimized)
    pct = round((1 - tt / ot) * 100, 1) if ot else 0.0
    return {
        "original": original,
        "optimized": optimized,
        "original_tokens": ot,
        "optimized_tokens": tt,
        "savings_pct": pct,
    }


# ── Rule-based backend ────────────────────────────────────────────────────────

# Patterns applied LEFT-TO-RIGHT; each is (compiled_regex, replacement)
_PREFIX_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"^(?:could|can|would|will)\s+you\s+(?:please\s+)?", re.I), ""),
    (re.compile(r"^please\s+", re.I), ""),
    (re.compile(r"^I(?:'d| would)\s+like\s+(?:you\s+to\s+|to\s+know\s+)?", re.I), ""),
    (re.compile(r"^I\s+(?:want|need|wish)\s+(?:you\s+to\s+|to\s+know\s+)?", re.I), ""),
    (re.compile(r"^I\s+was\s+wondering\s+(?:if\s+you\s+could\s+|about\s+)?", re.I), ""),
    (re.compile(r"^I(?:'m| am)\s+(?:trying|looking)\s+to\s+(?:understand|find\s+out|figure\s+out|know)\s+", re.I), ""),
    (re.compile(r"^(?:could|can)\s+you\s+(?:help\s+me\s+(?:understand\s+|with\s+)?)?", re.I), ""),
    (re.compile(r"^(?:tell|show)\s+me\s+(?:about\s+)?", re.I), ""),
    (re.compile(r"^explain\s+(?:to\s+me\s+)?(?:what\s+)?", re.I), ""),
    (re.compile(r"^help\s+me\s+(?:understand\s+)?", re.I), ""),
    (re.compile(r"^(?:hey|hi|hello)[,!]?\s+", re.I), ""),
]

_SUFFIX_RULES: list[tuple[re.Pattern, str]] = [
    (re.compile(r"[,.]?\s*(?:please|thanks?|thank\s+you)[!?.]*\s*$", re.I), ""),
    (re.compile(r"[,.]?\s*if\s+(?:at\s+all\s+)?possible[!?.]*\s*$", re.I), ""),
    (re.compile(r"[,.]?\s*if\s+you\s+(?:can|could|don'?t\s+mind)[!?.]*\s*$", re.I), ""),
    (re.compile(r"\s+in\s+(?:as\s+much\s+detail\s+as\s+possible|detail)[!?.]*\s*$", re.I), ""),
]

_INLINE_RULES: list[tuple[re.Pattern, str]] = [
    # Filler adverbs that don't change meaning (optional trailing comma)
    (re.compile(r"\b(?:basically|essentially|literally|actually|simply|just|really|very|quite|pretty|fairly|kinda|sorta|definitely|certainly|obviously|clearly)[,]?\s+", re.I), ""),
    # Hedging phrases
    (re.compile(r"\b(?:maybe|perhaps|possibly)[,]?\s+(?=\w)", re.I), ""),
    # "in order to" → "to"
    (re.compile(r"\bin\s+order\s+to\b", re.I), "to"),
    # "the thing is" / "the fact is"
    (re.compile(r"\bthe\s+(?:thing|fact)\s+is\s+(?:that\s+)?", re.I), ""),
    # Collapse whitespace
    (re.compile(r"[ \t]{2,}"), " "),
    (re.compile(r"\n{3,}"), "\n\n"),
]


def _apply_rules(text: str, rules: list[tuple[re.Pattern, str]]) -> str:
    for pattern, replacement in rules:
        text = pattern.sub(replacement, text)
    return text.strip()


class RuleBasedOptimizerBackend(PromptOptimizerBackend):
    """
    Zero-dependency optimizer using hand-crafted regex rules.
    Strips filler prefixes/suffixes and redundant adverbs.
    Average savings: 15-40% on typical developer prompts.
    """

    def optimize(self, prompt: str) -> tuple[str, dict]:
        text = prompt.strip()
        text = _apply_rules(text, _PREFIX_RULES)
        text = _apply_rules(text, _SUFFIX_RULES)
        text = _apply_rules(text, _INLINE_RULES)
        # Capitalize first letter if we stripped a lowercase prefix
        if text and text[0].islower():
            text = text[0].upper() + text[1:]
        return text, _stats(prompt, text)


# ── LLM-powered backend ───────────────────────────────────────────────────────

_LLM_SYSTEM = """\
You are a prompt optimizer for LLM API calls. Your only job is to rewrite \
the user's prompt to use fewer tokens while preserving every bit of intent \
and required information.

Rules:
- Remove all filler: "please", "could you", "I was wondering", "basically", etc.
- Use direct imperative language ("Explain X" not "I would like you to explain X")
- Never remove technical terms, variable names, file names, or domain concepts
- Never add information not in the original
- If the prompt is already concise, return it unchanged
- Return ONLY the optimized prompt — no explanation, no preamble\
"""


class LLMOptimizerBackend(PromptOptimizerBackend):
    """
    LLM-powered optimizer. Uses a cheap fast model (default: Haiku) so the
    cost of optimization is negligible vs. the savings on the main model call.
    Falls back to the original prompt on any error.
    """

    def __init__(self, llm_client, model: str, max_tokens: int = 512):
        self._llm = llm_client
        self._model = model
        self._max_tokens = max_tokens

    def optimize(self, prompt: str) -> tuple[str, dict]:
        try:
            optimized = self._llm.chat(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                system=_LLM_SYSTEM,
                max_tokens=self._max_tokens,
            ).strip()
            # Safety: never return something longer than the input
            if _tokens(optimized) >= _tokens(prompt):
                return prompt, _stats(prompt, prompt)
            return optimized, _stats(prompt, optimized)
        except Exception as exc:
            print(f"[ragstack] optimizer warning: {exc} — using original prompt")
            return prompt, _stats(prompt, prompt)


# ── Passthrough backend ───────────────────────────────────────────────────────

class PassthroughOptimizerBackend(PromptOptimizerBackend):
    """No-op. Returns the prompt unchanged. Use when latency budget is tight."""

    def optimize(self, prompt: str) -> tuple[str, dict]:
        return prompt, _stats(prompt, prompt)


# ── Registry ──────────────────────────────────────────────────────────────────

OPTIMIZER_BACKENDS: dict[str, type[PromptOptimizerBackend]] = {
    "rules":       RuleBasedOptimizerBackend,
    "llm":         LLMOptimizerBackend,
    "passthrough": PassthroughOptimizerBackend,
}
