from pydantic import BaseModel
from typing import Optional

class DownloadRequest(BaseModel):
    url: str
    output_name: Optional[str] = None

class TrimRequest(BaseModel):
    input_path: str
    output_path: str
    start_time: str
    end_time: Optional[str] = None

class TranscribeRequest(BaseModel):
    file_path: str
    model_size: str = "base"
