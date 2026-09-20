import re
from pathlib import Path
from typing import Union

TimeValue = Union[str, int, float]


def safe_filename(name: str, fallback: str = "video") -> str:
    """Keep a filename path-safe without directory components."""
    cleaned = Path(name).name.strip()
    cleaned = re.sub(r"[^\w.\-]+", "_", cleaned, flags=re.ASCII)
    cleaned = cleaned.strip("._")
    return cleaned or fallback


def unique_path(directory: Path, filename: str) -> Path:
    """Return directory/filename, adding _1, _2, ... if the file already exists."""
    directory.mkdir(parents=True, exist_ok=True)
    candidate = directory / filename
    if not candidate.exists():
        return candidate

    stem = candidate.stem
    suffix = candidate.suffix
    index = 1
    while True:
        candidate = directory / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def time_to_seconds(value: TimeValue) -> float:
    """Parse seconds or HH:MM:SS / MM:SS into a float second count."""
    if isinstance(value, (int, float)):
        seconds = float(value)
        if seconds < 0:
            raise ValueError("Time values cannot be negative.")
        return seconds

    text = str(value).strip()
    if not text:
        raise ValueError("Time value is empty.")

    parts = text.split(":")
    try:
        numbers = [float(part) for part in parts]
    except ValueError as exc:
        raise ValueError(f"Invalid timestamp: {value!r}") from exc

    if len(numbers) == 1:
        seconds = numbers[0]
    elif len(numbers) == 2:
        seconds = numbers[0] * 60 + numbers[1]
    elif len(numbers) == 3:
        seconds = numbers[0] * 3600 + numbers[1] * 60 + numbers[2]
    else:
        raise ValueError(f"Invalid timestamp: {value!r}")

    if seconds < 0:
        raise ValueError("Time values cannot be negative.")
    return seconds


def ffmpeg_time(value: TimeValue) -> str:
    """Format a timestamp the way FFmpeg accepts as -ss / -to."""
    if isinstance(value, str) and ":" in value.strip():
        time_to_seconds(value)
        return value.strip()
    return f"{time_to_seconds(value):.3f}"
