"""
LLM Router (Phase 5 — CutClaw pattern).

Routes different task types to different LLM models via LiteLLM, enabling
ensemble (Plan-LLM ≠ Critic-LLM ≠ Reviewer-LLM) which catches errors a
single-LLM approach misses. Falls back to a single local model (Ollama
Qwen2.5-Coder) when LiteLLM is unavailable or no API keys are set.

Task types:
  - plan     — EditPlan generation (needs strong reasoning; Claude/GPT-4o if available)
  - critic   — Plan critique (different model than planner; catches planner blind spots)
  - reviewer — 7-dimension review (needs judgment; can be same as critic)
  - research — Editing Research pure-reasoning sub-phase (Crayotter pattern)
  - score    — transcript segment semantic scoring (lightweight, high-volume)

Public surface:
  - LLMRouter class (route(task_type, prompt, **opts) -> str | None)
  - get_router() — singleton accessor
"""
from __future__ import annotations

import json
import os
import subprocess
import typing as t


# Default model per task type. Order: cloud-first (if API key set) then local fallback.
DEFAULT_MODELS: dict[str, list[str]] = {
    "plan": [
        "claude-sonnet-4-20250514",      # via litellm if ANTHROPIC_API_KEY set
        "gpt-4o",                         # via litellm if OPENAI_API_KEY set
        "ollama/qwen2.5-coder:7b",        # local fallback (always available if ollama running)
    ],
    "critic": [
        "gpt-4o-mini",                    # different family than planner (ensemble diversity)
        "claude-haiku-4-20250506",        # FIX: added Anthropic for reviewer ensemble
        "ollama/qwen2.5-coder:7b",
    ],
    "reviewer": [
        "gpt-4o-mini",
        "claude-haiku-4-20250506",        # FIX: added Anthropic entry (was missing — broke ensemble)
        "ollama/qwen2.5-coder:7b",
    ],
    "research": [
        "claude-sonnet-4-20250514",
        "ollama/qwen2.5-coder:7b",
    ],
    "score": [
        "ollama/qwen2.5-coder:7b",        # lightweight, high-volume — local preferred
    ],
}


class LLMRouter:
    """Routes task types to LLM models with graceful fallback."""

    def __init__(self, model_overrides: t.Optional[dict[str, str]] = None):
        self.overrides = model_overrides or {}
        self._litellm = None
        try:
            import litellm  # noqa
            self._litellm = litellm
        except ImportError:
            pass

    def _candidate_models(self, task_type: str) -> list[str]:
        if task_type in self.overrides:
            return [self.overrides[task_type]]
        return DEFAULT_MODELS.get(task_type, ["ollama/qwen2.5-coder:7b"])

    def _model_available(self, model: str) -> bool:
        if model.startswith("ollama/"):
            return True  # always try ollama; it fails gracefully if not running
        if model.startswith("claude") or model.startswith("anthropic"):
            return bool(os.environ.get("ANTHROPIC_API_KEY"))
        if model.startswith("gpt") or model.startswith("openai"):
            return bool(os.environ.get("OPENAI_API_KEY"))
        return False

    def route(self, task_type: str, prompt: str, *,
              json_mode: bool = False, temperature: float = 0.4,
              max_tokens: int = 4000, timeout: int = 120) -> t.Optional[str]:
        """Route a prompt to the best available model for the task type. Returns text or None."""
        for model in self._candidate_models(task_type):
            if not self._model_available(model):
                continue
            result = self._call(model, prompt, json_mode=json_mode,
                                temperature=temperature, max_tokens=max_tokens, timeout=timeout)
            if result is not None:
                return result
        return None

    def route_json(self, task_type: str, prompt: str, **opts) -> t.Optional[dict]:
        """Route and parse JSON response. Returns dict or None."""
        opts.setdefault("json_mode", True)
        text = self.route(task_type, prompt, **opts)
        if text is None:
            return None
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            # Try to extract JSON from the text
            import re
            m = re.search(r'\{[\s\S]*\}|\[[\s\S]*\]', text)
            if m:
                try:
                    return json.loads(m.group())
                except json.JSONDecodeError:
                    pass
            return None

    def _call(self, model: str, prompt: str, *, json_mode: bool, temperature: float,
              max_tokens: int, timeout: int) -> t.Optional[str]:
        if self._litellm is not None:
            try:
                kwargs = {
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                    "timeout": timeout,
                }
                if json_mode:
                    # FIX: litellm uses response_format for cloud models, format for ollama
                    if model.startswith("ollama/"):
                        kwargs["format"] = "json"
                    else:
                        kwargs["response_format"] = {"type": "json_object"}
                response = self._litellm.completion(**kwargs)
                return response.choices[0].message.content
            except Exception:
                pass  # fall through to ollama direct
        # Direct ollama fallback (for ollama/* models when litellm unavailable)
        if model.startswith("ollama/"):
            ollama_model = model.split("/", 1)[1]
            return self._call_ollama_direct(ollama_model, prompt, timeout)
        return None

    @staticmethod
    def _call_ollama_direct(model: str, prompt: str, timeout: int) -> t.Optional[str]:
        try:
            result = subprocess.run(
                ["ollama", "run", model, prompt],
                capture_output=True, text=True, timeout=timeout,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass
        return None

    def available(self) -> bool:
        """Returns True if ANY model is reachable."""
        return self._litellm is not None or self._ollama_running()

    @staticmethod
    def _ollama_running() -> bool:
        try:
            result = subprocess.run(
                ["ollama", "list"], capture_output=True, text=True, timeout=5,
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return False

    def status(self) -> dict:
        """Return routing status for debugging."""
        return {
            "litellm_available": self._litellm is not None,
            "ollama_running": self._ollama_running(),
            "anthropic_key_set": bool(os.environ.get("ANTHROPIC_API_KEY")),
            "openai_key_set": bool(os.environ.get("OPENAI_API_KEY")),
            "overrides": self.overrides,
            "task_models": {
                tt: [m for m in models if self._model_available(m)]
                for tt, models in DEFAULT_MODELS.items()
            },
        }


# Singleton
_ROUTER: t.Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    global _ROUTER
    if _ROUTER is None:
        _ROUTER = LLMRouter()
    return _ROUTER
