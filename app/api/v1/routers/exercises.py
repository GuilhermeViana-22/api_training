from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.core.pagination import PaginatedResponse
from app.database.session import get_db
from app.repositories.exercise_repository import ExerciseRepository
from app.schemas.exercise import ExerciseCreate, ExerciseDetailResponse, ExerciseImageResponse, ExerciseListItem, ExerciseUpdate
from app.services import exercise_service, upload_service

router = APIRouter()


@router.get("", response_model=PaginatedResponse[ExerciseListItem])
def list_exercises(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = None,
    muscle_group: str | None = None,
    user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    return exercise_service.list_exercises(db, user.id, page, limit, search, muscle_group)


@router.post("", response_model=ExerciseDetailResponse, status_code=201)
def create_exercise(data: ExerciseCreate, user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    return exercise_service.create_exercise(db, user.id, data)


@router.get("/{exercise_id}", response_model=ExerciseDetailResponse)
def get_exercise(exercise_id: str, user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    return exercise_service.get_exercise(db, user.id, exercise_id)


@router.put("/{exercise_id}", response_model=ExerciseDetailResponse)
def update_exercise(
    exercise_id: str, data: ExerciseUpdate, user=Depends(require_role("admin")), db: Session = Depends(get_db)
):
    return exercise_service.update_exercise(db, user.id, exercise_id, data)


@router.delete("/{exercise_id}", status_code=204)
def delete_exercise(exercise_id: str, user=Depends(require_role("admin")), db: Session = Depends(get_db)):
    exercise_service.delete_exercise(db, user.id, exercise_id)


@router.post("/{exercise_id}/images", response_model=ExerciseImageResponse, status_code=201)
async def upload_exercise_image(
    exercise_id: str,
    file: UploadFile = File(...),
    sort_order: int = Form(0),
    user=Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    exercise = ExerciseRepository().get_by_id(db, exercise_id, user.id)
    if exercise is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError()
    return await upload_service.save_exercise_media(db, exercise_id, file, sort_order)


@router.delete("/{exercise_id}/images/{image_id}", status_code=204)
def delete_exercise_image(
    exercise_id: str, image_id: str, user=Depends(require_role("admin")), db: Session = Depends(get_db)
):
    repo = ExerciseRepository()
    exercise = repo.get_by_id(db, exercise_id, user.id)
    if exercise is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError()
    image = repo.get_image(db, exercise_id, image_id)
    if image is None:
        from app.core.exceptions import NotFoundError

        raise NotFoundError()
    db.delete(image)
    db.commit()


@router.post("/{exercise_id}/images/{image_id}/feature", response_model=ExerciseDetailResponse)
def feature_exercise_image(
    exercise_id: str, image_id: str, user=Depends(require_role("admin")), db: Session = Depends(get_db)
):
    """Marca uma midia como destaque (capa) do exercicio, desmarcando as demais."""
    return exercise_service.set_featured_image(db, user.id, exercise_id, image_id)
