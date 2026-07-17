from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.uuid import generate_uuid


class ExerciseCompletion(Base):
    __tablename__ = "exercise_completions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    workout_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("workout_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    training_exercise_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("training_exercises.id", ondelete="CASCADE"), nullable=False, index=True
    )
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    session = relationship("WorkoutSession", back_populates="exercise_completions")
    training_exercise = relationship("TrainingExercise")
