from sqlalchemy.orm import Session

from app.core.exceptions import BusinessError, NotFoundError
from app.repositories.category_repository import CategoryRepository
from app.schemas.workout import TrainingCategoryCreate, TrainingCategoryResponse, TrainingCategoryUpdate
from app.utils.slug import slugify

category_repo = CategoryRepository()


def _to_response(category) -> TrainingCategoryResponse:
    return TrainingCategoryResponse(
        id=category.id,
        slug=category.slug,
        name=category.name,
        description=category.description,
        sort_order=category.sort_order,
    )


def list_categories(db: Session) -> list[TrainingCategoryResponse]:
    return [_to_response(c) for c in category_repo.list_active(db)]


def list_all_categories(db: Session) -> list[TrainingCategoryResponse]:
    return [_to_response(c) for c in category_repo.list_all(db)]


def _unique_slug(db: Session, name: str) -> str:
    base = slugify(name) or "categoria"
    slug = base
    suffix = 2
    while category_repo.get_by_slug(db, slug) is not None:
        slug = f"{base}-{suffix}"
        suffix += 1
    return slug


def create_category(db: Session, data: TrainingCategoryCreate) -> TrainingCategoryResponse:
    if category_repo.name_exists(db, data.name):
        raise BusinessError("DUPLICATE_CATEGORY_NAME", "Categoria já cadastrada.", 409)

    category = category_repo.create(
        db,
        slug=_unique_slug(db, data.name),
        name=data.name,
        description=data.description,
        sort_order=data.sort_order,
    )
    db.commit()
    return _to_response(category)


def update_category(db: Session, category_id: str, data: TrainingCategoryUpdate) -> TrainingCategoryResponse:
    category = category_repo.get_by_id(db, category_id)
    if category is None:
        raise NotFoundError("Categoria não encontrada.")

    payload = data.model_dump(exclude_unset=True)
    if "name" in payload and category_repo.name_exists(db, payload["name"], category_id):
        raise BusinessError("DUPLICATE_CATEGORY_NAME", "Categoria já cadastrada.", 409)

    for field, value in payload.items():
        setattr(category, field, value)

    db.commit()
    return _to_response(category)


def delete_category(db: Session, category_id: str) -> None:
    category = category_repo.get_by_id(db, category_id)
    if category is None:
        raise NotFoundError("Categoria não encontrada.")
    if category_repo.is_in_use(db, category_id):
        raise BusinessError("CATEGORY_IN_USE", "Categoria vinculada a exercícios ou treinos.", 409)

    category_repo.delete(db, category)
    db.commit()


def seed_categories(db: Session) -> None:
    category_repo.seed_presets(db)
