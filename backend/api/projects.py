import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.db.models import Project
from backend.db.serialize import project_detail, project_summary, touch
from backend.db.session import get_db
from backend.models.schemas import (
    ProjectCreate,
    ProjectDetail,
    ProjectListResponse,
    ProjectResponse,
    ProjectSummary,
    ProjectUpdate,
)

router = APIRouter(prefix="/projects", tags=["Projects"])


def _http_error(exc: Exception) -> HTTPException:
    if isinstance(exc, FileNotFoundError):
        return HTTPException(status_code=404, detail=str(exc))
    if isinstance(exc, ValueError):
        return HTTPException(status_code=400, detail=str(exc))
    return HTTPException(status_code=500, detail=str(exc))


def _get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise FileNotFoundError(f"Project {project_id} was not found.")
    return project


def _response(project: Project) -> ProjectResponse:
    return ProjectResponse(project=ProjectDetail(**project_detail(project)))


@router.get("", response_model=ProjectListResponse)
def list_projects(db: Session = Depends(get_db)):
    rows = db.scalars(select(Project).order_by(Project.updated_at.desc())).all()
    return ProjectListResponse(projects=[ProjectSummary(**project_summary(row)) for row in rows])


@router.post("", response_model=ProjectResponse)
def create_project(request: ProjectCreate, db: Session = Depends(get_db)):
    try:
        project = Project(
            title=(request.title or "Untitled sermon").strip() or "Untitled sermon",
            source_url=request.source_url,
            source_path=request.source_path,
            video_path=request.video_path or request.source_path,
            duration=request.duration or 0,
            trim_start=request.trim_start or 0,
            trim_end=request.trim_end or request.duration or 0,
            current_step=request.current_step or "import",
        )
        db.add(project)
        db.commit()
        db.refresh(project)
        return _response(project)
    except Exception as exc:
        db.rollback()
        raise _http_error(exc) from exc


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(project_id: int, db: Session = Depends(get_db)):
    try:
        return _response(_get_project(db, project_id))
    except Exception as exc:
        raise _http_error(exc) from exc


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(project_id: int, request: ProjectUpdate, db: Session = Depends(get_db)):
    try:
        project = _get_project(db, project_id)
        data = request.model_dump(exclude_unset=True)
        transcript = data.pop("transcript", None)
        for key, value in data.items():
            setattr(project, key, value)
        if transcript is not None:
            project.transcript_json = json.dumps(transcript, ensure_ascii=False)
            project.transcript = str(transcript.get("full_text") or "")
        touch(project)
        db.commit()
        db.refresh(project)
        return _response(project)
    except Exception as exc:
        db.rollback()
        raise _http_error(exc) from exc


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db)):
    try:
        project = _get_project(db, project_id)
        db.delete(project)
        db.commit()
        return {"status": "success", "id": project_id}
    except Exception as exc:
        db.rollback()
        raise _http_error(exc) from exc
