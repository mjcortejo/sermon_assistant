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


class GenerateNotesRequest(BaseModel):
    transcript: Optional[str] = None
    title: Optional[str] = None
    transcript_path: Optional[str] = None
    project_id: Optional[int] = None


class SermonNotes(BaseModel):
    main_theme: str
    scriptures: list[str]
    takeaways: list[str]
    summary: str
    user_notes: str = ""


class NotesResponse(BaseModel):
    status: str = "success"
    project_id: int
    title: Optional[str] = None
    notes: SermonNotes


class UserNotesRequest(BaseModel):
    user_notes: str


class ChatRequest(BaseModel):
    project_id: int
    message: str


class ChatMessageOut(BaseModel):
    id: int
    role: str
    content: str


class ChatResponse(BaseModel):
    status: str = "success"
    project_id: int
    reply: str
    history: list[ChatMessageOut]


class ModelStatusResponse(BaseModel):
    path: str
    exists: bool
    loaded: bool
    n_ctx: int


class ProjectCreate(BaseModel):
    title: Optional[str] = None
    source_url: Optional[str] = None
    source_path: str = ""
    video_path: str = ""
    duration: float = 0
    trim_start: float = 0
    trim_end: float = 0
    current_step: str = "import"


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    source_url: Optional[str] = None
    source_path: Optional[str] = None
    video_path: Optional[str] = None
    duration: Optional[float] = None
    trim_start: Optional[float] = None
    trim_end: Optional[float] = None
    transcript: Optional[dict[str, Any]] = None
    transcript_path: Optional[str] = None
    current_step: Optional[str] = None
    user_notes: Optional[str] = None


class ProjectSummary(BaseModel):
    id: int
    title: str
    source_url: Optional[str] = None
    source_path: str = ""
    video_path: str = ""
    duration: float = 0
    current_step: str = "import"
    has_transcript: bool = False
    has_notes: bool = False
    updated_at: Optional[str] = None
    created_at: Optional[str] = None


class ProjectDetail(ProjectSummary):
    trim_start: float = 0
    trim_end: float = 0
    transcript: Optional[dict[str, Any]] = None
    transcript_path: Optional[str] = None
    user_notes: str = ""
    notes: Optional[SermonNotes] = None
    chat: list[ChatMessageOut] = []


class ProjectListResponse(BaseModel):
    status: str = "success"
    projects: list[ProjectSummary]


class ProjectResponse(BaseModel):
    status: str = "success"
    project: ProjectDetail
