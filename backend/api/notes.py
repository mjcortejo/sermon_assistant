import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.models import GeneratedNotes, Sermon
from backend.db.session import get_db
from backend.models.schemas import (
    GenerateNotesRequest,
    NotesResponse,
    SermonNotes,
    UserNotesRequest,
)
from backend.services.llm import LlmUnavailableError, ModelNotFoundError, get_llama, model_status
from backend.services.notes_engine import generate_structured_notes

router = APIRouter(prefix="/notes", tags=["Notes"])


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (ModelNotFoundError, LlmUnavailableError)):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


def _to_response(sermon: Sermon, notes: GeneratedNotes) -> NotesResponse:
    return NotesResponse(
        sermon_id=sermon.id,
        title=sermon.title,
        notes=SermonNotes(
            main_theme=notes.main_theme,
            scriptures=json.loads(notes.scriptures_json or "[]"),
            takeaways=json.loads(notes.takeaways_json or "[]"),
            summary=notes.summary,
            user_notes=notes.user_notes or "",
        ),
    )


@router.get("/model", response_model=dict)
def get_model_status():
    return {"status": "success", **model_status()}


@router.post("/generate", response_model=NotesResponse)
def generate_notes(request: GenerateNotesRequest, db: Session = Depends(get_db)):
    try:
        get_llama()
        sermon = None
        if request.sermon_id is not None:
            sermon = db.get(Sermon, request.sermon_id)
            if sermon is None:
                raise FileNotFoundError(f"Sermon {request.sermon_id} was not found.")
            transcript = request.transcript or sermon.transcript
        else:
            transcript = request.transcript
            sermon = Sermon(
                title=request.title,
                transcript=transcript,
                transcript_path=request.transcript_path,
            )
            db.add(sermon)
            db.flush()

        structured = generate_structured_notes(transcript)
        notes = sermon.notes
        if notes is None:
            notes = GeneratedNotes(sermon_id=sermon.id)
            db.add(notes)

        notes.main_theme = structured["main_theme"]
        notes.scriptures_json = json.dumps(structured["scriptures"], ensure_ascii=False)
        notes.takeaways_json = json.dumps(structured["takeaways"], ensure_ascii=False)
        notes.summary = structured["summary"]
        notes.raw_json = structured["raw_json"]
        db.commit()
        db.refresh(sermon)
        db.refresh(notes)
        return _to_response(sermon, notes)
    except Exception as exc:
        db.rollback()
        raise _http_error(exc) from exc


@router.get("/{sermon_id}", response_model=NotesResponse)
def get_notes(sermon_id: int, db: Session = Depends(get_db)):
    sermon = db.get(Sermon, sermon_id)
    if sermon is None or sermon.notes is None:
        raise HTTPException(status_code=404, detail=f"Notes for sermon {sermon_id} were not found.")
    return _to_response(sermon, sermon.notes)


@router.put("/{sermon_id}/user", response_model=NotesResponse)
def update_user_notes(sermon_id: int, request: UserNotesRequest, db: Session = Depends(get_db)):
    sermon = db.get(Sermon, sermon_id)
    if sermon is None or sermon.notes is None:
        raise HTTPException(status_code=404, detail=f"Notes for sermon {sermon_id} were not found.")
    sermon.notes.user_notes = request.user_notes
    db.commit()
    db.refresh(sermon.notes)
    return _to_response(sermon, sermon.notes)
