from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

MEDIA_DIR = DATA_DIR / "media"
DOWNLOADS_DIR = MEDIA_DIR / "downloads"
TRIMS_DIR = MEDIA_DIR / "trims"
TRANSCRIPTS_DIR = MEDIA_DIR / "transcripts"

MODELS_DIR = DATA_DIR / "models"
DB_DIR = DATA_DIR / "db"

MEDIA_SUBDIRS = (DOWNLOADS_DIR, TRIMS_DIR, TRANSCRIPTS_DIR)


def ensure_data_dirs() -> None:
    """Create local storage folders if they do not exist."""
    for directory in (*MEDIA_SUBDIRS, MODELS_DIR, DB_DIR):
        directory.mkdir(parents=True, exist_ok=True)


ensure_data_dirs()
