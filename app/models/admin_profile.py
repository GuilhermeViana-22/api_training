from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class AdminProfile(Base):
    __tablename__ = "admin_profiles"

    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(150), nullable=False)
    cref: Mapped[str | None] = mapped_column(String(20), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    bio: Mapped[str | None] = mapped_column(Text, nullable=True)

    user = relationship("User", back_populates="admin_profile")
