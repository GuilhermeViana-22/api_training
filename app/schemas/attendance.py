from datetime import date, datetime

from pydantic import BaseModel, Field


class CheckInRequest(BaseModel):
    notes: str | None = None


class CheckInResponse(BaseModel):
    id: str
    check_in_date: date
    checked_in_at: datetime
    training_id: str
    training_title: str


class AttendanceSummary(BaseModel):
    total_check_ins: int
    period_start: date | None = None
    period_end: date | None = None
    attendance_rate_pct: float = 0.0


class AttendanceItem(BaseModel):
    id: str
    check_in_date: date
    checked_in_at: datetime
    training_id: str
    training_title: str


class AttendanceListResponse(BaseModel):
    student_id: str
    summary: AttendanceSummary
    items: list[AttendanceItem]
    pagination: dict


class ProgressPhotoResponse(BaseModel):
    id: str
    url: str
    photo_type: str
    weight_kg: float | None = None
    notes: str | None = None
    taken_at: date
    created_at: datetime
    training_id: str | None = None
    day_of_week: int | None = None


class ProgressMetricResponse(BaseModel):
    id: str
    metric_date: date
    weight_kg: float | None = None
    body_fat_pct: float | None = None
    measurements: dict | None = None


class StudentProgressSummary(BaseModel):
    latest_weight_kg: float | None = None
    initial_weight_kg: float | None = None
    weight_delta_kg: float | None = None
    photos_count: int = 0
    last_photo_at: date | None = None
    check_ins_total: int = 0


class HistoryTrainingItem(BaseModel):
    id: str
    title: str
    start_date: date
    end_date: date
    status: str


class HistoryCheckInItem(BaseModel):
    check_in_date: date
    training_title: str


class HistoryResponse(BaseModel):
    trainings: list[HistoryTrainingItem]
    recent_check_ins: list[HistoryCheckInItem]


class StudentDayTrainingResponse(BaseModel):
    day_of_week: int
    day_name: str
    label: str | None = None
    training: dict
    exercises: list[dict]
    checked_in_today: bool = False
    day_completed: bool = False
    session: dict | None = None
    day_photos: list[dict] = Field(default_factory=list)


class StudentTrainingOverview(BaseModel):
    id: str
    title: str
    description: str | None = None
    category: dict | None = None
    start_date: date
    end_date: date
    status: str
    days: list[dict]
    created_at: datetime
    updated_at: datetime
