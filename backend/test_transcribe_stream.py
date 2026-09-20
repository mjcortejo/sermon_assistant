"""SSE transcription stream checks that do not run Whisper.

Run from the repo root:

    .venv\\Scripts\\python.exe backend/test_transcribe_stream.py
"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def fake_events(file_path: str, model_size: str = "base", start_time: float = 0.0):
    yield {
        "type": "info",
        "data": {"language": "en", "duration": 2.0, "full_text": "", "segments": []},
    }
    yield {
        "type": "segment",
        "data": {
            "language": "en",
            "full_text": "Faith is trust.",
            "segments": [{"start": 0.0, "end": 1.2, "text": "Faith is trust."}],
            "segment": {"start": 0.0, "end": 1.2, "text": "Faith is trust."},
        },
    }
    yield {
        "type": "done",
        "data": {
            "language": "en",
            "full_text": "Faith is trust.",
            "segments": [{"start": 0.0, "end": 1.2, "text": "Faith is trust."}],
            "transcript_path": "E:/tmp/faith.json",
        },
    }


def test_stream_missing_file():
    response = client.post(
        "/media/transcribe/stream",
        json={"file_path": "Z:/missing-sermon.mp4", "model_size": "tiny"},
    )
    assert response.status_code == 404, response.text


def test_transcribe_stream_emits_cues():
    existing = str(Path(__file__).resolve())
    with patch("backend.api.media.iter_transcript_events", side_effect=lambda *args, **kwargs: fake_events(*args, **kwargs)):
        with client.stream(
            "POST",
            "/media/transcribe/stream",
            json={"file_path": existing, "model_size": "tiny"},
        ) as response:
            assert response.status_code == 200, response.read().decode()
            body = "".join(response.iter_text())
    assert "event: info" in body
    assert "event: segment" in body
    assert "Faith is trust." in body
    assert "event: done" in body


def test_transcribe_stop_route():
    response = client.post("/media/transcribe/stop")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "success"


if __name__ == "__main__":
    test_stream_missing_file()
    test_transcribe_stream_emits_cues()
    test_transcribe_stop_route()
    print("Transcript stream checks passed (Whisper not invoked).")
