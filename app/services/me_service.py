from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.pagination import build_pagination
from app.repositories.attendance_repository import AttendanceRepository, ProgressRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.training_repository import TrainingRepository
from app.repositories.workout_repository import WorkoutRepository
from app.schemas.attendance import (
    AttendanceItem,
    AttendanceListResponse,
    AttendanceSummary,
    CheckInResponse,
    HistoryCheckInItem,
    HistoryResponse,
    HistoryTrainingItem,
    ProgressPhotoResponse,
    StudentDayTrainingResponse,
    StudentProgressSummary,
    StudentTrainingOverview,
)
from app.services import training_service
from app.utils.dates import day_name

attendance_repo = AttendanceRepository()
progress_repo = ProgressRepository()
training_repo = TrainingRepository()
student_repo = StudentRepository()
workout_repo = WorkoutRepository()


def _photo_url(file_path: str) -> str:
    return f"/api/v1/uploads/{file_path}"


def _serialize_session(session, exercises_total: int, exercises: list[dict]) -> dict:
    completed_ids = {c.training_exercise_id for c in session.exercise_completions}
    exercises_completed = len(completed_ids)
    return {
        "id": session.id,
        "training_id": session.training_id,
        "training_day_id": session.training_day_id,
        "day_of_week": None,
        "session_date": session.session_date.isoformat(),
        "status": session.status,
        "exercises_total": exercises_total,
        "exercises_completed": exercises_completed,
        "started_at": session.started_at.isoformat(),
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
    }


def _enrich_exercises(day_exercises: list, completed_ids: set[str]) -> list[dict]:
    result = []
    for exercise in day_exercises:
        data = exercise.model_dump() if hasattr(exercise, "model_dump") else dict(exercise)
        entry_id = data.get("id")
        data["completed"] = entry_id in completed_ids
        result.append(data)
    return result


def _get_training_day_context(db: Session, student_id: str, day_of_week: int):
    training = training_repo.get_active_for_student(db, student_id)
    if training is None:
        raise NotFoundError("Nenhum treino ativo encontrado.")

    detail = training_service.get_training(db, None, training.id)
    day = next((d for d in detail.days if d.day_of_week == day_of_week), None)
    if day is None:
        raise NotFoundError("Dia de treino não configurado.")

    return training, detail, day


def get_my_training(db: Session, student_id: str) -> StudentTrainingOverview:
    training = training_repo.get_active_for_student(db, student_id)
    if training is None:
        raise NotFoundError("Nenhum treino ativo encontrado.")

    detail = training_service.get_training(db, None, training.id)
    today = date.today()

    category = None
    if training.category:
        category = {"id": training.category.id, "slug": training.category.slug, "name": training.category.name}

    days_overview = []
    for day in detail.days:
        session = workout_repo.get_session(db, student_id, day.id, today)
        completed_ids: set[str] = set()
        if session:
            completed_ids = {c.training_exercise_id for c in session.exercise_completions}

        exercises = _enrich_exercises(day.exercises, completed_ids)
        day_completed = session.status == "completed" if session else False

        days_overview.append(
            {
                "id": day.id,
                "day_of_week": day.day_of_week,
                "day_name": day.day_name,
                "label": day.label,
                "exercises_count": len(day.exercises),
                "exercises_completed": len(completed_ids),
                "day_completed": day_completed,
                "session_status": session.status if session else None,
                "exercises": exercises,
            }
        )

    return StudentTrainingOverview(
        id=detail.id,
        title=detail.title,
        description=detail.description,
        category=category,
        start_date=detail.start_date,
        end_date=detail.end_date,
        status=detail.status,
        days=days_overview,
        created_at=detail.created_at,
        updated_at=detail.updated_at,
    )


def get_my_training_day(db: Session, student_id: str, day_of_week: int) -> StudentDayTrainingResponse:
    training, detail, day = _get_training_day_context(db, student_id, day_of_week)

    today = date.today()
    checked_in = attendance_repo.get_by_student_date(db, student_id, today) is not None
    session = workout_repo.get_session(db, student_id, day.id, today)

    completed_ids: set[str] = set()
    if session:
        completed_ids = {c.training_exercise_id for c in session.exercise_completions}

    exercises = _enrich_exercises(day.exercises, completed_ids)
    day_completed = session.status == "completed" if session else False

    session_data = None
    if session:
        session_data = _serialize_session(session, len(day.exercises), exercises)
        session_data["day_of_week"] = day_of_week

    day_photos = [
        {
            "id": p.id,
            "url": _photo_url(p.file_path),
            "photo_type": p.photo_type,
            "taken_at": p.taken_at.isoformat(),
        }
        for p in progress_repo.list_day_photos(db, student_id, training.id, day_of_week)
    ]

    return StudentDayTrainingResponse(
        day_of_week=day.day_of_week,
        day_name=day.day_name,
        label=day.label,
        training={
            "id": detail.id,
            "title": detail.title,
            "start_date": detail.start_date.isoformat(),
            "end_date": detail.end_date.isoformat(),
        },
        exercises=exercises,
        checked_in_today=checked_in,
        day_completed=day_completed,
        session=session_data,
        day_photos=day_photos,
    )


def _ensure_session(db: Session, student_id: str, training_id: str, training_day_id: str) -> tuple:
    today = date.today()
    session = workout_repo.get_session(db, student_id, training_day_id, today)
    if session is None:
        session = workout_repo.create_session(db, student_id, training_id, training_day_id, today)
    return session, today


def complete_exercise(db: Session, student_id: str, day_of_week: int, entry_id: str) -> dict:
    training, detail, day = _get_training_day_context(db, student_id, day_of_week)

    entry_ids = {ex.id for ex in day.exercises}
    if entry_id not in entry_ids:
        raise NotFoundError("Exercício não encontrado neste dia.")

    session, _ = _ensure_session(db, student_id, training.id, day.id)

    if session.status == "completed":
        raise BusinessError("DAY_ALREADY_COMPLETED", "Treino do dia já foi concluído.", 409)

    workout_repo.mark_exercise_complete(db, session, entry_id)
    db.flush()
    session = workout_repo.get_session_by_id(db, session.id, student_id)
    completed_ids = {c.training_exercise_id for c in session.exercise_completions}
    all_done = len(completed_ids) >= len(day.exercises)
    if all_done:
        workout_repo.complete_session(db, session)

    db.commit()

    session = workout_repo.get_session_by_id(db, session.id, student_id)
    exercises = _enrich_exercises(day.exercises, completed_ids)

    return {
        "session": _serialize_session(session, len(day.exercises), exercises),
        "exercises": exercises,
        "day_completed": session.status == "completed",
    }


def complete_workout_day(db: Session, student_id: str, day_of_week: int) -> dict:
    training, detail, day = _get_training_day_context(db, student_id, day_of_week)
    session, _ = _ensure_session(db, student_id, training.id, day.id)

    if session.status == "completed":
        raise BusinessError("DAY_ALREADY_COMPLETED", "Treino do dia já foi concluído.", 409)

    completed_ids = {c.training_exercise_id for c in session.exercise_completions}
    if len(completed_ids) < len(day.exercises):
        pending = len(day.exercises) - len(completed_ids)
        raise BusinessError(
            "EXERCISES_PENDING",
            f"Ainda faltam {pending} exercício(s) para concluir o dia.",
            422,
        )

    workout_repo.complete_session(db, session)
    db.commit()

    session = workout_repo.get_session_by_id(db, session.id, student_id)
    exercises = _enrich_exercises(day.exercises, completed_ids)

    return {
        "message": "Treino do dia concluído com sucesso.",
        "session": _serialize_session(session, len(day.exercises), exercises),
        "day_completed": True,
    }


def check_in(db: Session, student_id: str, notes: str | None = None) -> CheckInResponse:
    training = training_repo.get_active_for_student_in_period(db, student_id)
    if training is None:
        raise BusinessError("TRAINING_NOT_ACTIVE", "Não há treino ativo para a data informada.")

    today = date.today()
    if attendance_repo.get_by_student_date(db, student_id, today):
        raise BusinessError("DUPLICATE_CHECKIN", "Check-in já registrado para esta data.", 409)

    record = attendance_repo.create(db, student_id, training.id, today, notes)
    db.commit()
    return CheckInResponse(
        id=record.id,
        check_in_date=record.check_in_date,
        checked_in_at=record.checked_in_at,
        training_id=training.id,
        training_title=training.title,
    )


def get_history(db: Session, student_id: str) -> HistoryResponse:
    trainings = training_repo.list_student_history(db, student_id)
    check_ins = attendance_repo.recent_by_student(db, student_id)
    return HistoryResponse(
        trainings=[
            HistoryTrainingItem(
                id=t.id,
                title=t.title,
                start_date=t.start_date,
                end_date=t.end_date,
                status=t.status,
            )
            for t in trainings
        ],
        recent_check_ins=[
            HistoryCheckInItem(check_in_date=c.check_in_date, training_title=c.training.title)
            for c in check_ins
        ],
    )


def get_progress_summary(db: Session, student_id: str) -> StudentProgressSummary:
    profile = student_repo.get_by_id(db, student_id)
    initial = float(profile.weight_kg) if profile and profile.weight_kg is not None else None

    photos, _ = progress_repo.list_photos(db, student_id, 1, 1)
    latest_weight = float(photos[0].weight_kg) if photos and photos[0].weight_kg is not None else initial
    delta = None
    if initial is not None and latest_weight is not None:
        delta = round(latest_weight - initial, 2)

    return StudentProgressSummary(
        latest_weight_kg=latest_weight,
        initial_weight_kg=initial,
        weight_delta_kg=delta,
        photos_count=progress_repo.count_photos(db, student_id),
        last_photo_at=progress_repo.last_photo_date(db, student_id),
        check_ins_total=attendance_repo.count_by_student(db, student_id),
    )


def list_my_photos(db: Session, student_id: str, page: int, limit: int) -> dict:
    items, total = progress_repo.list_photos(db, student_id, page, limit)
    return {
        "items": [
            ProgressPhotoResponse(
                id=p.id,
                url=_photo_url(p.file_path),
                photo_type=p.photo_type,
                weight_kg=float(p.weight_kg) if p.weight_kg is not None else None,
                notes=p.notes,
                taken_at=p.taken_at,
                created_at=p.created_at,
                training_id=p.training_id,
                day_of_week=p.day_of_week,
            )
            for p in items
        ],
        "pagination": build_pagination(page, limit, total).model_dump(),
    }


def list_student_attendance(
    db: Session, admin_id: str, student_id: str, page: int, limit: int, start_date: date | None, end_date: date | None
) -> AttendanceListResponse:
    profile = student_repo.get_by_id(db, student_id, admin_id)
    if profile is None:
        raise NotFoundError()

    items, total = attendance_repo.list_by_student(db, student_id, page, limit, start_date, end_date)
    total_check_ins = attendance_repo.count_by_student(db, student_id, start_date, end_date)

    return AttendanceListResponse(
        student_id=student_id,
        summary=AttendanceSummary(
            total_check_ins=total_check_ins,
            period_start=start_date,
            period_end=end_date,
            attendance_rate_pct=0.0,
        ),
        items=[
            AttendanceItem(
                id=i.id,
                check_in_date=i.check_in_date,
                checked_in_at=i.checked_in_at,
                training_id=i.training_id,
                training_title=i.training.title,
            )
            for i in items
        ],
        pagination=build_pagination(page, limit, total).model_dump(),
    )


def list_student_photos(db: Session, admin_id: str, student_id: str, page: int, limit: int) -> dict:
    profile = student_repo.get_by_id(db, student_id, admin_id)
    if profile is None:
        raise NotFoundError()
    return list_my_photos(db, student_id, page, limit)
