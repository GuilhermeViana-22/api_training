from sqlalchemy import ForeignKey, Integer, SmallInteger, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.uuid import generate_uuid


class TrainingDay(Base):
    __tablename__ = "training_days"
    __table_args__ = (UniqueConstraint("training_id", "day_of_week", name="uk_training_days_training_dow"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    training_id: Mapped[str] = mapped_column(String(36), ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False)
    day_of_week: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    training = relationship("Training", back_populates="days")
    exercises = relationship(
        "TrainingExercise", back_populates="training_day", cascade="all, delete-orphan", order_by="TrainingExercise.sort_order"
    )
