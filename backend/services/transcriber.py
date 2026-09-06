import os
import asyncio
from typing import List, Dict, Any
from faster_whisper import WhisperModel

# Global model instance so it isn't reloaded for every request
_model = None

def get_model(model_size: str = "base", device: str = "cpu", compute_type: str = "int8") -> WhisperModel:
    """
    Lazy loads the Whisper model.
    By default, uses CPU with int8 quantization.
    For GPU support, this could dynamically check if CUDA is available and use 'cuda' with 'float16'.
    """
    global _model
    if _model is None:
        print(f"Loading Whisper model '{model_size}' on {device}...")
        _model = WhisperModel(model_size, device=device, compute_type=compute_type)
    return _model

def transcribe_audio(file_path: str, model_size: str = "base") -> Dict[str, Any]:
    """
    Transcribes the audio file and returns text with timestamps.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    model = get_model(model_size=model_size)
    
    # Transcribe the audio
    segments, info = model.transcribe(file_path, beam_size=5)

    segments_data = []
    full_text = ""
    for segment in segments:
        segments_data.append({
            "start": segment.start,
            "end": segment.end,
            "text": segment.text
        })
        full_text += segment.text + " "

    return {
        "language": info.language,
        "language_probability": info.language_probability,
        "full_text": full_text.strip(),
        "segments": segments_data
    }

async def transcribe_audio_async(file_path: str, model_size: str = "base") -> Dict[str, Any]:
    """
    Async wrapper for transcribe_audio to avoid blocking the event loop.
    """
    return await asyncio.to_thread(transcribe_audio, file_path, model_size)
