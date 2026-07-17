from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.uuid import generate_uuid


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"
    __table_args__ = (UniqueConstraint("student_id", "check_in_date", name="uk_attendance_student_date"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("student_profiles.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    training_id: Mapped[str] = mapped_column(String(36), ForeignKey("trainings.id", ondelete="CASCADE"), nullable=False)
    check_in_date: Mapped[date] = mapped_column(Date, nullable=False)
    checked_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    student = relationship("StudentProfile", back_populates="attendance_records")
    training = relationship("Training", back_populates="attendance_records")
