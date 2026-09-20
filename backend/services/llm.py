"""Local GGUF inference via llama-cpp-python. CPU-only in Phase 2."""

from __future__ import annotations

import os
from typing import Any, Optional

from backend.core.config import LLM_N_CTX, LLM_N_THREADS, llm_model_path

_llm = None
_llm_path: Optional[str] = None


class ModelNotFoundError(FileNotFoundError):
    pass


class LlmUnavailableError(RuntimeError):
    pass


def model_status() -> dict[str, Any]:
    path = llm_model_path()
    return {
        "path": str(path),
        "exists": path.is_file(),
        "loaded": _llm is not None,
        "n_ctx": LLM_N_CTX,
    }


def get_llama():
    """Lazy-load the GGUF model. Reloads if the configured path changes."""
    global _llm, _llm_path
    path = llm_model_path()
    if not path.is_file():
        raise ModelNotFoundError(
            f"GGUF model not found at {path}. "
            "Place Meta-Llama-3-8B-Instruct-Q4_K_M.gguf in backend/data/models/ "
            "(or set SERMON_LLM_MODEL). First-run download is Phase 4."
        )

    resolved = str(path.resolve())
    if _llm is None or _llm_path != resolved:
        try:
            from llama_cpp import Llama
        except ImportError as exc:
            raise LlmUnavailableError(
                "llama-cpp-python is not installed in this environment."
            ) from exc

        threads = int(LLM_N_THREADS) if LLM_N_THREADS else os.cpu_count() or 4
        _llm = Llama(
            model_path=resolved,
            n_ctx=LLM_N_CTX,
            n_threads=threads,
            n_gpu_layers=0,
            verbose=False,
        )
        _llm_path = resolved
    return _llm


def chat_completion(
    messages: list[dict[str, str]],
    *,
    json_mode: bool = False,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> str:
    llm = get_llama()
    kwargs: dict[str, Any] = {
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    result = llm.create_chat_completion(**kwargs)
    choice = result["choices"][0]
    content = choice.get("message", {}).get("content") or ""
    return content.strip()
