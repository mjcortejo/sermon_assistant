import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_full_pipeline():
    # 1. Download a very short video
    # "Me at the zoo" is the shortest, but let's use a very short test video URL
    test_url = "https://www.youtube.com/watch?v=jNQXAC9IVRw"
    print("1. Downloading video...")
    response = client.post("/media/download", json={"url": test_url, "output_name": "test_video"})
    assert response.status_code == 200, f"Download failed: {response.text}"
    file_path = response.json()["file_path"]
    print(f"Downloaded to: {file_path}")
    
    # 2. Trim the video
    print("2. Trimming video (first 5 seconds)...")
    trim_output = file_path.replace(".webm", "_trimmed.webm").replace(".mp4", "_trimmed.mp4")
    response = client.post("/media/trim", json={
        "input_path": file_path,
        "output_path": trim_output,
        "start_time": "00:00:00",
        "end_time": "00:00:05"
    })
    assert response.status_code == 200, f"Trim failed: {response.text}"
    trimmed_path = response.json()["output_path"]
    print(f"Trimmed to: {trimmed_path}")
    
    # 3. Transcribe the trimmed video
    print("3. Transcribing video...")
    response = client.post("/media/transcribe", json={
        "file_path": trimmed_path,
        "model_size": "tiny"  # using tiny for faster testing
    })
    assert response.status_code == 200, f"Transcription failed: {response.text}"
    data = response.json()["data"]
    print("Transcription complete!")
    print(f"Detected Language: {data['language']}")
    print(f"Text: {data['full_text']}")

if __name__ == "__main__":
    test_full_pipeline()
    print("All tests passed successfully!")
