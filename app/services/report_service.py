from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.repositories.attendance_repository import AttendanceRepository, ProgressRepository
from app.repositories.student_repository import StudentRepository
from app.repositories.training_repository import TrainingRepository
from app.schemas.report import (
    AttendanceReportItem,
    AttendanceReportResponse,
    AttendanceTimelineItem,
    ProgressPhotoItem,
    ReportsOverviewResponse,
    StudentMonitoringDetailResponse,
    StudentMonitoringListResponse,
    StudentMonitoringSummary,
    StudentReportAttendance,
    StudentReportProgress,
    StudentReportResponse,
    StudentReportTraining,
    WeightHistoryItem,
)
from app.services import training_service
from app.services.training_service import _to_list_item

student_repo = StudentRepository()
training_repo = TrainingRepository()
attendance_repo = AttendanceRepository()
progress_repo = ProgressRepository()


def _photo_url(file_path: str) -> str:
    return f"/api/v1/uploads/{file_path}"


def _expected_sessions(db: Session, training, period_start: date, period_end: date) -> int:
    if training is None:
        return 0
    days_per_week = training_repo.count_days_per_week(db, training.id) or 1
    start = max(period_start, training.start_date)
    end = min(period_end, training.end_date)
    if end < start:
        return 0
    weeks = max((end - start).days // 7, 1)
    return days_per_week * weeks


def _attendance_rate(check_ins: int, expected: int) -> float:
    if expected <= 0:
        return 0.0
    return round(min(check_ins / expected * 100, 100), 1)


def _weight_delta(db: Session, student_id: str, profile) -> tuple[float | None, float | None, float | None]:
    initial = float(profile.weight_kg) if profile.weight_kg is not None else None
    photos, _ = progress_repo.list_photos(db, student_id, 1, 50)
    latest = initial
    for photo in photos:
        if photo.weight_kg is not None:
            latest = float(photo.weight_kg)
            break
    delta = round(latest - initial, 2) if initial is not None and latest is not None else None
    return initial, latest, delta


def overview(db: Session, admin_id: str) -> ReportsOverviewResponse:
    total = student_repo.count_total_students(db, admin_id)
    active = student_repo.count_active_students(db, admin_id)
    with_training = training_repo.count_students_with_active_training(db, admin_id)
    expiring = training_repo.count_expiring_soon(db, admin_id)
    check_ins_week = attendance_repo.count_this_week_by_admin(db, admin_id)
    check_ins_week_per_day = attendance_repo.count_this_week_by_admin_per_day(db, admin_id)
    photos_month = progress_repo.count_photos_this_month_by_admin(db, admin_id)

    week_start = date.today() - timedelta(days=date.today().weekday())
    week_end = week_start + timedelta(days=6)
    profiles, _ = student_repo.list_by_admin(db, admin_id, 1, 1000)
    rates = []
    for profile in profiles:
        training = training_repo.get_active_for_student(db, profile.user_id)
        expected = _expected_sessions(db,training, week_start, week_end)
        check_ins = attendance_repo.count_by_student(db, profile.user_id, week_start, week_end)
        if expected > 0:
            rates.append(_attendance_rate(check_ins, expected))

    avg_rate = round(sum(rates) / len(rates), 1) if rates else 0.0

    return ReportsOverviewResponse(
        total_students=total,
        active_students=active,
        students_with_active_training=with_training,
        trainings_expiring_soon=expiring,
        avg_weekly_attendance_pct=avg_rate,
        check_ins_this_week=check_ins_week,
        check_ins_this_week_per_day=check_ins_week_per_day,
        new_progress_photos_this_month=photos_month,
    )


def list_students_monitoring(db: Session, admin_id: str) -> StudentMonitoringListResponse:
    """Lista todos os alunos com resumo para a guia de relatórios."""
    profiles, total = student_repo.list_by_admin(db, admin_id, 1, 1000)
    month_start = date.today().replace(day=1)
    today = date.today()

    items: list[StudentMonitoringSummary] = []
    for profile in profiles:
        training = training_repo.get_active_for_student(db, profile.user_id)
        active_item = _to_list_item(training) if training else None
        expected = _expected_sessions(db,training, month_start, today)
        check_ins = attendance_repo.count_by_student(db, profile.user_id, month_start, today)
        _, _, delta = _weight_delta(db, profile.user_id, profile)

        items.append(
            StudentMonitoringSummary(
                student_id=profile.user_id,
                full_name=profile.full_name,
                email=profile.user.email,
                goal=profile.goal,
                is_active=profile.user.is_active,
                active_training=active_item,
                total_check_ins=attendance_repo.count_by_student(db, profile.user_id),
                attendance_rate_pct=_attendance_rate(check_ins, expected),
                photos_count=progress_repo.count_photos(db, profile.user_id),
                weight_delta_kg=delta,
                last_check_in=student_repo.last_check_in(db, profile.user_id),
            )
        )

    return StudentMonitoringListResponse(items=items, total=total)


def student_monitoring_detail(db: Session, admin_id: str, student_id: str) -> StudentMonitoringDetailResponse:
    """Acompanhamento individual completo — treino por dia, frequência, fotos e evolução."""
    profile = student_repo.get_by_id(db, student_id, admin_id)
    if profile is None:
        raise NotFoundError("Aluno não encontrado.")

    month_start = date.today().replace(day=1)
    today = date.today()

    training = training_repo.get_active_for_student(db, student_id)
    current_item = _to_list_item(training) if training else None
    schedule = []
    if training:
        detail = training_service.get_training(db, admin_id, training.id)
        schedule = detail.days

    expected = _expected_sessions(db,training, month_start, today)
    check_ins_month = attendance_repo.count_by_student(db, student_id, month_start, today)
    check_ins_total = attendance_repo.count_by_student(db, student_id)

    initial, latest, delta = _weight_delta(db, student_id, profile)

    records, _ = attendance_repo.list_by_student(db, student_id, 1, 30)
    timeline = [
        AttendanceTimelineItem(
            check_in_date=r.check_in_date,
            checked_in_at=r.checked_in_at,
            training_title=r.training.title,
        )
        for r in records
    ]

    photos, _ = progress_repo.list_photos(db, student_id, 1, 20)
    photo_items = [
        ProgressPhotoItem(
            id=p.id,
            url=_photo_url(p.file_path),
            photo_type=p.photo_type,
            weight_kg=float(p.weight_kg) if p.weight_kg is not None else None,
            taken_at=p.taken_at,
        )
        for p in photos
    ]

    weight_history: list[WeightHistoryItem] = []
    if initial is not None:
        weight_history.append(WeightHistoryItem(date=profile.user.created_at.date(), weight_kg=initial, source="profile"))
    for p in reversed(photos):
        if p.weight_kg is not None:
            weight_history.append(
                WeightHistoryItem(date=p.taken_at, weight_kg=float(p.weight_kg), source="photo")
            )

    all_trainings = training_repo.list_by_student(db, admin_id, student_id)
    history_items = [_to_list_item(t) for t in all_trainings if t.status != "active"]

    return StudentMonitoringDetailResponse(
        student={
            "id": profile.user_id,
            "full_name": profile.full_name,
            "email": profile.user.email,
            "phone": profile.phone,
            "goal": profile.goal,
            "height_cm": float(profile.height_cm) if profile.height_cm else None,
            "weight_kg": initial,
            "birth_date": profile.birth_date.isoformat() if profile.birth_date else None,
        },
        current_training=current_item,
        training_schedule=schedule,
        attendance={
            "total_check_ins": check_ins_total,
            "check_ins_this_month": check_ins_month,
            "expected_sessions_this_month": expected,
            "rate_pct": _attendance_rate(check_ins_month, expected),
        },
        progress={
            "initial_weight_kg": initial,
            "latest_weight_kg": latest,
            "weight_delta_kg": delta,
            "photos_count": len(photo_items),
        },
        attendance_timeline=timeline,
        progress_photos=photo_items,
        weight_history=weight_history,
        trainings_history=history_items,
    )


def student_report(db: Session, admin_id: str, student_id: str) -> StudentReportResponse:
    profile = student_repo.get_by_id(db, student_id, admin_id)
    if profile is None:
        raise NotFoundError()

    training = training_repo.get_active_for_student(db, student_id)
    current = None
    if training:
        today = date.today()
        total_days = (training.end_date - training.start_date).days or 1
        elapsed = max((today - training.start_date).days, 0)
        remaining = max((training.end_date - today).days, 0)
        current = StudentReportTraining(
            title=training.title,
            start_date=training.start_date,
            end_date=training.end_date,
            days_remaining=remaining,
            completion_pct=round(min(elapsed / total_days * 100, 100), 1),
        )

    month_start = date.today().replace(day=1)
    expected = _expected_sessions(db,training, month_start, date.today())
    check_ins = attendance_repo.count_by_student(db, student_id, month_start, date.today())
    initial, latest, delta = _weight_delta(db, student_id, profile)

    return StudentReportResponse(
        student={"id": profile.user_id, "full_name": profile.full_name, "goal": profile.goal},
        current_training=current,
        attendance=StudentReportAttendance(
            total_check_ins=attendance_repo.count_by_student(db, student_id),
            expected_sessions=expected,
            rate_pct=_attendance_rate(check_ins, expected),
        ),
        progress=StudentReportProgress(
            initial_weight_kg=initial,
            latest_weight_kg=latest,
            weight_delta_kg=delta,
            photos_count=progress_repo.count_photos(db, student_id),
        ),
    )


def attendance_report(
    db: Session, admin_id: str, start_date: date | None, end_date: date | None, student_id: str | None = None
) -> AttendanceReportResponse:
    start = start_date or date.today().replace(day=1)
    end = end_date or date.today()

    profiles, _ = student_repo.list_by_admin(db, admin_id, 1, 1000)
    if student_id:
        profiles = [p for p in profiles if p.user_id == student_id]

    items = []
    for profile in profiles:
        training = training_repo.get_active_for_student(db, profile.user_id)
        expected = _expected_sessions(db,training, start, end)
        check_ins = attendance_repo.count_by_student(db, profile.user_id, start, end)
        items.append(
            AttendanceReportItem(
                student_id=profile.user_id,
                student_name=profile.full_name,
                check_ins=check_ins,
                expected=expected,
                rate_pct=_attendance_rate(check_ins, expected),
            )
        )

    return AttendanceReportResponse(period={"start": start.isoformat(), "end": end.isoformat()}, items=items)
