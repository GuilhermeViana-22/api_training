from datetime import date, datetime

from pydantic import BaseModel, Field


class TrainingCategoryResponse(BaseModel):
    id: str
    slug: str
    name: str
    description: str | None = None
    sort_order: int = 0


class TrainingCategoryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None
    sort_order: int = 0


class TrainingCategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None
    sort_order: int | None = None


class ExerciseCompletionStatus(BaseModel):
    training_exercise_id: str
    exercise_name: str
    sets: int
    reps: int
    load_kg: float | None = None
    completed: bool = False
    completed_at: datetime | None = None


class WorkoutSessionResponse(BaseModel):
    id: str
    training_id: str
    training_day_id: str
    day_of_week: int
    day_name: str
    session_date: date
    status: str
    exercises_total: int = 0
    exercises_completed: int = 0
    exercises: list[ExerciseCompletionStatus] = Field(default_factory=list)
    started_at: datetime
    completed_at: datetime | None = None


class CompleteExerciseRequest(BaseModel):
    training_exercise_id: str


class StudentDayTrainingExtended(BaseModel):
    day_of_week: int
    day_name: str
    label: str | None = None
    training: dict
    exercises: list[dict]
    session: WorkoutSessionResponse | None = None
    checked_in_today: bool = False
    day_completed: bool = False
