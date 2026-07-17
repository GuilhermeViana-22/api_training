from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.uuid import generate_uuid


class TrainingExercise(Base):
    __tablename__ = "training_exercises"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    training_day_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("training_days.id", ondelete="CASCADE"), nullable=False, index=True
    )
    exercise_id: Mapped[str] = mapped_column(String(36), ForeignKey("exercises.id", ondelete="RESTRICT"), nullable=False)
    sets: Mapped[int] = mapped_column(Integer, nullable=False)
    reps: Mapped[int] = mapped_column(Integer, nullable=False)
    load_kg: Mapped[float | None] = mapped_column(Numeric(6, 2), nullable=True)
    rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    training_day = relationship("TrainingDay", back_populates="exercises")
    exercise = relationship("Exercise", back_populates="training_exercises")
