# Sermon Assistant — Phase Tracker

Local-first video sermon auto note-taking and study assistant.
Last updated: 2026-09-20

| Phase | Name | Status |
| --- | --- | --- |
| 1 | The Media Pipeline | **Complete** |
| 2 | The LLM & Note-Generation Engine | **Code complete** — GGUF runtime not installed on this Python 3.14 machine |
| 3 | The User Interface | **Complete** (Vite React; Tauri needs Rust to compile the desktop window) |
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
| 2.1 | llama-cpp-python inference pipeline (quantized GGUF, e.g. Llama-3-8B-Instruct) | Code done; package did not build on this machine |
| 2.2 | Sermon system prompts → structured JSON (theme, scriptures, takeaways, summary) | Done |
| 2.3 | SQLite persistence for sermons, generated notes, and chat history | Done |
| 2.4 | Chat endpoint that retains transcript + notes in context | Done |

### What landed

- `POST /notes/generate` — transcript → `{main_theme, scriptures, takeaways, summary}` JSON, stored in SQLite
- `GET /notes/{sermon_id}` and `PUT /notes/{sermon_id}/user` — generated notes plus the user's own notes
- `POST /chat` and `GET /chat/{sermon_id}` — Q&A with transcript + notes + history in context
- `GET /notes/model` — whether the GGUF file is on disk (does not load it)
- Long transcripts are chunked then merged so a ~8k context window can still cover a full sermon
- Default model file: `backend/data/models/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf` (override with `SERMON_LLM_MODEL`)
- Missing model returns **503** instead of crashing. First-run download stays Phase 4.

### Blocker

`llama-cpp-python` has no Python 3.14 wheel here and failed to compile (`nmake` / C++ toolchain missing). SQLAlchemy is installed. Inference will work after either:

- installing Visual Studio Build Tools and rebuilding `llama-cpp-python`, or
- using Python 3.11/3.12 (recommended for Phase 4 packaging) which has prebuilt wheels

Place the GGUF in `backend/data/models/` before generating notes. Do not bundle the 4.9GB file in git.

Visual inspect of this phase waits for Phase 3 UI.

---

## Phase 3: The User Interface

**Goal:** Tauri + React desktop UI for import, trimming, and the study workspace.

| # | Item | Status |
| --- | --- | --- |
| 3.1 | Import view (URL + local file dropzone) | Done |
| 3.2 | Trimming studio (HTML5 player + dual-handle range slider) | Done |
| 3.3 | Split-screen workspace (video/transcript vs notes/chat/user notes) | Done |
| 3.4 | Visual inspect + small UI tests (no download/trim/transcribe/LLM) | Done |

### What landed

- Vite + React UI at `http://localhost:5173` (`npm run dev`)
- Tauri 2 shell in `src-tauri/` — Rust is not installed on this machine, so the desktop wrapper is not runnable yet
- Import: URL + download, file dropzone, continue to trim
- Trim studio: HTML5 player, dual-handle range, trim (disabled until a video is loaded)
- Study: video + transcript on the left; generated notes, personal notes, chat on the right
- FastAPI `/media/file` streams local library files into the player
- Processing buttons (Download, Trim selection, Transcribe, Generate notes, Send) are present but were **not** executed in this pass

### Visual inspect + small tests (2026-09-20)

Playwright against `http://localhost:5173` with the local API up. Did not click Download, Trim selection, Transcribe, Generate notes, or Send.

Looks right:
- Top bar: Sermon Assistant, steps 1–3, **API ready**
- Import: URL field, Download, dropzone, Continue to trim
- Trim: empty-player copy, Start/End, dual sliders, Trim selection **disabled** without a video
- Study: split layout; Transcribe/Generate notes disabled without a clip/transcript; Send disabled until chat text
- Typed personal notes and a chat draft; typed a YouTube URL into Import without submitting

Nits:
- Empty trim studio showed End `0:01` because duration 0 still used a 1s slider max (guard added)
- Missing favicon 404 (svg icon added)

Run UI: `npm run dev` (frontend) and `python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000` (API).

---

## Phase 4: Packaging (Single-Click Install)

**Goal:** One installer, no Docker, models downloaded on first run, GPU if available else CPU.

| # | Item | Status |
| --- | --- | --- |
| 4.1 | PyInstaller FastAPI backend | Not started |
| 4.2 | First-run model download (Whisper + GGUF) with progress bar | Not started |
| 4.3 | Inno Setup (Windows) / DMG (macOS) bundling Tauri + backend + FFmpeg | Not started |
| 4.4 | Hardware detection (CUDA/Metal) with CPU fallback | Not started |
