from fastapi import APIRouter, HTTPException
from backend.models.schemas import DownloadRequest, TrimRequest, TranscribeRequest
from backend.services.downloader import download_video_async, get_video_info
from backend.services.video_editor import trim_video_async
from backend.services.transcriber import transcribe_audio_async

router = APIRouter(prefix="/media", tags=["Media"])

@router.post("/download")
async def download_media(request: DownloadRequest):
    try:
        file_path = await download_video_async(request.url, request.output_name)
        return {"status": "success", "file_path": file_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/info")
async def get_info(url: str):
    try:
        info = get_video_info(url)
        return {"status": "success", "info": info}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/trim")
async def trim_media(request: TrimRequest):
    try:
        output_path = await trim_video_async(
            request.input_path, 
            request.output_path, 
            request.start_time, 
            request.end_time
        )
        return {"status": "success", "output_path": output_path}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/transcribe")
async def transcribe_media(request: TranscribeRequest):
    try:
        result = await transcribe_audio_async(request.file_path, request.model_size)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
