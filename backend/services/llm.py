"""Local LLM: prefer a running Ollama server, otherwise llama-cpp GGUF."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Optional

from backend.core.config import LLM_N_CTX, LLM_N_THREADS, OLLAMA_HOST, OLLAMA_MODEL, llm_model_path

_llm = None
_llm_path: Optional[str] = None


class ModelNotFoundError(FileNotFoundError):
    pass


class LlmUnavailableError(RuntimeError):
    pass


def _ollama_url(path: str) -> str:
    return f"{OLLAMA_HOST}{path}"


def _ollama_request(path: str, payload: dict[str, Any] | None = None, timeout: float = 2.0) -> dict[str, Any]:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        _ollama_url(path),
        data=data,
        headers={"Content-Type": "application/json"} if payload is not None else {},
        method="GET" if payload is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        if exc.code == 404:
            raise ModelNotFoundError(detail or f"Ollama model was not found ({path}).") from exc
        raise LlmUnavailableError(detail or f"Ollama returned HTTP {exc.code}.") from exc
    except urllib.error.URLError as exc:
        raise LlmUnavailableError(
            f"Ollama is not reachable at {OLLAMA_HOST}. Start Ollama and keep llama3.2:latest installed."
        ) from exc
    if not body:
        return {}
    parsed = json.loads(body)
    return parsed if isinstance(parsed, dict) else {}


def list_ollama_models() -> list[str]:
    payload = _ollama_request("/api/tags", timeout=1.5)
    names: list[str] = []
    for item in payload.get("models") or []:
        name = str(item.get("name") or item.get("model") or "").strip()
        if name:
            names.append(name)
    return names


def ollama_available() -> bool:
    try:
        list_ollama_models()
        return True
    except (LlmUnavailableError, ModelNotFoundError, TimeoutError, json.JSONDecodeError, OSError):
        return False


def _model_installed(requested: str, installed: list[str]) -> bool:
    wanted = requested.strip()
    if not wanted:
        return False
    names = set(installed)
    if wanted in names:
        return True
    base = wanted.split(":")[0]
    if ":" not in wanted and f"{base}:latest" in names:
        return True
    if wanted.endswith(":latest") and base in names:
        return True
    return False


def resolve_backend() -> str:
    requested = os.environ.get("SERMON_LLM_BACKEND", "auto").strip().lower() or "auto"
    if requested == "ollama":
        return "ollama"
    if requested == "gguf":
        return "gguf"
    if ollama_available():
        return "ollama"
    if llm_model_path().is_file():
        return "gguf"
    return "none"


def model_status() -> dict[str, Any]:
    backend = resolve_backend()
    gguf = llm_model_path()
    installed: list[str] = []
    if backend == "ollama":
        try:
            installed = list_ollama_models()
        except (LlmUnavailableError, ModelNotFoundError, json.JSONDecodeError, OSError):
            installed = []
        exists = _model_installed(OLLAMA_MODEL, installed) if installed else ollama_available()
        return {
            "backend": "ollama",
            "path": OLLAMA_HOST,
            "model": OLLAMA_MODEL,
            "exists": exists,
            "loaded": exists,
            "n_ctx": LLM_N_CTX,
            "models": installed,
        }
    return {
        "backend": backend,
        "path": str(gguf),
        "model": gguf.name,
        "exists": gguf.is_file(),
        "loaded": _llm is not None,
        "n_ctx": LLM_N_CTX,
        "models": [],
    }


def get_llama():
    """Lazy-load a GGUF model via llama-cpp-python."""
    global _llm, _llm_path
    path = llm_model_path()
    if not path.is_file():
        raise ModelNotFoundError(
            f"GGUF model not found at {path}. "
            "Place a .gguf file in backend/data/models/ or use Ollama (llama3.2:latest)."
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


def ensure_llm() -> str:
    """Make sure some local backend can answer. Returns 'ollama' or 'gguf'."""
    backend = resolve_backend()
    if backend == "ollama":
        installed = list_ollama_models()
        if not _model_installed(OLLAMA_MODEL, installed):
            available = ", ".join(installed) or "none"
            raise ModelNotFoundError(
                f"Ollama model '{OLLAMA_MODEL}' is not installed. Available: {available}. "
                "Set SERMON_OLLAMA_MODEL to one of those names."
            )
        return "ollama"
    if backend == "gguf":
        get_llama()
        return "gguf"
    raise LlmUnavailableError(
        "No local LLM is available. Start Ollama (llama3.2:latest is already on this machine) "
        "or place a GGUF file in backend/data/models/."
    )


def _ollama_chat(
    messages: list[dict[str, str]],
    *,
    json_mode: bool,
    max_tokens: int,
    temperature: float,
) -> str:
    payload: dict[str, Any] = {
        "model": OLLAMA_MODEL,
        "messages": messages,
        "stream": False,
        "keep_alive": "10m",
        "options": {
            "temperature": temperature,
            "num_predict": max_tokens,
            "num_ctx": LLM_N_CTX,
        },
    }
    if json_mode:
        payload["format"] = "json"
    result = _ollama_request("/api/chat", payload, timeout=300)
    content = (result.get("message") or {}).get("content") or ""
    return str(content).strip()


def chat_completion(
    messages: list[dict[str, str]],
    *,
    json_mode: bool = False,
    max_tokens: int = 1024,
    temperature: float = 0.3,
) -> str:
    backend = ensure_llm()
    if backend == "ollama":
        return _ollama_chat(
            messages,
            json_mode=json_mode,
            max_tokens=max_tokens,
            temperature=temperature,
        )

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
