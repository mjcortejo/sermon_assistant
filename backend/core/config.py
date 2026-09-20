from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

MEDIA_DIR = DATA_DIR / "media"
DOWNLOADS_DIR = MEDIA_DIR / "downloads"
TRIMS_DIR = MEDIA_DIR / "trims"
TRANSCRIPTS_DIR = MEDIA_DIR / "transcripts"
FRAMES_DIR = MEDIA_DIR / "frames"

MODELS_DIR = DATA_DIR / "models"
DB_DIR = DATA_DIR / "db"
DATABASE_PATH = DB_DIR / "sermon_assistant.db"
DATABASE_URL = f"sqlite:///{DATABASE_PATH.as_posix()}"

LLM_MODEL_NAME = os.environ.get("SERMON_LLM_MODEL", "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf")
LLM_N_CTX = int(os.environ.get("SERMON_LLM_N_CTX", "8192"))
LLM_N_THREADS = os.environ.get("SERMON_LLM_N_THREADS")
OLLAMA_HOST = os.environ.get("SERMON_OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("SERMON_OLLAMA_MODEL", "llama3.2:latest").strip() or "llama3.2:latest"

MEDIA_SUBDIRS = (DOWNLOADS_DIR, TRIMS_DIR, TRANSCRIPTS_DIR, FRAMES_DIR)


def llm_model_path() -> Path:
    return MODELS_DIR / LLM_MODEL_NAME


def ensure_data_dirs() -> None:
    """Create local storage folders if they do not exist."""
    for directory in (*MEDIA_SUBDIRS, MODELS_DIR, DB_DIR):
        directory.mkdir(parents=True, exist_ok=True)


ensure_data_dirs()
