"""Whisper device selection. Does not run a transcription.

Run from the repo root:

    .venv\\Scripts\\python.exe backend/test_hardware.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient

from backend.core.hardware import detect_whisper_runtime
from backend.main import app

client = TestClient(app)


def test_health_reports_whisper_runtime():
    detect_whisper_runtime.cache_clear()
    response = client.get("/health")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["status"] == "ok"
    whisper = payload["whisper"]
    assert whisper["device"] in {"cuda", "cpu"}
    assert whisper["compute_type"]


def test_cpu_override(monkeypatch):
    monkeypatch.setenv("SERMON_WHISPER_DEVICE", "cpu")
    detect_whisper_runtime.cache_clear()
    runtime = detect_whisper_runtime()
    assert runtime.device == "cpu"
    detect_whisper_runtime.cache_clear()


def test_auto_selects_usable_device():
    detect_whisper_runtime.cache_clear()
    runtime = detect_whisper_runtime()
    assert runtime.device in {"cuda", "cpu"}
    if runtime.device == "cuda":
        assert runtime.compute_type in {"int8", "int8_float16", "float16", "int8_float32", "float32"}


if __name__ == "__main__":
    class _Dummy:
        def setenv(self, key, value):
            os.environ[key] = value

    test_health_reports_whisper_runtime()
    test_auto_selects_usable_device()
    test_cpu_override(_Dummy())
    os.environ.pop("SERMON_WHISPER_DEVICE", None)
    detect_whisper_runtime.cache_clear()
    print("Whisper hardware checks passed.")
