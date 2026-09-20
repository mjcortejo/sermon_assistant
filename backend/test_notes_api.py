"""Phase 2 API checks that do not require a GGUF model on disk.

Run from the repo root:

    .venv\\Scripts\\python.exe backend/test_notes_api.py
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_model_status_and_generate_without_gguf():
    response = client.get("/notes/model")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "path" in payload
    assert payload["exists"] is False
    assert payload["loaded"] is False

    response = client.post(
        "/notes/generate",
        json={"transcript": "God is faithful.", "title": "Smoke"},
    )
    assert response.status_code == 503, response.text

    response = client.post("/chat", json={"sermon_id": 1, "message": "What was the theme?"})
    assert response.status_code in {404, 503}, response.text


if __name__ == "__main__":
    test_model_status_and_generate_without_gguf()
    print("Notes API checks passed (no GGUF present).")
