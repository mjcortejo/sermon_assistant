import asyncio
import json
import threading
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse

from backend.core.config import DOWNLOADS_DIR, MEDIA_DIR, ensure_data_dirs
from backend.core.utils import safe_filename, unique_path
from backend.models.schemas import (
    DownloadRequest,
    DownloadResponse,
    InfoResponse,
    IngestPathRequest,
    IngestResponse,
    ProbeResponse,
    TranscribeRequest,
    TranscribeResponse,
    TranscriptData,
    TrimRequest,
    TrimResponse,
    VideoInfo,
)
from backend.services.downloader import (
    download_video_async,
    get_video_info_async,
    ingest_local_file_async,
    iter_download_events,
)
from backend.services.transcriber import ALLOWED_MODEL_SIZES, iter_transcript_events, transcribe_audio_async
from backend.services.video_editor import probe_video_async, trim_video_async

router = APIRouter(prefix="/media", tags=["Media"])


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _event_stream(producer):
    loop = asyncio.get_running_loop()
    queue: asyncio.Queue[dict | None] = asyncio.Queue()

    def worker() -> None:
        try:
            for event in producer():
                asyncio.run_coroutine_threadsafe(queue.put(event), loop).result()
        except Exception as exc:
            asyncio.run_coroutine_threadsafe(
                queue.put({"type": "error", "data": {"detail": str(exc)}}),
                loop,
            ).result()
        finally:
            asyncio.run_coroutine_threadsafe(queue.put(None), loop).result()

    threading.Thread(target=worker, daemon=True).start()

    async def generate():
        while True:
            item = await queue.get()
            if item is None:
                break
            yield _sse(item.get("type") or "message", item.get("data") or {})

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/download", response_model=DownloadResponse)
async def download_media(request: DownloadRequest):
    try:
        result = await download_video_async(request.url, request.output_name)
        return DownloadResponse(
            file_path=result["file_path"],
            info=VideoInfo(**result["info"]) if result.get("info") else None,
        )
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/download/stream")
async def download_media_stream(request: DownloadRequest):
    """Stream yt-dlp progress so the import step can show a live bar."""
    url = (request.url or "").strip()
    if not url:
        raise HTTPException(status_code=400, detail="A video URL is required.")
    return _event_stream(lambda: iter_download_events(url, request.output_name))


@router.get("/info", response_model=InfoResponse)
async def get_info(url: str):
    try:
        info = await get_video_info_async(url)
        return InfoResponse(info=VideoInfo(**info))
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/ingest-path", response_model=IngestResponse)
async def ingest_path(request: IngestPathRequest):
    try:
        file_path = await ingest_local_file_async(request.source_path, request.output_name)
        return IngestResponse(file_path=file_path)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/upload", response_model=IngestResponse)
async def upload_media(file: UploadFile = File(...)):
    ensure_data_dirs()
    original = file.filename or "upload.mp4"
    dest = unique_path(DOWNLOADS_DIR, safe_filename(original, fallback="upload.mp4"))
    try:
        with dest.open("wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)
                if not chunk:
                    break
                buffer.write(chunk)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc
    finally:
        await file.close()

    if dest.stat().st_size == 0:
        dest.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    return IngestResponse(file_path=str(dest.resolve()))


@router.get("/probe", response_model=ProbeResponse)
async def probe_media(path: str):
    try:
        info = await probe_video_async(path)
        return ProbeResponse(**info)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/trim", response_model=TrimResponse)
async def trim_media(request: TrimRequest):
    try:
        result = await trim_video_async(
            request.input_path,
            request.start_time,
            request.end_time,
            request.output_name,
        )
        return TrimResponse(**result)
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/transcribe", response_model=TranscribeResponse)
async def transcribe_media(request: TranscribeRequest):
    try:
        result = await transcribe_audio_async(request.file_path, request.model_size)
        transcript_path = result.pop("transcript_path")
        return TranscribeResponse(
            data=TranscriptData(**result),
            transcript_path=transcript_path,
        )
    except Exception as exc:
        raise _http_error(exc) from exc


@router.post("/transcribe/stream")
async def transcribe_media_stream(request: TranscribeRequest):
    """Stream timestamped cues as faster-whisper produces them (SSE)."""
    source = Path(request.file_path)
    if not source.is_file():
        raise HTTPException(status_code=404, detail=f"Audio/video file not found: {request.file_path}")
    if request.model_size not in ALLOWED_MODEL_SIZES:
        raise HTTPException(status_code=400, detail=f"Unsupported Whisper model size: {request.model_size}")
    return _event_stream(lambda: iter_transcript_events(request.file_path, request.model_size))


@router.get("/file")
def stream_media(path: str):
    """Stream a file from the local media library so the HTML5 player can play it."""
    try:
        resolved = Path(path).expanduser().resolve()
        root = MEDIA_DIR.resolve()
        if not resolved.is_file() or not resolved.is_relative_to(root):
            raise FileNotFoundError("File is not in the local media library.")
        return FileResponse(resolved)
    except Exception as exc:
        raise _http_error(exc) from exc
