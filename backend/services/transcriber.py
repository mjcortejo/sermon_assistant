import asyncio
import json
import threading
from pathlib import Path
from typing import Any, Iterator, Optional

from faster_whisper import WhisperModel

from backend.core.config import MODELS_DIR, TRANSCRIPTS_DIR, ensure_data_dirs
from backend.core.hardware import WhisperRuntime, detect_whisper_runtime
from backend.core.utils import unique_path

_model: Optional[WhisperModel] = None
_model_key: Optional[tuple[str, str, str]] = None
_runtime: Optional[WhisperRuntime] = None
_transcribe_lock = threading.Lock()
ALLOWED_MODEL_SIZES = {
    "tiny",
    "tiny.en",
    "base",
    "base.en",
    "small",
    "small.en",
    "medium",
    "large-v2",
    "large-v3",
}


def current_whisper_runtime() -> WhisperRuntime:
    return _runtime or detect_whisper_runtime()


def _load_model(model_size: str, runtime: WhisperRuntime) -> WhisperModel:
    return WhisperModel(
        model_size,
        device=runtime.device,
        compute_type=runtime.compute_type,
        download_root=str(MODELS_DIR),
    )


def get_model(model_size: str = "base") -> WhisperModel:
    """Lazy-load faster-whisper on CUDA when available, otherwise CPU int8."""
    global _model, _model_key, _runtime
    runtime = _runtime or detect_whisper_runtime()
    key = (model_size, runtime.device, runtime.compute_type)
    if _model is None or _model_key != key:
        try:
            _model = _load_model(model_size, runtime)
        except Exception:
            if runtime.device == "cpu":
                raise
            runtime = WhisperRuntime(device="cpu", compute_type="int8")
            _model = _load_model(model_size, runtime)
        _model_key = (model_size, runtime.device, runtime.compute_type)
        _runtime = runtime
    return _model


def _normalize_segment(segment: Any, duration: Optional[float]) -> dict[str, Any]:
    piece = (segment.text or "").strip()
    start = max(0.0, float(segment.start))
    end = float(segment.end)
    if duration is not None:
        end = min(end, duration)
    if end < start:
        end = start
    return {"start": start, "end": end, "text": piece}


def iter_transcript_events(file_path: str, model_size: str = "base") -> Iterator[dict[str, Any]]:
    """Yield info, then each cue, then a final done payload with the saved JSON path."""
    ensure_data_dirs()
    source = Path(file_path)
    if not source.is_file():
        raise FileNotFoundError(f"Audio/video file not found: {file_path}")

    if model_size not in ALLOWED_MODEL_SIZES:
        raise ValueError(f"Unsupported Whisper model size: {model_size}")

    with _transcribe_lock:
        model = get_model(model_size=model_size)
        segments_iter, info = model.transcribe(str(source), beam_size=5)
        duration = float(info.duration) if getattr(info, "duration", None) is not None else None
        language = getattr(info, "language", None)
        language_probability = (
            float(info.language_probability) if info.language_probability is not None else None
        )

        runtime = current_whisper_runtime()
        yield {
            "type": "info",
            "data": {
                "language": language,
                "language_probability": language_probability,
                "duration": duration,
                "full_text": "",
                "segments": [],
                "device": runtime.device,
                "compute_type": runtime.compute_type,
                "gpu_name": runtime.gpu_name,
            },
        }

        segments_data: list[dict[str, Any]] = []
        text_parts: list[str] = []
        for segment in segments_iter:
            item = _normalize_segment(segment, duration)
            segments_data.append(item)
            if item["text"]:
                text_parts.append(item["text"])
            payload = {
                "language": language,
                "language_probability": language_probability,
                "duration": duration,
                "full_text": " ".join(text_parts).strip(),
                "segments": list(segments_data),
                "segment": item,
            }
            yield {"type": "segment", "data": payload}

        result: dict[str, Any] = {
            "language": language,
            "language_probability": language_probability,
            "duration": duration,
            "full_text": " ".join(text_parts).strip(),
            "segments": segments_data,
        }
        transcript_path = unique_path(TRANSCRIPTS_DIR, f"{source.stem}.json")
        transcript_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        result["transcript_path"] = str(transcript_path.resolve())
        yield {"type": "done", "data": result}


def transcribe_audio(file_path: str, model_size: str = "base") -> dict[str, Any]:
    """
    Transcribe a local video/audio file.
    Returns full text plus timestamped segments, and writes JSON under transcripts/.
    """
    result: dict[str, Any] | None = None
    for event in iter_transcript_events(file_path, model_size):
        if event["type"] == "done":
            result = event["data"]
    if result is None:
        raise RuntimeError("Transcription produced no result.")
    return result


async def transcribe_audio_async(file_path: str, model_size: str = "base") -> dict[str, Any]:
    return await asyncio.to_thread(transcribe_audio, file_path, model_size)
