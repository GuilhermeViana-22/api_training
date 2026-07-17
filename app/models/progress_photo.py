from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Numeric, SmallInteger, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.uuid import generate_uuid


class ProgressPhoto(Base):
    __tablename__ = "progress_photos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("student_profiles.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    training_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("trainings.id", ondelete="SET NULL"), nullable=True)
    day_of_week: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    photo_type: Mapped[str] = mapped_column(
        Enum("front", "side", "back", "other", name="photo_type"), default="other", nullable=False
    )
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    taken_at: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    student = relationship("StudentProfile", back_populates="progress_photos")
