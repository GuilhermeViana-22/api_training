from datetime import date

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile
from sqlalchemy.orm import Session

from app.auth.dependencies import require_role
from app.database.session import get_db
from app.schemas.attendance import (
    CheckInRequest,
    CheckInResponse,
    HistoryResponse,
    StudentDayTrainingResponse,
    StudentProgressSummary,
    StudentTrainingOverview,
)
from app.schemas.auth import MeResponse
from app.schemas.profile import EmailChangeRequest, PasswordChangeRequest, ProfileUpdateRequest
from app.services import me_service, profile_service, upload_service

router = APIRouter()


@router.put("/profile", response_model=MeResponse)
def update_my_profile(
    data: ProfileUpdateRequest, user=Depends(require_role("student")), db: Session = Depends(get_db)
):
    return profile_service.update_profile(db, user.id, data)


@router.put("/password")
def change_my_password(
    data: PasswordChangeRequest, user=Depends(require_role("student")), db: Session = Depends(get_db)
):
    return profile_service.change_password(db, user.id, data)


@router.put("/email", response_model=MeResponse)
def change_my_email(data: EmailChangeRequest, user=Depends(require_role("student")), db: Session = Depends(get_db)):
    return profile_service.change_email(db, user.id, data)


@router.get("/training", response_model=StudentTrainingOverview)
def my_training(user=Depends(require_role("student")), db: Session = Depends(get_db)):
    return me_service.get_my_training(db, user.id)


@router.get("/training/days/{day_of_week}", response_model=StudentDayTrainingResponse)
def my_training_day(day_of_week: int, user=Depends(require_role("student")), db: Session = Depends(get_db)):
    return me_service.get_my_training_day(db, user.id, day_of_week)


@router.post("/training/days/{day_of_week}/exercises/{entry_id}/complete")
def complete_exercise(
    day_of_week: int, entry_id: str, user=Depends(require_role("student")), db: Session = Depends(get_db)
):
    return me_service.complete_exercise(db, user.id, day_of_week, entry_id)


@router.post("/training/days/{day_of_week}/complete")
def complete_workout_day(day_of_week: int, user=Depends(require_role("student")), db: Session = Depends(get_db)):
    return me_service.complete_workout_day(db, user.id, day_of_week)


@router.post("/training/days/{day_of_week}/photos", status_code=201)
async def upload_day_photo(
    day_of_week: int,
    file: UploadFile = File(...),
    photo_type: str = Form("other"),
    weight_kg: float | None = Form(None),
    notes: str | None = Form(None),
    taken_at: str | None = Form(None),
    user=Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    parsed_date = date.fromisoformat(taken_at) if taken_at else None
    return await upload_service.save_day_photo(
        db, user.id, day_of_week, file, photo_type=photo_type, weight_kg=weight_kg, notes=notes, taken_at=parsed_date
    )


@router.get("/history", response_model=HistoryResponse)
def my_history(user=Depends(require_role("student")), db: Session = Depends(get_db)):
    return me_service.get_history(db, user.id)


@router.get("/progress", response_model=StudentProgressSummary)
def my_progress(user=Depends(require_role("student")), db: Session = Depends(get_db)):
    return me_service.get_progress_summary(db, user.id)


@router.get("/progress/photos")
def my_progress_photos(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user=Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    return me_service.list_my_photos(db, user.id, page, limit)


@router.post("/progress/photos", status_code=201)
async def upload_progress_photo(
    file: UploadFile = File(...),
    photo_type: str = Form("other"),
    weight_kg: float | None = Form(None),
    notes: str | None = Form(None),
    taken_at: str | None = Form(None),
    user=Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    parsed_date = date.fromisoformat(taken_at) if taken_at else None
    return await upload_service.save_student_photo(
        db, user.id, file, photo_type=photo_type, weight_kg=weight_kg, notes=notes, taken_at=parsed_date
    )


@router.post("/attendance/check-in", response_model=CheckInResponse, status_code=201)
def check_in(data: CheckInRequest | None = None, user=Depends(require_role("student")), db: Session = Depends(get_db)):
    notes = data.notes if data else None
    return me_service.check_in(db, user.id, notes)
