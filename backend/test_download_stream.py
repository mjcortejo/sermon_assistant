"""Download progress stream checks that do not hit the network.

Run from the repo root:

    .venv\\Scripts\\python.exe backend/test_download_stream.py
"""

import os
import sys
from unittest.mock import patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def fake_download(url, output_name=None, on_progress=None):
    if on_progress:
        on_progress({"phase": "resolving", "percent": 0.0, "message": "Looking up the video…"})
        on_progress(
            {
                "phase": "downloading",
                "percent": 40.0,
                "downloaded_bytes": 40,
                "total_bytes": 100,
                "speed": 10,
                "eta": 6,
                "message": "Downloading…",
            }
        )
    return {
        "file_path": "E:/tmp/sermon.mp4",
        "info": {"title": "Sunday sermon", "duration": 120},
    }


def test_download_stream_requires_url():
    response = client.post("/media/download/stream", json={"url": "  "})
    assert response.status_code == 400, response.text


def test_download_stream_emits_progress():
    with patch("backend.services.downloader.download_video", side_effect=fake_download):
        with client.stream("POST", "/media/download/stream", json={"url": "https://example.com/watch"}) as response:
            assert response.status_code == 200, response.read().decode()
            body = "".join(response.iter_text())
    assert "event: progress" in body
    assert "Looking up the video" in body
    assert "event: done" in body
    assert "Sunday sermon" in body


if __name__ == "__main__":
    test_download_stream_requires_url()
    test_download_stream_emits_progress()
    print("Download progress stream checks passed (no network).")
