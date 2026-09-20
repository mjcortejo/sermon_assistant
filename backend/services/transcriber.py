import asyncio
import json
from pathlib import Path
from typing import Any, Optional

from faster_whisper import WhisperModel

from backend.core.config import MODELS_DIR, TRANSCRIPTS_DIR, ensure_data_dirs
from backend.core.utils import unique_path

_model: Optional[WhisperModel] = None
_model_key: Optional[tuple[str, str, str]] = None

DEFAULT_DEVICE = "cpu"
DEFAULT_COMPUTE_TYPE = "int8"


def get_model(
    model_size: str = "base",
    device: str = DEFAULT_DEVICE,
    compute_type: str = DEFAULT_COMPUTE_TYPE,
) -> WhisperModel:
    """
    Lazy-load faster-whisper. Reloads if size/device/compute_type change.
    Phase 1 uses CPU + int8. GPU selection is Phase 4.
    """
    global _model, _model_key
    key = (model_size, device, compute_type)
    if _model is None or _model_key != key:
        _model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            download_root=str(MODELS_DIR),
        )
        _model_key = key
    return _model


def transcribe_audio(file_path: str, model_size: str = "base") -> dict[str, Any]:
    """
    Transcribe a local video/audio file.
    Returns full text plus timestamped segments, and writes JSON under transcripts/.
    """
    ensure_data_dirs()
    source = Path(file_path)
    if not source.is_file():
        raise FileNotFoundError(f"Audio/video file not found: {file_path}")

    allowed_sizes = {"tiny", "tiny.en", "base", "base.en", "small", "small.en", "medium", "large-v2", "large-v3"}
    if model_size not in allowed_sizes:
        raise ValueError(f"Unsupported Whisper model size: {model_size}")

    model = get_model(model_size=model_size)
    segments_iter, info = model.transcribe(str(source), beam_size=5)
    duration = float(info.duration) if getattr(info, "duration", None) is not None else None

    segments_data = []
    text_parts: list[str] = []
    for segment in segments_iter:
        piece = (segment.text or "").strip()
        start = max(0.0, float(segment.start))
        end = float(segment.end)
        if duration is not None:
            end = min(end, duration)
        if end < start:
            end = start
        segments_data.append({
            "start": start,
            "end": end,
            "text": piece,
        })
        if piece:
            text_parts.append(piece)

    result: dict[str, Any] = {
        "language": info.language,
        "language_probability": float(info.language_probability) if info.language_probability is not None else None,
        "duration": duration,
        "full_text": " ".join(text_parts).strip(),
        "segments": segments_data,
    }

    transcript_path = unique_path(TRANSCRIPTS_DIR, f"{source.stem}.json")
    transcript_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    result["transcript_path"] = str(transcript_path.resolve())
    return result


async def transcribe_audio_async(file_path: str, model_size: str = "base") -> dict[str, Any]:
    return await asyncio.to_thread(transcribe_audio, file_path, model_size)
