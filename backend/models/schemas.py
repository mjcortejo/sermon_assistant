from typing import Any, Optional, Union

from pydantic import BaseModel, Field

TimeValue = Union[str, int, float]


class DownloadRequest(BaseModel):
    url: str
    output_name: Optional[str] = None


class VideoInfo(BaseModel):
    id: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    duration: Optional[float] = None
    thumbnail: Optional[str] = None
    extractor: Optional[str] = None


class DownloadResponse(BaseModel):
    status: str = "success"
    file_path: str
    info: Optional[VideoInfo] = None


class InfoResponse(BaseModel):
    status: str = "success"
    info: VideoInfo


class IngestPathRequest(BaseModel):
    source_path: str
    output_name: Optional[str] = None


class IngestResponse(BaseModel):
    status: str = "success"
    file_path: str


class ProbeResponse(BaseModel):
    status: str = "success"
    duration: float
    format: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None


class TrimRequest(BaseModel):
    input_path: str
    start_time: TimeValue
    end_time: Optional[TimeValue] = None
    output_name: Optional[str] = None


class TrimResponse(BaseModel):
    status: str = "success"
    output_path: str
    start_time: float
    end_time: Optional[float] = None


class TranscribeRequest(BaseModel):
    file_path: str
    model_size: str = Field(default="base", description="faster-whisper model size, e.g. tiny, base, small")


class TranscriptSegment(BaseModel):
    start: float
    end: float
    text: str


class TranscriptData(BaseModel):
    language: Optional[str] = None
    language_probability: Optional[float] = None
    full_text: str
    segments: list[TranscriptSegment]
    duration: Optional[float] = None


class TranscribeResponse(BaseModel):
    status: str = "success"
    data: TranscriptData
    transcript_path: str


class ErrorResponse(BaseModel):
    detail: str
    extra: Optional[dict[str, Any]] = None
