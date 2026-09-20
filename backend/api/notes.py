import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.models import GeneratedNotes, Project
from backend.db.serialize import notes_payload, touch
from backend.db.session import get_db
from backend.models.schemas import GenerateNotesRequest, NotesResponse, SermonNotes, UserNotesRequest
from backend.services.llm import LlmUnavailableError, ModelNotFoundError, ensure_llm, model_status
from backend.services.notes_engine import generate_structured_notes
from backend.services.ocr import format_screen_texts

router = APIRouter(prefix="/notes", tags=["Notes"])


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (ModelNotFoundError, LlmUnavailableError)):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


def _to_response(project: Project, notes: GeneratedNotes) -> NotesResponse:
    payload = notes_payload(project) or {}
    return NotesResponse(
        project_id=project.id,
        title=project.title,
        notes=SermonNotes(**payload),
    )


@router.get("/model", response_model=dict)
def get_model_status():
    return {"status": "success", **model_status()}


@router.post("/generate", response_model=NotesResponse)
def generate_notes(request: GenerateNotesRequest, db: Session = Depends(get_db)):
    try:
        ensure_llm()
        if request.project_id is not None:
            project = db.get(Project, request.project_id)
            if project is None:
                raise FileNotFoundError(f"Project {request.project_id} was not found.")
            transcript = request.transcript or project.transcript
        else:
            transcript = request.transcript or ""
            project = Project(
                title=request.title or "Untitled sermon",
                transcript=transcript,
                transcript_path=request.transcript_path,
                current_step="study",
            )
            db.add(project)
            db.flush()

        if not (transcript or "").strip():
            raise ValueError("Transcript is empty.")

        structured = generate_structured_notes(
            transcript,
            screen_text=format_screen_texts(project.captures),
        )
        notes = project.notes
        if notes is None:
            notes = GeneratedNotes(project_id=project.id)
            db.add(notes)

        notes.main_theme = structured["main_theme"]
        notes.scriptures_json = json.dumps(structured["scriptures"], ensure_ascii=False)
        notes.takeaways_json = json.dumps(structured["takeaways"], ensure_ascii=False)
        notes.summary = structured["summary"]
        notes.raw_json = structured["raw_json"]
        if not project.transcript:
            project.transcript = transcript
        touch(project)
        db.commit()
        db.refresh(project)
        db.refresh(notes)
        return _to_response(project, notes)
    except Exception as exc:
        db.rollback()
        raise _http_error(exc) from exc


@router.get("/{project_id}", response_model=NotesResponse)
def get_notes(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None or project.notes is None:
        raise HTTPException(status_code=404, detail=f"Notes for project {project_id} were not found.")
    return _to_response(project, project.notes)


@router.put("/{project_id}/user", response_model=NotesResponse)
def update_user_notes(project_id: int, request: UserNotesRequest, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} was not found.")
    project.user_notes = request.user_notes
    touch(project)
    db.commit()
    if project.notes is None:
        return NotesResponse(
            project_id=project.id,
            title=project.title,
            notes=SermonNotes(
                main_theme="",
                scriptures=[],
                takeaways=[],
                summary="",
                user_notes=project.user_notes,
            ),
        )
    db.refresh(project)
    return _to_response(project, project.notes)
