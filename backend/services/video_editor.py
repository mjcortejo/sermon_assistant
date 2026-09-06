import ffmpeg
import os
import asyncio
from pathlib import Path

def trim_video(input_path: str, output_path: str, start_time: str, end_time: str = None) -> str:
    """
    Trims a video losslessly using ffmpeg's copy codec.
    start_time and end_time should be in format 'HH:MM:SS' or seconds.
    """
    if not os.path.exists(input_path):
        raise FileNotFoundError(f"Input file not found: {input_path}")
        
    # Build ffmpeg input arguments
    # We apply -ss before -i for fast seeking
    input_kwargs = {"ss": start_time}
    
    if end_time:
        # Calculate duration or use -to (ffmpeg-python takes kwargs)
        input_kwargs["to"] = end_time

    stream = ffmpeg.input(input_path, **input_kwargs)
    
    # Lossless copy for both audio and video
    stream = ffmpeg.output(stream, output_path, c="copy")
    
    # Overwrite output if it exists and run quietly
    ffmpeg.run(stream, overwrite_output=True, quiet=True)
    
    return output_path

async def trim_video_async(input_path: str, output_path: str, start_time: str, end_time: str = None) -> str:
    """
    Async wrapper for trim_video.
    """
    return await asyncio.to_thread(trim_video, input_path, output_path, start_time, end_time)
