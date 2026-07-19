from datetime import date

from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.pagination import PaginatedResponse, build_pagination
from app.repositories.attendance_repository import AttendanceRepository
from app.repositories.category_repository import CategoryRepository
from app.repositories.exercise_repository import ExerciseRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.training_repository import TrainingRepository
from app.schemas.training import (
    TrainingCompleteCreate,
    TrainingCreate,
    TrainingDayCreate,
    TrainingDayResponse,
    TrainingDayUpdate,
    TrainingDetailResponse,
    TrainingExerciseCreate,
    TrainingExerciseResponse,
    TrainingExerciseUpdate,
    TrainingListItem,
    TrainingUpdate,
    StudentTrainingSummary,
)
from app.utils.dates import day_name
from app.utils.media import build_upload_url

training_repo = TrainingRepository()
student_repo = StudentRepository()
exercise_repo = ExerciseRepository()
category_repo = CategoryRepository()
attendance_repo = AttendanceRepository()


def _category_dict(category) -> dict | None:
    if category is None:
        return None
    return {"id": category.id, "slug": category.slug, "name": category.name}


def _image_url(file_path: str) -> str:
    return f"/api/v1/uploads/{file_path}"


MAX_LIST_MEDIA = 5


def _collect_media(training) -> list[dict]:
    """Midias dos exercicios do treino, na ordem dia -> exercicio -> midia, sem repetir a mesma midia, limitado a MAX_LIST_MEDIA."""
    media: list[dict] = []
    seen_ids: set[str] = set()
    for day in sorted(training.days, key=lambda d: d.sort_order):
        for entry in sorted(day.exercises, key=lambda e: e.sort_order):
            for img in sorted(entry.exercise.images, key=lambda i: (not i.is_featured, i.sort_order)):
                if img.id in seen_ids:
                    continue
                seen_ids.add(img.id)
                media.append({"url": _image_url(img.file_path), "media_type": img.media_type})
                if len(media) >= MAX_LIST_MEDIA:
                    return media
    return media


def _to_list_item(training) -> TrainingListItem:
    exercises_count = sum(len(day.exercises) for day in training.days) if training.days else 0
    student_email = None
    avatar_url = None
    if training.student and training.student.user:
        student_email = training.student.user.email
        avatar_url = build_upload_url(training.student.user.avatar_path)
    return TrainingListItem(
        id=training.id,
        student_id=training.student_id,
        student_name=training.student.full_name,
        student_email=student_email,
        avatar_url=avatar_url,
        title=training.title,
        category=_category_dict(training.category),
        start_date=training.start_date,
        end_date=training.end_date,
        status=training.status,
        days_count=len(training.days),
        exercises_count=exercises_count,
        media=_collect_media(training),
        created_at=training.created_at,
    )


def _serialize_training(db: Session, training) -> TrainingDetailResponse:
    days = []
    for day in sorted(training.days, key=lambda d: d.sort_order):
        exercises = []
        for entry in sorted(day.exercises, key=lambda e: e.sort_order):
            images = [{"url": _image_url(img.file_path), "media_type": img.media_type} for img in entry.exercise.images]
            exercises.append(
                TrainingExerciseResponse(
                    id=entry.id,
                    exercise_id=entry.exercise_id,
                    exercise_name=entry.exercise.name,
                    exercise_description=entry.exercise.description,
                    sets=entry.sets,
                    reps=entry.reps,
                    load_kg=float(entry.load_kg) if entry.load_kg is not None else None,
                    rest_seconds=entry.rest_seconds,
                    sort_order=entry.sort_order,
                    notes=entry.notes,
                    images=images,
                )
            )
        days.append(
            TrainingDayResponse(
                id=day.id,
                day_of_week=day.day_of_week,
                day_name=day_name(day.day_of_week),
                label=day.label,
                notes=day.notes,
                sort_order=day.sort_order,
                exercises=exercises,
            )
        )

    student_email = training.student.user.email if training.student and training.student.user else None

    return TrainingDetailResponse(
        id=training.id,
        student_id=training.student_id,
        student_name=training.student.full_name,
        student_email=student_email,
        title=training.title,
        description=training.description,
        category=_category_dict(training.category),
        start_date=training.start_date,
        end_date=training.end_date,
        status=training.status,
        days=days,
        days_attended=attendance_repo.count_by_training(db, training.id),
        created_at=training.created_at,
        updated_at=training.updated_at,
    )


def list_trainings(
    db: Session, admin_id: str, page: int, limit: int, student_id: str | None = None, status: str | None = None
) -> PaginatedResponse[TrainingListItem]:
    items, total = training_repo.list_by_admin(db, admin_id, page, limit, student_id, status)
    return PaginatedResponse(
        items=[_to_list_item(item) for item in items],
        pagination=build_pagination(page, limit, total),
    )


def list_student_trainings(db: Session, admin_id: str, student_id: str) -> StudentTrainingSummary:
    student = student_repo.get_by_id(db, student_id, admin_id)
    if student is None:
        raise NotFoundError("Aluno não encontrado.")

    trainings = training_repo.list_by_student(db, admin_id, student_id)
    items = [_to_list_item(t) for t in trainings]
    active = next((i for i in items if i.status == "active"), None)

    return StudentTrainingSummary(
        student_id=student.user_id,
        student_name=student.full_name,
        student_email=student.user.email,
        active_training=active,
        trainings=items,
    )


def _validate_category(db: Session, category_id: str | None) -> None:
    if category_id is None:
        return
    if category_repo.get_by_id(db, category_id) is None:
        raise NotFoundError("Categoria de treino não encontrada.")


def _validate_training_days(db: Session, admin_id: str, days: list) -> None:
    """Valida ausencia de dia duplicado e existencia dos exercicios referenciados no payload.
    Compartilhado entre create_training_complete e update_training_complete."""
    seen_days: set[int] = set()
    for day_data in days:
        if day_data.day_of_week in seen_days:
            raise BusinessError("DUPLICATE_DAY", f"Dia {day_data.day_of_week} duplicado no payload.", 409)
        seen_days.add(day_data.day_of_week)
        for exercise_data in day_data.exercises:
            if exercise_repo.get_by_id(db, exercise_data.exercise_id, admin_id) is None:
                raise NotFoundError(f"Exercício {exercise_data.exercise_id} não encontrado.")


def _write_training_days(db: Session, training_id: str, days: list) -> None:
    """Cria os dias/exercicios do payload para um treino que ja esta sem nenhum dia
    (recem-criado, ou com os dias antigos removidos por update_training_complete)."""
    for day_data in days:
        day = training_repo.add_day(
            db,
            training_id,
            day_of_week=day_data.day_of_week,
            label=day_data.label,
            notes=day_data.notes,
            sort_order=day_data.sort_order,
        )
        for exercise_data in day_data.exercises:
            training_repo.add_exercise_to_day(db, day.id, **exercise_data.model_dump())


def create_training_complete(db: Session, admin_id: str, data: TrainingCompleteCreate) -> TrainingDetailResponse:
    """Cadastra treino completo vinculado ao aluno: dias da semana + exercícios em uma única operação."""
    if data.end_date < data.start_date:
        raise BusinessError("INVALID_DATE_RANGE", "Data inicial deve ser anterior ou igual à data final.")

    _validate_category(db, data.category_id)
    _validate_training_days(db, admin_id, data.days)

    student = student_repo.get_by_id(db, data.student_id, admin_id)
    if student is None:
        raise NotFoundError("Aluno não encontrado.")

    training = training_repo.create(
        db,
        admin_id=admin_id,
        student_id=data.student_id,
        title=data.title,
        description=data.description,
        category_id=data.category_id,
        start_date=data.start_date,
        end_date=data.end_date,
        status="draft",
    )

    _write_training_days(db, training.id, data.days)

    if data.activate:
        if not training_repo.has_exercises(db, training.id):
            raise BusinessError("TRAINING_EMPTY", "Treino deve ter ao menos um dia com exercícios para ser ativado.")
        training_repo.complete_active_for_student(db, data.student_id, exclude_id=training.id)
        training.status = "active"

    db.commit()
    return get_training(db, admin_id, training.id)


def update_training_complete(
    db: Session, admin_id: str, training_id: str, data: TrainingCompleteCreate
) -> TrainingDetailResponse:
    """Substitui integralmente um treino existente: metadados + dias + exercicios, em uma unica operacao.
    O aluno vinculado (student_id) nao e alterado por aqui — so create_training_complete atribui aluno."""
    training = training_repo.get_by_id(db, training_id, admin_id)
    if training is None:
        raise NotFoundError()
    if training.status in {"active", "completed"} and training_repo.has_student_interaction(db, training_id):
        raise BusinessError(
            "TRAINING_LOCKED",
            "Aluno ja tem check-in ou treino registrado neste plano — nao pode ser editado.",
        )
    if data.end_date < data.start_date:
        raise BusinessError("INVALID_DATE_RANGE", "Data inicial deve ser anterior ou igual à data final.")

    _validate_category(db, data.category_id)
    _validate_training_days(db, admin_id, data.days)

    training.title = data.title
    training.description = data.description
    training.category_id = data.category_id
    training.start_date = data.start_date
    training.end_date = data.end_date

    for day in list(training.days):
        db.delete(day)
    db.flush()

    _write_training_days(db, training.id, data.days)

    if data.activate and training.status != "active":
        if not training_repo.has_exercises(db, training.id):
            raise BusinessError("TRAINING_EMPTY", "Treino deve ter ao menos um dia com exercícios para ser ativado.")
        training_repo.complete_active_for_student(db, training.student_id, exclude_id=training.id)
        training.status = "active"

    db.commit()
    return get_training(db, admin_id, training.id)


def activate_training(db: Session, admin_id: str, training_id: str) -> TrainingDetailResponse:
    return update_training(db, admin_id, training_id, TrainingUpdate(status="active"))


def get_training(db: Session, admin_id: str | None, training_id: str) -> TrainingDetailResponse:
    training = training_repo.get_detail(db, training_id, admin_id)
    if training is None:
        raise NotFoundError()
    return _serialize_training(db, training)


def create_training(db: Session, admin_id: str, data: TrainingCreate) -> TrainingDetailResponse:
    if data.end_date < data.start_date:
        raise BusinessError("INVALID_DATE_RANGE", "Data inicial deve ser anterior ou igual à data final.")

    _validate_category(db, data.category_id)

    student = student_repo.get_by_id(db, data.student_id, admin_id)
    if student is None:
        raise NotFoundError("Aluno não encontrado.")

    training = training_repo.create(
        db,
        admin_id=admin_id,
        student_id=data.student_id,
        title=data.title,
        description=data.description,
        start_date=data.start_date,
        end_date=data.end_date,
        status="draft",
    )
    db.commit()
    return get_training(db, admin_id, training.id)


def update_training(db: Session, admin_id: str, training_id: str, data: TrainingUpdate) -> TrainingDetailResponse:
    training = training_repo.get_by_id(db, training_id, admin_id)
    if training is None:
        raise NotFoundError()

    if training.status in {"completed", "cancelled"}:
        raise BusinessError("TRAINING_LOCKED", "Treino concluído ou cancelado não pode ser editado.")

    payload = data.model_dump(exclude_unset=True)
    new_status = payload.get("status")

    if "category_id" in payload:
        _validate_category(db, payload.get("category_id"))

    start_date = payload.get("start_date", training.start_date)
    end_date = payload.get("end_date", training.end_date)
    if end_date < start_date:
        raise BusinessError("INVALID_DATE_RANGE", "Data inicial deve ser anterior ou igual à data final.")

    if new_status == "active":
        if not training_repo.has_exercises(db, training_id):
            raise BusinessError("TRAINING_EMPTY", "Treino deve ter ao menos um dia com exercícios para ser ativado.")
        existing = training_repo.get_any_active_for_student(db, training.student_id, exclude_id=training_id)
        if existing:
            training_repo.complete_active_for_student(db, training.student_id, exclude_id=training_id)

    for field, value in payload.items():
        setattr(training, field, value)

    db.commit()
    return get_training(db, admin_id, training_id)


def delete_training(db: Session, admin_id: str, training_id: str) -> None:
    training = training_repo.get_by_id(db, training_id, admin_id)
    if training is None:
        raise NotFoundError()
    if training.status in {"active", "completed"} and training_repo.has_student_interaction(db, training_id):
        raise BusinessError(
            "TRAINING_LOCKED",
            "Aluno ja tem check-in ou treino registrado neste plano — nao pode ser excluido.",
        )

    db.delete(training)
    db.commit()


def add_day(db: Session, admin_id: str, training_id: str, data: TrainingDayCreate) -> TrainingDayResponse:
    training = training_repo.get_by_id(db, training_id, admin_id)
    if training is None:
        raise NotFoundError()
    if training.status in {"completed", "cancelled"}:
        raise BusinessError("TRAINING_LOCKED", "Treino concluído ou cancelado não pode ser editado.")
    if training_repo.day_exists(db, training_id, data.day_of_week):
        raise BusinessError("DUPLICATE_DAY", "Dia da semana já configurado neste treino.", 409)

    day = training_repo.add_day(db, training_id, **data.model_dump())
    db.commit()
    return TrainingDayResponse(
        id=day.id,
        day_of_week=day.day_of_week,
        day_name=day_name(day.day_of_week),
        label=day.label,
        notes=day.notes,
        sort_order=day.sort_order,
        exercises=[],
    )


def update_day(db: Session, admin_id: str, training_id: str, day_id: str, data: TrainingDayUpdate) -> TrainingDayResponse:
    training = training_repo.get_by_id(db, training_id, admin_id)
    if training is None:
        raise NotFoundError()

    day = training_repo.get_day(db, training_id, day_id)
    if day is None:
        raise NotFoundError()

    payload = data.model_dump(exclude_unset=True)
    if "day_of_week" in payload and training_repo.day_exists(db, training_id, payload["day_of_week"], day_id):
        raise BusinessError("DUPLICATE_DAY", "Dia da semana já configurado neste treino.", 409)

    for field, value in payload.items():
        setattr(day, field, value)

    db.commit()
    updated = get_training(db, admin_id, training_id)
    updated_day = next((d for d in updated.days if d.id == day_id), None)
    if updated_day is None:
        raise NotFoundError()
    return updated_day


def delete_day(db: Session, admin_id: str, training_id: str, day_id: str) -> None:
    training = training_repo.get_by_id(db, training_id, admin_id)
    if training is None:
        raise NotFoundError()

    day = training_repo.get_day(db, training_id, day_id)
    if day is None:
        raise NotFoundError()

    db.delete(day)
    db.commit()


def add_exercise_to_day(
    db: Session, admin_id: str, training_id: str, day_id: str, data: TrainingExerciseCreate
) -> TrainingExerciseResponse:
    training = training_repo.get_by_id(db, training_id, admin_id)
    if training is None:
        raise NotFoundError()

    day = training_repo.get_day(db, training_id, day_id)
    if day is None:
        raise NotFoundError()

    exercise = exercise_repo.get_by_id(db, data.exercise_id, admin_id)
    if exercise is None:
        raise NotFoundError("Exercício não encontrado.")

    entry = training_repo.add_exercise_to_day(db, day_id, **data.model_dump())
    db.commit()
    return TrainingExerciseResponse(
        id=entry.id,
        exercise_id=entry.exercise_id,
        exercise_name=exercise.name,
        exercise_description=exercise.description,
        sets=entry.sets,
        reps=entry.reps,
        load_kg=float(entry.load_kg) if entry.load_kg is not None else None,
        rest_seconds=entry.rest_seconds,
        sort_order=entry.sort_order,
        notes=entry.notes,
        images=[{"url": _image_url(img.file_path), "media_type": img.media_type} for img in exercise.images],
    )


def update_exercise_entry(
    db: Session, admin_id: str, training_id: str, day_id: str, entry_id: str, data: TrainingExerciseUpdate
) -> TrainingExerciseResponse:
    training = training_repo.get_by_id(db, training_id, admin_id)
    if training is None:
        raise NotFoundError()

    entry = training_repo.get_exercise_entry(db, day_id, entry_id)
    if entry is None:
        raise NotFoundError()

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(entry, field, value)

    db.commit()
    exercise = exercise_repo.get_detail(db, entry.exercise_id, admin_id)
    return TrainingExerciseResponse(
        id=entry.id,
        exercise_id=entry.exercise_id,
        exercise_name=exercise.name if exercise else "",
        exercise_description=exercise.description if exercise else None,
        sets=entry.sets,
        reps=entry.reps,
        load_kg=float(entry.load_kg) if entry.load_kg is not None else None,
        rest_seconds=entry.rest_seconds,
        sort_order=entry.sort_order,
        notes=entry.notes,
        images=[{"url": _image_url(img.file_path), "media_type": img.media_type} for img in (exercise.images if exercise else [])],
    )


def delete_exercise_entry(db: Session, admin_id: str, training_id: str, day_id: str, entry_id: str) -> None:
    training = training_repo.get_by_id(db, training_id, admin_id)
    if training is None:
        raise NotFoundError()

    entry = training_repo.get_exercise_entry(db, day_id, entry_id)
    if entry is None:
        raise NotFoundError()

    db.delete(entry)
    db.commit()
