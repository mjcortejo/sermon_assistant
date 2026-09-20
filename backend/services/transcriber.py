import asyncio
import json
import threading
from pathlib import Path
from typing import Any, Iterator, Optional

from faster_whisper import WhisperModel

from backend.core.config import MODELS_DIR, TRANSCRIPTS_DIR, ensure_data_dirs
from backend.core.hardware import (
    WhisperRuntime,
    detect_whisper_runtime,
    ensure_cuda_dll_dirs,
    is_cuda_library_error,
)
from backend.core.utils import unique_path

_model: Optional[WhisperModel] = None
_model_key: Optional[tuple[str, str, str]] = None
_runtime: Optional[WhisperRuntime] = None
_transcribe_lock = threading.Lock()
_cancel_event = threading.Event()
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


def request_transcribe_stop() -> None:
    """Ask the in-flight transcription to stop after the current cue."""
    _cancel_event.set()


def transcribe_was_stopped() -> bool:
    return _cancel_event.is_set()


def current_whisper_runtime() -> WhisperRuntime:
    return _runtime or detect_whisper_runtime()


def _load_model(model_size: str, runtime: WhisperRuntime) -> WhisperModel:
    return WhisperModel(
        model_size,
        device=runtime.device,
        compute_type=runtime.compute_type,
        download_root=str(MODELS_DIR),
    )


def _reload_on_cpu(model_size: str) -> WhisperModel:
    global _model, _model_key, _runtime
    runtime = WhisperRuntime(device="cpu", compute_type="int8")
    _model = _load_model(model_size, runtime)
    _model_key = (model_size, "cpu", "int8")
    _runtime = runtime
    return _model


def get_model(model_size: str = "base") -> WhisperModel:
    """Lazy-load faster-whisper on CUDA when available, otherwise CPU int8."""
    global _model, _model_key, _runtime
    ensure_cuda_dll_dirs()
    runtime = _runtime or detect_whisper_runtime()
    key = (model_size, runtime.device, runtime.compute_type)
    if _model is None or _model_key != key:
        try:
            _model = _load_model(model_size, runtime)
            _model_key = key
            _runtime = runtime
        except Exception:
            if runtime.device == "cpu":
                raise
            return _reload_on_cpu(model_size)
    return _model


def _transcribe_file(file_path: str, model_size: str, start_time: float = 0.0):
    model = get_model(model_size=model_size)
    kwargs: dict[str, Any] = {"beam_size": 5}
    if start_time and start_time > 0:
        kwargs["clip_timestamps"] = [float(start_time), 10_000_000.0]
    try:
        return model.transcribe(str(file_path), **kwargs)
    except Exception as exc:
        if current_whisper_runtime().device == "cpu" or not is_cuda_library_error(exc):
            raise
        model = _reload_on_cpu(model_size)
        return model.transcribe(str(file_path), **kwargs)


def _normalize_segment(segment: Any, duration: Optional[float]) -> dict[str, Any]:
    piece = (segment.text or "").strip()
    start = max(0.0, float(segment.start))
    end = float(segment.end)
    if duration is not None:
        end = min(end, duration)
    if end < start:
        end = start
    return {"start": start, "end": end, "text": piece}


def iter_transcript_events(
    file_path: str,
    model_size: str = "base",
    start_time: float = 0.0,
) -> Iterator[dict[str, Any]]:
    """Yield info, then each cue, then a final done payload with the saved JSON path."""
    ensure_data_dirs()
    source = Path(file_path)
    if not source.is_file():
        raise FileNotFoundError(f"Audio/video file not found: {file_path}")

    if model_size not in ALLOWED_MODEL_SIZES:
        raise ValueError(f"Unsupported Whisper model size: {model_size}")

    resume_at = max(0.0, float(start_time or 0.0))
    _cancel_event.clear()

    with _transcribe_lock:
        segments_iter, info = _transcribe_file(str(source), model_size, resume_at)
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
                "start_time": resume_at,
            },
        }

        def consume_segments() -> Iterator[Any]:
            try:
                yield from segments_iter
            except Exception as exc:
                if current_whisper_runtime().device == "cpu" or not is_cuda_library_error(exc):
                    raise
                retry_iter, _ = _transcribe_file(str(source), model_size, resume_at)
                yield from retry_iter

        segments_data: list[dict[str, Any]] = []
        text_parts: list[str] = []
        stopped = False
        for segment in consume_segments():
            item = _normalize_segment(segment, duration)
            if item["end"] <= resume_at and resume_at > 0:
                continue
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
                "stopped": False,
            }
            yield {"type": "segment", "data": payload}
            if _cancel_event.is_set():
                stopped = True
                break

        stopped = stopped or _cancel_event.is_set()
        result: dict[str, Any] = {
            "language": language,
            "language_probability": language_probability,
            "duration": duration,
            "full_text": " ".join(text_parts).strip(),
            "segments": segments_data,
            "stopped": stopped,
        }
        transcript_path = unique_path(TRANSCRIPTS_DIR, f"{source.stem}.json")
        transcript_path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        result["transcript_path"] = str(transcript_path.resolve())
        yield {"type": "done", "data": result}


def transcribe_audio(file_path: str, model_size: str = "base", start_time: float = 0.0) -> dict[str, Any]:
    """
    Transcribe a local video/audio file.
    Returns full text plus timestamped segments, and writes JSON under transcripts/.
    """
    result: dict[str, Any] | None = None
    for event in iter_transcript_events(file_path, model_size, start_time):
        if event["type"] == "done":
            result = event["data"]
    if result is None:
        raise RuntimeError("Transcription produced no result.")
    return result


async def transcribe_audio_async(
    file_path: str, model_size: str = "base", start_time: float = 0.0
) -> dict[str, Any]:
    return await asyncio.to_thread(transcribe_audio, file_path, model_size, start_time)
