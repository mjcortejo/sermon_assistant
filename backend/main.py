from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api import media

app = FastAPI(
    title="Sermon Assistant API",
    description="Local-first video sermon auto note-taking and study assistant platform.",
    version="1.0.0",
)

# Configure CORS for local development (Tauri will hit this from localhost)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict this to Tauri's local origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(media.router)

@app.get("/")
def read_root():
    return {"message": "Sermon Assistant API is running locally!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
