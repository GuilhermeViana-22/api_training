from sqlalchemy.orm import Session

from app.auth.password import hash_password
from app.core.exceptions import BusinessError, NotFoundError
from app.core.pagination import PaginatedResponse, build_pagination
from app.repositories.student_repository import StudentRepository
from app.repositories.training_repository import TrainingRepository
from app.repositories.user_repository import UserRepository
from app.schemas.student import (
    ActiveTrainingSummary,
    StudentCreate,
    StudentDetailResponse,
    StudentListItem,
    StudentStatusUpdate,
    StudentUpdate,
)
from app.schemas.report import StudentOption
from app.utils.media import build_upload_url

user_repo = UserRepository()
student_repo = StudentRepository()
training_repo = TrainingRepository()


def _to_list_item(db: Session, profile) -> StudentListItem:
    active = training_repo.get_active_for_student(db, profile.user_id)
    active_training = None
    if active:
        active_training = ActiveTrainingSummary(
            id=active.id,
            title=active.title,
            start_date=active.start_date,
            end_date=active.end_date,
            status=active.status,
        )
    return StudentListItem(
        id=profile.user_id,
        email=profile.user.email,
        full_name=profile.full_name,
        phone=profile.phone,
        is_active=profile.user.is_active,
        active_training=active_training,
        avatar_url=build_upload_url(profile.user.avatar_path),
        created_at=profile.user.created_at,
    )


def list_student_options(db: Session, admin_id: str) -> list[StudentOption]:
    """Lista alunos para dropdown no cadastro de treino (id + nome + status treino)."""
    profiles, _ = student_repo.list_by_admin(db, admin_id, 1, 1000)
    options: list[StudentOption] = []
    for profile in profiles:
        active = training_repo.get_active_for_student(db, profile.user_id)
        options.append(
            StudentOption(
                id=profile.user_id,
                full_name=profile.full_name,
                email=profile.user.email,
                is_active=profile.user.is_active,
                has_active_training=active is not None,
                active_training_title=active.title if active else None,
            )
        )
    return options


def list_students(
    db: Session, admin_id: str, page: int, limit: int, search: str | None = None, is_active: bool | None = None
) -> PaginatedResponse[StudentListItem]:
    items, total = student_repo.list_by_admin(db, admin_id, page, limit, search, is_active)
    return PaginatedResponse(
        items=[_to_list_item(db, item) for item in items],
        pagination=build_pagination(page, limit, total),
    )


def get_student(db: Session, admin_id: str, student_id: str) -> StudentDetailResponse:
    profile = student_repo.get_by_id(db, student_id, admin_id)
    if profile is None:
        raise NotFoundError()

    return StudentDetailResponse(
        id=profile.user_id,
        email=profile.user.email,
        full_name=profile.full_name,
        phone=profile.phone,
        birth_date=profile.birth_date,
        height_cm=float(profile.height_cm) if profile.height_cm is not None else None,
        weight_kg=float(profile.weight_kg) if profile.weight_kg is not None else None,
        goal=profile.goal,
        notes=profile.notes,
        is_active=profile.user.is_active,
        trainings_count=student_repo.count_trainings(db, profile.user_id),
        last_check_in=student_repo.last_check_in(db, profile.user_id),
        avatar_url=build_upload_url(profile.user.avatar_path),
        created_at=profile.user.created_at,
    )


def create_student(db: Session, admin_id: str, data: StudentCreate) -> StudentDetailResponse:
    if user_repo.email_exists(db, data.email):
        raise BusinessError("DUPLICATE_EMAIL", "Email já cadastrado.", 409)

    user = user_repo.create_user(db, data.email, hash_password(data.password), "student")
    student_repo.create(
        db,
        user_id=user.id,
        admin_id=admin_id,
        full_name=data.full_name,
        phone=data.phone,
        birth_date=data.birth_date,
        height_cm=data.height_cm,
        weight_kg=data.weight_kg,
        goal=data.goal,
        notes=data.notes,
    )
    db.commit()
    return get_student(db, admin_id, user.id)


def update_student(db: Session, admin_id: str, student_id: str, data: StudentUpdate) -> StudentDetailResponse:
    profile = student_repo.get_by_id(db, student_id, admin_id)
    if profile is None:
        raise NotFoundError()

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    db.commit()
    return get_student(db, admin_id, student_id)


def update_status(db: Session, admin_id: str, student_id: str, data: StudentStatusUpdate) -> StudentDetailResponse:
    profile = student_repo.get_by_id(db, student_id, admin_id)
    if profile is None:
        raise NotFoundError()

    profile.user.is_active = data.is_active
    db.commit()
    return get_student(db, admin_id, student_id)


def delete_student(db: Session, admin_id: str, student_id: str) -> None:
    profile = student_repo.get_by_id(db, student_id, admin_id)
    if profile is None:
        raise NotFoundError()

    student_repo.soft_delete(db, profile)
    db.commit()
