from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.uuid import generate_uuid


class Training(Base):
    __tablename__ = "trainings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    admin_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("student_profiles.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("training_categories.id", ondelete="SET NULL"), nullable=True, index=True)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("draft", "active", "completed", "cancelled", name="training_status"),
        default="draft",
        nullable=False,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    student = relationship("StudentProfile", back_populates="trainings")
    category = relationship("TrainingCategory", back_populates="trainings")
    days = relationship("TrainingDay", back_populates="training", cascade="all, delete-orphan", order_by="TrainingDay.sort_order")
    attendance_records = relationship("AttendanceRecord", back_populates="training")
