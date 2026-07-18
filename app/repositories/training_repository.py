from datetime import date, datetime

from sqlalchemy.orm import Session, joinedload

from app.models.attendance_record import AttendanceRecord
from app.models.exercise import Exercise
from app.models.student_profile import StudentProfile
from app.models.training import Training
from app.models.training_category import TrainingCategory
from app.models.training_day import TrainingDay
from app.models.training_exercise import TrainingExercise
from app.models.workout_session import WorkoutSession
from app.utils.uuid import generate_uuid


class TrainingRepository:
    def get_by_id(self, db: Session, training_id: str, admin_id: str | None = None) -> Training | None:
        query = db.query(Training).filter(Training.id == training_id)
        if admin_id:
            query = query.filter(Training.admin_id == admin_id)
        return query.first()

    def get_detail(self, db: Session, training_id: str, admin_id: str | None = None) -> Training | None:
        query = (
            db.query(Training)
            .options(
                joinedload(Training.student).joinedload(StudentProfile.user),
                joinedload(Training.category),
                joinedload(Training.days)
                .joinedload(TrainingDay.exercises)
                .joinedload(TrainingExercise.exercise)
                .joinedload(Exercise.images),
            )
            .filter(Training.id == training_id)
        )
        if admin_id:
            query = query.filter(Training.admin_id == admin_id)
        return query.first()

    def list_by_admin(
        self,
        db: Session,
        admin_id: str,
        page: int,
        limit: int,
        student_id: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Training], int]:
        query = (
            db.query(Training)
            .options(
                joinedload(Training.student).joinedload(StudentProfile.user),
                joinedload(Training.days)
                .joinedload(TrainingDay.exercises)
                .joinedload(TrainingExercise.exercise)
                .joinedload(Exercise.images),
            )
            .filter(Training.admin_id == admin_id)
        )
        if student_id:
            query = query.filter(Training.student_id == student_id)
        if status:
            query = query.filter(Training.status == status)

        total = query.count()
        items = query.order_by(Training.created_at.desc()).offset((page - 1) * limit).limit(limit).all()
        return items, total

    def search_by_title(self, db: Session, admin_id: str, term: str, limit: int = 5) -> list[Training]:
        return (
            db.query(Training)
            .options(joinedload(Training.student).joinedload(StudentProfile.user))
            .filter(Training.admin_id == admin_id, Training.title.ilike(f"%{term}%"))
            .order_by(Training.created_at.desc())
            .limit(limit)
            .all()
        )

    def create(self, db: Session, admin_id: str, **kwargs) -> Training:
        training = Training(id=generate_uuid(), admin_id=admin_id, **kwargs)
        db.add(training)
        db.flush()
        return training

    def get_active_for_student(self, db: Session, student_id: str) -> Training | None:
        return (
            db.query(Training)
            .options(joinedload(Training.category), joinedload(Training.days))
            .filter(Training.student_id == student_id, Training.status == "active")
            .order_by(Training.created_at.desc())
            .first()
        )

    def get_active_for_student_in_period(self, db: Session, student_id: str) -> Training | None:
        today = date.today()
        return (
            db.query(Training)
            .options(joinedload(Training.category), joinedload(Training.days))
            .filter(
                Training.student_id == student_id,
                Training.status == "active",
                Training.start_date <= today,
                Training.end_date >= today,
            )
            .first()
        )

    def get_any_active_for_student(self, db: Session, student_id: str, exclude_id: str | None = None) -> Training | None:
        query = db.query(Training).filter(Training.student_id == student_id, Training.status == "active")
        if exclude_id:
            query = query.filter(Training.id != exclude_id)
        return query.first()

    def complete_active_for_student(self, db: Session, student_id: str, exclude_id: str | None = None) -> None:
        query = db.query(Training).filter(Training.student_id == student_id, Training.status == "active")
        if exclude_id:
            query = query.filter(Training.id != exclude_id)
        for training in query.all():
            training.status = "completed"

    def has_exercises(self, db: Session, training_id: str) -> bool:
        return (
            db.query(TrainingExercise.id)
            .join(TrainingDay, TrainingDay.id == TrainingExercise.training_day_id)
            .filter(TrainingDay.training_id == training_id)
            .first()
            is not None
        )

    def add_day(self, db: Session, training_id: str, **kwargs) -> TrainingDay:
        day = TrainingDay(id=generate_uuid(), training_id=training_id, **kwargs)
        db.add(day)
        db.flush()
        return day

    def get_day(self, db: Session, training_id: str, day_id: str) -> TrainingDay | None:
        return db.query(TrainingDay).filter(TrainingDay.id == day_id, TrainingDay.training_id == training_id).first()

    def day_exists(self, db: Session, training_id: str, day_of_week: int, exclude_id: str | None = None) -> bool:
        query = db.query(TrainingDay.id).filter(TrainingDay.training_id == training_id, TrainingDay.day_of_week == day_of_week)
        if exclude_id:
            query = query.filter(TrainingDay.id != exclude_id)
        return query.first() is not None

    def add_exercise_to_day(self, db: Session, training_day_id: str, **kwargs) -> TrainingExercise:
        entry = TrainingExercise(id=generate_uuid(), training_day_id=training_day_id, **kwargs)
        db.add(entry)
        db.flush()
        return entry

    def get_exercise_entry(self, db: Session, day_id: str, entry_id: str) -> TrainingExercise | None:
        return (
            db.query(TrainingExercise)
            .filter(TrainingExercise.id == entry_id, TrainingExercise.training_day_id == day_id)
            .first()
        )

    def count_expiring_soon(self, db: Session, admin_id: str, days: int = 14) -> int:
        today = date.today()
        limit = today.toordinal()
        from datetime import timedelta

        end = today + timedelta(days=days)
        return (
            db.query(Training)
            .filter(
                Training.admin_id == admin_id,
                Training.status == "active",
                Training.end_date >= today,
                Training.end_date <= end,
            )
            .count()
        )

    def count_students_with_active_training(self, db: Session, admin_id: str) -> int:
        return (
            db.query(Training.student_id)
            .filter(Training.admin_id == admin_id, Training.status == "active")
            .distinct()
            .count()
        )

    def list_by_student(self, db: Session, admin_id: str, student_id: str) -> list[Training]:
        return (
            db.query(Training)
            .options(joinedload(Training.student).joinedload(StudentProfile.user), joinedload(Training.days).joinedload(TrainingDay.exercises))
            .filter(Training.admin_id == admin_id, Training.student_id == student_id)
            .order_by(Training.created_at.desc())
            .all()
        )

    def count_days_per_week(self, db: Session, training_id: str) -> int:
        return db.query(TrainingDay.id).filter(TrainingDay.training_id == training_id).count()

    def count_exercises(self, db: Session, training_id: str) -> int:
        return (
            db.query(TrainingExercise.id)
            .join(TrainingDay, TrainingDay.id == TrainingExercise.training_day_id)
            .filter(TrainingDay.training_id == training_id)
            .count()
        )

    def has_student_interaction(self, db: Session, training_id: str) -> bool:
        """True se o aluno ja fez check-in ou registrou/concluiu algum treino
        (workout session), independente do status atual do plano."""
        has_session = db.query(WorkoutSession.id).filter(WorkoutSession.training_id == training_id).first() is not None
        if has_session:
            return True
        return db.query(AttendanceRecord.id).filter(AttendanceRecord.training_id == training_id).first() is not None

    def list_student_history(self, db: Session, student_id: str) -> list[Training]:
        return (
            db.query(Training)
            .filter(Training.student_id == student_id, Training.status.in_(["completed", "cancelled"]))
            .order_by(Training.end_date.desc())
            .all()
        )
