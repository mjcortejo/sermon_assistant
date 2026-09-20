from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.models import ChatMessage, Project
from backend.db.serialize import touch
from backend.db.session import get_db
from backend.models.schemas import ChatMessageOut, ChatRequest, ChatResponse
from backend.services.chat_engine import answer_question
from backend.services.llm import LlmUnavailableError, ModelNotFoundError

router = APIRouter(prefix="/chat", tags=["Chat"])


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, (ModelNotFoundError, LlmUnavailableError)):
        return HTTPException(status_code=503, detail=str(exc))
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


def _history(project: Project) -> list[ChatMessageOut]:
    return [
        ChatMessageOut(id=message.id, role=message.role, content=message.content)
        for message in project.messages
    ]


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        project = db.get(Project, request.project_id)
        if project is None:
            raise FileNotFoundError(f"Project {request.project_id} was not found.")
        if not (project.transcript or "").strip():
            raise ValueError("Transcribe this project before chatting.")
        question = (request.message or "").strip()
        if not question:
            raise ValueError("message is required.")

        history = [{"role": m.role, "content": m.content} for m in project.messages]
        reply = answer_question(
            transcript=project.transcript,
            notes_json=(project.notes.raw_json if project.notes else "{}"),
            user_notes=project.user_notes or "",
            history=history,
            question=question,
        )

        db.add(ChatMessage(project_id=project.id, role="user", content=question))
        db.add(ChatMessage(project_id=project.id, role="assistant", content=reply))
        touch(project)
        db.commit()
        db.refresh(project)
        return ChatResponse(project_id=project.id, reply=reply, history=_history(project))
    except Exception as exc:
        db.rollback()
        raise _http_error(exc) from exc


@router.get("/{project_id}", response_model=ChatResponse)
def get_chat(project_id: int, db: Session = Depends(get_db)):
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} was not found.")
    last_assistant = next((m.content for m in reversed(project.messages) if m.role == "assistant"), "")
    return ChatResponse(project_id=project.id, reply=last_assistant, history=_history(project))
