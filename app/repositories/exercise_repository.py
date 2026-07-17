from datetime import datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.exercise import Exercise
from app.models.exercise_image import ExerciseImage
from app.utils.uuid import generate_uuid


class ExerciseRepository:
    def get_by_id(self, db: Session, exercise_id: str, admin_id: str | None = None) -> Exercise | None:
        query = db.query(Exercise).filter(Exercise.id == exercise_id, Exercise.deleted_at.is_(None))
        if admin_id:
            query = query.filter(Exercise.admin_id == admin_id)
        return query.first()

    def get_detail(self, db: Session, exercise_id: str, admin_id: str) -> Exercise | None:
        return (
            db.query(Exercise)
            .options(joinedload(Exercise.images), joinedload(Exercise.category))
            .filter(Exercise.id == exercise_id, Exercise.admin_id == admin_id, Exercise.deleted_at.is_(None))
            .first()
        )

    def list_by_admin(
        self,
        db: Session,
        admin_id: str,
        page: int,
        limit: int,
        search: str | None = None,
        muscle_group: str | None = None,
        category_id: str | None = None,
    ) -> tuple[list[Exercise], int]:
        query = db.query(Exercise).options(joinedload(Exercise.category)).filter(
            Exercise.admin_id == admin_id, Exercise.deleted_at.is_(None)
        )
        if search:
            query = query.filter(Exercise.name.ilike(f"%{search}%"))
        if muscle_group:
            query = query.filter(Exercise.muscle_group == muscle_group)
        if category_id:
            query = query.filter(Exercise.category_id == category_id)

        total = query.count()
        items = query.order_by(Exercise.name.asc()).offset((page - 1) * limit).limit(limit).all()
        return items, total

    def name_exists(self, db: Session, admin_id: str, name: str, exclude_id: str | None = None) -> bool:
        query = db.query(Exercise.id).filter(
            Exercise.admin_id == admin_id,
            func.lower(Exercise.name) == name.lower(),
            Exercise.deleted_at.is_(None),
        )
        if exclude_id:
            query = query.filter(Exercise.id != exclude_id)
        return query.first() is not None

    def create(self, db: Session, admin_id: str, **kwargs) -> Exercise:
        exercise = Exercise(id=generate_uuid(), admin_id=admin_id, **kwargs)
        db.add(exercise)
        db.flush()
        return exercise

    def soft_delete(self, db: Session, exercise: Exercise) -> None:
        exercise.deleted_at = datetime.utcnow()

    def add_image(self, db: Session, exercise_id: str, file_path: str, **kwargs) -> ExerciseImage:
        image = ExerciseImage(id=generate_uuid(), exercise_id=exercise_id, file_path=file_path, **kwargs)
        db.add(image)
        db.flush()
        return image

    def get_image(self, db: Session, exercise_id: str, image_id: str) -> ExerciseImage | None:
        return (
            db.query(ExerciseImage)
            .filter(ExerciseImage.id == image_id, ExerciseImage.exercise_id == exercise_id)
            .first()
        )

    def count_images(self, db: Session, exercise_id: str) -> int:
        return db.query(func.count(ExerciseImage.id)).filter(ExerciseImage.exercise_id == exercise_id).scalar() or 0

    def is_in_active_training(self, db: Session, exercise_id: str) -> bool:
        from app.models.training import Training
        from app.models.training_exercise import TrainingExercise

        return (
            db.query(TrainingExercise.id)
            .join(Training, Training.id == TrainingExercise.training_id)
            .filter(TrainingExercise.exercise_id == exercise_id, Training.status == "active")
            .first()
            is not None
        )
