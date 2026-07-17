from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.utils.uuid import generate_uuid


class ProgressMetric(Base):
    __tablename__ = "progress_metrics"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("student_profiles.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    metric_date: Mapped[date] = mapped_column(Date, nullable=False)
    weight_kg: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    body_fat_pct: Mapped[float | None] = mapped_column(Numeric(4, 2), nullable=True)
    measurements: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=False), server_default=func.now(), nullable=False)

    student = relationship("StudentProfile", back_populates="progress_metrics")
