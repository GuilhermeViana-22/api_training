from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.uuid import generate_uuid


class WorkoutSession(Base):
    __tablename__ = "workout_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("student_profiles.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    training_id: Mapped[str] = mapped_column(String(36), ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False)
    training_day_id: Mapped[str] = mapped_column(String(36), ForeignKey("training_days.id", ondelete="CASCADE"), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        Enum("in_progress", "completed", name="workout_session_status"), default="in_progress", nullable=False
    )
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    training_day = relationship("TrainingDay")
    training = relationship("Training")
    exercise_completions = relationship("ExerciseCompletion", back_populates="session", cascade="all, delete-orphan")
