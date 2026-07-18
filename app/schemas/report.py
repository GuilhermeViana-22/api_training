from datetime import date, datetime

from pydantic import BaseModel, Field

from app.schemas.training import TrainingDayResponse, TrainingListItem


class StudentOption(BaseModel):
    """Aluno para seleção no cadastro de treino."""

    id: str
    full_name: str
    email: str
    is_active: bool
    has_active_training: bool
    active_training_title: str | None = None


class StudentMonitoringSummary(BaseModel):
    """Resumo na guia de relatórios — um card por aluno."""

    student_id: str
    full_name: str
    email: str
    goal: str | None = None
    is_active: bool
    active_training: TrainingListItem | None = None
    total_check_ins: int = 0
    attendance_rate_pct: float = 0.0
    photos_count: int = 0
    weight_delta_kg: float | None = None
    last_check_in: date | None = None


class StudentMonitoringListResponse(BaseModel):
    items: list[StudentMonitoringSummary]
    total: int


class AttendanceTimelineItem(BaseModel):
    check_in_date: date
    checked_in_at: datetime
    training_title: str


class ProgressPhotoItem(BaseModel):
    id: str
    url: str
    photo_type: str
    weight_kg: float | None = None
    taken_at: date


class WeightHistoryItem(BaseModel):
    date: date
    weight_kg: float
    source: str  # "photo" | "profile" | "metric"


class StudentMonitoringDetailResponse(BaseModel):
    """Acompanhamento individual completo do aluno."""

    student: dict
    current_training: TrainingListItem | None = None
    training_schedule: list[TrainingDayResponse] = Field(default_factory=list)
    attendance: dict
    progress: dict
    attendance_timeline: list[AttendanceTimelineItem] = Field(default_factory=list)
    progress_photos: list[ProgressPhotoItem] = Field(default_factory=list)
    weight_history: list[WeightHistoryItem] = Field(default_factory=list)
    trainings_history: list[TrainingListItem] = Field(default_factory=list)


class ReportsOverviewResponse(BaseModel):
    total_students: int
    active_students: int
    students_with_active_training: int
    trainings_expiring_soon: int
    avg_weekly_attendance_pct: float
    check_ins_this_week: int
    check_ins_this_week_per_day: list[int]
    new_progress_photos_this_month: int


class StudentReportTraining(BaseModel):
    title: str
    start_date: date
    end_date: date
    days_remaining: int
    completion_pct: float


class StudentReportAttendance(BaseModel):
    total_check_ins: int
    expected_sessions: int
    rate_pct: float


class StudentReportProgress(BaseModel):
    initial_weight_kg: float | None = None
    latest_weight_kg: float | None = None
    weight_delta_kg: float | None = None
    photos_count: int = 0


class StudentReportResponse(BaseModel):
    student: dict
    current_training: StudentReportTraining | None = None
    attendance: StudentReportAttendance
    progress: StudentReportProgress


class AttendanceReportItem(BaseModel):
    student_id: str
    student_name: str
    check_ins: int
    expected: int
    rate_pct: float


class AttendanceReportResponse(BaseModel):
    period: dict
    items: list[AttendanceReportItem]
