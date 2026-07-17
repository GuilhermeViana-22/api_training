from datetime import date, datetime

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.attendance_record import AttendanceRecord
from app.models.student_profile import StudentProfile
from app.models.training import Training
from app.models.user import User
from app.utils.uuid import generate_uuid


class StudentRepository:
    def get_by_id(self, db: Session, student_id: str, admin_id: str | None = None) -> StudentProfile | None:
        query = (
            db.query(StudentProfile)
            .options(joinedload(StudentProfile.user))
            .filter(StudentProfile.user_id == student_id, StudentProfile.deleted_at.is_(None))
        )
        if admin_id:
            query = query.filter(StudentProfile.admin_id == admin_id)
        return query.first()

    def list_by_admin(
        self, db: Session, admin_id: str, page: int, limit: int, search: str | None = None, is_active: bool | None = None
    ) -> tuple[list[StudentProfile], int]:
        query = (
            db.query(StudentProfile)
            .options(joinedload(StudentProfile.user))
            .join(User, User.id == StudentProfile.user_id)
            .filter(StudentProfile.admin_id == admin_id, StudentProfile.deleted_at.is_(None))
        )
        if search:
            like = f"%{search}%"
            query = query.filter(or_(StudentProfile.full_name.ilike(like), User.email.ilike(like)))
        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        total = query.count()
        items = (
            query.options(joinedload(StudentProfile.user))
            .order_by(StudentProfile.full_name.asc())
            .offset((page - 1) * limit)
            .limit(limit)
            .all()
        )
        return items, total

    def create(self, db: Session, user_id: str, admin_id: str, **kwargs) -> StudentProfile:
        profile = StudentProfile(user_id=user_id, admin_id=admin_id, **kwargs)
        db.add(profile)
        db.flush()
        return profile

    def update_profile(self, db: Session, profile: StudentProfile, **kwargs) -> StudentProfile:
        for field, value in kwargs.items():
            if value is not None:
                setattr(profile, field, value)
        db.flush()
        return profile

    def soft_delete(self, db: Session, profile: StudentProfile) -> None:
        now = datetime.utcnow()
        profile.deleted_at = now
        profile.user.deleted_at = now
        profile.user.is_active = False

    def count_trainings(self, db: Session, student_id: str) -> int:
        return db.query(func.count(Training.id)).filter(Training.student_id == student_id).scalar() or 0

    def last_check_in(self, db: Session, student_id: str) -> date | None:
        return (
            db.query(func.max(AttendanceRecord.check_in_date))
            .filter(AttendanceRecord.student_id == student_id)
            .scalar()
        )

    def count_active_students(self, db: Session, admin_id: str) -> int:
        return (
            db.query(func.count(StudentProfile.user_id))
            .join(User, User.id == StudentProfile.user_id)
            .filter(
                StudentProfile.admin_id == admin_id,
                StudentProfile.deleted_at.is_(None),
                User.is_active.is_(True),
            )
            .scalar()
            or 0
        )

    def count_total_students(self, db: Session, admin_id: str) -> int:
        return (
            db.query(func.count(StudentProfile.user_id))
            .filter(StudentProfile.admin_id == admin_id, StudentProfile.deleted_at.is_(None))
            .scalar()
            or 0
        )
