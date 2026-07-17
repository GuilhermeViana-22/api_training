from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.uuid import generate_uuid


class ExerciseImage(Base):
    __tablename__ = "exercise_images"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    exercise_id: Mapped[str] = mapped_column(String(36), ForeignKey("exercises.id", ondelete="CASCADE"), nullable=False, index=True)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    media_type: Mapped[str] = mapped_column(Enum("image", "video", name="media_type"), default="image", nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    exercise = relationship("Exercise", back_populates="images")
