"""Local media pipeline checks that do not require YouTube.

Creates no network traffic except when Whisper downloads its model.
Run from the repo root:

    .venv\\Scripts\\python.exe backend/test_local_pipeline.py
"""

import os
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient

from backend.core.utils import time_to_seconds
from backend.main import app

SOURCE = Path(ROOT) / "backend" / "data" / "media" / "downloads" / "_phase1_source.mp4"
client = TestClient(app)


def test_time_helpers():
    assert time_to_seconds("00:01:30") == 90
    assert time_to_seconds("1:02") == 62
    assert time_to_seconds(12.5) == 12.5
    try:
        time_to_seconds(-1)
        raise AssertionError("negative time should fail")
    except ValueError:
        pass


def test_health_and_trim():
    assert SOURCE.is_file(), f"Missing fixture video: {SOURCE}"

    response = client.get("/health")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "ok"

    response = client.post(
        "/media/ingest-path",
        json={"source_path": str(SOURCE), "output_name": "phase1_ingest"},
    )
    assert response.status_code == 200, response.text
    ingested = response.json()["file_path"]
    assert Path(ingested).is_file()

    response = client.get("/media/probe", params={"path": ingested})
    assert response.status_code == 200, response.text
    duration = response.json()["duration"]
    assert duration >= 7, f"unexpected duration {duration}"

    response = client.post(
        "/media/trim",
        json={
            "input_path": ingested,
            "start_time": "00:00:01",
            "end_time": "00:00:04",
            "output_name": "phase1_trim",
        },
    )
    assert response.status_code == 200, response.text
    trimmed = response.json()["output_path"]
    assert Path(trimmed).is_file()
    assert Path(trimmed).stat().st_size > 0

    response = client.post(
        "/media/trim",
        json={"input_path": ingested, "start_time": 5, "end_time": 2},
    )
    assert response.status_code == 400, response.text

    return trimmed


def test_transcribe(trimmed_path: str):
    response = client.post(
        "/media/transcribe",
        json={"file_path": trimmed_path, "model_size": "tiny"},
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert Path(payload["transcript_path"]).is_file()
    data = payload["data"]
    assert "full_text" in data
    assert isinstance(data["segments"], list)
    print(f"   Language: {data.get('language')}")
    print(f"   Segments: {len(data['segments'])}")
    print(f"   Text: {data.get('full_text')!r}")
    print(f"   Transcript: {payload['transcript_path']}")


if __name__ == "__main__":
    print("1. Time helpers...")
    test_time_helpers()
    print("2. Health, ingest, probe, trim...")
    trimmed = test_health_and_trim()
    print(f"   Trimmed clip: {trimmed}")
    print("3. Transcribe (faster-whisper tiny)...")
    test_transcribe(trimmed)
    print("Local pipeline checks passed.")
