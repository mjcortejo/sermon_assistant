from fastapi import APIRouter, File, HTTPException, UploadFile

from backend.core.config import DOWNLOADS_DIR, ensure_data_dirs
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
)
from backend.services.transcriber import transcribe_audio_async
from backend.services.video_editor import probe_video_async, trim_video_async

router = APIRouter(prefix="/media", tags=["Media"])


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


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
