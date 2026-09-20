from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api import media
from backend.core.config import ensure_data_dirs


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_data_dirs()
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


@app.get("/")
def read_root():
    return {"message": "Sermon Assistant API is running locally!"}


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
