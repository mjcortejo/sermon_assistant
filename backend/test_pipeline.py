"""Manual end-to-end check: download → trim → transcribe.

Run from the repo root:

    python backend/test_pipeline.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)

# "Me at the zoo" — short public YouTube clip suitable for a smoke test.
TEST_URL = "https://www.youtube.com/watch?v=jNQXAC9IVRw"


def test_full_pipeline():
    print("1. Downloading video...")
    response = client.post("/media/download", json={"url": TEST_URL, "output_name": "test_video"})
    assert response.status_code == 200, f"Download failed: {response.text}"
    file_path = response.json()["file_path"]
    print(f"   Downloaded to: {file_path}")

    print("2. Probing video...")
    response = client.get("/media/probe", params={"path": file_path})
    assert response.status_code == 200, f"Probe failed: {response.text}"
    print(f"   Duration: {response.json()['duration']}s")

    print("3. Trimming video (first 5 seconds)...")
    response = client.post(
        "/media/trim",
        json={
            "input_path": file_path,
            "start_time": "00:00:00",
            "end_time": "00:00:05",
            "output_name": "test_video_trim",
        },
    )
    assert response.status_code == 200, f"Trim failed: {response.text}"
    trimmed_path = response.json()["output_path"]
    print(f"   Trimmed to: {trimmed_path}")

    print("4. Transcribing trimmed clip (whisper tiny)...")
    response = client.post(
        "/media/transcribe",
        json={"file_path": trimmed_path, "model_size": "tiny"},
    )
    assert response.status_code == 200, f"Transcription failed: {response.text}"
    payload = response.json()
    data = payload["data"]
    print(f"   Language: {data['language']}")
    print(f"   Segments: {len(data['segments'])}")
    print(f"   Text: {data['full_text']}")
    print(f"   Transcript JSON: {payload['transcript_path']}")


if __name__ == "__main__":
    test_full_pipeline()
    print("All tests passed successfully!")
