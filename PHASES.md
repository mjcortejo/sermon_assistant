# Sermon Assistant — Phase Tracker

Local-first video sermon auto note-taking and study assistant.
Last updated: 2026-09-20

| Phase | Name | Status |
| --- | --- | --- |
| 1 | The Media Pipeline | **Complete** |
| 2 | The LLM & Note-Generation Engine | Not started — waiting for approval |
| 3 | The User Interface | Not started |
| 4 | Packaging (Single-Click Install) | Not started |

Review this file anytime to see what is done, what was verified, and what is next. Code for a new phase does not start until the phase checklist is approved.

---

## Phase 1: The Media Pipeline

**Goal:** Download (yt-dlp), trim (FFmpeg lossless), and transcribe (faster-whisper with timestamps) entirely on the local machine.

| # | Item | Status |
| --- | --- | --- |
| 1.1 | Backend scaffold (package layout, FastAPI app, CORS, health check, requirements) | Done |
| 1.2 | Local media storage (`downloads/`, `trims/`, `transcripts/`) | Done |
| 1.3 | yt-dlp download for YouTube and public Facebook Live, returning the real file path | Done (YouTube verified; Facebook uses the same yt-dlp path) |
| 1.4 | Lossless FFmpeg trim API (`-c copy`), server-generated output path | Done |
| 1.5 | faster-whisper transcription with timestamped segments + persisted JSON | Done |
| 1.6 | Media routes and typed schemas (download, info, upload/ingest, probe, trim, transcribe) | Done |
| 1.7 | End-to-end verification (download → trim → transcribe) | Done |
| 1.8 | Visual inspect (local Swagger + `/health`; no media processing) | Done |

### What landed

- `backend/` is a runnable Python package with `__init__.py` files.
- Local storage lives under `backend/data/`:
  - `media/downloads/` — yt-dlp and uploaded/ingested source files
  - `media/trims/` — lossless clips
  - `media/transcripts/` — JSON transcripts
  - `models/` — Whisper weights (downloaded on first transcribe)
  - `db/` — reserved for Phase 2 SQLite
- GPU/CUDA/Metal auto-detect is still Phase 4. Whisper currently runs **CPU + int8**.

### API (all local)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Process is up |
| POST | `/media/download` | yt-dlp YouTube / public Facebook Live → `downloads/` |
| GET | `/media/info` | Metadata only (no download) |
| POST | `/media/upload` | Multipart file upload → `downloads/` |
| POST | `/media/ingest-path` | Copy an existing local file into `downloads/` |
| GET | `/media/probe` | Duration / codec via FFmpeg |
| POST | `/media/trim` | Lossless clip (`-c copy`) → `trims/` |
| POST | `/media/transcribe` | faster-whisper + timestamps → JSON in `transcripts/` |

### Visual inspect (2026-09-20)

Phase 1 has no app UI yet (that is Phase 3). Inspected the local FastAPI surface only: `http://127.0.0.1:8000/docs` and `http://127.0.0.1:8000/health`. Did **not** Execute download, trim, transcribe, info, or probe.

Looks right:
- Title **Sermon Assistant API** `1.0.0`, OAS 3.1
- **Media** group: POST download, GET info, POST ingest-path, POST upload, GET probe, POST trim, POST transcribe
- **default** group: GET `/`, GET `/health`
- `/health` renders `{"status":"ok"}`

Nit: `/` and `/health` sit under an unnamed `default` tag instead of something like `System`. Cosmetic only.

---

### Verification (2026-09-20)

Ran against the local FastAPI app with FFmpeg on PATH and a project `.venv`.

1. **Helpers + trim:** ingest of a generated 8s MP4, probe duration, lossless trim 1s–4s, invalid range returns 400.
2. **Speech transcription:** synthesized spoken clip transcribed with `tiny` as  
   `"Welcome to this sermon about faith hope and love in Jesus Christ."` with a timestamped segment.
3. **Full URL pipeline:** YouTube `jNQXAC9IVRw` (“Me at the zoo”)  
   download → trim 0–5s → transcribe `tiny` →  
   `"All right, so here we are one of the elephants."`

Facebook Live was not hit with a church URL in this pass. It goes through the same yt-dlp service; we should smoke-test a real public church link when you have one.

### How to run (dev)

From the repo root, FFmpeg must be on PATH:

```text
python -m venv .venv
.venv\Scripts\activate
pip install fastapi[all] yt-dlp ffmpeg-python pydantic httpx faster-whisper
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Smoke tests:

```text
.venv\Scripts\python.exe backend/test_local_pipeline.py
.venv\Scripts\python.exe backend/test_pipeline.py
```

`backend/requirements.txt` still lists Phase 2 packages (`llama-cpp-python`, SQLAlchemy). Those are not required to run Phase 1.

---

## Phase 2: The LLM & Note-Generation Engine

**Goal:** Local llama-cpp-python inference that turns a Whisper transcript into structured sermon notes, plus contextual chat.

| # | Item | Status |
| --- | --- | --- |
| 2.1 | llama-cpp-python inference pipeline (quantized GGUF, e.g. Llama-3-8B-Instruct) | Not started |
| 2.2 | Sermon system prompts → structured JSON (theme, scriptures, takeaways, summary) | Not started |
| 2.3 | SQLite persistence for sermons, generated notes, and chat history | Not started |
| 2.4 | Chat endpoint that retains transcript + notes in context | Not started |

**Blocked on:** your approval of a detailed Phase 2 checklist (same gate as Phase 1).

---

## Phase 3: The User Interface

**Goal:** Tauri + React desktop UI for import, trimming, and the study workspace.

| # | Item | Status |
| --- | --- | --- |
| 3.1 | Import view (URL + local file dropzone) | Not started |
| 3.2 | Trimming studio (HTML5 player + dual-handle range slider) | Not started |
| 3.3 | Split-screen workspace (video/transcript vs notes/chat/user notes) | Not started |

---

## Phase 4: Packaging (Single-Click Install)

**Goal:** One installer, no Docker, models downloaded on first run, GPU if available else CPU.

| # | Item | Status |
| --- | --- | --- |
| 4.1 | PyInstaller FastAPI backend | Not started |
| 4.2 | First-run model download (Whisper + GGUF) with progress bar | Not started |
| 4.3 | Inno Setup (Windows) / DMG (macOS) bundling Tauri + backend + FFmpeg | Not started |
| 4.4 | Hardware detection (CUDA/Metal) with CPU fallback | Not started |
