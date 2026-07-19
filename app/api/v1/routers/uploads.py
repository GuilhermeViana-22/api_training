from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.core.config import settings
from app.core.exceptions import ForbiddenError, NotFoundError
from app.database.session import get_db
from app.repositories.exercise_repository import ExerciseRepository
from app.repositories.student_repository import StudentRepository

router = APIRouter()


@router.get("/{category}/{resource_id}/{filename}")
def get_upload(
    category: str,
    resource_id: str,
    filename: str,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if category not in {"students", "exercises", "avatars"}:
        raise NotFoundError()

    relative_path = f"{category}/{resource_id}/{filename}"
    absolute_path = Path(settings.upload_dir) / relative_path
    if not absolute_path.exists():
        raise NotFoundError()

    if category == "students":
        if user.role == "student" and user.id != resource_id:
            raise ForbiddenError()
        if user.role == "admin":
            profile = StudentRepository().get_by_id(db, resource_id, user.id)
            if profile is None:
                raise ForbiddenError()
    elif category == "exercises":
        if user.role == "admin":
            exercise = ExerciseRepository().get_by_id(db, resource_id, user.id)
            if exercise is None:
                raise ForbiddenError()
    elif category == "avatars":
        if user.id != resource_id:
            if user.role == "admin":
                student = StudentRepository().get_by_id(db, resource_id, user.id)
                if student is None:
                    raise ForbiddenError()
            elif user.role == "student":
                own_profile = StudentRepository().get_by_id(db, user.id)
                if own_profile is None or own_profile.admin_id != resource_id:
                    raise ForbiddenError()
            else:
                raise ForbiddenError()

    return FileResponse(absolute_path)
