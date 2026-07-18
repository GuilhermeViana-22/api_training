from datetime import date, datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.attendance_record import AttendanceRecord
from app.models.progress_photo import ProgressPhoto
from app.utils.uuid import generate_uuid


class AttendanceRepository:
    def get_by_student_date(self, db: Session, student_id: str, check_in_date: date) -> AttendanceRecord | None:
        return (
            db.query(AttendanceRecord)
            .filter(AttendanceRecord.student_id == student_id, AttendanceRecord.check_in_date == check_in_date)
            .first()
        )

    def create(self, db: Session, student_id: str, training_id: str, check_in_date: date, notes: str | None = None) -> AttendanceRecord:
        record = AttendanceRecord(
            id=generate_uuid(),
            student_id=student_id,
            training_id=training_id,
            check_in_date=check_in_date,
            notes=notes,
        )
        db.add(record)
        db.flush()
        return record

    def list_by_student(
        self, db: Session, student_id: str, page: int, limit: int, start_date: date | None = None, end_date: date | None = None
    ) -> tuple[list[AttendanceRecord], int]:
        query = db.query(AttendanceRecord).filter(AttendanceRecord.student_id == student_id)
        if start_date:
            query = query.filter(AttendanceRecord.check_in_date >= start_date)
        if end_date:
            query = query.filter(AttendanceRecord.check_in_date <= end_date)

        total = query.count()
        items = query.order_by(AttendanceRecord.check_in_date.desc()).offset((page - 1) * limit).limit(limit).all()
        return items, total

    def count_by_student(self, db: Session, student_id: str, start_date: date | None = None, end_date: date | None = None) -> int:
        query = db.query(func.count(AttendanceRecord.id)).filter(AttendanceRecord.student_id == student_id)
        if start_date:
            query = query.filter(AttendanceRecord.check_in_date >= start_date)
        if end_date:
            query = query.filter(AttendanceRecord.check_in_date <= end_date)
        return query.scalar() or 0

    def count_by_training(self, db: Session, training_id: str) -> int:
        return db.query(func.count(AttendanceRecord.id)).filter(AttendanceRecord.training_id == training_id).scalar() or 0

    def count_this_week_by_admin(self, db: Session, admin_id: str) -> int:
        from app.models.student_profile import StudentProfile

        week_start = date.today() - timedelta(days=date.today().weekday())
        return (
            db.query(func.count(AttendanceRecord.id))
            .join(StudentProfile, StudentProfile.user_id == AttendanceRecord.student_id)
            .filter(StudentProfile.admin_id == admin_id, AttendanceRecord.check_in_date >= week_start)
            .scalar()
            or 0
        )

    def count_this_week_by_admin_per_day(self, db: Session, admin_id: str) -> list[int]:
        """Check-ins da semana atual (seg..dom), um total por dia."""
        from app.models.student_profile import StudentProfile

        week_start = date.today() - timedelta(days=date.today().weekday())
        rows = (
            db.query(AttendanceRecord.check_in_date, func.count(AttendanceRecord.id))
            .join(StudentProfile, StudentProfile.user_id == AttendanceRecord.student_id)
            .filter(StudentProfile.admin_id == admin_id, AttendanceRecord.check_in_date >= week_start)
            .group_by(AttendanceRecord.check_in_date)
            .all()
        )
        counts_by_date = {check_in_date: total for check_in_date, total in rows}
        return [counts_by_date.get(week_start + timedelta(days=offset), 0) for offset in range(7)]

    def recent_by_student(self, db: Session, student_id: str, limit: int = 10) -> list[AttendanceRecord]:
        return (
            db.query(AttendanceRecord)
            .filter(AttendanceRecord.student_id == student_id)
            .order_by(AttendanceRecord.check_in_date.desc())
            .limit(limit)
            .all()
        )


class ProgressRepository:
    def create_photo(self, db: Session, student_id: str, file_path: str, **kwargs) -> ProgressPhoto:
        photo = ProgressPhoto(id=generate_uuid(), student_id=student_id, file_path=file_path, **kwargs)
        db.add(photo)
        db.flush()
        return photo

    def list_day_photos(
        self, db: Session, student_id: str, training_id: str, day_of_week: int, limit: int = 10
    ) -> list[ProgressPhoto]:
        return (
            db.query(ProgressPhoto)
            .filter(
                ProgressPhoto.student_id == student_id,
                ProgressPhoto.training_id == training_id,
                ProgressPhoto.day_of_week == day_of_week,
            )
            .order_by(ProgressPhoto.taken_at.desc())
            .limit(limit)
            .all()
        )

    def list_photos(
        self, db: Session, student_id: str, page: int, limit: int, start_date: date | None = None, end_date: date | None = None
    ) -> tuple[list[ProgressPhoto], int]:
        query = db.query(ProgressPhoto).filter(ProgressPhoto.student_id == student_id)
        if start_date:
            query = query.filter(ProgressPhoto.taken_at >= start_date)
        if end_date:
            query = query.filter(ProgressPhoto.taken_at <= end_date)

        total = query.count()
        items = query.order_by(ProgressPhoto.taken_at.desc()).offset((page - 1) * limit).limit(limit).all()
        return items, total

    def count_photos(self, db: Session, student_id: str) -> int:
        return db.query(func.count(ProgressPhoto.id)).filter(ProgressPhoto.student_id == student_id).scalar() or 0

    def last_photo_date(self, db: Session, student_id: str) -> date | None:
        return db.query(func.max(ProgressPhoto.taken_at)).filter(ProgressPhoto.student_id == student_id).scalar()

    def count_photos_this_month_by_admin(self, db: Session, admin_id: str) -> int:
        from app.models.student_profile import StudentProfile

        today = date.today()
        month_start = today.replace(day=1)
        return (
            db.query(func.count(ProgressPhoto.id))
            .join(StudentProfile, StudentProfile.user_id == ProgressPhoto.student_id)
            .filter(StudentProfile.admin_id == admin_id, ProgressPhoto.taken_at >= month_start)
            .scalar()
            or 0
        )

    def list_metrics(self, db: Session, student_id: str) -> list:
        from app.models.progress_metric import ProgressMetric

        return (
            db.query(ProgressMetric)
            .filter(ProgressMetric.student_id == student_id)
            .order_by(ProgressMetric.metric_date.desc())
            .all()
        )
