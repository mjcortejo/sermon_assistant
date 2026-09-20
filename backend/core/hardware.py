"""Pick a Whisper runtime: CUDA when CTranslate2 can see a GPU, otherwise CPU."""

from __future__ import annotations

import os
import site
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

CUDA_COMPUTE_PREFERENCE = (
    "int8",
    "int8_float16",
    "float16",
    "bfloat16",
    "int8_float32",
    "float32",
)
CPU_COMPUTE_PREFERENCE = ("int8", "int8_float32", "int16", "float32")

_dll_dirs_ready = False


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
        import subprocess

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


def _nvidia_bin_dirs() -> list[Path]:
    dirs: list[Path] = []
    roots: list[Path] = []
    try:
        roots.extend(Path(p) for p in site.getsitepackages())
    except Exception:
        pass
    roots.append(Path(sys.prefix) / "Lib" / "site-packages")
    seen: set[Path] = set()
    for root in roots:
        nvidia = root / "nvidia"
        if not nvidia.is_dir():
            continue
        for bin_dir in nvidia.glob("*/bin"):
            resolved = bin_dir.resolve()
            if resolved.is_dir() and resolved not in seen:
                seen.add(resolved)
                dirs.append(resolved)
    return dirs


def ensure_cuda_dll_dirs() -> None:
    """Put pip CUDA wheels on the DLL search path (Windows needs this for cublas64_12.dll)."""
    global _dll_dirs_ready
    if _dll_dirs_ready:
        return
    dirs = _nvidia_bin_dirs()
    if dirs:
        os.environ["PATH"] = os.pathsep.join(str(path) for path in dirs) + os.pathsep + os.environ.get("PATH", "")
        adder = getattr(os, "add_dll_directory", None)
        if adder is not None:
            for path in dirs:
                try:
                    adder(str(path))
                except OSError:
                    pass
    _dll_dirs_ready = True


def cuda_libraries_available() -> bool:
    """True when the CUDA 12 runtime CTranslate2 needs can actually load."""
    ensure_cuda_dll_dirs()
    if os.name != "nt":
        return True
    try:
        from ctypes import WinDLL

        WinDLL("cublas64_12.dll")
        return True
    except OSError:
        return False


def is_cuda_library_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(
        token in text
        for token in ("cublas", "cublas64", "cudnn", "cudnn64", "nvcuda", "cuda runtime")
    )


@lru_cache(maxsize=1)
def detect_whisper_runtime() -> WhisperRuntime:
    """
    Auto-select CUDA when a GPU is visible to CTranslate2 and cuBLAS can load.
    Override with SERMON_WHISPER_DEVICE=cpu|cuda and SERMON_WHISPER_COMPUTE_TYPE.
    """
    requested = _env_device()
    preferred_compute = _env_compute_type()
    ensure_cuda_dll_dirs()

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

    use_cuda = requested != "cpu" and cuda_count > 0 and (
        requested == "cuda" or cuda_libraries_available()
    )
    if use_cuda:
        try:
            supported = set(ctranslate2.get_supported_compute_types("cuda"))
        except Exception:
            supported = {"float32"}
        return WhisperRuntime(
            device="cuda",
            compute_type=_pick_compute(preferred_compute, supported, CUDA_COMPUTE_PREFERENCE),
            gpu_name=_gpu_name(),
        )

    try:
        supported = set(ctranslate2.get_supported_compute_types("cpu"))
    except Exception:
        supported = {"int8", "float32"}
    return WhisperRuntime(
        device="cpu",
        compute_type=_pick_compute(preferred_compute, supported, CPU_COMPUTE_PREFERENCE),
    )
