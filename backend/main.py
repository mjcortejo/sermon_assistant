from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import chat, media, notes, projects
from backend.core.config import ensure_data_dirs
from backend.core.hardware import detect_whisper_runtime, ensure_cuda_dll_dirs
from backend.db.session import init_db
from backend.services.llm import model_status as llm_status


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_data_dirs()
    init_db()
    ensure_cuda_dll_dirs()
    yield


app = FastAPI(
    title="Sermon Assistant API",
    description="Local-first video sermon auto note-taking and study assistant platform.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(media.router)
app.include_router(projects.router)
app.include_router(notes.router)
app.include_router(chat.router)


@app.get("/")
def read_root():
    return {"message": "Sermon Assistant API is running locally!"}


@app.get("/health")
def health():
    runtime = detect_whisper_runtime()
    llm = llm_status()
    return {
        "status": "ok",
        "whisper": {
            "device": runtime.device,
            "compute_type": runtime.compute_type,
            "gpu": runtime.gpu_name,
        },
        "llm": {
            "backend": llm.get("backend"),
            "model": llm.get("model"),
            "available": bool(llm.get("exists")),
        },
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
