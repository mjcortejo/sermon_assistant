"""OCR checks for slide/verse text. Uses RapidOCR on a generated image.

Run from the repo root:

    .venv\\Scripts\\python.exe backend/test_ocr.py
"""

import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from PIL import Image, ImageDraw

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.ocr import format_screen_texts, ocr_image

client = TestClient(app)


def _slide_image() -> Path:
    path = Path(ROOT) / "backend" / "data" / "media" / "frames" / "ocr_test_slide.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    image = Image.new("RGB", (900, 220), "white")
    draw = ImageDraw.Draw(image)
    draw.text((32, 80), "John 3:16 For God so loved the world", fill="black")
    image.save(path)
    return path


def test_rapidocr_reads_slide_text():
    path = _slide_image()
    result = ocr_image(str(path))
    text = (result["text"] or "").lower()
    assert "john 3:16" in text
    assert "loved" in text


def test_format_screen_texts():
    formatted = format_screen_texts(
        [{"timestamp": 74, "text": "Romans 8:28"}, {"timestamp": 12.4, "text": "  "}]
    )
    assert formatted == "[1:14] Romans 8:28"


def test_ocr_missing_file():
    response = client.post(
        "/media/ocr",
        json={"file_path": "Z:/missing-sermon.mp4", "timestamp": 1.5},
    )
    assert response.status_code == 404, response.text


def test_ocr_persists_on_project():
    created = client.post(
        "/projects",
        json={
            "title": "Slide study",
            "source_path": "E:/tmp/sermon.mp4",
            "video_path": "E:/tmp/sermon.mp4",
            "duration": 90,
            "current_step": "study",
        },
    )
    assert created.status_code == 200, created.text
    project_id = created.json()["project"]["id"]

    fake = {
        "timestamp": 12.5,
        "text": "John 3:16 For God so loved the world",
        "lines": ["John 3:16 For God so loved the world"],
        "confidence": 0.99,
        "frame_path": "E:/tmp/frame.png",
    }
    with patch("backend.api.media.capture_on_screen_text_async", new=AsyncMock(return_value=fake)):
        response = client.post(
            "/media/ocr",
            json={"file_path": "E:/tmp/sermon.mp4", "timestamp": 12.5, "project_id": project_id},
        )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "John 3:16" in payload["text"]
    assert payload["captures"]
    assert payload["captures"][0]["timestamp"] == 12.5

    loaded = client.get(f"/projects/{project_id}")
    assert loaded.status_code == 200, loaded.text
    captures = loaded.json()["project"]["captures"]
    assert captures and "John 3:16" in captures[0]["text"]

    client.delete(f"/projects/{project_id}")


if __name__ == "__main__":
    test_rapidocr_reads_slide_text()
    test_format_screen_texts()
    test_ocr_missing_file()
    test_ocr_persists_on_project()
    print("OCR checks passed.")
