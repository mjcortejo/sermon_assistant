"""Read on-screen sermon text from a video frame with RapidOCR (PP-OCRv6 small)."""

from __future__ import annotations

import threading
from typing import Any

from backend.core.utils import TimeValue, time_to_seconds
from backend.services.video_editor import extract_frame

_engine = None
_engine_lock = threading.Lock()


def get_engine():
    """Lazy-load RapidOCR so import stays cheap until the first capture."""
    global _engine
    with _engine_lock:
        if _engine is None:
            from rapidocr import RapidOCR

            _engine = RapidOCR()
        return _engine


def ocr_image(image_path: str) -> dict[str, Any]:
    result = get_engine()(str(image_path))
    lines = [str(item).strip() for item in (getattr(result, "txts", None) or ()) if str(item).strip()]
    scores = [float(score) for score in (getattr(result, "scores", None) or ()) if score is not None]
    confidence = sum(scores) / len(scores) if scores else None
    return {
        "text": "\n".join(lines).strip(),
        "lines": lines,
        "confidence": confidence,
    }


def capture_on_screen_text(file_path: str, timestamp: TimeValue) -> dict[str, Any]:
    seconds = time_to_seconds(timestamp)
    frame_path = extract_frame(file_path, seconds)
    read = ocr_image(frame_path)
    if not read["text"]:
        raise ValueError("No readable text was found on this frame.")
    return {
        "timestamp": seconds,
        "frame_path": frame_path,
        **read,
    }


async def capture_on_screen_text_async(file_path: str, timestamp: TimeValue) -> dict[str, Any]:
    import asyncio

    return await asyncio.to_thread(capture_on_screen_text, file_path, timestamp)


def format_screen_texts(captures: list[Any]) -> str:
    blocks: list[str] = []
    for item in captures:
        text = (getattr(item, "text", None) or (item.get("text") if isinstance(item, dict) else "") or "").strip()
        if not text:
            continue
        timestamp = getattr(item, "timestamp", None)
        if timestamp is None and isinstance(item, dict):
            timestamp = item.get("timestamp") or 0
        total = max(0, int(float(timestamp or 0)))
        stamp = f"{total // 60}:{total % 60:02d}"
        blocks.append(f"[{stamp}] {text}")
    return "\n".join(blocks)
