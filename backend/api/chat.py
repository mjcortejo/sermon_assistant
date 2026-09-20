from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.db.models import ChatMessage, Sermon
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


def _history(sermon: Sermon) -> list[ChatMessageOut]:
    return [
        ChatMessageOut(id=message.id, role=message.role, content=message.content)
        for message in sermon.messages
    ]


@router.post("", response_model=ChatResponse)
def chat(request: ChatRequest, db: Session = Depends(get_db)):
    try:
        sermon = db.get(Sermon, request.sermon_id)
        if sermon is None:
            raise FileNotFoundError(f"Sermon {request.sermon_id} was not found.")
        if sermon.notes is None:
            raise ValueError("Generate notes for this sermon before chatting.")
        question = (request.message or "").strip()
        if not question:
            raise ValueError("message is required.")

        history = [{"role": m.role, "content": m.content} for m in sermon.messages]
        reply = answer_question(
            transcript=sermon.transcript,
            notes_json=sermon.notes.raw_json or "{}",
            user_notes=sermon.notes.user_notes or "",
            history=history,
            question=question,
        )

        db.add(ChatMessage(sermon_id=sermon.id, role="user", content=question))
        db.add(ChatMessage(sermon_id=sermon.id, role="assistant", content=reply))
        db.commit()
        db.refresh(sermon)
        return ChatResponse(sermon_id=sermon.id, reply=reply, history=_history(sermon))
    except Exception as exc:
        db.rollback()
        raise _http_error(exc) from exc


@router.get("/{sermon_id}", response_model=ChatResponse)
def get_chat(sermon_id: int, db: Session = Depends(get_db)):
    sermon = db.get(Sermon, sermon_id)
    if sermon is None:
        raise HTTPException(status_code=404, detail=f"Sermon {sermon_id} was not found.")
    last_assistant = next((m.content for m in reversed(sermon.messages) if m.role == "assistant"), "")
    return ChatResponse(sermon_id=sermon.id, reply=last_assistant, history=_history(sermon))
