from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class StudentProfile(Base):
    __tablename__ = "student_profiles"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    admin_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    birth_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    height_cm: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    goal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)

    user = relationship("User", back_populates="student_profile", foreign_keys=[user_id])
    trainings = relationship("Training", back_populates="student")
    attendance_records = relationship("AttendanceRecord", back_populates="student")
    progress_photos = relationship("ProgressPhoto", back_populates="student")
    progress_metrics = relationship("ProgressMetric", back_populates="student")
