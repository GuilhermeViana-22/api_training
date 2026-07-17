from datetime import date, datetime

from pydantic import BaseModel, Field, field_validator


class TrainingExerciseInput(BaseModel):
    exercise_id: str
    sets: int = Field(ge=1)
    reps: int = Field(ge=1)
    load_kg: float | None = Field(default=None, ge=0)
    rest_seconds: int | None = Field(default=None, ge=0)
    sort_order: int = 0
    notes: str | None = None


class TrainingDayInput(BaseModel):
    day_of_week: int = Field(ge=0, le=6, description="0=Segunda ... 6=Domingo")
    label: str | None = None
    notes: str | None = None
    sort_order: int = 0
    exercises: list[TrainingExerciseInput] = Field(min_length=1)


class TrainingCompleteCreate(BaseModel):
    """Cadastra treino completo para um aluno: metadados + dias da semana + exercícios."""

    student_id: str = Field(description="UUID do aluno (cada aluno possui treino independente)")
    title: str = Field(min_length=2, max_length=150)
    description: str | None = None
    category_id: str | None = Field(default=None, description="Categoria: musculação, cardio, calistenia")
    start_date: date
    end_date: date
    days: list[TrainingDayInput] = Field(min_length=1, description="Dias da semana com exercícios")
    activate: bool = Field(default=False, description="Se true, ativa o treino após criar")

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, end_date: date, info) -> date:
        start_date = info.data.get("start_date")
        if start_date and end_date < start_date:
            raise ValueError("Data final deve ser posterior ou igual à data inicial.")
        return end_date

    @field_validator("days")
    @classmethod
    def validate_unique_days(cls, days: list[TrainingDayInput]) -> list[TrainingDayInput]:
        dow = [d.day_of_week for d in days]
        if len(dow) != len(set(dow)):
            raise ValueError("Não pode haver dois dias com o mesmo day_of_week.")
        return days


class TrainingCreate(BaseModel):
    student_id: str
    title: str = Field(min_length=2, max_length=150)
    description: str | None = None
    category_id: str | None = None
    start_date: date
    end_date: date

    @field_validator("end_date")
    @classmethod
    def validate_date_range(cls, end_date: date, info) -> date:
        start_date = info.data.get("start_date")
        if start_date and end_date < start_date:
            raise ValueError("Data final deve ser posterior ou igual à data inicial.")
        return end_date


class TrainingUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=2, max_length=150)
    description: str | None = None
    category_id: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: str | None = None


class TrainingDayCreate(BaseModel):
    day_of_week: int = Field(ge=0, le=6)
    label: str | None = None
    notes: str | None = None
    sort_order: int = 0


class TrainingDayUpdate(BaseModel):
    day_of_week: int | None = Field(default=None, ge=0, le=6)
    label: str | None = None
    notes: str | None = None
    sort_order: int | None = None


class TrainingExerciseCreate(BaseModel):
    exercise_id: str
    sets: int = Field(ge=1)
    reps: int = Field(ge=1)
    load_kg: float | None = Field(default=None, ge=0)
    rest_seconds: int | None = Field(default=None, ge=0)
    sort_order: int = 0
    notes: str | None = None


class TrainingExerciseUpdate(BaseModel):
    sets: int | None = Field(default=None, ge=1)
    reps: int | None = Field(default=None, ge=1)
    load_kg: float | None = Field(default=None, ge=0)
    rest_seconds: int | None = Field(default=None, ge=0)
    sort_order: int | None = None
    notes: str | None = None


class TrainingExerciseResponse(BaseModel):
    id: str
    exercise_id: str
    exercise_name: str
    sets: int
    reps: int
    load_kg: float | None = None
    rest_seconds: int | None = None
    sort_order: int = 0
    notes: str | None = None
    images: list[dict] = Field(default_factory=list)


class TrainingDayResponse(BaseModel):
    id: str
    day_of_week: int
    day_name: str
    label: str | None = None
    notes: str | None = None
    sort_order: int = 0
    exercises: list[TrainingExerciseResponse] = Field(default_factory=list)


class TrainingListItem(BaseModel):
    id: str
    student_id: str
    student_name: str
    student_email: str | None = None
    title: str
    category: dict | None = None
    start_date: date
    end_date: date
    status: str
    days_count: int = 0
    exercises_count: int = 0
    created_at: datetime


class StudentTrainingSummary(BaseModel):
    """Resumo de treinos de um aluno específico."""

    student_id: str
    student_name: str
    student_email: str
    active_training: TrainingListItem | None = None
    trainings: list[TrainingListItem] = Field(default_factory=list)


class TrainingDetailResponse(BaseModel):
    id: str
    student_id: str
    student_name: str
    student_email: str | None = None
    title: str
    description: str | None = None
    category: dict | None = None
    start_date: date
    end_date: date
    status: str
    days: list[TrainingDayResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
