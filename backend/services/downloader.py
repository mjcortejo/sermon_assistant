import asyncio
import shutil
from pathlib import Path
from typing import Any, Optional

import yt_dlp
from yt_dlp.utils import DownloadError

from backend.core.config import DOWNLOADS_DIR, ensure_data_dirs
from backend.core.utils import safe_filename, unique_path

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

# Prefer an MP4 merge so the HTML5 player and FFmpeg copy-trim behave consistently.
YDL_FORMAT = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"


def _base_opts() -> dict[str, Any]:
    return {
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
        "retries": 3,
        "socket_timeout": 30,
        "http_headers": {"User-Agent": BROWSER_UA},
    }


def _resolve_downloaded_path(ydl: yt_dlp.YoutubeDL, info: dict[str, Any]) -> str:
    """Return the file yt-dlp actually wrote after merge/post-process."""
    requested = info.get("requested_downloads") or []
    if requested:
        for key in ("filepath", "filename"):
            candidate = requested[0].get(key)
            if candidate and Path(candidate).exists():
                return str(Path(candidate).resolve())

    prepared = Path(ydl.prepare_filename(info))
    stem = prepared.with_suffix("")
    for ext in (".mp4", ".mkv", ".webm", ".m4a", prepared.suffix):
        if not ext:
            continue
        candidate = Path(str(stem) + ext)
        if candidate.exists():
            return str(candidate.resolve())

    if prepared.exists():
        return str(prepared.resolve())

    matches = sorted(DOWNLOADS_DIR.glob(f"{prepared.stem}.*"))
    if matches:
        return str(matches[-1].resolve())

    raise FileNotFoundError(
        "yt-dlp finished but the output file could not be located. "
        f"Expected something like {prepared}"
    )


def _video_info_from_dict(info: dict[str, Any]) -> dict[str, Any]:
    duration = info.get("duration")
    return {
        "id": info.get("id"),
        "title": info.get("title"),
        "description": info.get("description"),
        "duration": float(duration) if duration is not None else None,
        "thumbnail": info.get("thumbnail"),
        "extractor": info.get("extractor") or info.get("ie_key"),
    }


def get_video_info(url: str) -> dict[str, Any]:
    """Extract metadata without downloading the media file."""
    ydl_opts = _base_opts()
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except DownloadError as exc:
        raise ValueError(f"Could not read video info: {exc}") from exc

    if not info:
        raise ValueError("No metadata returned for that URL.")
    return _video_info_from_dict(info)


def download_video(url: str, output_name: Optional[str] = None) -> dict[str, Any]:
    """
    Download a YouTube or public Facebook (Live) URL with yt-dlp.
    Files land in data/media/downloads/ as a merged MP4 when possible.
    """
    ensure_data_dirs()
    url = (url or "").strip()
    if not url:
        raise ValueError("A video URL is required.")

    if output_name:
        dest = unique_path(DOWNLOADS_DIR, f"{safe_filename(output_name)}.mp4")
        template = str(dest.with_suffix("")) + ".%(ext)s"
    else:
        template = str(DOWNLOADS_DIR / "%(id)s.%(ext)s")

    ydl_opts = {
        **_base_opts(),
        "format": YDL_FORMAT,
        "merge_output_format": "mp4",
        "outtmpl": template,
        "restrictfilenames": True,
        "quiet": False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            file_path = _resolve_downloaded_path(ydl, info)
    except DownloadError as exc:
        raise ValueError(f"Download failed: {exc}") from exc

    return {"file_path": file_path, "info": _video_info_from_dict(info)}


def ingest_local_file(source_path: str, output_name: Optional[str] = None) -> str:
    """Copy an existing local video into the downloads directory."""
    ensure_data_dirs()
    source = Path(source_path).expanduser()
    if not source.is_file():
        raise FileNotFoundError(f"Input file not found: {source_path}")

    filename = safe_filename(output_name or source.name, fallback=source.stem)
    if not Path(filename).suffix:
        filename = filename + (source.suffix or ".mp4")

    dest = unique_path(DOWNLOADS_DIR, filename)
    shutil.copy2(source, dest)
    return str(dest.resolve())


async def download_video_async(url: str, output_name: Optional[str] = None) -> dict[str, Any]:
    return await asyncio.to_thread(download_video, url, output_name)


async def get_video_info_async(url: str) -> dict[str, Any]:
    return await asyncio.to_thread(get_video_info, url)


async def ingest_local_file_async(source_path: str, output_name: Optional[str] = None) -> str:
    return await asyncio.to_thread(ingest_local_file, source_path, output_name)
