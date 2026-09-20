"""API checks that do not require a GGUF model on disk.

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


def test_model_status_and_generate_without_backend():
    response = client.get("/notes/model")
    assert response.status_code == 200, response.text
    payload = response.json()
    assert "backend" in payload
    assert "exists" in payload
    if payload.get("backend") in {None, "none"} or not payload.get("exists"):
        response = client.post(
            "/notes/generate",
            json={"transcript": "God is faithful.", "title": "Smoke"},
        )
        assert response.status_code == 503, response.text

    response = client.post("/chat", json={"project_id": 999999, "message": "What was the theme?"})
    assert response.status_code in {404, 400, 503}, response.text


def test_project_create_list_and_reload():
    created = client.post(
        "/projects",
        json={
            "title": "Faithfulness",
            "source_path": "E:/tmp/sermon.mp4",
            "video_path": "E:/tmp/sermon.mp4",
            "duration": 120,
            "current_step": "trim",
        },
    )
    assert created.status_code == 200, created.text
    project_id = created.json()["project"]["id"]

    listed = client.get("/projects")
    assert listed.status_code == 200, listed.text
    ids = [item["id"] for item in listed.json()["projects"]]
    assert project_id in ids

    patched = client.patch(
        f"/projects/{project_id}",
        json={"user_notes": "Keep going with this study.", "current_step": "study"},
    )
    assert patched.status_code == 200, patched.text
    assert patched.json()["project"]["user_notes"] == "Keep going with this study."

    loaded = client.get(f"/projects/{project_id}")
    assert loaded.status_code == 200, loaded.text
    assert loaded.json()["project"]["title"] == "Faithfulness"
    assert loaded.json()["project"]["current_step"] == "study"

    deleted = client.delete(f"/projects/{project_id}")
    assert deleted.status_code == 200, deleted.text


if __name__ == "__main__":
    test_model_status_and_generate_without_backend()
    test_project_create_list_and_reload()
    print("Project and notes API checks passed.")
