from datetime import date, datetime

from sqlalchemy.orm import Session, joinedload

from app.models.exercise_completion import ExerciseCompletion
from app.models.workout_session import WorkoutSession
from app.utils.uuid import generate_uuid


class WorkoutRepository:
    def get_session(
        self, db: Session, student_id: str, training_day_id: str, session_date: date
    ) -> WorkoutSession | None:
        return (
            db.query(WorkoutSession)
            .options(joinedload(WorkoutSession.exercise_completions))
            .filter(
                WorkoutSession.student_id == student_id,
                WorkoutSession.training_day_id == training_day_id,
                WorkoutSession.session_date == session_date,
            )
            .first()
        )

    def get_session_by_id(self, db: Session, session_id: str, student_id: str) -> WorkoutSession | None:
        return (
            db.query(WorkoutSession)
            .options(joinedload(WorkoutSession.exercise_completions))
            .filter(WorkoutSession.id == session_id, WorkoutSession.student_id == student_id)
            .first()
        )

    def create_session(
        self, db: Session, student_id: str, training_id: str, training_day_id: str, session_date: date
    ) -> WorkoutSession:
        session = WorkoutSession(
            id=generate_uuid(),
            student_id=student_id,
            training_id=training_id,
            training_day_id=training_day_id,
            session_date=session_date,
            status="in_progress",
        )
        db.add(session)
        db.flush()
        return session

    def mark_exercise_complete(
        self, db: Session, session: WorkoutSession, training_exercise_id: str
    ) -> ExerciseCompletion:
        existing = (
            db.query(ExerciseCompletion)
            .filter(
                ExerciseCompletion.workout_session_id == session.id,
                ExerciseCompletion.training_exercise_id == training_exercise_id,
            )
            .first()
        )
        if existing:
            return existing

        completion = ExerciseCompletion(
            id=generate_uuid(),
            workout_session_id=session.id,
            training_exercise_id=training_exercise_id,
        )
        db.add(completion)
        db.flush()
        return completion

    def complete_session(self, db: Session, session: WorkoutSession) -> WorkoutSession:
        session.status = "completed"
        session.completed_at = datetime.utcnow()
        db.flush()
        return session

    def list_sessions_by_student(
        self, db: Session, student_id: str, limit: int = 20
    ) -> list[WorkoutSession]:
        return (
            db.query(WorkoutSession)
            .filter(WorkoutSession.student_id == student_id)
            .order_by(WorkoutSession.session_date.desc())
            .limit(limit)
            .all()
        )
