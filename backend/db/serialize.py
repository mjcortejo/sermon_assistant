import json
from datetime import datetime

from backend.db.models import Project


def touch(project: Project) -> None:
    project.updated_at = datetime.now()


def parse_transcript(project: Project) -> dict | None:
    if project.transcript_json:
        try:
            data = json.loads(project.transcript_json)
            if isinstance(data, dict) and (data.get("full_text") or data.get("segments")):
                return data
        except json.JSONDecodeError:
            pass
    if project.transcript:
        return {"full_text": project.transcript, "segments": []}
    return None


def notes_payload(project: Project) -> dict | None:
    notes = project.notes
    if notes is None:
        return None
    return {
        "main_theme": notes.main_theme,
        "scriptures": json.loads(notes.scriptures_json or "[]"),
        "takeaways": json.loads(notes.takeaways_json or "[]"),
        "summary": notes.summary,
        "user_notes": project.user_notes or "",
    }


def chat_payload(project: Project) -> list[dict]:
    return [
        {"id": message.id, "role": message.role, "content": message.content}
        for message in project.messages
    ]


def project_summary(project: Project) -> dict:
    return {
        "id": project.id,
        "title": project.title,
        "source_url": project.source_url,
        "source_path": project.source_path,
        "video_path": project.video_path,
        "duration": project.duration,
        "current_step": project.current_step,
        "has_transcript": bool(project.transcript),
        "has_notes": project.notes is not None,
        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
        "created_at": project.created_at.isoformat() if project.created_at else None,
    }


def project_detail(project: Project) -> dict:
    return {
        **project_summary(project),
        "trim_start": project.trim_start,
        "trim_end": project.trim_end,
        "transcript": parse_transcript(project),
        "transcript_path": project.transcript_path,
        "user_notes": project.user_notes or "",
        "notes": notes_payload(project),
        "chat": chat_payload(project),
    }
