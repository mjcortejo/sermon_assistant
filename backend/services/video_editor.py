import asyncio
import shutil
from pathlib import Path
from typing import Optional

import ffmpeg

from backend.core.config import TRIMS_DIR, ensure_data_dirs
from backend.core.utils import TimeValue, ffmpeg_time, safe_filename, time_to_seconds, unique_path


def _assert_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError(
            "FFmpeg is not installed or not on PATH. "
            "Install FFmpeg and restart the app before trimming video."
        )


def probe_video(input_path: str) -> dict:
    """Return duration and stream metadata for a local media file."""
    _assert_ffmpeg()
    path = Path(input_path)
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    try:
        info = ffmpeg.probe(str(path))
    except ffmpeg.Error as exc:
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace")
        raise RuntimeError(f"Could not probe video: {stderr[-2000:]}") from exc

    fmt = info.get("format") or {}
    streams = info.get("streams") or []
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})

    duration_raw = fmt.get("duration") or video.get("duration") or 0
    return {
        "duration": float(duration_raw or 0),
        "format": fmt.get("format_name"),
        "width": video.get("width"),
        "height": video.get("height"),
        "video_codec": video.get("codec_name"),
        "audio_codec": audio.get("codec_name"),
    }


def trim_video(
    input_path: str,
    start_time: TimeValue,
    end_time: Optional[TimeValue] = None,
    output_name: Optional[str] = None,
) -> dict:
    """
    Cut a clip losslessly with FFmpeg stream copy (`-c copy`).
    Output is always written under data/media/trims/.
    """
    _assert_ffmpeg()
    ensure_data_dirs()

    source = Path(input_path)
    if not source.is_file():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    start_seconds = time_to_seconds(start_time)
    end_seconds = time_to_seconds(end_time) if end_time is not None else None
    if end_seconds is not None and end_seconds <= start_seconds:
        raise ValueError("end_time must be greater than start_time.")

    stem = safe_filename(output_name or f"{source.stem}_trim", fallback="trim")
    output_path = unique_path(TRIMS_DIR, f"{stem}.mp4")

    input_kwargs = {"ss": ffmpeg_time(start_time)}
    if end_time is not None:
        # With -ss before -i, -to is an absolute timestamp on the source timeline.
        input_kwargs["to"] = ffmpeg_time(end_time)

    stream = ffmpeg.input(str(source), **input_kwargs)
    stream = ffmpeg.output(
        stream,
        str(output_path),
        c="copy",
        avoid_negative_ts="make_zero",
        movflags="+faststart",
    )

    try:
        ffmpeg.run(stream, overwrite_output=True, capture_stdout=True, capture_stderr=True)
    except ffmpeg.Error as exc:
        stderr = (exc.stderr or b"").decode("utf-8", errors="replace")
        raise RuntimeError(f"FFmpeg trim failed: {stderr[-2000:]}") from exc

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise RuntimeError("FFmpeg reported success but the trimmed file is missing or empty.")

    return {
        "output_path": str(output_path.resolve()),
        "start_time": start_seconds,
        "end_time": end_seconds,
    }


async def trim_video_async(
    input_path: str,
    start_time: TimeValue,
    end_time: Optional[TimeValue] = None,
    output_name: Optional[str] = None,
) -> dict:
    return await asyncio.to_thread(trim_video, input_path, start_time, end_time, output_name)


async def probe_video_async(input_path: str) -> dict:
    return await asyncio.to_thread(probe_video, input_path)
