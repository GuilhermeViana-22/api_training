from sqlalchemy.orm import Session

from app.repositories.category_repository import CategoryRepository
from app.schemas.workout import TrainingCategoryResponse

category_repo = CategoryRepository()


def list_categories(db: Session) -> list[TrainingCategoryResponse]:
    items = category_repo.list_active(db)
    return [
        TrainingCategoryResponse(
            id=c.id,
            slug=c.slug,
            name=c.name,
            description=c.description,
            sort_order=c.sort_order,
        )
        for c in items
    ]


def seed_categories(db: Session) -> None:
    category_repo.seed_presets(db)
