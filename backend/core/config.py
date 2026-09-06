import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

# Subdirectories for data
MEDIA_DIR = DATA_DIR / "media"
MODELS_DIR = DATA_DIR / "models"
DB_DIR = DATA_DIR / "db"

# Ensure directories exist
MEDIA_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR.mkdir(parents=True, exist_ok=True)
DB_DIR.mkdir(parents=True, exist_ok=True)
