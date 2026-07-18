from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.core.pagination import PaginatedResponse, build_pagination
from app.repositories.exercise_repository import ExerciseRepository
from app.schemas.exercise import ExerciseCreate, ExerciseDetailResponse, ExerciseImageResponse, ExerciseListItem, ExerciseUpdate

exercise_repo = ExerciseRepository()


def _image_url(file_path: str) -> str:
    return f"/api/v1/uploads/{file_path}"


def list_exercises(
    db: Session,
    admin_id: str,
    page: int,
    limit: int,
    search: str | None = None,
    muscle_group: str | None = None,
) -> PaginatedResponse[ExerciseListItem]:
    items, total = exercise_repo.list_by_admin(db, admin_id, page, limit, search, muscle_group)
    return PaginatedResponse(
        items=[
            ExerciseListItem(
                id=item.id,
                name=item.name,
                description=item.description,
                muscle_group=item.muscle_group,
                default_sets=item.default_sets,
                default_reps=item.default_reps,
                default_rest_seconds=item.default_rest_seconds,
                images_count=len(item.images) if item.images else exercise_repo.count_images(db, item.id),
                created_at=item.created_at,
            )
            for item in items
        ],
        pagination=build_pagination(page, limit, total),
    )


def get_exercise(db: Session, admin_id: str, exercise_id: str) -> ExerciseDetailResponse:
    exercise = exercise_repo.get_detail(db, exercise_id, admin_id)
    if exercise is None:
        raise NotFoundError()

    return ExerciseDetailResponse(
        id=exercise.id,
        name=exercise.name,
        description=exercise.description,
        muscle_group=exercise.muscle_group,
        default_sets=exercise.default_sets,
        default_reps=exercise.default_reps,
        default_rest_seconds=exercise.default_rest_seconds,
        images=[
            ExerciseImageResponse(
                id=img.id,
                url=_image_url(img.file_path),
                media_type=img.media_type,
                sort_order=img.sort_order,
                is_featured=img.is_featured,
            )
            for img in sorted(exercise.images, key=lambda x: (not x.is_featured, x.sort_order))
        ],
        created_at=exercise.created_at,
    )


def create_exercise(db: Session, admin_id: str, data: ExerciseCreate) -> ExerciseDetailResponse:
    if exercise_repo.name_exists(db, admin_id, data.name):
        raise BusinessError("DUPLICATE_EXERCISE_NAME", "Nome de exercício já cadastrado.", 409)

    exercise = exercise_repo.create(db, admin_id, **data.model_dump())
    db.commit()
    return get_exercise(db, admin_id, exercise.id)


def update_exercise(db: Session, admin_id: str, exercise_id: str, data: ExerciseUpdate) -> ExerciseDetailResponse:
    exercise = exercise_repo.get_by_id(db, exercise_id, admin_id)
    if exercise is None:
        raise NotFoundError()

    payload = data.model_dump(exclude_unset=True)
    if "name" in payload and exercise_repo.name_exists(db, admin_id, payload["name"], exercise_id):
        raise BusinessError("DUPLICATE_EXERCISE_NAME", "Nome de exercício já cadastrado.", 409)

    for field, value in payload.items():
        setattr(exercise, field, value)

    db.commit()
    return get_exercise(db, admin_id, exercise_id)


def set_featured_image(db: Session, admin_id: str, exercise_id: str, image_id: str) -> ExerciseDetailResponse:
    exercise = exercise_repo.get_by_id(db, exercise_id, admin_id)
    if exercise is None:
        raise NotFoundError()

    image = exercise_repo.get_image(db, exercise_id, image_id)
    if image is None:
        raise NotFoundError()

    exercise_repo.set_featured_image(db, exercise_id, image)
    db.commit()
    return get_exercise(db, admin_id, exercise_id)


def delete_exercise(db: Session, admin_id: str, exercise_id: str) -> None:
    exercise = exercise_repo.get_by_id(db, exercise_id, admin_id)
    if exercise is None:
        raise NotFoundError()
    if exercise_repo.is_in_active_training(db, exercise_id):
        raise BusinessError("EXERCISE_IN_USE", "Exercício vinculado a treino ativo.", 409)

    exercise_repo.soft_delete(db, exercise)
    db.commit()
