"""Pick a Whisper runtime: CUDA when CTranslate2 can see a GPU, otherwise CPU."""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from functools import lru_cache

CUDA_COMPUTE_PREFERENCE = (
    "int8",
    "int8_float16",
    "float16",
    "bfloat16",
    "int8_float32",
    "float32",
)
CPU_COMPUTE_PREFERENCE = ("int8", "int8_float32", "int16", "float32")


@dataclass(frozen=True)
class WhisperRuntime:
    device: str
    compute_type: str
    gpu_name: str | None = None


def _env_device() -> str:
    return os.environ.get("SERMON_WHISPER_DEVICE", "auto").strip().lower() or "auto"


def _env_compute_type() -> str | None:
    value = os.environ.get("SERMON_WHISPER_COMPUTE_TYPE", "").strip().lower()
    return value or None


def _pick_compute(preferred: str | None, supported: set[str], order: tuple[str, ...]) -> str:
    if preferred and preferred in supported:
        return preferred
    for item in order:
        if item in supported:
            return item
    return "float32"


def _gpu_name() -> str | None:
    try:
        output = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            text=True,
            timeout=3,
            stderr=subprocess.DEVNULL,
        )
        name = output.strip().splitlines()[0].strip()
        return name or None
    except Exception:
        return None


@lru_cache(maxsize=1)
def detect_whisper_runtime() -> WhisperRuntime:
    """
    Auto-select CUDA when a GPU is visible to CTranslate2.
    Override with SERMON_WHISPER_DEVICE=cpu|cuda and SERMON_WHISPER_COMPUTE_TYPE.
    """
    requested = _env_device()
    preferred_compute = _env_compute_type()

    try:
        import ctranslate2
    except Exception:
        return WhisperRuntime(device="cpu", compute_type=preferred_compute or "int8")

    cuda_count = 0
    if requested != "cpu":
        try:
            cuda_count = int(ctranslate2.get_cuda_device_count() or 0)
        except Exception:
            cuda_count = 0

    if requested == "cuda" or (requested == "auto" and cuda_count > 0):
        if cuda_count > 0:
            try:
                supported = set(ctranslate2.get_supported_compute_types("cuda"))
            except Exception:
                supported = {"float32"}
            return WhisperRuntime(
                device="cuda",
                compute_type=_pick_compute(preferred_compute, supported, CUDA_COMPUTE_PREFERENCE),
                gpu_name=_gpu_name(),
            )
        if requested == "cuda":
            # User asked for GPU but none is usable.
            pass

    try:
        supported = set(ctranslate2.get_supported_compute_types("cpu"))
    except Exception:
        supported = {"int8", "float32"}
    return WhisperRuntime(
        device="cpu",
        compute_type=_pick_compute(preferred_compute, supported, CPU_COMPUTE_PREFERENCE),
    )
