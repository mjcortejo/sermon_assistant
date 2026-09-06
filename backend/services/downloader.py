import yt_dlp
import os
import asyncio
from backend.core.config import MEDIA_DIR

def download_video(url: str, output_name: str = None) -> str:
    """
    Downloads a video from a given URL using yt-dlp.
    Returns the absolute path to the downloaded file.
    """
    if not output_name:
        output_template = os.path.join(MEDIA_DIR, '%(id)s.%(ext)s')
    else:
        output_template = os.path.join(MEDIA_DIR, f"{output_name}.%(ext)s")

    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'merge_output_format': 'mp4',
        'outtmpl': output_template,
        'quiet': False,
        'no_warnings': True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=True)
        # yt-dlp might change the extension depending on the format downloaded,
        # so we get the actual filename from the info_dict
        downloaded_file = ydl.prepare_filename(info_dict)
        return downloaded_file

async def download_video_async(url: str, output_name: str = None) -> str:
    """
    Async wrapper for download_video to avoid blocking the FastAPI event loop.
    """
    return await asyncio.to_thread(download_video, url, output_name)

def get_video_info(url: str) -> dict:
    """
    Extracts metadata for a video without downloading it.
    """
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return {
            "id": info.get("id"),
            "title": info.get("title"),
            "description": info.get("description"),
            "duration": info.get("duration"),
            "thumbnail": info.get("thumbnail"),
        }
