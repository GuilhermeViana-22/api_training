from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.core.pagination import PaginatedResponse
from app.database.session import get_db
from app.schemas.report import StudentOption
from app.schemas.student import StudentCreate, StudentDetailResponse, StudentListItem, StudentStatusUpdate, StudentUpdate
from app.schemas.training import StudentTrainingSummary
from app.services import me_service, student_service, training_service

router = APIRouter()


@router.get("/options", response_model=list[StudentOption])
def list_student_options(user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    """Lista alunos (id + nome) para vincular treino — cada aluno tem treino independente."""
    return student_service.list_student_options(db, user.id)


@router.get("", response_model=PaginatedResponse[StudentListItem])
def list_students(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    is_active: bool | None = None,
    user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return student_service.list_students(db, user.id, page, limit, search, is_active)


@router.post("", response_model=StudentDetailResponse, status_code=201)
def create_student(data: StudentCreate, user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    return student_service.create_student(db, user.id, data)


@router.get("/{student_id}/trainings", response_model=StudentTrainingSummary)
def list_student_trainings(student_id: str, user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    """Treinos de um aluno específico (ativo + histórico) com dias e exercícios."""
    return training_service.list_student_trainings(db, user.id, student_id)


@router.get("/{student_id}", response_model=StudentDetailResponse)
def get_student(student_id: str, user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    return student_service.get_student(db, user.id, student_id)


@router.put("/{student_id}", response_model=StudentDetailResponse)
def update_student(
    student_id: str, data: StudentUpdate, user=Depends(require_role("admin")), db: Session = Depends(get_db)
):
    return student_service.update_student(db, user.id, student_id, data)


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: str, user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    student_service.delete_student(db, user.id, student_id)


@router.patch("/{student_id}/status", response_model=StudentDetailResponse)
def update_student_status(
    student_id: str, data: StudentStatusUpdate, user=Depends(require_role("admin")), db: Session = Depends(get_db)
):
    return student_service.update_status(db, user.id, student_id, data)


@router.get("/{student_id}/attendance")
def student_attendance(
    student_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    start_date: str | None = None,
    end_date: str | None = None,
    user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    from datetime import date

    start = date.fromisoformat(start_date) if start_date else None
    end = date.fromisoformat(end_date) if end_date else None
    return me_service.list_student_attendance(db, user.id, student_id, page, limit, start, end)


@router.get("/{student_id}/progress/photos")
def student_progress_photos(
    student_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return me_service.list_student_photos(db, user.id, student_id, page, limit)


@router.get("/{student_id}/progress/metrics")
def student_progress_metrics(student_id: str, user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    from app.repositories.attendance_repository import ProgressRepository
    from app.repositories.student_repository import StudentRepository
    from app.core.exceptions import NotFoundError

    profile = StudentRepository().get_by_id(db, student_id, user.id)
    if profile is None:
        raise NotFoundError()
    metrics = ProgressRepository().list_metrics(db, student_id)
    return {
        "items": [
            {
                "id": m.id,
                "metric_date": m.metric_date.isoformat(),
                "weight_kg": float(m.weight_kg) if m.weight_kg is not None else None,
                "body_fat_pct": float(m.body_fat_pct) if m.body_fat_pct is not None else None,
                "measurements": m.measurements,
            }
            for m in metrics
        ]
    }
