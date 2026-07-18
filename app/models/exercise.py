from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.uuid import generate_uuid


class Exercise(Base):
    __tablename__ = "exercises"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    admin_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    muscle_group: Mapped[str | None] = mapped_column(String(50), nullable=True)
    default_sets: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_reps: Mapped[int | None] = mapped_column(Integer, nullable=True)
    default_rest_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    images = relationship(
        "ExerciseImage",
        back_populates="exercise",
        cascade="all, delete-orphan",
        order_by="[ExerciseImage.is_featured.desc(), ExerciseImage.sort_order]",
    )
    training_exercises = relationship("TrainingExercise", back_populates="exercise")
