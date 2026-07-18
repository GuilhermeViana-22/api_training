from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.training_category import TrainingCategory
from app.utils.uuid import generate_uuid

PRESET_CATEGORIES = [
    {
        "slug": "musculacao",
        "name": "Musculação",
        "description": "Treinos de força e hipertrofia com cargas, máquinas e peso livre.",
        "sort_order": 0,
    },
    {
        "slug": "cardio",
        "name": "Cardio",
        "description": "Treinos aeróbicos: corrida, bike, elíptico, HIIT e condicionamento.",
        "sort_order": 1,
    },
    {
        "slug": "calistenia",
        "name": "Calistenia",
        "description": "Treinos com peso corporal: barras, paralelas, flexões e progressões.",
        "sort_order": 2,
    },
]


class CategoryRepository:
    def list_all(self, db: Session) -> list[TrainingCategory]:
        return db.query(TrainingCategory).order_by(TrainingCategory.sort_order.asc()).all()

    def list_active(self, db: Session) -> list[TrainingCategory]:
        return (
            db.query(TrainingCategory)
            .filter(TrainingCategory.is_active.is_(True))
            .order_by(TrainingCategory.sort_order.asc())
            .all()
        )

    def get_by_id(self, db: Session, category_id: str) -> TrainingCategory | None:
        return db.get(TrainingCategory, category_id)

    def get_by_slug(self, db: Session, slug: str) -> TrainingCategory | None:
        return db.query(TrainingCategory).filter(TrainingCategory.slug == slug).first()

    def name_exists(self, db: Session, name: str, exclude_id: str | None = None) -> bool:
        query = db.query(TrainingCategory.id).filter(func.lower(TrainingCategory.name) == name.lower())
        if exclude_id:
            query = query.filter(TrainingCategory.id != exclude_id)
        return query.first() is not None

    def create(self, db: Session, *, slug: str, name: str, description: str | None, sort_order: int) -> TrainingCategory:
        category = TrainingCategory(id=generate_uuid(), slug=slug, name=name, description=description, sort_order=sort_order)
        db.add(category)
        db.flush()
        return category

    def is_in_use(self, db: Session, category_id: str) -> bool:
        from app.models.training import Training

        return db.query(Training.id).filter(Training.category_id == category_id).first() is not None

    def delete(self, db: Session, category: TrainingCategory) -> None:
        db.delete(category)

    def seed_presets(self, db: Session) -> None:
        for preset in PRESET_CATEGORIES:
            existing = self.get_by_slug(db, preset["slug"])
            if existing:
                continue
            db.add(TrainingCategory(id=generate_uuid(), **preset))
        db.commit()
